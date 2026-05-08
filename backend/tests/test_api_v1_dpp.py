"""
Tests for POST /api/v1/generate/dpp and /dpp/pdf.

Strategy:
- WorksheetService.generate_dpp_structured, CreditService, CosmosRepo are
  patched at the module level inside api_v1.dpp.
- verify_api_key and rate_limit are overridden via dependency_overrides.
- TestClient provides a synchronous request/response cycle.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.api_key_auth import verify_api_key
from app.middleware.rate_limiter import rate_limit
from app.models.client import Client
from app.routes.api_v1.dpp import router


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


def _make_questions(n: int = 5) -> list[dict]:
    return [
        {
            "question_text": f"Question {i}: What is Newton's {i}st law?",
            "difficulty": "easy" if i % 3 == 0 else "medium",
            "solution_steps": f"Step 1: State the law.\nStep 2: Apply it.",
            "correct_answer": f"Answer {i}",
            "concept_tags": ["Newton's Laws", "Motion"],
        }
        for i in range(1, n + 1)
    ]


def _build_app(client: Client) -> FastAPI:
    app = FastAPI()

    async def _auth():
        return client

    async def _no_rate():
        pass

    app.dependency_overrides[verify_api_key] = _auth
    app.dependency_overrides[rate_limit] = _no_rate
    app.include_router(router, prefix="/generate")
    return app


_BASE_REQUEST = {
    "board": "cbse",
    "class_level": 10,
    "subject": "Physics",
    "chapter": 3,
    "topic": "Laws of Motion",
    "difficulty": "mixed",
    "num_questions": 10,
    "include_solutions": True,
    "language": "en",
    "institute_name": "Test School",
}


# ── Test: successful DPP generation ──────────────────────────────────────────

def test_generate_dpp_success():
    client_obj = _make_client()
    app = _build_app(client_obj)
    questions = _make_questions(10)

    with (
        patch("app.routes.api_v1.dpp._credits") as mock_credits,
        patch("app.routes.api_v1.dpp._worksheet_service") as mock_svc,
        patch("app.routes.api_v1.dpp._cosmos") as mock_cosmos,
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=9_000)
        mock_svc.generate_dpp_structured = AsyncMock(return_value=(questions, 400, 250))
        mock_cosmos.log_query_usage = AsyncMock()

        with TestClient(app) as tc:
            resp = tc.post("/generate/dpp", json=_BASE_REQUEST)

    assert resp.status_code == 200
    body = resp.json()
    assert body["request_id"]
    assert len(body["questions"]) == 10
    assert body["questions"][0]["number"] == 1
    assert body["questions"][0]["text"] == questions[0]["question_text"]
    assert body["questions"][0]["answer"] == questions[0]["correct_answer"]
    assert body["questions"][0]["solution"] == questions[0]["solution_steps"]
    assert body["questions"][0]["concept_tags"] == questions[0]["concept_tags"]
    assert body["tokens_used"] == 650
    assert body["credits_consumed"] == 1  # ceil(650 / 1000) = 1
    assert body["credits_remaining"] == 9_000


# ── Test: solutions omitted when include_solutions=False ─────────────────────

def test_solutions_omitted_when_disabled():
    client_obj = _make_client()
    app = _build_app(client_obj)
    questions = _make_questions(5)

    with (
        patch("app.routes.api_v1.dpp._credits") as mock_credits,
        patch("app.routes.api_v1.dpp._worksheet_service") as mock_svc,
        patch("app.routes.api_v1.dpp._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=9_000)
        mock_svc.generate_dpp_structured = AsyncMock(return_value=(questions, 200, 100))

        req = {**_BASE_REQUEST, "include_solutions": False, "num_questions": 5}
        with TestClient(app) as tc:
            resp = tc.post("/generate/dpp", json=req)

    assert resp.status_code == 200
    q = resp.json()["questions"][0]
    assert q["solution"] is None
    assert q["answer"] is None
    assert q["concept_tags"] == questions[0]["concept_tags"]


# ── Test: insufficient credits returns 402 ───────────────────────────────────

def test_insufficient_credits_returns_402():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with (
        patch("app.routes.api_v1.dpp._credits") as mock_credits,
        patch("app.routes.api_v1.dpp._worksheet_service") as mock_svc,
        patch("app.routes.api_v1.dpp._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=False)

        with TestClient(app) as tc:
            resp = tc.post("/generate/dpp", json=_BASE_REQUEST)

    assert resp.status_code == 402
    assert "Insufficient credits" in resp.json()["detail"]
    mock_svc.generate_dpp_structured.assert_not_called()


def test_preflight_uses_correct_credit_estimate():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with (
        patch("app.routes.api_v1.dpp._credits") as mock_credits,
        patch("app.routes.api_v1.dpp._worksheet_service"),
        patch("app.routes.api_v1.dpp._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=False)

        with TestClient(app) as tc:
            tc.post("/generate/dpp", json=_BASE_REQUEST)

    mock_credits.check_and_reserve.assert_called_once_with("clnt_test_school", 12)


# ── Test: service ValueError returns 400 ─────────────────────────────────────

def test_service_value_error_returns_400():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with (
        patch("app.routes.api_v1.dpp._credits") as mock_credits,
        patch("app.routes.api_v1.dpp._worksheet_service") as mock_svc,
        patch("app.routes.api_v1.dpp._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_svc.generate_dpp_structured = AsyncMock(
            side_effect=ValueError("LLM returned zero questions.")
        )

        with TestClient(app) as tc:
            resp = tc.post("/generate/dpp", json=_BASE_REQUEST)

    assert resp.status_code == 400
    assert "LLM returned zero questions" in resp.json()["detail"]


# ── Test: service unexpected error returns 500 ────────────────────────────────

def test_service_unexpected_error_returns_500():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with (
        patch("app.routes.api_v1.dpp._credits") as mock_credits,
        patch("app.routes.api_v1.dpp._worksheet_service") as mock_svc,
        patch("app.routes.api_v1.dpp._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_svc.generate_dpp_structured = AsyncMock(
            side_effect=RuntimeError("Azure timeout")
        )

        with TestClient(app) as tc:
            resp = tc.post("/generate/dpp", json=_BASE_REQUEST)

    assert resp.status_code == 500
    assert "Generation failed" in resp.json()["detail"]


# ── Test: schema validation ───────────────────────────────────────────────────

def test_num_questions_below_minimum_rejected():
    client_obj = _make_client()
    app = _build_app(client_obj)

    req = {**_BASE_REQUEST, "num_questions": 2}
    with TestClient(app) as tc:
        resp = tc.post("/generate/dpp", json=req)

    assert resp.status_code == 422


def test_num_questions_above_maximum_rejected():
    client_obj = _make_client()
    app = _build_app(client_obj)

    req = {**_BASE_REQUEST, "num_questions": 25}
    with TestClient(app) as tc:
        resp = tc.post("/generate/dpp", json=req)

    assert resp.status_code == 422


def test_invalid_difficulty_rejected():
    client_obj = _make_client()
    app = _build_app(client_obj)

    req = {**_BASE_REQUEST, "difficulty": "extreme"}
    with TestClient(app) as tc:
        resp = tc.post("/generate/dpp", json=req)

    assert resp.status_code == 422


def test_invalid_board_rejected():
    client_obj = _make_client()
    app = _build_app(client_obj)

    req = {**_BASE_REQUEST, "board": "icse"}
    with TestClient(app) as tc:
        resp = tc.post("/generate/dpp", json=req)

    assert resp.status_code == 422


def test_optional_topic_accepted_without_value():
    client_obj = _make_client()
    app = _build_app(client_obj)
    questions = _make_questions(5)

    with (
        patch("app.routes.api_v1.dpp._credits") as mock_credits,
        patch("app.routes.api_v1.dpp._worksheet_service") as mock_svc,
        patch("app.routes.api_v1.dpp._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=9_000)
        mock_svc.generate_dpp_structured = AsyncMock(return_value=(questions, 200, 100))

        req = {k: v for k, v in _BASE_REQUEST.items() if k != "topic"}
        req["num_questions"] = 5
        with TestClient(app) as tc:
            resp = tc.post("/generate/dpp", json=req)

    assert resp.status_code == 200


# ── Test: PDF endpoint returns HTML ──────────────────────────────────────────

def test_pdf_endpoint_returns_html():
    client_obj = _make_client()
    app = _build_app(client_obj)

    pdf_req = {
        "questions": [
            {
                "number": 1,
                "text": "State Newton's first law of motion.",
                "difficulty": "easy",
                "solution": "Step 1: The law states...",
                "answer": "An object remains in rest or uniform motion...",
                "concept_tags": ["Newton's Laws"],
            }
        ],
        "board": "cbse",
        "class_level": 10,
        "subject": "Physics",
        "chapter": 3,
        "topic": "Laws of Motion",
        "institute_name": "Test School",
        "include_solutions": True,
    }

    with TestClient(app) as tc:
        resp = tc.post("/generate/dpp/pdf", json=pdf_req)

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert "Newton" in body
    assert "Test School" in body
    assert "katex" in body
    assert "Answer Key" in body


def test_pdf_endpoint_no_solutions():
    client_obj = _make_client()
    app = _build_app(client_obj)

    pdf_req = {
        "questions": [
            {
                "number": 1,
                "text": "Describe uniform motion.",
                "difficulty": "medium",
                "solution": None,
                "answer": None,
                "concept_tags": [],
            }
        ],
        "board": "cbse",
        "class_level": 9,
        "subject": "Physics",
        "chapter": 8,
        "include_solutions": False,
    }

    with TestClient(app) as tc:
        resp = tc.post("/generate/dpp/pdf", json=pdf_req)

    assert resp.status_code == 200
    assert "Answer Key" not in resp.text


def test_pdf_endpoint_empty_questions_returns_400():
    client_obj = _make_client()
    app = _build_app(client_obj)

    pdf_req = {
        "questions": [],
        "board": "cbse",
        "class_level": 10,
        "subject": "Physics",
        "chapter": 1,
    }

    with TestClient(app) as tc:
        resp = tc.post("/generate/dpp/pdf", json=pdf_req)

    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"]


# ── Test: questions numbered correctly ────────────────────────────────────────

def test_questions_are_numbered_sequentially():
    client_obj = _make_client()
    app = _build_app(client_obj)
    questions = _make_questions(5)

    with (
        patch("app.routes.api_v1.dpp._credits") as mock_credits,
        patch("app.routes.api_v1.dpp._worksheet_service") as mock_svc,
        patch("app.routes.api_v1.dpp._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=9_000)
        mock_svc.generate_dpp_structured = AsyncMock(return_value=(questions, 100, 50))

        req = {**_BASE_REQUEST, "num_questions": 5}
        with TestClient(app) as tc:
            resp = tc.post("/generate/dpp", json=req)

    body = resp.json()
    numbers = [q["number"] for q in body["questions"]]
    assert numbers == [1, 2, 3, 4, 5]
