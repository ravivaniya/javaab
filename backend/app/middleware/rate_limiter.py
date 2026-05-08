import logging
import time
import uuid
from typing import Optional

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException

from app.config import get_settings
from app.models.client import Client
from app.middleware.api_key_auth import verify_api_key

logger = logging.getLogger(__name__)

# Module-level Redis singleton — initialised once on first request.
_redis: Optional[aioredis.Redis] = None
_redis_init = False


def get_redis_client() -> Optional[aioredis.Redis]:
    """
    FastAPI dependency that returns the shared Redis client.

    Returns ``None`` when Redis is unconfigured (local dev / degraded mode).
    Exposing this as a named dependency lets tests override it cleanly via
    ``app.dependency_overrides[get_redis_client] = lambda: mock_redis``.
    """
    global _redis, _redis_init
    if _redis_init:
        return _redis
    _redis_init = True

    settings = get_settings()
    host = settings.AZURE_REDIS_HOST
    port = settings.AZURE_REDIS_PORT
    password = settings.AZURE_REDIS_KEY

    if not host or "example" in host:
        logger.warning("RateLimiter: Redis not configured — rate limiting disabled (fail-open).")
        return None

    try:
        _redis = aioredis.Redis(
            host=host,
            port=port,
            password=password or None,
            ssl=(port == 6380),
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
    except Exception as exc:
        logger.error("RateLimiter: failed to init Redis client: %s", exc)
    return _redis


async def _sliding_window(
    r: aioredis.Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """
    Sliding window counter using a Redis sorted set.

    Members are unique ``{timestamp}:{uuid4}`` strings scored by epoch time.
    Old entries outside the window are pruned atomically in the same pipeline.

    Returns:
        (allowed, current_count_after_add)
    """
    now = time.time()
    member = f"{now}:{uuid.uuid4().hex}"
    cutoff = now - window_seconds

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, cutoff)          # prune expired entries
    pipe.zadd(key, {member: now})                   # record this request
    pipe.zcard(key)                                 # count within window
    pipe.expire(key, window_seconds + 1)            # auto-cleanup TTL
    results = await pipe.execute()

    count = int(results[2])
    return count <= limit, count


async def rate_limit(
    client: Client = Depends(verify_api_key),
    redis: Optional[aioredis.Redis] = Depends(get_redis_client),
) -> None:
    """
    FastAPI dependency: per-client sliding window rate limiter.

    Enforces two independent windows using per-client limits from the Client
    record:
    - Per minute  (key: ``ratelimit:{client_id}:minute``, window 60 s)
    - Per day     (key: ``ratelimit:{client_id}:day``,    window 86 400 s)

    Fails open if Redis is unavailable so a Redis outage does not take down
    the API.  Always raises *after* verify_api_key has already validated the
    key, so the client object is guaranteed to be present here.
    """
    if redis is None:
        return  # degraded mode — no Redis, skip limiting

    try:
        minute_key = f"ratelimit:{client.client_id}:minute"
        allowed, _ = await _sliding_window(redis, minute_key, client.rate_limit_per_minute, 60)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Per-minute rate limit exceeded.",
                headers={"Retry-After": "60"},
            )

        day_key = f"ratelimit:{client.client_id}:day"
        allowed, _ = await _sliding_window(redis, day_key, client.rate_limit_per_day, 86400)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Daily rate limit exceeded.",
                headers={"Retry-After": "86400"},
            )

    except HTTPException:
        raise
    except Exception as exc:
        # Fail open on unexpected Redis errors — never let the rate limiter
        # bring down the API for paying clients.
        logger.error("rate_limit check failed (fail-open): %s", exc)
