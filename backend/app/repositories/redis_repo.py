import os
import logging
from datetime import date

logger = logging.getLogger(__name__)

# TTL constants
SESSION_WORD_TTL = 86400   # 24 hours
DAILY_CAP_TTL = 86400      # resets at midnight (natural key expiry)

class RedisRepo:
    """
    Data access layer for Azure Redis Cache.
    All methods are stubs; replace with real redis.asyncio calls.
    """
    def __init__(self):
        # TODO: initialise real async Redis client:
        # import redis.asyncio as aioredis
        # self._client = aioredis.from_url(...)
        pass

    async def get_cache(self, key: str) -> str:
        """Get a string value from Redis."""
        # TODO: return await self._client.get(key) or ""
        return ""

    # ── Session word-count limits (H) ────────────────────────────────────────

    async def get_session_word_count(self, conversation_id: str) -> int:
        """Return cumulative word count for this conversation (24-h window)."""
        key = f"session_words:{conversation_id}"
        logger.info(f"Fetching session word count for key: {key}")
        # TODO: val = await self._client.get(key); return int(val) if val else 0
        return 0

    async def increment_session_words(self, conversation_id: str, word_count: int) -> int:
        """Increment the session word counter; set TTL on first write. Returns new total."""
        key = f"session_words:{conversation_id}"
        logger.info(f"Incrementing session words by {word_count} for key: {key}")
        # TODO:
        #   new_val = await self._client.incrby(key, word_count)
        #   await self._client.expire(key, SESSION_WORD_TTL)
        #   return new_val
        return word_count

    # ── Daily global query cap (O) ────────────────────────────────────────────

    async def check_and_increment_daily_cap(self, cap: int) -> bool:
        """
        Atomically increment today's global query counter.
        Returns True if the request is allowed (under cap), False if cap is exceeded.
        """
        today = date.today().isoformat()          # e.g. "2026-04-24"
        key = f"daily_queries:{today}"
        logger.info(f"Checking daily cap (cap={cap}) for key: {key}")
        # TODO:
        #   new_val = await self._client.incr(key)
        #   await self._client.expire(key, DAILY_CAP_TTL)
        #   return new_val <= cap
        return True  # stub: always allow

    async def get_daily_count(self) -> int:
        """Return today's global query count (for monitoring)."""
        today = date.today().isoformat()
        key = f"daily_queries:{today}"
        # TODO: val = await self._client.get(key); return int(val) if val else 0
        return 0
