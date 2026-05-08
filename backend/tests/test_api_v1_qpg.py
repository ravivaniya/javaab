"""
Tests for POST /api/v1/generate/question-paper and /question-paper/pdf.

Strategy:
- PaperService.generate_structured, CreditService, CosmosRepo are patched at
  the module level inside api_v1.qpg.
- verify_api_key and rate_limit are overridden via dependency_overrides.
- TestClient provides a synchronous request/response cycle.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware.api_key_auth import verify_api_key
from app.middleware.rate_limiter import rate_limit
from app.models.client import Client
from app.models.paper import GeneratedQuestion, PaperVariant, QuestionType
from app.routes.api_v1.qpg import router


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


def _make_question(
    qtype: QuestionType = QuestionType.MCQ,
    marks: int = 1,
    chapter: str = "Chapter 1",
) -> GeneratedQuestion:
    return GeneratedQuestion(
        question_text="What is Newton's first law?",
        question_type=qtype,
        marks=marks,
        difficulty="easy",
        chapter=chapter,
        topic="Laws of Motion",
        options=["A) Inertia", "B) Force", "C) Energy", "D) Momentum"] if qtype == QuestionType.MCQ else [],
        correct_answer="A",
        marking_scheme="State the law correctly (1 mark)",
        bloom_level="Remember",
    )


def _make_variant(label: str = "Set A", n_questions: int = 2) -> PaperVariant:
    return PaperVariant(
        variant_label=label,
        sections={
            "Section A": [_make_question() for _ in range(n_questions)],
        },
    )


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
    "chapters": ["Chapter 1: Laws of Motion", "Chapter 2: Work and Energy"],
    "difficulty_mix": {"easy": 30, "medium": 50, "hard": 20},
    "question_distribution": {"mcq": 2, "short": 1},
    "total_marks": 5,
    "duration_minutes": 30,
    "num_variants": 1,
    "include_answer_key": True,
    "include_marking_scheme": True,
}


# ── Test: single variant ──────────────────────────────────────────────────────

def test_single_variant_success():
    client_obj = _make_client()
    app = _build_app(client_obj)

    variant = _make_variant("Set A", n_questions=3)

    with (
        patch("app.routes.api_v1.qpg._credits") as mock_credits,
        patch("app.routes.api_v1.qpg._paper_service") as mock_svc,
        patch("app.routes.api_v1.qpg._cosmos") as mock_cosmos,
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=9_000)
        mock_svc.generate_structured = AsyncMock(return_value=([variant], 500, 300))
        mock_cosmos.log_query_usage = AsyncMock()

        with TestClient(app) as tc:
            resp = tc.post("/generate/question-paper", json=_BASE_REQUEST)

    assert resp.status_code == 200
    body = resp.json()
    assert body["request_id"]
    assert len(body["variants"]) == 1
    assert body["variants"][0]["variant_label"] == "Set A"
    assert len(body["variants"][0]["questions"]) == 3
    assert body["tokens_used"] == 800
    assert body["credits_consumed"] == 1  # ceil(800/1000) = 1
    assert body["credits_remaining"] == 9_000
    assert body["variants"][0]["answer_key"] is not None
    assert body["variants"][0]["marking_scheme"] is not None


# ── Test: multi-variant ───────────────────────────────────────────────────────

def test_multi_variant_returns_all_sets():
    client_obj = _make_client()
    app = _build_app(client_obj)

    variants = [_make_variant(f"Set {l}") for l in ["A", "B", "C"]]

    with (
        patch("app.routes.api_v1.qpg._credits") as mock_credits,
        patch("app.routes.api_v1.qpg._paper_service") as mock_svc,
        patch("app.routes.api_v1.qpg._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=8_000)
        mock_svc.generate_structured = AsyncMock(return_value=(variants, 1200, 600))

        req = {**_BASE_REQUEST, "num_variants": 3}
        with TestClient(app) as tc:
            resp = tc.post("/generate/question-paper", json=req)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["variants"]) == 3
    labels = [v["variant_label"] for v in body["variants"]]
    assert labels == ["Set A", "Set B", "Set C"]
    assert body["tokens_used"] == 1800

    # Pre-flight should have been called with 15 * 3 = 45
    mock_credits.check_and_reserve.assert_called_once_with("clnt_test_school", 45)


# ── Test: missing/empty chapters raises 400 ───────────────────────────────────

def test_missing_chapters_returns_400():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with (
        patch("app.routes.api_v1.qpg._credits") as mock_credits,
        patch("app.routes.api_v1.qpg._paper_service") as mock_svc,
        patch("app.routes.api_v1.qpg._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        # Service raises ValueError when chapters list yields no questions
        mock_svc.generate_structured = AsyncMock(
            side_effect=ValueError("Failed to generate questions for section 'Section A'")
        )

        req = {**_BASE_REQUEST, "chapters": ["Nonexistent Chapter 999"]}
        with TestClient(app) as tc:
            resp = tc.post("/generate/question-paper", json=req)

    assert resp.status_code == 400
    assert "Failed to generate" in resp.json()["detail"]


def test_empty_chapters_list_rejected_by_schema():
    client_obj = _make_client()
    app = _build_app(client_obj)

    req = {**_BASE_REQUEST, "chapters": []}
    with TestClient(app) as tc:
        resp = tc.post("/generate/question-paper", json=req)

    assert resp.status_code == 422


# ── Test: insufficient credits returns 402 ───────────────────────────────────

def test_insufficient_credits_returns_402():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with (
        patch("app.routes.api_v1.qpg._credits") as mock_credits,
        patch("app.routes.api_v1.qpg._paper_service") as mock_svc,
        patch("app.routes.api_v1.qpg._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=False)

        with TestClient(app) as tc:
            resp = tc.post("/generate/question-paper", json=_BASE_REQUEST)

    assert resp.status_code == 402
    assert "Insufficient credits" in resp.json()["detail"]
    # Service must NOT have been called — no AI work before credit check
    mock_svc.generate_structured.assert_not_called()


def test_insufficient_credits_multi_variant_uses_correct_estimate():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with (
        patch("app.routes.api_v1.qpg._credits") as mock_credits,
        patch("app.routes.api_v1.qpg._paper_service"),
        patch("app.routes.api_v1.qpg._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=False)

        req = {**_BASE_REQUEST, "num_variants": 3}
        with TestClient(app) as tc:
            resp = tc.post("/generate/question-paper", json=req)

    assert resp.status_code == 402
    # 15 credits × 3 variants = 45
    mock_credits.check_and_reserve.assert_called_once_with("clnt_test_school", 45)


# ── Test: invalid question type rejected ─────────────────────────────────────

def test_invalid_question_type_rejected():
    client_obj = _make_client()
    app = _build_app(client_obj)

    req = {**_BASE_REQUEST, "question_distribution": {"essay": 5}}
    with TestClient(app) as tc:
        resp = tc.post("/generate/question-paper", json=req)

    assert resp.status_code == 422


# ── Test: difficulty mix not summing to 100 rejected ─────────────────────────

def test_bad_difficulty_mix_rejected():
    client_obj = _make_client()
    app = _build_app(client_obj)

    req = {**_BASE_REQUEST, "difficulty_mix": {"easy": 50, "medium": 50, "hard": 10}}
    with TestClient(app) as tc:
        resp = tc.post("/generate/question-paper", json=req)

    assert resp.status_code == 422


# ── Test: answer_key / marking_scheme flags respected ────────────────────────

def test_no_answer_key_omitted_from_response():
    client_obj = _make_client()
    app = _build_app(client_obj)

    variant = _make_variant()
    with (
        patch("app.routes.api_v1.qpg._credits") as mock_credits,
        patch("app.routes.api_v1.qpg._paper_service") as mock_svc,
        patch("app.routes.api_v1.qpg._cosmos"),
    ):
        mock_credits.check_and_reserve = AsyncMock(return_value=True)
        mock_credits.deduct = AsyncMock(return_value=9_000)
        mock_svc.generate_structured = AsyncMock(return_value=([variant], 200, 100))

        req = {**_BASE_REQUEST, "include_answer_key": False, "include_marking_scheme": False}
        with TestClient(app) as tc:
            resp = tc.post("/generate/question-paper", json=req)

    assert resp.status_code == 200
    v = resp.json()["variants"][0]
    assert v["answer_key"] is None
    assert v["marking_scheme"] is None


# ── Test: PDF endpoint returns HTML ──────────────────────────────────────────

def test_pdf_endpoint_returns_html():
    client_obj = _make_client()
    app = _build_app(client_obj)

    question = {
        "number": 1,
        "type": "mcq",
        "text": "What is 2+2?",
        "marks": 1,
        "difficulty": "easy",
        "chapter_ref": "Chapter 1",
        "options": ["A) 3", "B) 4", "C) 5", "D) 6"],
    }
    pdf_req = {
        "variants": [
            {
                "variant_label": "Set A",
                "questions": [question],
                "answer_key": None,
                "marking_scheme": None,
            }
        ],
        "board": "cbse",
        "class_level": 10,
        "subject": "Maths",
        "exam_title": "Unit Test 1",
        "total_marks": 1,
        "duration_minutes": 10,
        "institute_name": "Test School",
    }

    with TestClient(app) as tc:
        resp = tc.post("/generate/question-paper/pdf", json=pdf_req)

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert "What is 2+2?" in body
    assert "Test School" in body
    assert "katex" in body  # KaTeX CDN present
