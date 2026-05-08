"""
Tests for POST /api/v1/chat (B2B chat endpoint).

Strategy:
- All external services (CreditService, CacheService, RagService, ModelRouter,
  ImageService, CosmosRepo) are patched at the module level in api_v1.chat.
- verify_api_key and rate_limit are overridden via dependency_overrides.
- TestClient provides synchronous request/response cycle.
"""

import base64
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.middleware.api_key_auth import verify_api_key
from app.middleware.rate_limiter import rate_limit
from app.models.client import Client
from app.routes.api_v1.chat import ChatRequest, ChatResponse, router


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_client(**overrides) -> Client:
    defaults = dict(
        client_id="clnt_test_school",
        org_name="Test School",
        contact_name="Test User",
        contact_phone="+919876543210",
        contact_email="test@school.com",
        api_key_hash="a" * 64,
        api_key_prefix="jvb_live_te",
        plan_tier="starter",
        credit_balance=10_000,
        credit_alert_threshold=2_000,
        is_active=True,
        rate_limit_per_minute=60,
        rate_limit_per_day=50_000,
        whatsapp_number="+919876543210",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Client(**defaults)


def _build_app(client: Client) -> FastAPI:
    """Minimal FastAPI app with the chat router mounted and auth bypassed."""
    app = FastAPI()

    async def _auth():
        return client

    async def _no_rate_limit():
        pass

    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(router, prefix="/chat")
    app.include_router(v1)

    app.dependency_overrides[verify_api_key] = _auth
    app.dependency_overrides[rate_limit] = _no_rate_limit
    return app


def _make_model_router_mock(
    answer: str = "Photosynthesis is the process by which plants make food.",
    tier: int = 1,
    sources: list | None = None,
    total_billable_tokens: int = 170,
) -> MagicMock:
    """Return a mock ModelRouter whose route_query_stream yields text + [METADATA]."""
    meta = {
        "content": answer,
        "model_used": "gpt-4.1-nano",
        "tier": tier,
        "tokens_input": 100,
        "tokens_output": 70,
        "tokens_total": 170,
        "from_cache": False,
        "confidence": "high",
        "sources": sources or [],
        "classification_tokens": 0,
        "embedding_tokens": 0,
        "total_billable_tokens": total_billable_tokens,
        "cost": 0.001,
    }

    async def _stream(*args, **kwargs):
        yield answer
        yield f"\n\n[METADATA]{json.dumps(meta)}"

    mock = MagicMock()
    mock.route_query_stream = _stream
    return mock


def _make_cache_miss() -> AsyncMock:
    return AsyncMock(return_value=None)


def _make_cache_hit() -> AsyncMock:
    """Simulate a verified-cache hit returning a CachedAnswer-like object."""
    from app.services.cache_service import CachedAnswer
    hit = CachedAnswer(
        cache_id="cache-001",
        question="What is photosynthesis?",
        answers={"en": "Plants make food using sunlight."},
        board="cbse",
        class_level=9,
        subject="Science",
        source_citation="NCERT Class 9 Science Ch.6",
    )
    return AsyncMock(return_value=hit)


def _make_rag_mock(confidence: str = "HIGH") -> AsyncMock:
    return AsyncMock(return_value={
        "context": "Photosynthesis occurs in chloroplasts...",
        "confidence": confidence,
        "confidence_score": 0.042,
    })


def _make_credit_mock(balance: int = 5000) -> MagicMock:
    mock = MagicMock()
    mock.check_and_reserve = AsyncMock(return_value=True)
    mock.deduct = AsyncMock(return_value=balance - 1)
    mock.get_balance = AsyncMock(return_value=balance)
    return mock


def _make_cosmos_mock() -> MagicMock:
    mock = MagicMock()
    mock.create_conversation = AsyncMock(return_value=None)
    mock.save_conversation = AsyncMock(return_value=None)
    mock.get_conversation_history = AsyncMock(return_value=[])
    return mock


# ── Helpers ───────────────────────────────────────────────────────────────────

_BASE_PAYLOAD = {
    "query": "What is photosynthesis?",
    "board": "cbse",
    "class_level": 9,
    "subject": "Science",
}

MODULE = "app.routes.api_v1.chat"


def _patch_all(
    credits=None,
    cache=None,
    rag=None,
    model_router=None,
    cosmos=None,
    image=None,
):
    """Return a context manager stack that patches all services."""
    import contextlib

    credits = credits or _make_credit_mock()
    cache = cache or _make_cache_miss()
    rag = rag or _make_rag_mock()
    model_router = model_router or _make_model_router_mock()
    cosmos = cosmos or _make_cosmos_mock()

    @contextlib.contextmanager
    def _ctx():
        with (
            patch(f"{MODULE}._credits", credits),
            patch(f"{MODULE}._cache.check_cache", cache),
            patch(f"{MODULE}._rag.get_context", rag),
            patch(f"{MODULE}._model_router", model_router),
            patch(f"{MODULE}._cosmos", cosmos),
        ):
            if image:
                with patch(f"{MODULE}._image", image):
                    yield
            else:
                yield

    return _ctx()


# ── Schema validation tests ───────────────────────────────────────────────────

class TestChatRequestValidation:
    def test_missing_query_and_image_raises(self):
        with pytest.raises(Exception, match="query.*image_base64|image_base64.*query|required"):
            ChatRequest(board="cbse", class_level=9)

    def test_query_alone_is_valid(self):
        req = ChatRequest(query="Hello", board="cbse", class_level=10)
        assert req.query == "Hello"

    def test_image_alone_is_valid(self):
        req = ChatRequest(image_base64="abc123==", board="gseb", class_level=8)
        assert req.image_base64 == "abc123=="

    def test_class_level_bounds(self):
        with pytest.raises(Exception):
            ChatRequest(query="Q", board="cbse", class_level=5)
        with pytest.raises(Exception):
            ChatRequest(query="Q", board="cbse", class_level=13)

    def test_invalid_board_raises(self):
        with pytest.raises(Exception):
            ChatRequest(query="Q", board="icse", class_level=10)

    def test_stream_defaults_false(self):
        req = ChatRequest(query="Q", board="cbse", class_level=10)
        assert req.stream is False

    def test_language_auto_detect_when_none(self):
        req = ChatRequest(query="Q", board="cbse", class_level=10)
        assert req.language is None


# ── Language detection unit tests ─────────────────────────────────────────────

class TestDetectLanguage:
    def test_latin_script_is_english(self):
        from app.routes.api_v1.chat import _detect_language
        assert _detect_language("What is photosynthesis?") == "en"

    def test_devanagari_is_hindi(self):
        from app.routes.api_v1.chat import _detect_language
        assert _detect_language("प्रकाश संश्लेषण क्या है?") == "hi"

    def test_gujarati_script(self):
        from app.routes.api_v1.chat import _detect_language
        assert _detect_language("પ્રકાશ સંશ્લેષણ શું છે?") == "gu"

    def test_empty_string_returns_en(self):
        from app.routes.api_v1.chat import _detect_language
        assert _detect_language("") == "en"


# ── Feature label tests ───────────────────────────────────────────────────────

class TestTierToFeature:
    def test_tier_0_is_simple(self):
        from app.routes.api_v1.chat import _tier_to_feature
        assert _tier_to_feature(0, False) == "chat_simple"

    def test_tier_1_is_simple(self):
        from app.routes.api_v1.chat import _tier_to_feature
        assert _tier_to_feature(1, False) == "chat_simple"

    def test_tier_2_without_image_is_medium(self):
        from app.routes.api_v1.chat import _tier_to_feature
        assert _tier_to_feature(2, False) == "chat_medium"

    def test_tier_2_with_image_is_image(self):
        from app.routes.api_v1.chat import _tier_to_feature
        assert _tier_to_feature(2, True) == "chat_image"

    def test_tier_3_is_complex(self):
        from app.routes.api_v1.chat import _tier_to_feature
        assert _tier_to_feature(3, False) == "chat_complex"


# ── HTTP endpoint tests ───────────────────────────────────────────────────────

class TestChatEndpointSuccess:
    def test_text_query_returns_200_and_json(self):
        client = _make_client()
        app = _build_app(client)
        with _patch_all():
            tc = TestClient(app)
            resp = tc.post("/api/v1/chat", json=_BASE_PAYLOAD)

        assert resp.status_code == 200
        body = resp.json()
        assert "request_id" in body
        assert "conversation_id" in body
        assert len(body["answer"]) > 0
        assert body["model_used"] == "gpt-4.1-nano"
        assert body["confidence"] == "high"
        assert isinstance(body["credits_consumed"], int)
        assert isinstance(body["credits_remaining"], int)

    def test_new_conversation_id_generated(self):
        client = _make_client()
        app = _build_app(client)
        with _patch_all():
            resp = TestClient(app).post("/api/v1/chat", json=_BASE_PAYLOAD)

        assert resp.status_code == 200
        conv_id = resp.json()["conversation_id"]
        # UUID format
        import uuid as _uuid
        _uuid.UUID(conv_id)  # raises ValueError if invalid

    def test_existing_conversation_id_preserved(self):
        client = _make_client()
        app = _build_app(client)
        existing_id = "11111111-1111-1111-1111-111111111111"
        payload = {**_BASE_PAYLOAD, "conversation_id": existing_id}

        with _patch_all():
            resp = TestClient(app).post("/api/v1/chat", json=payload)

        assert resp.status_code == 200
        assert resp.json()["conversation_id"] == existing_id

    def test_cache_hit_returns_zero_credits_consumed(self):
        """Cache hits do not incur LLM token cost (total_billable_tokens=0)."""
        client = _make_client()
        app = _build_app(client)

        # When cache hits, model router still runs (via ModelRouter.route_query_stream
        # which handles the Tier-0 path internally). We simulate it returning 0 tokens.
        router_mock = _make_model_router_mock(
            answer="Plants make food using sunlight.",
            tier=0,
            total_billable_tokens=0,
        )
        credit_mock = _make_credit_mock(balance=5000)

        with _patch_all(model_router=router_mock, credits=credit_mock):
            resp = TestClient(app).post("/api/v1/chat", json=_BASE_PAYLOAD)

        assert resp.status_code == 200
        body = resp.json()
        assert body["credits_consumed"] == 0
        # get_balance called instead of deduct when credits_consumed == 0
        credit_mock.deduct.assert_not_awaited()
        credit_mock.get_balance.assert_awaited_once()

    def test_tokens_used_matches_metadata(self):
        client = _make_client()
        app = _build_app(client)
        router_mock = _make_model_router_mock(total_billable_tokens=500)
        with _patch_all(model_router=router_mock):
            resp = TestClient(app).post("/api/v1/chat", json=_BASE_PAYLOAD)

        assert resp.status_code == 200
        assert resp.json()["tokens_used"] == 500

    def test_sources_in_response(self):
        client = _make_client()
        app = _build_app(client)
        sources = [{"title": "NCERT Class 9 Science", "chapter": "6", "page": 85, "score": 0.94}]
        router_mock = _make_model_router_mock(sources=sources)
        with _patch_all(model_router=router_mock):
            resp = TestClient(app).post("/api/v1/chat", json=_BASE_PAYLOAD)

        assert resp.status_code == 200
        resp_sources = resp.json()["sources"]
        assert len(resp_sources) == 1
        assert resp_sources[0]["title"] == "NCERT Class 9 Science"

    def test_gseb_board_accepted(self):
        client = _make_client()
        app = _build_app(client)
        payload = {**_BASE_PAYLOAD, "board": "gseb"}
        with _patch_all():
            resp = TestClient(app).post("/api/v1/chat", json=payload)
        assert resp.status_code == 200

    def test_conversation_history_fetched_for_followup(self):
        client = _make_client()
        app = _build_app(client)
        cosmos = _make_cosmos_mock()
        cosmos.get_conversation_history = AsyncMock(return_value=[
            {"role": "user", "content": "What is a cell?"},
            {"role": "assistant", "content": "A cell is the basic unit of life."},
        ])
        payload = {**_BASE_PAYLOAD, "conversation_id": "conv-abc-123"}
        with _patch_all(cosmos=cosmos):
            resp = TestClient(app).post("/api/v1/chat", json=payload)

        assert resp.status_code == 200
        cosmos.get_conversation_history.assert_awaited_once_with(
            "conv-abc-123", max_turns=6, max_tokens=1500
        )


class TestChatEndpointErrors:
    def test_no_query_no_image_returns_422(self):
        """Pydantic model_validator raises → FastAPI returns 422."""
        client = _make_client()
        app = _build_app(client)
        with _patch_all():
            resp = TestClient(app).post("/api/v1/chat", json={
                "board": "cbse",
                "class_level": 9,
            })
        assert resp.status_code == 422

    def test_insufficient_credits_returns_402(self):
        client = _make_client()
        app = _build_app(client)
        credit_mock = _make_credit_mock()
        credit_mock.check_and_reserve = AsyncMock(return_value=False)

        with _patch_all(credits=credit_mock):
            resp = TestClient(app).post("/api/v1/chat", json=_BASE_PAYLOAD)

        assert resp.status_code == 402
        assert "credits" in resp.json()["detail"].lower()

    def test_internal_error_returns_500_with_request_id(self):
        client = _make_client()
        app = _build_app(client)

        async def _boom(*args, **kwargs):
            raise RuntimeError("Azure exploded")
            yield  # make it a generator

        router_mock = MagicMock()
        router_mock.route_query_stream = _boom

        with _patch_all(model_router=router_mock):
            resp = TestClient(app, raise_server_exceptions=False).post(
                "/api/v1/chat", json=_BASE_PAYLOAD
            )

        assert resp.status_code == 500
        detail = resp.json()["detail"]
        assert "Internal error" in detail
        assert "Reference:" in detail

    def test_invalid_board_returns_422(self):
        client = _make_client()
        app = _build_app(client)
        with _patch_all():
            resp = TestClient(app).post("/api/v1/chat", json={
                **_BASE_PAYLOAD, "board": "icse"
            })
        assert resp.status_code == 422

    def test_class_level_below_6_returns_422(self):
        client = _make_client()
        app = _build_app(client)
        with _patch_all():
            resp = TestClient(app).post("/api/v1/chat", json={
                **_BASE_PAYLOAD, "class_level": 5
            })
        assert resp.status_code == 422

    def test_class_level_above_12_returns_422(self):
        client = _make_client()
        app = _build_app(client)
        with _patch_all():
            resp = TestClient(app).post("/api/v1/chat", json={
                **_BASE_PAYLOAD, "class_level": 13
            })
        assert resp.status_code == 422


class TestChatEndpointImage:
    def _make_tiny_jpeg_b64(self) -> str:
        """1×1 white JPEG as base64."""
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (1, 1), color=(255, 255, 255)).save(buf, format="JPEG")
        return base64.b64encode(buf.getvalue()).decode()

    def test_image_query_success(self):
        client = _make_client()
        app = _build_app(client)

        img_mock = MagicMock()
        img_mock.validate_image = AsyncMock(return_value=True)
        img_mock.optimize_image = AsyncMock(return_value=b"optimized")

        from app.models.schemas import ImageExtractionResult
        img_mock.extract_question = AsyncMock(return_value=ImageExtractionResult(
            extracted_text="What is osmosis?",
            detected_language="en",
            detected_subject="Science",
            is_clear=True,
        ))

        payload = {
            "image_base64": self._make_tiny_jpeg_b64(),
            "board": "cbse",
            "class_level": 10,
        }
        with _patch_all(image=img_mock):
            resp = TestClient(app).post("/api/v1/chat", json=payload)

        assert resp.status_code == 200

    def test_corrupted_image_returns_400(self):
        client = _make_client()
        app = _build_app(client)

        img_mock = MagicMock()
        img_mock.validate_image = AsyncMock(return_value=False)

        payload = {
            "image_base64": base64.b64encode(b"not_an_image").decode(),
            "board": "cbse",
            "class_level": 10,
        }
        with _patch_all(image=img_mock):
            resp = TestClient(app).post("/api/v1/chat", json=payload)

        assert resp.status_code == 400
        assert "corrupted" in resp.json()["detail"].lower() or "5 mb" in resp.json()["detail"].lower()

    def test_unclear_image_returns_400(self):
        client = _make_client()
        app = _build_app(client)

        img_mock = MagicMock()
        img_mock.validate_image = AsyncMock(return_value=True)
        img_mock.optimize_image = AsyncMock(return_value=b"bytes")

        from app.models.schemas import ImageExtractionResult
        img_mock.extract_question = AsyncMock(return_value=ImageExtractionResult(
            extracted_text="",
            detected_language="en",
            detected_subject="Unknown",
            is_clear=False,
        ))

        payload = {
            "image_base64": base64.b64encode(b"blurry").decode(),
            "board": "cbse",
            "class_level": 10,
        }
        with _patch_all(image=img_mock):
            resp = TestClient(app).post("/api/v1/chat", json=payload)

        assert resp.status_code == 400
        assert "unclear" in resp.json()["detail"].lower()

    def test_invalid_base64_returns_400(self):
        client = _make_client()
        app = _build_app(client)

        img_mock = MagicMock()
        # validate_image won't even be called — base64.b64decode raises first

        payload = {
            "image_base64": "!!!not-valid-base64!!!",
            "board": "cbse",
            "class_level": 10,
        }
        with _patch_all(image=img_mock):
            resp = TestClient(app).post("/api/v1/chat", json=payload)

        assert resp.status_code == 400


class TestChatEndpointStreaming:
    def test_stream_true_returns_event_stream(self):
        client = _make_client()
        app = _build_app(client)

        with _patch_all():
            resp = TestClient(app).post(
                "/api/v1/chat", json={**_BASE_PAYLOAD, "stream": True}
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_stream_contains_chunk_events(self):
        client = _make_client()
        app = _build_app(client)

        with _patch_all():
            resp = TestClient(app).post(
                "/api/v1/chat", json={**_BASE_PAYLOAD, "stream": True}
            )

        events = [
            json.loads(line[len("data: "):])
            for line in resp.text.splitlines()
            if line.startswith("data: ")
        ]
        types = [e["type"] for e in events]
        assert "chunk" in types
        assert "metadata" in types
        assert "sources" in types
        assert "usage" in types
        assert "done" in types

    def test_stream_usage_event_has_credit_fields(self):
        client = _make_client()
        app = _build_app(client)

        with _patch_all():
            resp = TestClient(app).post(
                "/api/v1/chat", json={**_BASE_PAYLOAD, "stream": True}
            )

        events = {
            e["type"]: e
            for line in resp.text.splitlines()
            if line.startswith("data: ")
            for e in [json.loads(line[len("data: "):])]
        }
        usage = events.get("usage", {})
        assert "tokens_used" in usage
        assert "credits_consumed" in usage
        assert "credits_remaining" in usage

    def test_stream_done_is_last_event(self):
        client = _make_client()
        app = _build_app(client)

        with _patch_all():
            resp = TestClient(app).post(
                "/api/v1/chat", json={**_BASE_PAYLOAD, "stream": True}
            )

        data_lines = [
            json.loads(line[len("data: "):])
            for line in resp.text.splitlines()
            if line.startswith("data: ")
        ]
        assert data_lines[-1]["type"] == "done"

    def test_stream_insufficient_credits_returns_402(self):
        """Preflight check runs before streaming starts → proper 402 status."""
        client = _make_client()
        app = _build_app(client)
        credit_mock = _make_credit_mock()
        credit_mock.check_and_reserve = AsyncMock(return_value=False)

        with _patch_all(credits=credit_mock):
            resp = TestClient(app).post(
                "/api/v1/chat", json={**_BASE_PAYLOAD, "stream": True}
            )

        assert resp.status_code == 402

    def test_stream_x_request_id_header_present(self):
        client = _make_client()
        app = _build_app(client)

        with _patch_all():
            resp = TestClient(app).post(
                "/api/v1/chat", json={**_BASE_PAYLOAD, "stream": True}
            )

        assert "x-request-id" in resp.headers


class TestChatEndpointCreditAccounting:
    def test_deduct_called_with_correct_request_id(self):
        client = _make_client()
        app = _build_app(client)
        credit_mock = _make_credit_mock()

        with _patch_all(credits=credit_mock):
            resp = TestClient(app).post("/api/v1/chat", json=_BASE_PAYLOAD)

        assert resp.status_code == 200
        body = resp.json()
        credit_mock.deduct.assert_awaited_once()
        call_kwargs = credit_mock.deduct.call_args
        assert call_kwargs.kwargs["request_id"] == body["request_id"]

    def test_deduct_called_with_correct_client_id(self):
        client = _make_client(client_id="clnt_target")
        app = _build_app(client)
        credit_mock = _make_credit_mock()

        with _patch_all(credits=credit_mock):
            TestClient(app).post("/api/v1/chat", json=_BASE_PAYLOAD)

        credit_mock.deduct.assert_awaited_once()
        assert credit_mock.deduct.call_args.kwargs["client_id"] == "clnt_target"

    def test_no_deduct_on_500_error(self):
        """Internal AI errors should not charge the client."""
        client = _make_client()
        app = _build_app(client)
        credit_mock = _make_credit_mock()

        async def _boom(*args, **kwargs):
            raise RuntimeError("downstream failure")
            yield

        router_mock = MagicMock()
        router_mock.route_query_stream = _boom

        with _patch_all(credits=credit_mock, model_router=router_mock):
            TestClient(app, raise_server_exceptions=False).post(
                "/api/v1/chat", json=_BASE_PAYLOAD
            )

        credit_mock.deduct.assert_not_awaited()
