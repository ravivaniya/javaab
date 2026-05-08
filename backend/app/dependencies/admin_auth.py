"""
FastAPI dependencies for admin JWT authentication.

Admin tokens are issued by POST /admin/auth/login.  They arrive either as an
httpOnly cookie (``admin_token``) or an ``Authorization: Bearer <token>``
header (used by the admin SPA's axios interceptor).

All injectable provider functions (get_client_repo, get_credit_service, …)
live here so tests can override them via app.dependency_overrides.
"""
import logging
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request
from jose import JWTError, jwt

from app.config import get_settings
from app.repositories.admin_audit_repo import AdminAuditRepository
from app.repositories.admin_analytics_repo import AdminAnalyticsRepository
from app.repositories.client_repo import ClientRepository
from app.repositories.ledger_repo import LedgerRepository
from app.services.credit_service import CreditService

logger = logging.getLogger(__name__)


async def get_current_admin(
    request: Request,
    admin_token: Optional[str] = Cookie(default=None),
) -> str:
    """
    Extract and validate the admin JWT from cookie or Authorization header.
    Returns the admin username on success; raises 401 otherwise.
    """
    token = admin_token
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    settings = get_settings()
    secret = settings.ADMIN_JWT_SECRET or settings.JWT_SECRET
    if not secret:
        raise HTTPException(status_code=500, detail="Admin JWT secret not configured")

    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        logger.info("Admin JWT rejected: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    return str(payload.get("sub", "admin"))


# ── Repository / service providers ────────────────────────────────────────────
# These thin wrappers exist solely so tests can override them via
# app.dependency_overrides without having to mock class constructors.


def get_client_repo() -> ClientRepository:
    """Provide a ClientRepository instance."""
    return ClientRepository()


def get_ledger_repo() -> LedgerRepository:
    """Provide a LedgerRepository instance."""
    return LedgerRepository()


def get_credit_service() -> CreditService:
    """Provide a CreditService instance."""
    return CreditService()


def get_audit_repo() -> AdminAuditRepository:
    """Provide an AdminAuditRepository instance."""
    return AdminAuditRepository()


def get_analytics_repo() -> AdminAnalyticsRepository:
    """Provide an AdminAnalyticsRepository instance."""
    return AdminAnalyticsRepository()
