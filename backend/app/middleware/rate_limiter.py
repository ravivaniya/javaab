import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.repositories.redis_repo import RedisRepo
from app.middleware.auth_middleware import _is_public

logger = logging.getLogger(__name__)

# Per-minute request caps by tier.
TIER_RATE_LIMITS = {
    "Free": 20,
    "Plus": 60,
    "Pro": 200,
}

_redis_repo = RedisRepo()


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Token-bucket rate limiter using Redis. Reads request.state.user_id set by
    AuthMiddleware. Skips public paths. Fails open on Redis errors.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or _is_public(request.url.path):
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            return await call_next(request)

        tier = getattr(request.state, "user_tier", "Free") or "Free"
        limit = TIER_RATE_LIMITS.get(tier, TIER_RATE_LIMITS["Free"])

        try:
            allowed = await _redis_repo.check_minute_rate(user_id, limit)
        except Exception as e:
            logger.error(f"rate limiter check failed (fail-open): {e}")
            allowed = True

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded for tier {tier}"},
            )
        return await call_next(request)
