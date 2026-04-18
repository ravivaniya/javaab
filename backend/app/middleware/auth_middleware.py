from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to verify JWT tokens and inject user ID into request state.
    """
    async def dispatch(self, request: Request, call_next):
        # TODO: Implement JWT decoding securely
        response = await call_next(request)
        return response
