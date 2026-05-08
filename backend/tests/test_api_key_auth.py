"""
Tests for API key authentication and rate limiting.

Strategy:
- APIKeyService: tested directly (no I/O, no mocking).
- verify_api_key: called as an async function with the repo patched at the
  module level — fast, no HTTP server overhead for pure auth logic.
- rate_limit (429 path): uses TestClient + dependency_overrides so the full
  FastAPI request/response cycle is exercised including the Retry-After header.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.middleware.api_key_auth import verify_api_key
from app.middleware.rate_limiter import get_redis_client, rate_limit
from app.models.client import Client
from app.services.api_key_service import APIKeyService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_client(**overrides) -> Client:
    """Return a fully-populated Client fixture."""
    defaults = dict(
        client_id="clnt_test_school",
        org_name="Test School",
        contact_name="Ravi Tester",
        contact_phone="+919876543210",
        contact_email="ravi@testschool.com",
        api_key_hash="deadbeef" * 8,  # 64 hex chars
        api_key_prefix="jvb_live_a3",
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


# Minimal FastAPI app used only for rate-limit integration tests.
_test_app = FastAPI()


@_test_app.get("/api/v1/probe", dependencies=[Depends(verify_api_key), Depends(rate_limit)])
async def _probe():
    return {"ok": True}


# ── APIKeyService ─────────────────────────────────────────────────────────────

class TestAPIKeyService:
    def test_raw_key_format(self):
        raw, _, _ = APIKeyService.generate_api_key()
        assert raw.startswith("jvb_live_")
        assert len(raw) == len("jvb_live_") + 32
        assert raw[len("jvb_live_"):].isalnum()

    def test_hash_is_sha256_hex(self):
        _, key_hash, _ = APIKeyService.generate_api_key()
        assert len(key_hash) == 64
        int(key_hash, 16)  # raises ValueError if not valid hex

    def test_prefix_is_first_12_chars(self):
        raw, _, prefix = APIKeyService.generate_api_key()
        assert prefix == raw[:12]

    def test_hash_is_deterministic(self):
        raw, hash1, _ = APIKeyService.generate_api_key()
        hash2 = APIKeyService.hash_api_key(raw)
        assert hash1 == hash2

    def test_each_key_is_unique(self):
        keys = {APIKeyService.generate_api_key()[0] for _ in range(20)}
        assert len(keys) == 20


# ── verify_api_key ────────────────────────────────────────────────────────────

class TestVerifyAPIKey:
    """Direct async-function tests — no HTTP server needed."""

    @pytest.mark.asyncio
    async def test_missing_header_raises_401(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await verify_api_key(x_api_key=None)
        assert exc.value.status_code == 401
        assert "X-API-Key" in exc.value.detail or "API key" in exc.value.detail

    @pytest.mark.asyncio
    async def test_invalid_key_raises_401(self):
        from fastapi import HTTPException

        with patch(
            "app.middleware.api_key_auth._client_repo.get_client_by_api_key_hash",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(HTTPException) as exc:
                await verify_api_key(x_api_key="jvb_live_doesnotexist12345678901234")
            assert exc.value.status_code == 401
            assert exc.value.detail == "Invalid API key."

    @pytest.mark.asyncio
    async def test_suspended_client_raises_403(self):
        from fastapi import HTTPException

        suspended = _make_client(is_active=False)
        with patch(
            "app.middleware.api_key_auth._client_repo.get_client_by_api_key_hash",
            new=AsyncMock(return_value=suspended),
        ):
            with pytest.raises(HTTPException) as exc:
                await verify_api_key(x_api_key="jvb_live_validkeybutclientsuspended")
            assert exc.value.status_code == 403
            assert "suspended" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_valid_key_returns_client(self):
        active = _make_client()
        with patch(
            "app.middleware.api_key_auth._client_repo.get_client_by_api_key_hash",
            new=AsyncMock(return_value=active),
        ):
            result = await verify_api_key(x_api_key="jvb_live_validkey1234567890123456")
        assert result.client_id == active.client_id
        assert result.is_active is True


# ── rate_limit (429 path) ─────────────────────────────────────────────────────

class TestRateLimit:
    """
    Integration tests via TestClient.  We override verify_api_key to skip the
    Cosmos lookup and override get_redis_client to inject a mock Redis that
    simulates an exceeded sliding window.
    """

    def _client_with_override(self, active_client: Client, mock_redis):
        """Return a TestClient with both dependencies overridden."""
        app = _test_app

        async def _mock_auth():
            return active_client

        app.dependency_overrides[verify_api_key] = _mock_auth
        app.dependency_overrides[get_redis_client] = lambda: mock_redis
        return TestClient(app, raise_server_exceptions=False)

    def _make_redis_mock(self, *, minute_count: int, day_count: int) -> MagicMock:
        """Build an AsyncMock Redis whose pipeline simulates specific window counts."""
        mock_pipe = AsyncMock()
        # pipeline().execute() returns [zremrangebyscore, zadd, zcard, expire]
        # First call → minute window, second call → day window.
        mock_pipe.execute = AsyncMock(
            side_effect=[
                [None, 1, minute_count, True],  # minute window results
                [None, 1, day_count, True],     # day window results
            ]
        )
        mock_pipe.zremrangebyscore = MagicMock(return_value=mock_pipe)
        mock_pipe.zadd = MagicMock(return_value=mock_pipe)
        mock_pipe.zcard = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)

        mock_redis = MagicMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        return mock_redis

    def teardown_method(self, _):
        _test_app.dependency_overrides.clear()

    def test_valid_key_returns_200(self):
        active = _make_client()
        mock_redis = self._make_redis_mock(minute_count=1, day_count=1)
        client = self._client_with_override(active, mock_redis)
        resp = client.get("/api/v1/probe")
        assert resp.status_code == 200

    def test_per_minute_exceeded_returns_429(self):
        active = _make_client(rate_limit_per_minute=60)
        # minute_count > limit triggers 429; day check is never reached
        mock_redis = self._make_redis_mock(minute_count=61, day_count=1)
        client = self._client_with_override(active, mock_redis)
        resp = client.get("/api/v1/probe")
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "60"
        assert "minute" in resp.json()["detail"].lower()

    def test_per_day_exceeded_returns_429(self):
        active = _make_client(rate_limit_per_minute=60, rate_limit_per_day=50_000)
        # minute passes, day fails
        mock_redis = self._make_redis_mock(minute_count=1, day_count=50_001)
        client = self._client_with_override(active, mock_redis)
        resp = client.get("/api/v1/probe")
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "86400"
        assert "daily" in resp.json()["detail"].lower()
