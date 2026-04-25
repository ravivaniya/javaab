import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError

from app.config import get_settings

logger = logging.getLogger(__name__)

# Public endpoints that bypass JWT verification entirely.
PUBLIC_PATHS = {
    "/health",
    "/auth/login",
    "/auth/verify",
    "/auth/register",
    "/docs",
    "/openapi.json",
    "/redoc",
}


def _is_public(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    # Allow Swagger / ReDoc static assets under /docs and /redoc.
    if path.startswith("/docs/") or path.startswith("/redoc/"):
        return True
    return False


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Verify JWT tokens on every non-public request and attach user info to
    request.state. Rejects requests without a valid Bearer token with 401.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or _is_public(request.url.path):
            return await call_next(request)

        auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Could not validate credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_header.split(" ", 1)[1].strip()
        settings = get_settings()
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except JWTError as e:
            logger.info(f"JWT rejected on {request.url.path}: {e}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Could not validate credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.user_id = payload.get("sub")
        request.state.user_tier = payload.get("tier", "Free")
        request.state.user_phone = payload.get("phone")
        return await call_next(request)
