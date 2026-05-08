"""
Tests for GET /api/v1/usage and GET /api/v1/usage/ledger.

Strategy:
- CreditService and LedgerRepository are patched at the module level inside
  api_v1.usage.
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
from app.models.client import Client, LedgerEntry
from app.routes.api_v1.usage import router


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
        credit_balance=5_000,
        credit_alert_threshold=1_000,
        is_active=True,
        rate_limit_per_minute=60,
        rate_limit_per_day=50_000,
        whatsapp_number="+919876543210",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Client(**defaults)


def _make_ledger_entry(
    entry_type: str = "consumption",
    credits: int = -5,
    balance_after: int = 4_995,
    feature: str = "chat_simple",
    **overrides,
) -> LedgerEntry:
    defaults = dict(
        ledger_id="ldg_" + "a" * 28,
        client_id="clnt_test_school",
        type=entry_type,
        credits=credits,
        balance_after=balance_after,
        feature=feature,
        tokens_input=200,
        tokens_output=80,
        request_id="req_abc123",
        created_by="system",
        created_at=datetime(2025, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return LedgerEntry(**defaults)


def _make_topup_entry(**overrides) -> LedgerEntry:
    defaults = dict(
        entry_type="topup",
        credits=10_000,
        balance_after=10_000,
        feature=None,
        tokens_input=None,
        tokens_output=None,
        amount_inr=5000,
        payment_ref="UTR123456",
        created_by="admin",
    )
    defaults.update(overrides)
    return _make_ledger_entry(**defaults)


_SUMMARY = {
    "by_feature": {
        "chat_simple": {"credits": 200, "tokens_input": 4000, "tokens_output": 1000, "count": 40},
        "dpp": {"credits": 50, "tokens_input": 800, "tokens_output": 600, "count": 5},
    },
    "total_credits": 250,
    "total_tokens": 6400,
    "daily_avg": 8.33,
    "forecast_eom": 200,
}


def _build_app(client: Client) -> FastAPI:
    app = FastAPI()

    async def _auth():
        return client

    async def _no_rate():
        pass

    app.dependency_overrides[verify_api_key] = _auth
    app.dependency_overrides[rate_limit] = _no_rate
    app.include_router(router, prefix="/usage")
    return app


# ── GET /usage ────────────────────────────────────────────────────────────────

def test_get_usage_success():
    client_obj = _make_client()
    app = _build_app(client_obj)
    topup = _make_topup_entry()

    with (
        patch("app.routes.api_v1.usage._credits") as mock_credits,
        patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger,
    ):
        mock_credits.get_balance = AsyncMock(return_value=4_800)
        mock_credits.get_consumption_summary = AsyncMock(return_value=_SUMMARY)
        mock_ledger.get_last_topup = AsyncMock(return_value=topup)

        with TestClient(app) as tc:
            resp = tc.get("/usage")

    assert resp.status_code == 200
    body = resp.json()
    assert body["client_id"] == "clnt_test_school"
    assert body["org_name"] == "Test School"
    assert body["plan_tier"] == "starter"
    assert body["credits_remaining"] == 4_800
    assert body["credits_alert_threshold"] == 1_000
    assert body["is_active"] is True
    assert body["rate_limits"] == {"per_minute": 60, "per_day": 50_000}
    assert body["daily_avg_credits"] == 8.33
    assert body["forecasted_eom_credits"] == 200
    assert body["consumption_30d"]["total_credits"] == 250
    assert body["consumption_30d"]["total_tokens"] == 6400
    assert "chat_simple" in body["consumption_30d"]["by_feature"]


def test_credits_remaining_comes_from_redis_not_cosmos_snapshot():
    """Live balance (Redis) overrides the stale client.credit_balance snapshot."""
    client_obj = _make_client(credit_balance=5_000)  # stale snapshot
    app = _build_app(client_obj)

    with (
        patch("app.routes.api_v1.usage._credits") as mock_credits,
        patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger,
    ):
        mock_credits.get_balance = AsyncMock(return_value=3_100)  # live Redis value
        mock_credits.get_consumption_summary = AsyncMock(return_value=_SUMMARY)
        mock_ledger.get_last_topup = AsyncMock(return_value=None)

        with TestClient(app) as tc:
            resp = tc.get("/usage")

    assert resp.json()["credits_remaining"] == 3_100  # Redis value, not 5_000


def test_estimated_days_remaining_correct_math():
    client_obj = _make_client()
    app = _build_app(client_obj)

    summary = {**_SUMMARY, "daily_avg": 100.0}

    with (
        patch("app.routes.api_v1.usage._credits") as mock_credits,
        patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger,
    ):
        mock_credits.get_balance = AsyncMock(return_value=1_500)
        mock_credits.get_consumption_summary = AsyncMock(return_value=summary)
        mock_ledger.get_last_topup = AsyncMock(return_value=None)

        with TestClient(app) as tc:
            resp = tc.get("/usage")

    # int(1500 / 100.0) = 15
    assert resp.json()["estimated_days_remaining"] == 15


def test_estimated_days_remaining_none_when_zero_avg():
    client_obj = _make_client()
    app = _build_app(client_obj)

    summary = {**_SUMMARY, "daily_avg": 0.0}

    with (
        patch("app.routes.api_v1.usage._credits") as mock_credits,
        patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger,
    ):
        mock_credits.get_balance = AsyncMock(return_value=5_000)
        mock_credits.get_consumption_summary = AsyncMock(return_value=summary)
        mock_ledger.get_last_topup = AsyncMock(return_value=None)

        with TestClient(app) as tc:
            resp = tc.get("/usage")

    assert resp.json()["estimated_days_remaining"] is None


def test_estimated_days_remaining_none_when_zero_balance():
    client_obj = _make_client()
    app = _build_app(client_obj)

    summary = {**_SUMMARY, "daily_avg": 50.0}

    with (
        patch("app.routes.api_v1.usage._credits") as mock_credits,
        patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger,
    ):
        mock_credits.get_balance = AsyncMock(return_value=0)
        mock_credits.get_consumption_summary = AsyncMock(return_value=summary)
        mock_ledger.get_last_topup = AsyncMock(return_value=None)

        with TestClient(app) as tc:
            resp = tc.get("/usage")

    assert resp.json()["estimated_days_remaining"] is None


def test_last_topup_none_when_no_topup_found():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with (
        patch("app.routes.api_v1.usage._credits") as mock_credits,
        patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger,
    ):
        mock_credits.get_balance = AsyncMock(return_value=5_000)
        mock_credits.get_consumption_summary = AsyncMock(return_value=_SUMMARY)
        mock_ledger.get_last_topup = AsyncMock(return_value=None)

        with TestClient(app) as tc:
            resp = tc.get("/usage")

    assert resp.json()["last_topup"] is None


def test_last_topup_fields_populated():
    client_obj = _make_client()
    app = _build_app(client_obj)
    topup = _make_topup_entry(
        payment_ref="UTR999888",
        credits=20_000,
        created_at=datetime(2025, 4, 10, 9, 0, 0, tzinfo=timezone.utc),
    )

    with (
        patch("app.routes.api_v1.usage._credits") as mock_credits,
        patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger,
    ):
        mock_credits.get_balance = AsyncMock(return_value=15_000)
        mock_credits.get_consumption_summary = AsyncMock(return_value=_SUMMARY)
        mock_ledger.get_last_topup = AsyncMock(return_value=topup)

        with TestClient(app) as tc:
            resp = tc.get("/usage")

    lt = resp.json()["last_topup"]
    assert lt is not None
    assert lt["credits"] == 20_000
    assert lt["payment_ref"] == "UTR999888"
    assert "2025-04-10" in lt["date"]


def test_usage_all_three_calls_made_in_parallel():
    """Verifies get_balance, get_consumption_summary, and get_last_topup are all called."""
    client_obj = _make_client()
    app = _build_app(client_obj)

    with (
        patch("app.routes.api_v1.usage._credits") as mock_credits,
        patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger,
    ):
        mock_credits.get_balance = AsyncMock(return_value=1_000)
        mock_credits.get_consumption_summary = AsyncMock(return_value=_SUMMARY)
        mock_ledger.get_last_topup = AsyncMock(return_value=None)

        with TestClient(app) as tc:
            resp = tc.get("/usage")

    assert resp.status_code == 200
    mock_credits.get_balance.assert_called_once_with("clnt_test_school")
    mock_credits.get_consumption_summary.assert_called_once_with("clnt_test_school", days=30)
    mock_ledger.get_last_topup.assert_called_once_with("clnt_test_school")


# ── GET /usage/ledger ─────────────────────────────────────────────────────────

def test_get_ledger_success():
    client_obj = _make_client()
    app = _build_app(client_obj)
    entries = [_make_ledger_entry() for _ in range(3)]

    with patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger:
        mock_ledger.get_entries_for_client = AsyncMock(return_value=entries)

        with TestClient(app) as tc:
            resp = tc.get("/usage/ledger")

    assert resp.status_code == 200
    body = resp.json()
    assert body["client_id"] == "clnt_test_school"
    assert body["count"] == 3
    assert len(body["entries"]) == 3
    e = body["entries"][0]
    assert e["ledger_id"] == entries[0].ledger_id
    assert e["type"] == "consumption"
    assert e["credits"] == -5
    assert e["balance_after"] == 4_995
    assert e["feature"] == "chat_simple"
    assert "2025-05-01" in e["created_at"]


def test_get_ledger_default_limit_is_50():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger:
        mock_ledger.get_entries_for_client = AsyncMock(return_value=[])

        with TestClient(app) as tc:
            tc.get("/usage/ledger")

    mock_ledger.get_entries_for_client.assert_called_once_with(
        "clnt_test_school", limit=50, before=None
    )


def test_get_ledger_custom_limit():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger:
        mock_ledger.get_entries_for_client = AsyncMock(return_value=[])

        with TestClient(app) as tc:
            tc.get("/usage/ledger?limit=10")

    mock_ledger.get_entries_for_client.assert_called_once_with(
        "clnt_test_school", limit=10, before=None
    )


def test_get_ledger_before_param_parsed_correctly():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger:
        mock_ledger.get_entries_for_client = AsyncMock(return_value=[])

        with TestClient(app) as tc:
            tc.get("/usage/ledger?before=2025-04-01T00%3A00%3A00Z")

    call_kwargs = mock_ledger.get_entries_for_client.call_args
    before_dt = call_kwargs.kwargs.get("before") or call_kwargs.args[2]
    assert before_dt is not None
    assert before_dt.year == 2025
    assert before_dt.month == 4
    assert before_dt.day == 1


def test_get_ledger_invalid_before_returns_400():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger:
        mock_ledger.get_entries_for_client = AsyncMock(return_value=[])

        with TestClient(app) as tc:
            resp = tc.get("/usage/ledger?before=not-a-date")

    assert resp.status_code == 400
    assert "Invalid 'before'" in resp.json()["detail"]


def test_get_ledger_has_more_true_when_full_page():
    """has_more=True when the repo returns exactly limit entries."""
    client_obj = _make_client()
    app = _build_app(client_obj)
    entries = [
        _make_ledger_entry(
            ledger_id=f"ldg_{i:032d}",
            created_at=datetime(2025, 5, 1, 12, i, 0, tzinfo=timezone.utc),
        )
        for i in range(5)
    ]

    with patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger:
        mock_ledger.get_entries_for_client = AsyncMock(return_value=entries)

        with TestClient(app) as tc:
            resp = tc.get("/usage/ledger?limit=5")

    body = resp.json()
    assert body["has_more"] is True
    assert body["next_before"] is not None
    # cursor points at the oldest (last) returned entry
    assert "2025-05-01" in body["next_before"]


def test_get_ledger_has_more_false_when_partial_page():
    """has_more=False when the repo returns fewer entries than limit."""
    client_obj = _make_client()
    app = _build_app(client_obj)
    entries = [_make_ledger_entry() for _ in range(3)]

    with patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger:
        mock_ledger.get_entries_for_client = AsyncMock(return_value=entries)

        with TestClient(app) as tc:
            resp = tc.get("/usage/ledger?limit=10")

    body = resp.json()
    assert body["has_more"] is False
    assert body["next_before"] is None


def test_get_ledger_empty_returns_zero_count():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger:
        mock_ledger.get_entries_for_client = AsyncMock(return_value=[])

        with TestClient(app) as tc:
            resp = tc.get("/usage/ledger")

    body = resp.json()
    assert body["count"] == 0
    assert body["entries"] == []
    assert body["has_more"] is False
    assert body["next_before"] is None


def test_get_ledger_limit_above_max_rejected():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with patch("app.routes.api_v1.usage._ledger_repo"):
        with TestClient(app) as tc:
            resp = tc.get("/usage/ledger?limit=500")

    assert resp.status_code == 422


def test_get_ledger_limit_zero_rejected():
    client_obj = _make_client()
    app = _build_app(client_obj)

    with patch("app.routes.api_v1.usage._ledger_repo"):
        with TestClient(app) as tc:
            resp = tc.get("/usage/ledger?limit=0")

    assert resp.status_code == 422


def test_get_ledger_topup_entry_fields():
    """Topup entries expose amount_inr and payment_ref; feature/tokens are null."""
    client_obj = _make_client()
    app = _build_app(client_obj)
    topup = _make_topup_entry()

    with patch("app.routes.api_v1.usage._ledger_repo") as mock_ledger:
        mock_ledger.get_entries_for_client = AsyncMock(return_value=[topup])

        with TestClient(app) as tc:
            resp = tc.get("/usage/ledger")

    e = resp.json()["entries"][0]
    assert e["type"] == "topup"
    assert e["credits"] == 10_000
    assert e["amount_inr"] == 5000
    assert e["payment_ref"] == "UTR123456"
    assert e["feature"] is None
    assert e["tokens_input"] is None
