"""
End-to-end pipeline integration tests.

Covers the full client lifecycle in order:
  1.  Admin creates a client → raw API key returned once.
  2.  Admin tops up credits → ledger updated, Redis updated.
  3.  Client calls POST /api/v1/chat → credits consumed, response returned.
  4.  Client calls POST /api/v1/generate/question-paper → variants returned.
  5.  Client calls POST /api/v1/generate/dpp → questions returned.
  6.  Client balance is insufficient → API returns 402.
  7.  Suspended client makes API call → returns 403.
  8.  Admin tops up suspended client → client reactivated.
  9.  Client calls GET /api/v1/usage → correct account data returned.

Strategy:
  - Admin routes use FastAPI DI → override via app.dependency_overrides.
  - /api/v1/* routes use module-level singletons → patch with unittest.mock.patch.
  - No real Azure credentials required; all I/O is mocked.

Run with:
    cd backend
    pytest tests/integration/test_full_pipeline.py -v
"""
import json
import bcrypt
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies.admin_auth import (
    get_analytics_repo,
    get_audit_repo,
    get_client_repo,
    get_credit_service,
    get_current_admin,
    get_ledger_repo,
)
from app.middleware.api_key_auth import verify_api_key
from app.models.client import Client, LedgerEntry

# ── Shared constants ──────────────────────────────────────────────────────────

_TEST_PASSWORD = "pilotpassword123"
_TEST_HASH = bcrypt.hashpw(_TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
_NOW = datetime.now(timezone.utc)

_ACTIVE_CLIENT_ID = "clnt_demo_school"
_CHAT_API_KEY = "jvb_live_testkey0000000000000000"


# ── Model factories ───────────────────────────────────────────────────────────

def _make_client(**overrides) -> Client:
    defaults = dict(
        client_id=_ACTIVE_CLIENT_ID,
        org_name="Demo Public School",
        contact_name="Demo Admin",
        contact_phone="+919000000001",
        contact_email="demo@javaab.in",
        api_key_hash="a" * 64,
        api_key_prefix="jvb_live_tes",
        plan_tier="growth",
        credit_balance=50_000,
        credit_alert_threshold=5_000,
        is_active=True,
        rate_limit_per_minute=120,
        rate_limit_per_day=100_000,
        whatsapp_number="+919000000001",
        notes=None,
        created_at=_NOW,
        updated_at=_NOW,
    )
    return Client(**{**defaults, **overrides})


def _make_ledger_entry(**overrides) -> LedgerEntry:
    defaults = dict(
        ledger_id="led-seed-001",
        client_id=_ACTIVE_CLIENT_ID,
        type="topup",
        credits=50_000,
        balance_after=50_000,
        amount_inr=25_000,
        payment_ref="UTR_PILOT_001",
        note="Initial topup",
        created_by="admin",
        created_at=_NOW,
    )
    return LedgerEntry(**{**defaults, **overrides})


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Inject test admin credentials and blank Azure endpoints before each test."""
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", _TEST_HASH)
    monkeypatch.setenv("ADMIN_JWT_SECRET", "test-secret-at-least-32-chars-ok!")
    monkeypatch.setenv("ADMIN_JWT_EXPIRY_HOURS", "12")
    monkeypatch.setenv("AZURE_COSMOS_ENDPOINT", "")
    monkeypatch.setenv("AZURE_REDIS_HOST", "")
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def mock_client_repo():
    repo = MagicMock()
    repo.list_clients = AsyncMock(return_value=[_make_client()])
    repo.get_client_by_id = AsyncMock(return_value=_make_client())
    repo.create_client = AsyncMock(return_value=_make_client())
    repo.update_client = AsyncMock(return_value=_make_client())
    repo.deactivate_client = AsyncMock(return_value=None)
    repo.update_balance_cache = AsyncMock(return_value=None)
    return repo


@pytest.fixture()
def mock_ledger_repo():
    repo = MagicMock()
    repo.get_entries_for_client = AsyncMock(return_value=[_make_ledger_entry()])
    repo.get_last_topup = AsyncMock(return_value=_make_ledger_entry())
    return repo


@pytest.fixture()
def mock_credit_svc():
    svc = MagicMock()
    svc.get_balance = AsyncMock(return_value=50_000)
    svc.topup = AsyncMock(return_value=55_000)
    svc.adjust = AsyncMock(return_value=49_500)
    svc.check_and_reserve = AsyncMock(return_value=True)
    svc.deduct = AsyncMock(return_value=49_998)
    svc.get_consumption_summary = AsyncMock(
        return_value={
            "by_feature": {
                "chat_simple": {"credits": 200, "tokens_input": 100000, "tokens_output": 100000, "count": 100},
            },
            "total_credits": 200,
            "total_tokens": 200_000,
            "daily_avg": 6.67,
            "forecast_eom": 100,
        }
    )
    return svc


@pytest.fixture()
def mock_audit_repo():
    repo = MagicMock()
    repo.log = AsyncMock(return_value=None)
    return repo


@pytest.fixture()
def mock_analytics_repo():
    repo = MagicMock()
    repo.get_platform_stats_since = AsyncMock(
        return_value={
            "total_credits_sold": 50_000,
            "total_credits_consumed": 200,
            "total_revenue_inr": 25_000,
            "by_client": {_ACTIVE_CLIENT_ID: 200},
        }
    )
    repo.get_client_consumption_since = AsyncMock(
        return_value={_ACTIVE_CLIENT_ID: 200}
    )
    return repo


@pytest.fixture()
def authed_admin(
    mock_client_repo,
    mock_ledger_repo,
    mock_credit_svc,
    mock_audit_repo,
    mock_analytics_repo,
):
    """TestClient with admin auth bypassed and all admin deps mocked."""
    app.dependency_overrides[get_current_admin] = lambda: "admin"
    app.dependency_overrides[get_client_repo] = lambda: mock_client_repo
    app.dependency_overrides[get_ledger_repo] = lambda: mock_ledger_repo
    app.dependency_overrides[get_credit_service] = lambda: mock_credit_svc
    app.dependency_overrides[get_audit_repo] = lambda: mock_audit_repo
    app.dependency_overrides[get_analytics_repo] = lambda: mock_analytics_repo
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def api_client():
    """TestClient with verify_api_key overridden to return an active mock client."""
    app.dependency_overrides[verify_api_key] = lambda: _make_client()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ── Pipeline step 1: Admin creates a client ───────────────────────────────────

class TestPipeline_01_AdminCreateClient:
    """Admin POST /admin/clients → receives client object + raw API key (once)."""

    def _payload(self):
        return {
            "org_name": "Demo Public School",
            "contact_name": "Demo Admin",
            "contact_phone": "+919000000001",
            "contact_email": "demo@javaab.in",
            "plan_tier": "growth",
            "rate_limit_per_minute": 120,
            "rate_limit_per_day": 100_000,
            "credit_alert_threshold": 5_000,
            "whatsapp_number": "+919000000001",
        }

    def test_create_returns_201_and_raw_key(self, authed_admin, mock_audit_repo):
        r = authed_admin.post("/admin/clients", json=self._payload())
        assert r.status_code == 201
        body = r.json()
        assert "raw_api_key" in body
        assert body["raw_api_key"].startswith("jvb_live_")
        assert "client" in body
        assert body["client"]["org_name"] == "Demo Public School"

    def test_audit_log_written_on_create(self, authed_admin, mock_audit_repo):
        authed_admin.post("/admin/clients", json=self._payload())
        mock_audit_repo.log.assert_called_once()

    def test_missing_required_field_returns_422(self, authed_admin):
        payload = self._payload()
        del payload["org_name"]
        r = authed_admin.post("/admin/clients", json=payload)
        assert r.status_code == 422

    def test_unauthenticated_returns_401(self):
        app.dependency_overrides.clear()
        with TestClient(app) as c:
            r = c.post("/admin/clients", json=self._payload())
        assert r.status_code == 401


# ── Pipeline step 2: Admin tops up credits ────────────────────────────────────

class TestPipeline_02_AdminTopup:
    """Admin POST /admin/clients/{id}/topup → new balance returned, ledger updated."""

    def test_topup_returns_new_balance(self, authed_admin, mock_credit_svc):
        r = authed_admin.post(
            f"/admin/clients/{_ACTIVE_CLIENT_ID}/topup",
            json={"credits": 5_000, "amount_inr": 2_500, "payment_ref": "UTR123456", "note": "Pilot load"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["credits_added"] == 5_000
        assert body["new_balance"] == 55_000  # mock_credit_svc.topup returns 55_000

    def test_topup_calls_credit_service(self, authed_admin, mock_credit_svc):
        authed_admin.post(
            f"/admin/clients/{_ACTIVE_CLIENT_ID}/topup",
            json={"credits": 5_000, "amount_inr": 2_500, "payment_ref": "UTR999"},
        )
        mock_credit_svc.topup.assert_called_once()

    def test_topup_audit_logged(self, authed_admin, mock_audit_repo):
        authed_admin.post(
            f"/admin/clients/{_ACTIVE_CLIENT_ID}/topup",
            json={"credits": 5_000, "amount_inr": 2_500, "payment_ref": "UTR999"},
        )
        mock_audit_repo.log.assert_called_once()

    def test_zero_credits_rejected(self, authed_admin):
        r = authed_admin.post(
            f"/admin/clients/{_ACTIVE_CLIENT_ID}/topup",
            json={"credits": 0, "amount_inr": 0, "payment_ref": ""},
        )
        assert r.status_code == 422

    def test_client_not_found_returns_404(self, authed_admin, mock_client_repo):
        mock_client_repo.get_client_by_id = AsyncMock(return_value=None)
        r = authed_admin.post(
            "/admin/clients/clnt_nonexistent/topup",
            json={"credits": 1_000, "amount_inr": 500, "payment_ref": "UTR001"},
        )
        assert r.status_code == 404


# ── Pipeline step 3: Client calls /api/v1/chat ────────────────────────────────

_METADATA_CHUNK = json.dumps({
    "model_used": "gpt-4.1-nano",
    "tier": 1,
    "total_billable_tokens": 1500,
    "tokens_input": 1000,
    "tokens_output": 500,
    "confidence": "HIGH",
    "confidence_score": 0.9,
    "sources": [],
})


def _chat_payload(**overrides):
    base = {
        "query": "What is photosynthesis?",
        "board": "cbse",
        "class_level": 10,
        "subject": "Science",
        "stream": False,
    }
    return {**base, **overrides}


class TestPipeline_03_ClientChat:
    """Client POST /api/v1/chat → answer returned, credits consumed."""

    def test_chat_returns_200_with_answer(self, api_client):
        async def _fake_stream(**kwargs):
            yield "Photosynthesis is the process by which plants make food using sunlight."
            yield f"\n\n[METADATA]{_METADATA_CHUNK}"

        mock_router = MagicMock()
        mock_router.route_query_stream = _fake_stream
        mock_credits = MagicMock()
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=49_998)
        mock_credits.get_balance = AsyncMock(return_value=49_998)
        mock_cache = MagicMock()
        mock_cache.check_cache = AsyncMock(return_value=None)
        mock_rag = MagicMock()
        mock_rag.get_context = AsyncMock(
            return_value={"context": "Plants use sunlight.", "confidence": "HIGH", "confidence_score": 0.9}
        )
        mock_cosmos = MagicMock()
        mock_cosmos.get_conversation_history = AsyncMock(return_value=[])
        mock_cosmos.save_conversation = AsyncMock(return_value=None)
        mock_cosmos.create_conversation = AsyncMock(return_value=None)

        with (
            patch("app.routes.api_v1.chat._model_router", mock_router),
            patch("app.routes.api_v1.chat._credits", mock_credits),
            patch("app.routes.api_v1.chat._cache", mock_cache),
            patch("app.routes.api_v1.chat._rag", mock_rag),
            patch("app.routes.api_v1.chat._cosmos", mock_cosmos),
        ):
            r = api_client.post("/api/v1/chat", json=_chat_payload())

        assert r.status_code == 200
        body = r.json()
        assert "answer" in body
        assert "credits_consumed" in body
        assert "credits_remaining" in body
        assert "request_id" in body
        assert body["credits_consumed"] == 2  # ceil(1500 / 1000)
        assert body["credits_remaining"] == 49_998

    def test_chat_preflight_check_called(self, api_client):
        """Confirms check_and_reserve is called before doing AI work."""
        async def _fake_stream(**kwargs):
            yield "Answer."
            yield f"\n\n[METADATA]{_METADATA_CHUNK}"

        mock_router = MagicMock()
        mock_router.route_query_stream = _fake_stream
        mock_credits = MagicMock()
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=49_998)
        mock_credits.get_balance = AsyncMock(return_value=49_998)
        mock_cache = MagicMock()
        mock_cache.check_cache = AsyncMock(return_value=None)
        mock_rag = MagicMock()
        mock_rag.get_context = AsyncMock(
            return_value={"context": "", "confidence": "NONE", "confidence_score": 0.0}
        )
        mock_cosmos = MagicMock()
        mock_cosmos.get_conversation_history = AsyncMock(return_value=[])
        mock_cosmos.save_conversation = AsyncMock(return_value=None)
        mock_cosmos.create_conversation = AsyncMock(return_value=None)

        with (
            patch("app.routes.api_v1.chat._model_router", mock_router),
            patch("app.routes.api_v1.chat._credits", mock_credits),
            patch("app.routes.api_v1.chat._cache", mock_cache),
            patch("app.routes.api_v1.chat._rag", mock_rag),
            patch("app.routes.api_v1.chat._cosmos", mock_cosmos),
        ):
            api_client.post("/api/v1/chat", json=_chat_payload())

        mock_credits.check_and_reserve.assert_called_once()

    def test_chat_missing_query_and_image_returns_422(self, api_client):
        r = api_client.post(
            "/api/v1/chat",
            json={"board": "cbse", "class_level": 10},
        )
        assert r.status_code == 422


# ── Pipeline step 4: Client calls /api/v1/generate/question-paper ─────────────

def _qpg_payload(**overrides):
    base = {
        "board": "cbse",
        "class_level": 10,
        "subject": "Science",
        "chapters": ["Chapter 1 — Chemical Reactions"],
        "difficulty_mix": {"easy": 30, "medium": 50, "hard": 20},
        "question_distribution": {"mcq": 10, "short": 5, "long": 3},
        "total_marks": 40,
        "duration_minutes": 90,
        "num_variants": 1,
    }
    return {**base, **overrides}


def _mock_paper_variant():
    q = MagicMock()
    q.question_text = "Define chemical reaction."
    q.marks = 3
    q.difficulty = "medium"
    q.chapter = "Chapter 1"
    q.options = None
    q.correct_answer = "A process in which new substances are formed."
    q.marking_scheme = "3 marks for complete definition with example."
    q.question_type = MagicMock(value="short")

    variant = MagicMock()
    variant.variant_label = "Set A"
    variant.sections = {"Section A": [q]}
    return variant


class TestPipeline_04_ClientQPG:
    """Client POST /api/v1/generate/question-paper → variants returned, credits deducted."""

    def test_qpg_returns_200_with_variants(self, api_client):
        mock_credits = MagicMock()
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=49_985)
        mock_paper_svc = MagicMock()
        mock_paper_svc.generate_structured = AsyncMock(
            return_value=([_mock_paper_variant()], 1_000, 500)
        )
        mock_cosmos = MagicMock()
        mock_cosmos.log_query_usage = AsyncMock(return_value=None)

        with (
            patch("app.routes.api_v1.qpg._credits", mock_credits),
            patch("app.routes.api_v1.qpg._paper_service", mock_paper_svc),
            patch("app.routes.api_v1.qpg._cosmos", mock_cosmos),
        ):
            r = api_client.post("/api/v1/generate/question-paper", json=_qpg_payload())

        assert r.status_code == 200
        body = r.json()
        assert "variants" in body
        assert len(body["variants"]) == 1
        assert body["variants"][0]["variant_label"] == "Set A"
        assert "credits_consumed" in body
        assert "credits_remaining" in body
        assert body["credits_remaining"] == 49_985

    def test_qpg_preflight_credit_check(self, api_client):
        mock_credits = MagicMock()
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=49_985)
        mock_paper_svc = MagicMock()
        mock_paper_svc.generate_structured = AsyncMock(
            return_value=([_mock_paper_variant()], 1_000, 500)
        )
        mock_cosmos = MagicMock()
        mock_cosmos.log_query_usage = AsyncMock(return_value=None)

        with (
            patch("app.routes.api_v1.qpg._credits", mock_credits),
            patch("app.routes.api_v1.qpg._paper_service", mock_paper_svc),
            patch("app.routes.api_v1.qpg._cosmos", mock_cosmos),
        ):
            api_client.post("/api/v1/generate/question-paper", json=_qpg_payload())

        mock_credits.check_and_reserve.assert_called_once_with(_ACTIVE_CLIENT_ID, 15)

    def test_qpg_invalid_difficulty_mix_returns_422(self, api_client):
        r = api_client.post(
            "/api/v1/generate/question-paper",
            json=_qpg_payload(difficulty_mix={"easy": 50, "medium": 50, "hard": 50}),
        )
        assert r.status_code == 422


# ── Pipeline step 5: Client calls /api/v1/generate/dpp ───────────────────────

def _dpp_payload(**overrides):
    base = {
        "board": "cbse",
        "class_level": 10,
        "subject": "Science",
        "chapter": 1,
        "topic": "Acids and Bases",
        "difficulty": "mixed",
        "num_questions": 10,
        "include_solutions": True,
    }
    return {**base, **overrides}


_MOCK_DPP_ITEMS = [
    {
        "question_text": "State Newton's first law of motion.",
        "difficulty": "easy",
        "solution_steps": "Newton's first law states that an object at rest stays at rest...",
        "correct_answer": "An object remains at rest or in uniform motion unless acted on by a net force.",
        "concept_tags": ["newton_laws", "inertia"],
    }
]


class TestPipeline_05_ClientDPP:
    """Client POST /api/v1/generate/dpp → questions returned, credits deducted."""

    def test_dpp_returns_200_with_questions(self, api_client):
        mock_credits = MagicMock()
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=49_988)
        mock_ws_svc = MagicMock()
        mock_ws_svc.generate_dpp_structured = AsyncMock(
            return_value=(_MOCK_DPP_ITEMS, 800, 600)
        )
        mock_cosmos = MagicMock()
        mock_cosmos.log_query_usage = AsyncMock(return_value=None)

        with (
            patch("app.routes.api_v1.dpp._credits", mock_credits),
            patch("app.routes.api_v1.dpp._worksheet_service", mock_ws_svc),
            patch("app.routes.api_v1.dpp._cosmos", mock_cosmos),
        ):
            r = api_client.post("/api/v1/generate/dpp", json=_dpp_payload())

        assert r.status_code == 200
        body = r.json()
        assert "questions" in body
        assert len(body["questions"]) == 1
        assert body["questions"][0]["number"] == 1
        assert "credits_consumed" in body
        assert body["credits_remaining"] == 49_988

    def test_dpp_preflight_check_called(self, api_client):
        mock_credits = MagicMock()
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=49_988)
        mock_ws_svc = MagicMock()
        mock_ws_svc.generate_dpp_structured = AsyncMock(
            return_value=(_MOCK_DPP_ITEMS, 800, 600)
        )
        mock_cosmos = MagicMock()
        mock_cosmos.log_query_usage = AsyncMock(return_value=None)

        with (
            patch("app.routes.api_v1.dpp._credits", mock_credits),
            patch("app.routes.api_v1.dpp._worksheet_service", mock_ws_svc),
            patch("app.routes.api_v1.dpp._cosmos", mock_cosmos),
        ):
            api_client.post("/api/v1/generate/dpp", json=_dpp_payload())

        mock_credits.check_and_reserve.assert_called_once_with(_ACTIVE_CLIENT_ID, 12)

    def test_dpp_too_many_questions_returns_422(self, api_client):
        r = api_client.post(
            "/api/v1/generate/dpp",
            json=_dpp_payload(num_questions=99),
        )
        assert r.status_code == 422


# ── Pipeline step 6: Insufficient credits → 402 ───────────────────────────────

class TestPipeline_06_InsufficientCredits:
    """Any feature endpoint returns 402 when check_and_reserve returns False."""

    def test_chat_returns_402_when_balance_exhausted(self, api_client):
        mock_credits = MagicMock()
        mock_credits.check_and_reserve = AsyncMock(return_value=False)

        with patch("app.routes.api_v1.chat._credits", mock_credits):
            r = api_client.post("/api/v1/chat", json=_chat_payload())

        assert r.status_code == 402
        assert "credits" in r.json()["detail"].lower()

    def test_qpg_returns_402_when_balance_exhausted(self, api_client):
        mock_credits = MagicMock()
        mock_credits.check_and_reserve = AsyncMock(return_value=False)

        with patch("app.routes.api_v1.qpg._credits", mock_credits):
            r = api_client.post("/api/v1/generate/question-paper", json=_qpg_payload())

        assert r.status_code == 402

    def test_dpp_returns_402_when_balance_exhausted(self, api_client):
        mock_credits = MagicMock()
        mock_credits.check_and_reserve = AsyncMock(return_value=False)

        with patch("app.routes.api_v1.dpp._credits", mock_credits):
            r = api_client.post("/api/v1/generate/dpp", json=_dpp_payload())

        assert r.status_code == 402


# ── Pipeline step 7: Suspended client → 403 ──────────────────────────────────

class TestPipeline_07_SuspendedClientBlocked:
    """Suspended client's API calls are rejected with 403."""

    def test_suspended_client_chat_returns_403(self):
        """Patch client_repo to return a suspended client, bypassing DI override."""
        mock_repo = MagicMock()
        mock_repo.get_client_by_api_key_hash = AsyncMock(
            return_value=_make_client(is_active=False)
        )

        with patch("app.middleware.api_key_auth._client_repo", mock_repo):
            with TestClient(app) as c:
                r = c.post(
                    "/api/v1/chat",
                    json=_chat_payload(),
                    headers={"X-API-Key": _CHAT_API_KEY},
                )

        assert r.status_code == 403
        assert "suspended" in r.json()["detail"].lower()

    def test_suspended_client_qpg_returns_403(self):
        mock_repo = MagicMock()
        mock_repo.get_client_by_api_key_hash = AsyncMock(
            return_value=_make_client(is_active=False)
        )

        with patch("app.middleware.api_key_auth._client_repo", mock_repo):
            with TestClient(app) as c:
                r = c.post(
                    "/api/v1/generate/question-paper",
                    json=_qpg_payload(),
                    headers={"X-API-Key": _CHAT_API_KEY},
                )

        assert r.status_code == 403

    def test_suspended_client_dpp_returns_403(self):
        mock_repo = MagicMock()
        mock_repo.get_client_by_api_key_hash = AsyncMock(
            return_value=_make_client(is_active=False)
        )

        with patch("app.middleware.api_key_auth._client_repo", mock_repo):
            with TestClient(app) as c:
                r = c.post(
                    "/api/v1/generate/dpp",
                    json=_dpp_payload(),
                    headers={"X-API-Key": _CHAT_API_KEY},
                )

        assert r.status_code == 403


# ── Pipeline step 8: Admin tops up suspended client → reactivated ─────────────

class TestPipeline_08_TopupReactivateSuspended:
    """Admin tops up a suspended client; the service reactivates it."""

    def test_topup_suspended_client_returns_new_balance(
        self, authed_admin, mock_client_repo, mock_credit_svc, mock_audit_repo
    ):
        mock_client_repo.get_client_by_id = AsyncMock(
            return_value=_make_client(is_active=False, credit_balance=0)
        )
        mock_credit_svc.topup = AsyncMock(return_value=10_000)

        r = authed_admin.post(
            f"/admin/clients/{_ACTIVE_CLIENT_ID}/topup",
            json={"credits": 10_000, "amount_inr": 5_000, "payment_ref": "UTR_REACTIVATE"},
        )

        assert r.status_code == 200
        assert r.json()["new_balance"] == 10_000
        mock_credit_svc.topup.assert_called_once()
        mock_audit_repo.log.assert_called_once()

    def test_reactivate_endpoint_restores_active_status(
        self, authed_admin, mock_client_repo, mock_credit_svc, mock_audit_repo
    ):
        mock_client_repo.get_client_by_id = AsyncMock(
            return_value=_make_client(is_active=False)
        )
        mock_credit_svc.get_balance = AsyncMock(return_value=10_000)
        mock_client_repo.update_client = AsyncMock(
            return_value=_make_client(is_active=True)
        )

        r = authed_admin.post(f"/admin/clients/{_ACTIVE_CLIENT_ID}/reactivate")

        assert r.status_code == 200
        assert r.json()["is_active"] is True


# ── Pipeline step 9: Client calls GET /api/v1/usage ──────────────────────────

class TestPipeline_09_UsageEndpoint:
    """Client GET /api/v1/usage → correct account data returned."""

    def test_usage_returns_200_with_account_data(self, api_client):
        mock_credits = MagicMock()
        mock_credits.get_balance = AsyncMock(return_value=49_800)
        mock_credits.get_consumption_summary = AsyncMock(
            return_value={
                "by_feature": {
                    "chat_simple": {"credits": 200, "tokens_input": 100_000, "tokens_output": 100_000, "count": 100},
                },
                "total_credits": 200,
                "total_tokens": 200_000,
                "daily_avg": 6.67,
                "forecast_eom": 100,
            }
        )
        mock_ledger = MagicMock()
        mock_ledger.get_last_topup = AsyncMock(return_value=_make_ledger_entry())

        with (
            patch("app.routes.api_v1.usage._credits", mock_credits),
            patch("app.routes.api_v1.usage._ledger_repo", mock_ledger),
        ):
            r = api_client.get("/api/v1/usage")

        assert r.status_code == 200
        body = r.json()
        assert body["client_id"] == _ACTIVE_CLIENT_ID
        assert body["credits_remaining"] == 49_800
        assert body["plan_tier"] == "growth"
        assert body["is_active"] is True
        assert "consumption_30d" in body
        assert "daily_avg_credits" in body
        assert "forecasted_eom_credits" in body
        assert body["last_topup"] is not None

    def test_usage_ledger_returns_entries(self, api_client):
        mock_credits = MagicMock()
        mock_credits.get_balance = AsyncMock(return_value=49_800)
        mock_credits.get_consumption_summary = AsyncMock(
            return_value={
                "by_feature": {},
                "total_credits": 0,
                "total_tokens": 0,
                "daily_avg": 0.0,
                "forecast_eom": 0,
            }
        )
        mock_ledger = MagicMock()
        mock_ledger.get_last_topup = AsyncMock(return_value=None)
        mock_ledger.get_entries_for_client = AsyncMock(
            return_value=[_make_ledger_entry()]
        )

        with (
            patch("app.routes.api_v1.usage._credits", mock_credits),
            patch("app.routes.api_v1.usage._ledger_repo", mock_ledger),
        ):
            r = api_client.get("/api/v1/usage/ledger")

        assert r.status_code == 200
        body = r.json()
        assert body["client_id"] == _ACTIVE_CLIENT_ID
        assert body["count"] == 1
        assert body["entries"][0]["type"] == "topup"

    def test_usage_no_api_key_returns_401(self):
        with TestClient(app) as c:
            r = c.get("/api/v1/usage")
        assert r.status_code == 401
