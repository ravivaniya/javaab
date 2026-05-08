import asyncio
import logging
import math
import uuid
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

from app.config import get_settings
from app.models.client import LedgerEntry
from app.repositories.client_repo import ClientRepository
from app.repositories.ledger_repo import LedgerRepository

logger = logging.getLogger(__name__)

# 1 credit = 1000 tokens billed internally
CREDITS_PER_1K_TOKENS = 1


def tokens_to_credits(tokens: int) -> int:
    """Convert raw token count to credits, always charging a minimum of 1."""
    return max(1, math.ceil(tokens / 1000))


class CreditService:
    """
    Manages client credit balances across two tiers:
      - Redis: live, atomic, fast — source of truth during request processing
      - Cosmos ledger: persistent, append-only — source of truth for reconciliation
    """

    REDIS_KEY_TEMPLATE = "client:{client_id}:credits"

    # How long to suppress duplicate low-credit alerts (resets on topup)
    _ALERT_SENTINEL_TTL = 86400  # 24 h
    # How long to remember a processed request_id for deduplication
    _DEDUP_TTL = 86400  # 24 h

    def __init__(self) -> None:
        self._redis: Optional[aioredis.Redis] = None
        self._redis_init_attempted = False
        self._redis_available = False
        self._client_repo = ClientRepository()
        self._ledger_repo = LedgerRepository()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _redis_key(self, client_id: str) -> str:
        return self.REDIS_KEY_TEMPLATE.format(client_id=client_id)

    def _ensure_redis(self) -> Optional[aioredis.Redis]:
        """Lazy-init Redis client once; degrades gracefully if not configured."""
        if self._redis_init_attempted:
            return self._redis
        self._redis_init_attempted = True

        settings = get_settings()
        host = settings.AZURE_REDIS_HOST
        port = settings.AZURE_REDIS_PORT
        password = settings.AZURE_REDIS_KEY or None

        if not host or "example" in host:
            logger.warning("CreditService: Redis not configured — running in degraded mode.")
            return None

        try:
            self._redis = aioredis.Redis(
                host=host,
                port=port,
                password=password,
                ssl=(port == 6380),
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            self._redis_available = True
        except Exception as exc:
            logger.error(f"CreditService: failed to initialise Redis: {exc}")

        return self._redis

    async def _write_ledger_entry(self, entry: LedgerEntry) -> None:
        """Background task: append a ledger entry, swallowing errors so callers never block."""
        try:
            await self._ledger_repo.append_entry(entry)
        except Exception as exc:
            logger.error(f"_write_ledger_entry(ledger_id={entry.ledger_id}): {exc}")

    async def _trigger_suspension(self, client_id: str) -> None:
        """Auto-suspend a client when their balance hits zero."""
        try:
            await self._client_repo.deactivate_client(
                client_id, reason="zero_balance_auto_suspension"
            )
            logger.warning(
                f"AUTO-SUSPENSION: client={client_id} suspended due to zero balance"
            )
            # TODO: Send WhatsApp Business API suspension alert
        except Exception as exc:
            logger.error(f"_trigger_suspension({client_id}): {exc}")

    async def _maybe_reactivate(self, client_id: str) -> None:
        """Reactivate a previously suspended client after a successful topup."""
        try:
            client = await self._client_repo.get_client_by_id(client_id)
            if client and not client.is_active:
                await self._client_repo.update_client(
                    client_id,
                    {"is_active": True, "notes": "Reactivated after topup"},
                )
                logger.info(f"_maybe_reactivate: client {client_id} reactivated")
        except Exception as exc:
            logger.error(f"_maybe_reactivate({client_id}): {exc}")

    async def _check_low_credit_alert(self, client_id: str, balance: int) -> None:
        """
        Send a low-credit alert when balance drops below the client's threshold.
        A Redis sentinel key prevents re-alerting until the next topup clears it.
        """
        try:
            client = await self._client_repo.get_client_by_id(client_id)
            if client is None or balance >= client.credit_alert_threshold:
                return

            redis = self._ensure_redis()
            sentinel_key = f"client:{client_id}:low_credit_alert"
            if redis is not None:
                try:
                    already_sent = await redis.get(sentinel_key)
                    if already_sent:
                        return
                    await redis.set(sentinel_key, "1", ex=self._ALERT_SENTINEL_TTL)
                except Exception as exc:
                    logger.warning(f"_check_low_credit_alert: sentinel check failed: {exc}")
                    # Continue and alert anyway to avoid silent misses

            logger.warning(
                f"LOW CREDIT ALERT: client={client_id} balance={balance} "
                f"threshold={client.credit_alert_threshold} "
                f"whatsapp={client.whatsapp_number}"
            )
            # TODO: Send WhatsApp Business API low-credit alert via client.whatsapp_number

        except Exception as exc:
            logger.error(f"_check_low_credit_alert({client_id}): {exc}")

    async def _clear_redis_key(self, key: str) -> None:
        redis = self._ensure_redis()
        if redis is not None:
            try:
                await redis.delete(key)
            except Exception as exc:
                logger.error(f"_clear_redis_key({key}): {exc}")

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_balance(self, client_id: str) -> int:
        """
        Read live balance from Redis.
        On a cache miss, reconcile from the ledger and rehydrate Redis.
        """
        redis = self._ensure_redis()
        key = self._redis_key(client_id)

        if redis is not None:
            try:
                val = await redis.get(key)
                if val is not None:
                    return int(val)
            except Exception as exc:
                logger.error(f"get_balance({client_id}): Redis GET failed: {exc}")

        # Redis miss or unavailable — fall back to ledger
        return await self.reconcile_from_ledger(client_id)

    async def check_and_reserve(self, client_id: str, estimated_credits: int) -> bool:
        """
        Preflight check: return True if current balance >= estimated_credits.
        Does NOT deduct — used to fast-reject requests before doing any AI work.
        """
        balance = await self.get_balance(client_id)
        allowed = balance >= estimated_credits
        if not allowed:
            logger.info(
                f"check_and_reserve({client_id}): balance={balance} "
                f"< estimated={estimated_credits} — rejected"
            )
        return allowed

    async def deduct(
        self,
        client_id: str,
        credits: int,
        feature: str,
        tokens_input: int,
        tokens_output: int,
        request_id: str,
    ) -> int:
        """
        Atomically deduct credits via Redis DECRBY, then asynchronously write
        to the ledger. Returns the new balance.

        If the resulting balance reaches zero, auto-suspension is triggered.
        If it crosses below the client's alert threshold, a low-credit alert fires.
        Idempotent: duplicate request_ids are detected via a Redis sentinel key.
        """
        redis = self._ensure_redis()
        key = self._redis_key(client_id)

        # Idempotency: skip if we already processed this request_id
        if redis is not None:
            dedup_key = f"client:{client_id}:deduct_dedup:{request_id}"
            try:
                set_result = await redis.set(dedup_key, "1", nx=True, ex=self._DEDUP_TTL)
                if set_result is None:
                    # NX condition failed → key existed → already processed
                    logger.info(
                        f"deduct: request_id={request_id} already processed, returning current balance"
                    )
                    val = await redis.get(key)
                    return int(val or 0)
            except Exception as exc:
                logger.warning(f"deduct({client_id}): dedup check failed: {exc}")

        # Atomic decrement
        if redis is not None:
            try:
                new_balance = int(await redis.decrby(key, credits))
            except Exception as exc:
                logger.error(f"deduct({client_id}): Redis DECRBY failed: {exc}")
                # Best-effort fallback: compute from ledger, no atomicity guarantee
                ledger_balance = await self._ledger_repo.get_balance_from_ledger(client_id)
                new_balance = ledger_balance - credits
        else:
            # Degraded mode: derive from ledger (no atomicity)
            ledger_balance = await self._ledger_repo.get_balance_from_ledger(client_id)
            new_balance = ledger_balance - credits

        logger.info(
            f"deduct: client={client_id} feature={feature} credits=-{credits} "
            f"balance_after={new_balance} request_id={request_id}"
        )

        entry = LedgerEntry(
            ledger_id=str(uuid.uuid4()),
            client_id=client_id,
            type="consumption",
            credits=-credits,
            balance_after=new_balance,
            feature=feature,  # type: ignore[arg-type]
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            request_id=request_id,
            created_by="system",
            created_at=datetime.now(timezone.utc),
        )
        asyncio.create_task(self._write_ledger_entry(entry))
        asyncio.create_task(self._client_repo.update_balance_cache(client_id, new_balance))

        if new_balance <= 0:
            asyncio.create_task(self._trigger_suspension(client_id))
        else:
            asyncio.create_task(self._check_low_credit_alert(client_id, new_balance))

        return new_balance

    async def topup(
        self,
        client_id: str,
        credits: int,
        amount_inr: int,
        payment_ref: str,
        note: str,
        admin_user: str,
    ) -> int:
        """
        Atomically add credits via Redis INCRBY + ledger write. Returns new balance.
        If the client was previously suspended due to zero balance, reactivates them.
        """
        redis = self._ensure_redis()
        key = self._redis_key(client_id)

        if redis is not None:
            try:
                new_balance = int(await redis.incrby(key, credits))
            except Exception as exc:
                logger.error(f"topup({client_id}): Redis INCRBY failed: {exc}")
                ledger_balance = await self._ledger_repo.get_balance_from_ledger(client_id)
                new_balance = ledger_balance + credits
        else:
            ledger_balance = await self._ledger_repo.get_balance_from_ledger(client_id)
            new_balance = ledger_balance + credits

        logger.info(
            f"topup: client={client_id} credits=+{credits} balance_after={new_balance} "
            f"admin={admin_user} payment_ref={payment_ref}"
        )

        entry = LedgerEntry(
            ledger_id=str(uuid.uuid4()),
            client_id=client_id,
            type="topup",
            credits=credits,
            balance_after=new_balance,
            amount_inr=amount_inr,
            payment_ref=payment_ref,
            note=note,
            created_by=admin_user,
            created_at=datetime.now(timezone.utc),
        )
        asyncio.create_task(self._write_ledger_entry(entry))
        asyncio.create_task(self._client_repo.update_balance_cache(client_id, new_balance))

        if new_balance > 0:
            asyncio.create_task(self._maybe_reactivate(client_id))
            # Clear the alert sentinel so the next low-credit period triggers a fresh alert
            sentinel_key = f"client:{client_id}:low_credit_alert"
            asyncio.create_task(self._clear_redis_key(sentinel_key))

        return new_balance

    async def adjust(
        self,
        client_id: str,
        credits: int,
        reason: str,
        admin_user: str,
    ) -> int:
        """
        Manual admin credit adjustment. credits may be positive (goodwill) or
        negative (correction). Writes to both Redis and the ledger.
        """
        redis = self._ensure_redis()
        key = self._redis_key(client_id)

        if redis is not None:
            try:
                if credits >= 0:
                    new_balance = int(await redis.incrby(key, credits))
                else:
                    new_balance = int(await redis.decrby(key, abs(credits)))
            except Exception as exc:
                logger.error(f"adjust({client_id}): Redis operation failed: {exc}")
                ledger_balance = await self._ledger_repo.get_balance_from_ledger(client_id)
                new_balance = ledger_balance + credits
        else:
            ledger_balance = await self._ledger_repo.get_balance_from_ledger(client_id)
            new_balance = ledger_balance + credits

        logger.info(
            f"adjust: client={client_id} credits={credits:+} balance_after={new_balance} "
            f"reason={reason!r} admin={admin_user}"
        )

        entry = LedgerEntry(
            ledger_id=str(uuid.uuid4()),
            client_id=client_id,
            type="adjustment",
            credits=credits,
            balance_after=new_balance,
            note=reason,
            created_by=admin_user,
            created_at=datetime.now(timezone.utc),
        )
        asyncio.create_task(self._write_ledger_entry(entry))
        asyncio.create_task(self._client_repo.update_balance_cache(client_id, new_balance))

        return new_balance

    async def reconcile_from_ledger(self, client_id: str) -> int:
        """
        Recompute the authoritative balance by summing all ledger entries,
        then SET that value in Redis. Use at startup or as a repair tool.
        """
        balance = await self._ledger_repo.get_balance_from_ledger(client_id)

        redis = self._ensure_redis()
        if redis is not None:
            key = self._redis_key(client_id)
            try:
                await redis.set(key, balance)
                logger.info(
                    f"reconcile_from_ledger({client_id}): Redis rehydrated with balance={balance}"
                )
            except Exception as exc:
                logger.error(f"reconcile_from_ledger({client_id}): Redis SET failed: {exc}")

        return balance

    async def get_consumption_summary(self, client_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Return aggregated consumption stats over the last *days* days.

        Shape:
        {
            "by_feature": {
                "chat_simple": {"credits": 450, "tokens_input": ..., "tokens_output": ..., "count": ...},
                ...
            },
            "total_credits": int,   # total credits consumed (positive)
            "total_tokens": int,
            "daily_avg": float,     # credits per day over the window
            "forecast_eom": int,    # projected additional credits until end of month
        }
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        breakdown = await self._ledger_repo.get_consumption_breakdown(client_id, since)

        # Normalise credits to positive values for the summary
        by_feature: Dict[str, Any] = {}
        for feature, stats in breakdown.items():
            by_feature[feature] = {
                "credits": abs(stats["credits"]),
                "tokens_input": stats["tokens_input"],
                "tokens_output": stats["tokens_output"],
                "count": stats["count"],
            }

        total_credits = sum(v["credits"] for v in by_feature.values())
        total_tokens = sum(v["tokens_input"] + v["tokens_output"] for v in by_feature.values())
        daily_avg = round(total_credits / max(1, days), 2)

        today = datetime.now(timezone.utc)
        _, days_in_month = monthrange(today.year, today.month)
        days_remaining = days_in_month - today.day
        forecast_eom = int(round(daily_avg * days_remaining))

        return {
            "by_feature": by_feature,
            "total_credits": total_credits,
            "total_tokens": total_tokens,
            "daily_avg": daily_avg,
            "forecast_eom": forecast_eom,
        }
