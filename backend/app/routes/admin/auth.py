"""
Admin authentication routes.

POST /admin/auth/login   → issue JWT, set httpOnly cookie
POST /admin/auth/logout  → clear cookie
GET  /admin/auth/me      → current admin identity
"""
import logging
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jose import jwt
from pydantic import BaseModel

from app.config import get_settings
from app.dependencies.admin_auth import get_audit_repo, get_current_admin
from app.repositories.admin_audit_repo import AdminAuditRepository

logger = logging.getLogger(__name__)
router = APIRouter()

_COOKIE_NAME = "admin_token"


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_at: str


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    audit: AdminAuditRepository = Depends(get_audit_repo),
) -> LoginResponse:
    """Verify credentials and issue an admin JWT."""
    settings = get_settings()

    # Constant-time checks to avoid username enumeration
    username_ok = body.username == settings.ADMIN_USERNAME
    password_hash = settings.ADMIN_PASSWORD_HASH or ""

    if not password_hash:
        logger.error("ADMIN_PASSWORD_HASH not configured — login rejected")
        raise HTTPException(status_code=503, detail="Admin auth not configured")

    password_ok = _verify_password(body.password, password_hash) if password_hash else False

    if not username_ok or not password_ok:
        await audit.log(
            admin_user=body.username,
            action="login_failed",
            details={"reason": "invalid_credentials"},
            ip=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    secret = settings.ADMIN_JWT_SECRET or settings.JWT_SECRET
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=settings.ADMIN_JWT_EXPIRY_HOURS)
    payload = {
        "sub": settings.ADMIN_USERNAME,
        "role": "admin",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)

    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=(settings.ENVIRONMENT != "development"),
        samesite="strict",
        max_age=settings.ADMIN_JWT_EXPIRY_HOURS * 3600,
        path="/admin",
    )

    await audit.log(
        admin_user=settings.ADMIN_USERNAME,
        action="login",
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    return LoginResponse(token=token, expires_at=exp.isoformat())


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Clear the admin session cookie."""
    response.delete_cookie(key=_COOKIE_NAME, path="/admin")
    return {"message": "Logged out"}


@router.get("/me")
async def me(admin: str = Depends(get_current_admin)) -> dict:
    """Return current admin identity."""
    return {"username": admin, "role": "admin"}
