"""
Tests for all /admin/* routes.

Strategy:
- Dependency-inject mocked repos / services so no Azure credentials are needed.
- Override get_current_admin for authenticated routes.
- Only test HTTP contract (status codes, response shape, side-effect calls).
- bcrypt hashing is tested against a pre-computed hash for speed.

Run with:
    cd backend
    pytest tests/test_admin_routes.py -v
"""
import bcrypt
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

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
from app.models.client import Client, LedgerEntry

_TEST_PASSWORD = "testpassword123"
_TEST_HASH = bcrypt.hashpw(_TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()

_NOW = datetime.now(timezone.utc)


def _make_client(**overrides) -> Client:
    defaults = dict(
        client_id="clnt_test_abc12345",
        org_name="Test Org",
        contact_name="Alice",
        contact_phone="+919876543210",
        contact_email="alice@testorg.com",
        api_key_hash="deadbeef" * 8,
        api_key_prefix="jvb_live_",
        plan_tier="starter",
        credit_balance=5000,
        credit_alert_threshold=2000,
        is_active=True,
        rate_limit_per_minute=60,
        rate_limit_per_day=50000,
        whatsapp_number="+919876543210",
        notes=None,
        created_at=_NOW,
        updated_at=_NOW,
    )
    return Client(**{**defaults, **overrides})


def _make_ledger_entry(**overrides) -> LedgerEntry:
    defaults = dict(
        ledger_id="led-001",
        client_id="clnt_test_abc12345",
        type="topup",
        credits=1000,
        balance_after=6000,
        amount_inr=500,
        payment_ref="UTR123",
        note="Test topup",
        created_by="admin",
        created_at=_NOW,
    )
    return LedgerEntry(**{**defaults, **overrides})


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    """Inject test admin credentials into settings before each test."""
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", _TEST_HASH)
    monkeypatch.setenv("ADMIN_JWT_SECRET", "test-secret-32-chars-minimum-ok!")
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
    return repo


@pytest.fixture()
def mock_ledger_repo():
    repo = MagicMock()
    repo.get_entries_for_client = AsyncMock(return_value=[_make_ledger_entry()])
    return repo


@pytest.fixture()
def mock_credit_svc():
    svc = MagicMock()
    svc.get_balance = AsyncMock(return_value=5000)
    svc.topup = AsyncMock(return_value=6000)
    svc.adjust = AsyncMock(return_value=4500)
    svc.get_consumption_summary = AsyncMock(
        return_value={"by_feature": {}, "total_credits": 0, "total_tokens": 0, "daily_avg": 0.0, "forecast_eom": 0}
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
            "total_credits_sold": 10000,
            "total_credits_consumed": 4500,
            "total_revenue_inr": 5000,
            "by_client": {"clnt_test_abc12345": 4500},
        }
    )
    repo.get_client_consumption_since = AsyncMock(
        return_value={"clnt_test_abc12345": 700}  # 100/day over 7 days
    )
    return repo


@pytest.fixture()
def authed_client(mock_client_repo, mock_ledger_repo, mock_credit_svc, mock_audit_repo, mock_analytics_repo):
    """TestClient with all deps mocked and admin auth bypassed."""
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
def unauthed_client():
    """TestClient with all repo deps mocked but NO auth override (tests 401 paths)."""
    mock_audit = MagicMock()
    mock_audit.log = AsyncMock(return_value=None)
    app.dependency_overrides[get_audit_repo] = lambda: mock_audit
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ── Auth tests ────────────────────────────────────────────────────────────────


class TestLogin:
    def test_login_success(self, unauthed_client):
        r = unauthed_client.post("/admin/auth/login", json={"username": "admin", "password": _TEST_PASSWORD})
        assert r.status_code == 200
        body = r.json()
        assert "token" in body
        assert "expires_at" in body

    def test_login_wrong_password(self, unauthed_client):
        r = unauthed_client.post("/admin/auth/login", json={"username": "admin", "password": "wrongpassword"})
        assert r.status_code == 401

    def test_login_wrong_username(self, unauthed_client):
        r = unauthed_client.post("/admin/auth/login", json={"username": "hacker", "password": _TEST_PASSWORD})
        assert r.status_code == 401

    def test_logout(self, authed_client):
        r = authed_client.post("/admin/auth/logout")
        assert r.status_code == 200

    def test_me_authenticated(self, authed_client):
        r = authed_client.get("/admin/auth/me")
        assert r.status_code == 200
        assert r.json()["username"] == "admin"

    def test_me_unauthenticated(self, unauthed_client):
        r = unauthed_client.get("/admin/auth/me")
        assert r.status_code == 401


# ── Client list / create tests ────────────────────────────────────────────────


class TestClientList:
    def test_list_clients_default(self, authed_client, mock_client_repo):
        r = authed_client.get("/admin/clients")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert data[0]["client_id"] == "clnt_test_abc12345"
        mock_client_repo.list_clients.assert_called_once_with(active_only=True)

    def test_list_clients_all(self, authed_client, mock_client_repo):
        r = authed_client.get("/admin/clients?active_only=false")
        assert r.status_code == 200
        mock_client_repo.list_clients.assert_called_once_with(active_only=False)

    def test_list_clients_unauthenticated(self, unauthed_client):
        r = unauthed_client.get("/admin/clients")
        assert r.status_code == 401


class TestClientCreate:
    def _payload(self):
        return {
            "org_name": "IIT JEE Ahmedabad",
            "contact_name": "Raj",
            "contact_phone": "+919876543210",
            "contact_email": "raj@iitjee.com",
            "plan_tier": "starter",
            "rate_limit_per_minute": 60,
            "rate_limit_per_day": 50000,
            "credit_alert_threshold": 2000,
            "whatsapp_number": "+919876543210",
        }

    def test_create_client_success(self, authed_client, mock_client_repo, mock_audit_repo):
        r = authed_client.post("/admin/clients", json=self._payload())
        assert r.status_code == 201
        body = r.json()
        assert "raw_api_key" in body
        assert body["raw_api_key"].startswith("jvb_live_")
        assert "client" in body
        mock_audit_repo.log.assert_called_once()

    def test_create_client_missing_field(self, authed_client):
        payload = self._payload()
        del payload["org_name"]
        r = authed_client.post("/admin/clients", json=payload)
        assert r.status_code == 422

    def test_create_client_invalid_email(self, authed_client):
        payload = self._payload()
        payload["contact_email"] = "not-an-email"
        r = authed_client.post("/admin/clients", json=payload)
        assert r.status_code == 422

    def test_create_client_unauthenticated(self, unauthed_client):
        r = unauthed_client.post("/admin/clients", json=self._payload())
        assert r.status_code == 401


class TestClientDetail:
    def test_get_client_found(self, authed_client, mock_credit_svc):
        r = authed_client.get("/admin/clients/clnt_test_abc12345")
        assert r.status_code == 200
        body = r.json()
        assert "client" in body
        assert "ledger" in body
        assert "usage_summary" in body
        assert body["client"]["credit_balance"] == 5000

    def test_get_client_not_found(self, authed_client, mock_client_repo):
        mock_client_repo.get_client_by_id = AsyncMock(return_value=None)
        r = authed_client.get("/admin/clients/clnt_missing")
        assert r.status_code == 404

    def test_get_client_unauthenticated(self, unauthed_client):
        r = unauthed_client.get("/admin/clients/clnt_test_abc12345")
        assert r.status_code == 401


class TestClientUpdate:
    def test_update_client_success(self, authed_client, mock_audit_repo):
        r = authed_client.put(
            "/admin/clients/clnt_test_abc12345",
            json={"contact_name": "Bob", "plan_tier": "growth"},
        )
        assert r.status_code == 200
        mock_audit_repo.log.assert_called_once()

    def test_update_client_no_fields(self, authed_client):
        r = authed_client.put("/admin/clients/clnt_test_abc12345", json={})
        assert r.status_code == 422

    def test_update_client_not_found(self, authed_client, mock_client_repo):
        mock_client_repo.get_client_by_id = AsyncMock(return_value=None)
        r = authed_client.put("/admin/clients/clnt_missing", json={"notes": "hi"})
        assert r.status_code == 404


class TestRotateKey:
    def test_rotate_key_success(self, authed_client, mock_audit_repo):
        r = authed_client.post("/admin/clients/clnt_test_abc12345/rotate-key")
        assert r.status_code == 200
        body = r.json()
        assert "new_raw_api_key" in body
        assert body["new_raw_api_key"].startswith("jvb_live_")
        mock_audit_repo.log.assert_called_once()

    def test_rotate_key_not_found(self, authed_client, mock_client_repo):
        mock_client_repo.get_client_by_id = AsyncMock(return_value=None)
        r = authed_client.post("/admin/clients/clnt_missing/rotate-key")
        assert r.status_code == 404


class TestSuspendReactivate:
    def test_suspend_active_client(self, authed_client, mock_audit_repo):
        r = authed_client.post("/admin/clients/clnt_test_abc12345/suspend")
        assert r.status_code == 200
        assert r.json()["is_active"] is False
        mock_audit_repo.log.assert_called_once()

    def test_suspend_already_inactive(self, authed_client, mock_client_repo):
        mock_client_repo.get_client_by_id = AsyncMock(return_value=_make_client(is_active=False))
        r = authed_client.post("/admin/clients/clnt_test_abc12345/suspend")
        assert r.status_code == 409

    def test_suspend_not_found(self, authed_client, mock_client_repo):
        mock_client_repo.get_client_by_id = AsyncMock(return_value=None)
        r = authed_client.post("/admin/clients/clnt_missing/suspend")
        assert r.status_code == 404

    def test_reactivate_inactive_with_balance(self, authed_client, mock_client_repo, mock_credit_svc, mock_audit_repo):
        mock_client_repo.get_client_by_id = AsyncMock(return_value=_make_client(is_active=False))
        mock_credit_svc.get_balance = AsyncMock(return_value=5000)
        r = authed_client.post("/admin/clients/clnt_test_abc12345/reactivate")
        assert r.status_code == 200
        assert r.json()["is_active"] is True
        mock_audit_repo.log.assert_called_once()

    def test_reactivate_with_zero_balance(self, authed_client, mock_client_repo, mock_credit_svc):
        mock_client_repo.get_client_by_id = AsyncMock(return_value=_make_client(is_active=False))
        mock_credit_svc.get_balance = AsyncMock(return_value=0)
        r = authed_client.post("/admin/clients/clnt_test_abc12345/reactivate")
        assert r.status_code == 400

    def test_reactivate_already_active(self, authed_client):
        r = authed_client.post("/admin/clients/clnt_test_abc12345/reactivate")
        assert r.status_code == 409


# ── Credits tests ─────────────────────────────────────────────────────────────


class TestTopup:
    def test_topup_success(self, authed_client, mock_audit_repo):
        r = authed_client.post(
            "/admin/clients/clnt_test_abc12345/topup",
            json={"credits": 5000, "amount_inr": 2500, "payment_ref": "UTR123456", "note": "Monthly"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["credits_added"] == 5000
        assert body["new_balance"] == 6000
        mock_audit_repo.log.assert_called_once()

    def test_topup_zero_credits_rejected(self, authed_client):
        r = authed_client.post(
            "/admin/clients/clnt_test_abc12345/topup",
            json={"credits": 0, "amount_inr": 0, "payment_ref": ""},
        )
        assert r.status_code == 422

    def test_topup_negative_credits_rejected(self, authed_client):
        r = authed_client.post(
            "/admin/clients/clnt_test_abc12345/topup",
            json={"credits": -100, "amount_inr": 0, "payment_ref": ""},
        )
        assert r.status_code == 422

    def test_topup_client_not_found(self, authed_client, mock_client_repo):
        mock_client_repo.get_client_by_id = AsyncMock(return_value=None)
        r = authed_client.post(
            "/admin/clients/clnt_missing/topup",
            json={"credits": 1000, "amount_inr": 500, "payment_ref": "UTR1"},
        )
        assert r.status_code == 404

    def test_topup_unauthenticated(self, unauthed_client):
        r = unauthed_client.post(
            "/admin/clients/clnt_test_abc12345/topup",
            json={"credits": 1000, "amount_inr": 500, "payment_ref": "UTR1"},
        )
        assert r.status_code == 401


class TestAdjust:
    def test_adjust_positive(self, authed_client, mock_audit_repo):
        r = authed_client.post(
            "/admin/clients/clnt_test_abc12345/adjust",
            json={"credits": 500, "reason": "Goodwill credit"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["credits_delta"] == 500
        assert "new_balance" in body
        mock_audit_repo.log.assert_called_once()

    def test_adjust_negative(self, authed_client):
        r = authed_client.post(
            "/admin/clients/clnt_test_abc12345/adjust",
            json={"credits": -200, "reason": "Correction for overbilling"},
        )
        assert r.status_code == 200
        assert r.json()["credits_delta"] == -200

    def test_adjust_zero_rejected(self, authed_client):
        r = authed_client.post(
            "/admin/clients/clnt_test_abc12345/adjust",
            json={"credits": 0, "reason": "No-op"},
        )
        assert r.status_code == 422

    def test_adjust_client_not_found(self, authed_client, mock_client_repo):
        mock_client_repo.get_client_by_id = AsyncMock(return_value=None)
        r = authed_client.post(
            "/admin/clients/clnt_missing/adjust",
            json={"credits": 100, "reason": "Test"},
        )
        assert r.status_code == 404


class TestLedger:
    def test_get_ledger_success(self, authed_client):
        r = authed_client.get("/admin/clients/clnt_test_abc12345/ledger")
        assert r.status_code == 200
        body = r.json()
        assert "entries" in body
        assert body["count"] == 1
        assert body["entries"][0]["type"] == "topup"

    def test_get_ledger_with_limit(self, authed_client, mock_ledger_repo):
        r = authed_client.get("/admin/clients/clnt_test_abc12345/ledger?limit=50")
        assert r.status_code == 200
        mock_ledger_repo.get_entries_for_client.assert_called_once_with(
            client_id="clnt_test_abc12345", limit=50, before=None
        )

    def test_get_ledger_client_not_found(self, authed_client, mock_client_repo):
        mock_client_repo.get_client_by_id = AsyncMock(return_value=None)
        r = authed_client.get("/admin/clients/clnt_missing/ledger")
        assert r.status_code == 404

    def test_get_ledger_unauthenticated(self, unauthed_client):
        r = unauthed_client.get("/admin/clients/clnt_test_abc12345/ledger")
        assert r.status_code == 401


# ── Analytics tests ───────────────────────────────────────────────────────────


class TestAnalyticsOverview:
    def test_overview_success(self, authed_client):
        r = authed_client.get("/admin/analytics/overview")
        assert r.status_code == 200
        body = r.json()
        assert body["total_clients"] == 1
        assert body["active_clients"] == 1
        assert body["total_credits_sold_30d"] == 10000
        assert body["total_credits_consumed_30d"] == 4500
        assert body["total_revenue_inr_30d"] == 5000
        assert isinstance(body["top_5_clients_by_consumption"], list)

    def test_overview_unauthenticated(self, unauthed_client):
        r = unauthed_client.get("/admin/analytics/overview")
        assert r.status_code == 401


class TestClientsBurningFast:
    def test_burning_fast_below_threshold(self, authed_client):
        # mock: 700 credits consumed in 7 days = 100/day avg; balance=5000 → 50 days → NOT at risk
        r = authed_client.get("/admin/analytics/clients-burning-fast")
        assert r.status_code == 200
        # 5000 / 100 = 50 days remaining → not in the list
        assert r.json() == []

    def test_burning_fast_above_threshold(self, authed_client, mock_analytics_repo, mock_client_repo):
        # high burn: 6300 credits in 7 days = 900/day; balance=5000 → 5.5 days → AT RISK
        mock_analytics_repo.get_client_consumption_since = AsyncMock(
            return_value={"clnt_test_abc12345": 6300}
        )
        r = authed_client.get("/admin/analytics/clients-burning-fast")
        assert r.status_code == 200
        result = r.json()
        assert len(result) == 1
        assert result[0]["client_id"] == "clnt_test_abc12345"
        assert result[0]["days_remaining"] < 7

    def test_burning_fast_no_consumption(self, authed_client, mock_analytics_repo):
        # zero consumption → skip (not at risk by definition)
        mock_analytics_repo.get_client_consumption_since = AsyncMock(return_value={})
        r = authed_client.get("/admin/analytics/clients-burning-fast")
        assert r.status_code == 200
        assert r.json() == []

    def test_burning_fast_unauthenticated(self, unauthed_client):
        r = unauthed_client.get("/admin/analytics/clients-burning-fast")
        assert r.status_code == 401
