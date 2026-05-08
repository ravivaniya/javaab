"""
Tests for CreditService.

Mocks out Redis and Cosmos repositories so tests run without Azure credentials.
Background asyncio tasks are flushed by awaiting asyncio.sleep(0) after each call.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.services.credit_service import CreditService, tokens_to_credits


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_client(*, is_active: bool = True, credit_alert_threshold: int = 2000) -> MagicMock:
    client = MagicMock()
    client.is_active = is_active
    client.credit_alert_threshold = credit_alert_threshold
    client.whatsapp_number = "+919999999999"
    return client


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Minimal Redis mock that behaves like a real counter for INCRBY/DECRBY."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.incrby = AsyncMock(return_value=6000)
    redis.decrby = AsyncMock(return_value=4900)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def mock_ledger_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_balance_from_ledger = AsyncMock(return_value=5000)
    repo.append_entry = AsyncMock(return_value=None)
    repo.get_consumption_breakdown = AsyncMock(return_value={})
    return repo


@pytest.fixture
def mock_client_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.update_balance_cache = AsyncMock(return_value=None)
    repo.deactivate_client = AsyncMock(return_value=None)
    repo.update_client = AsyncMock(return_value=None)
    repo.get_client_by_id = AsyncMock(return_value=_make_client())
    return repo


@pytest.fixture
def service(mock_redis, mock_ledger_repo, mock_client_repo) -> CreditService:
    svc = CreditService()
    # Inject mocks directly so we bypass lazy-init
    svc._redis = mock_redis
    svc._redis_init_attempted = True
    svc._redis_available = True
    svc._ledger_repo = mock_ledger_repo
    svc._client_repo = mock_client_repo
    return svc


async def _drain() -> None:
    """Yield control so pending asyncio tasks (background ledger writes) can run."""
    for _ in range(5):
        await asyncio.sleep(0)


# ── Token conversion ──────────────────────────────────────────────────────────


def test_tokens_to_credits_rounds_up():
    assert tokens_to_credits(1) == 1       # minimum 1
    assert tokens_to_credits(999) == 1
    assert tokens_to_credits(1000) == 1
    assert tokens_to_credits(1001) == 2
    assert tokens_to_credits(5000) == 5


# ── Topup ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_topup_increases_balance(service, mock_redis, mock_ledger_repo):
    """topup calls Redis INCRBY and writes a ledger entry."""
    mock_redis.incrby = AsyncMock(return_value=6000)

    new_balance = await service.topup(
        client_id="clnt_test",
        credits=1000,
        amount_inr=500,
        payment_ref="UTR123",
        note="Initial load",
        admin_user="admin@javaab.in",
    )

    assert new_balance == 6000
    mock_redis.incrby.assert_called_once_with("client:clnt_test:credits", 1000)

    await _drain()
    mock_ledger_repo.append_entry.assert_called_once()
    entry = mock_ledger_repo.append_entry.call_args[0][0]
    assert entry.type == "topup"
    assert entry.credits == 1000
    assert entry.balance_after == 6000
    assert entry.client_id == "clnt_test"
    assert entry.payment_ref == "UTR123"
    assert entry.created_by == "admin@javaab.in"


# ── Deduct ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_deduct_decreases_balance(service, mock_redis, mock_ledger_repo):
    """deduct calls Redis DECRBY and writes a consumption ledger entry."""
    mock_redis.set = AsyncMock(return_value=True)   # dedup key not yet set
    mock_redis.decrby = AsyncMock(return_value=4900)

    new_balance = await service.deduct(
        client_id="clnt_test",
        credits=100,
        feature="chat_simple",
        tokens_input=800,
        tokens_output=200,
        request_id="req_abc123",
    )

    assert new_balance == 4900
    mock_redis.decrby.assert_called_once_with("client:clnt_test:credits", 100)

    await _drain()
    mock_ledger_repo.append_entry.assert_called_once()
    entry = mock_ledger_repo.append_entry.call_args[0][0]
    assert entry.type == "consumption"
    assert entry.credits == -100
    assert entry.balance_after == 4900
    assert entry.feature == "chat_simple"
    assert entry.tokens_input == 800
    assert entry.tokens_output == 200
    assert entry.request_id == "req_abc123"


@pytest.mark.asyncio
async def test_deduct_idempotent_on_duplicate_request_id(service, mock_redis, mock_ledger_repo):
    """Duplicate request_id returns current balance without a second deduction."""
    mock_redis.set = AsyncMock(return_value=None)   # NX failed → already processed
    mock_redis.get = AsyncMock(return_value="4900")

    new_balance = await service.deduct(
        client_id="clnt_test",
        credits=100,
        feature="chat_simple",
        tokens_input=800,
        tokens_output=200,
        request_id="req_already_done",
    )

    assert new_balance == 4900
    mock_redis.decrby.assert_not_called()

    await _drain()
    mock_ledger_repo.append_entry.assert_not_called()


@pytest.mark.asyncio
async def test_deduct_below_zero_triggers_suspension(service, mock_redis, mock_client_repo):
    """When Redis DECRBY results in balance <= 0, deactivate_client is called."""
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.decrby = AsyncMock(return_value=0)

    await service.deduct(
        client_id="clnt_broke",
        credits=5000,
        feature="chat_complex",
        tokens_input=3000,
        tokens_output=2000,
        request_id="req_last_one",
    )

    await _drain()
    mock_client_repo.deactivate_client.assert_called_once_with(
        "clnt_broke", reason="zero_balance_auto_suspension"
    )


@pytest.mark.asyncio
async def test_deduct_negative_balance_also_suspends(service, mock_redis, mock_client_repo):
    """Balance going negative (e.g. race) also triggers suspension."""
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.decrby = AsyncMock(return_value=-50)

    await service.deduct(
        client_id="clnt_neg",
        credits=100,
        feature="chat_simple",
        tokens_input=100,
        tokens_output=100,
        request_id="req_neg",
    )

    await _drain()
    mock_client_repo.deactivate_client.assert_called_once()


@pytest.mark.asyncio
async def test_deduct_below_threshold_triggers_alert(service, mock_redis, mock_client_repo):
    """
    When balance drops below credit_alert_threshold after a deduction,
    the low-credit sentinel key is set in Redis (alert would fire via WhatsApp).
    """
    mock_client_repo.get_client_by_id = AsyncMock(
        return_value=_make_client(credit_alert_threshold=2000)
    )
    # Balance after deduction: 1500 (below threshold of 2000)
    mock_redis.set = AsyncMock(return_value=True)   # both dedup NX and sentinel NX succeed
    mock_redis.decrby = AsyncMock(return_value=1500)
    mock_redis.get = AsyncMock(return_value=None)   # sentinel not yet set

    await service.deduct(
        client_id="clnt_low",
        credits=500,
        feature="chat_medium",
        tokens_input=400,
        tokens_output=100,
        request_id="req_low_credit",
    )

    await _drain()

    sentinel_key = "client:clnt_low:low_credit_alert"
    # Verify the sentinel was set at some point during the background tasks
    set_keys = [c.args[0] for c in mock_redis.set.call_args_list]
    assert sentinel_key in set_keys


@pytest.mark.asyncio
async def test_deduct_does_not_alert_above_threshold(service, mock_redis, mock_client_repo):
    """No alert fires when balance remains above the threshold."""
    mock_client_repo.get_client_by_id = AsyncMock(
        return_value=_make_client(credit_alert_threshold=2000)
    )
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.decrby = AsyncMock(return_value=3000)
    mock_redis.get = AsyncMock(return_value=None)

    await service.deduct(
        client_id="clnt_ok",
        credits=100,
        feature="chat_simple",
        tokens_input=100,
        tokens_output=100,
        request_id="req_ok",
    )

    await _drain()

    sentinel_key = "client:clnt_ok:low_credit_alert"
    set_keys = [c.args[0] for c in mock_redis.set.call_args_list]
    assert sentinel_key not in set_keys


# ── Reconcile ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconcile_from_ledger_sets_redis(service, mock_redis, mock_ledger_repo):
    """reconcile_from_ledger reads the ledger SUM and writes it to Redis."""
    mock_ledger_repo.get_balance_from_ledger = AsyncMock(return_value=7500)

    balance = await service.reconcile_from_ledger("clnt_repair")

    assert balance == 7500
    mock_ledger_repo.get_balance_from_ledger.assert_called_once_with("clnt_repair")
    mock_redis.set.assert_called_once_with("client:clnt_repair:credits", 7500)


@pytest.mark.asyncio
async def test_get_balance_reconciles_on_redis_miss(service, mock_redis, mock_ledger_repo):
    """get_balance triggers reconciliation when Redis returns None."""
    mock_redis.get = AsyncMock(return_value=None)
    mock_ledger_repo.get_balance_from_ledger = AsyncMock(return_value=3000)

    balance = await service.get_balance("clnt_miss")

    assert balance == 3000
    mock_redis.set.assert_called_with("client:clnt_miss:credits", 3000)


@pytest.mark.asyncio
async def test_get_balance_returns_redis_value_when_present(service, mock_redis):
    """get_balance returns the Redis value directly when the key exists."""
    mock_redis.get = AsyncMock(return_value="8200")

    balance = await service.get_balance("clnt_cached")

    assert balance == 8200


# ── Reactivation ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_topup_reactivates_suspended_client(service, mock_redis, mock_client_repo):
    """A topup on a suspended (is_active=False) client reactivates them."""
    mock_client_repo.get_client_by_id = AsyncMock(
        return_value=_make_client(is_active=False)
    )
    mock_redis.incrby = AsyncMock(return_value=5000)

    await service.topup(
        client_id="clnt_suspended",
        credits=5000,
        amount_inr=2500,
        payment_ref="UTR999",
        note="Recharge",
        admin_user="admin@javaab.in",
    )

    await _drain()
    mock_client_repo.update_client.assert_called_once_with(
        "clnt_suspended",
        {"is_active": True, "notes": "Reactivated after topup"},
    )


@pytest.mark.asyncio
async def test_topup_does_not_reactivate_active_client(service, mock_redis, mock_client_repo):
    """topup on an already-active client does not call update_client."""
    mock_client_repo.get_client_by_id = AsyncMock(
        return_value=_make_client(is_active=True)
    )
    mock_redis.incrby = AsyncMock(return_value=6000)

    await service.topup(
        client_id="clnt_active",
        credits=1000,
        amount_inr=500,
        payment_ref="UTR001",
        note="Renewal",
        admin_user="admin@javaab.in",
    )

    await _drain()
    mock_client_repo.update_client.assert_not_called()


# ── Concurrent deductions ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_concurrent_deductions_no_race_condition():
    """
    Concurrent deductions should produce a consistent final balance.
    We simulate Redis atomicity with an asyncio.Lock-guarded counter.
    """
    balance_state = {"value": 10000}
    lock = asyncio.Lock()
    dedup_seen: set = set()

    async def mock_decrby(key: str, amount: int) -> int:
        async with lock:
            balance_state["value"] -= amount
            return balance_state["value"]

    async def mock_set_dedup(key: str, value: str, nx: bool = False, ex: int = 0) -> object:
        if nx:
            if key in dedup_seen:
                return None   # already set
            dedup_seen.add(key)
            return True
        return True

    async def mock_get(_key: str):
        return None

    mock_redis = AsyncMock()
    mock_redis.decrby = mock_decrby
    mock_redis.set = mock_set_dedup
    mock_redis.get = mock_get

    mock_ledger = AsyncMock()
    mock_ledger.append_entry = AsyncMock(return_value=None)
    mock_ledger.get_balance_from_ledger = AsyncMock(return_value=10000)

    mock_clients = AsyncMock()
    mock_clients.update_balance_cache = AsyncMock(return_value=None)
    mock_clients.deactivate_client = AsyncMock(return_value=None)
    mock_clients.get_client_by_id = AsyncMock(return_value=_make_client())

    svc = CreditService()
    svc._redis = mock_redis
    svc._redis_init_attempted = True
    svc._redis_available = True
    svc._ledger_repo = mock_ledger
    svc._client_repo = mock_clients

    # 10 concurrent deductions of 100 credits each → expected final = 10000 - 1000 = 9000
    tasks = [
        svc.deduct(
            client_id="clnt_concurrent",
            credits=100,
            feature="chat_simple",
            tokens_input=500,
            tokens_output=100,
            request_id=f"req_{i}",
        )
        for i in range(10)
    ]
    results = await asyncio.gather(*tasks)

    await _drain()

    assert balance_state["value"] == 9000
    # All returned balances must be between 9000 and 9900 (strictly decreasing under lock)
    assert all(9000 <= r <= 9900 for r in results)
    # No two tasks should return the same balance
    assert len(set(results)) == len(results)


# ── Adjust ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_adjust_positive(service, mock_redis, mock_ledger_repo):
    """Positive adjustment increments balance and writes an adjustment ledger entry."""
    mock_redis.incrby = AsyncMock(return_value=5500)

    new_balance = await service.adjust(
        client_id="clnt_goodwill",
        credits=500,
        reason="Goodwill credit for downtime",
        admin_user="ops@javaab.in",
    )

    assert new_balance == 5500
    mock_redis.incrby.assert_called_once_with("client:clnt_goodwill:credits", 500)

    await _drain()
    entry = mock_ledger_repo.append_entry.call_args[0][0]
    assert entry.type == "adjustment"
    assert entry.credits == 500


@pytest.mark.asyncio
async def test_adjust_negative(service, mock_redis, mock_ledger_repo):
    """Negative adjustment decrements balance."""
    mock_redis.decrby = AsyncMock(return_value=4700)

    new_balance = await service.adjust(
        client_id="clnt_fix",
        credits=-300,
        reason="Billing correction",
        admin_user="ops@javaab.in",
    )

    assert new_balance == 4700
    mock_redis.decrby.assert_called_once_with("client:clnt_fix:credits", 300)

    await _drain()
    entry = mock_ledger_repo.append_entry.call_args[0][0]
    assert entry.credits == -300


# ── Consumption summary ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_consumption_summary_aggregates_correctly(service, mock_ledger_repo):
    """Consumption summary correctly totals credits and tokens across features."""
    mock_ledger_repo.get_consumption_breakdown = AsyncMock(return_value={
        "chat_simple": {"credits": -300, "tokens_input": 1200, "tokens_output": 300, "count": 3},
        "chat_complex": {"credits": -700, "tokens_input": 5000, "tokens_output": 2000, "count": 2},
    })

    summary = await service.get_consumption_summary("clnt_test", days=30)

    assert summary["total_credits"] == 1000
    assert summary["total_tokens"] == 8500
    assert summary["daily_avg"] == round(1000 / 30, 2)
    assert summary["by_feature"]["chat_simple"]["credits"] == 300
    assert summary["by_feature"]["chat_complex"]["credits"] == 700
    assert "forecast_eom" in summary


@pytest.mark.asyncio
async def test_get_consumption_summary_empty(service, mock_ledger_repo):
    """Empty breakdown returns zeroed summary without errors."""
    mock_ledger_repo.get_consumption_breakdown = AsyncMock(return_value={})

    summary = await service.get_consumption_summary("clnt_new", days=30)

    assert summary["total_credits"] == 0
    assert summary["total_tokens"] == 0
    assert summary["daily_avg"] == 0.0
