import os
import logging
from datetime import date
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# TTL constants
SESSION_WORD_TTL = 86400   # 24 hours
DAILY_CAP_TTL = 86400      # resets at midnight (natural key expiry)


class RedisRepo:
    """
    Async data-access layer for Azure Redis Cache.

    Lazy-initialised: if AZURE_REDIS_HOST/KEY are missing or the client
    raises while connecting, every method degrades to a logged no-op.
    """

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._init_attempted = False
        self._available = False

    def _ensure_client(self) -> Optional[aioredis.Redis]:
        if self._init_attempted:
            return self._client
        self._init_attempted = True

        host = os.getenv("AZURE_REDIS_HOST", "")
        port = int(os.getenv("AZURE_REDIS_PORT", "6380") or 6380)
        password = os.getenv("AZURE_REDIS_KEY", "") or None

        if not host or "example" in host:
            logger.warning(
                "Redis not configured (AZURE_REDIS_HOST empty). "
                "Repository will run in degraded mode."
            )
            return None

        try:
            self._client = aioredis.Redis(
                host=host,
                port=port,
                password=password,
                ssl=(port == 6380),
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            self._available = True
        except Exception as e:
            logger.error(f"Failed to initialise Redis client: {e}")
            self._client = None
        return self._client

    async def get_cache(self, key: str) -> str:
        client = self._ensure_client()
        if client is None:
            return ""
        try:
            val = await client.get(key)
            return val or ""
        except Exception as e:
            logger.error(f"redis get_cache({key}) failed: {e}")
            return ""

    # ── Session word-count limits (H) ────────────────────────────────────────

    async def get_session_word_count(self, conversation_id: str) -> int:
        client = self._ensure_client()
        if client is None:
            return 0
        key = f"session_words:{conversation_id}"
        try:
            val = await client.get(key)
            return int(val) if val else 0
        except Exception as e:
            logger.error(f"get_session_word_count failed: {e}")
            return 0

    async def increment_session_words(self, conversation_id: str, word_count: int) -> int:
        client = self._ensure_client()
        if client is None:
            return word_count
        key = f"session_words:{conversation_id}"
        try:
            new_val = await client.incrby(key, word_count)
            await client.expire(key, SESSION_WORD_TTL)
            return int(new_val)
        except Exception as e:
            logger.error(f"increment_session_words failed: {e}")
            return word_count

    # ── Daily global query cap (O) ────────────────────────────────────────────

    async def check_and_increment_daily_cap(self, cap: int) -> bool:
        """
        Atomically increment today's global query counter.
        Returns True if the request is allowed (under cap), False if cap is exceeded.
        Fails open if Redis is unavailable.
        """
        client = self._ensure_client()
        if client is None:
            return True
        today = date.today().isoformat()
        key = f"daily_queries:{today}"
        try:
            new_val = await client.incr(key)
            await client.expire(key, DAILY_CAP_TTL)
            return int(new_val) <= cap
        except Exception as e:
            logger.error(f"check_and_increment_daily_cap failed: {e}")
            return True

    async def get_daily_count(self) -> int:
        client = self._ensure_client()
        if client is None:
            return 0
        today = date.today().isoformat()
        key = f"daily_queries:{today}"
        try:
            val = await client.get(key)
            return int(val) if val else 0
        except Exception as e:
            logger.error(f"get_daily_count failed: {e}")
            return 0

    # ── Per-tier rate limiting (used by RateLimiterMiddleware) ────────────────

    async def check_minute_rate(self, user_id: str, limit: int) -> bool:
        """
        Token-bucket per minute. Returns True if the request is allowed.
        Fails open on Redis errors.
        """
        client = self._ensure_client()
        if client is None:
            return True
        try:
            from datetime import datetime, timezone
            bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
            key = f"rate:{user_id}:{bucket}"
            new_val = await client.incr(key)
            await client.expire(key, 65)
            return int(new_val) <= limit
        except Exception as e:
            logger.error(f"check_minute_rate failed: {e}")
            return True
