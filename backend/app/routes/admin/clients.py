"""
Admin client management routes.

GET    /admin/clients                       list all clients
POST   /admin/clients                       create client (returns raw API key ONCE)
GET    /admin/clients/:id                   full detail + ledger + usage
PUT    /admin/clients/:id                   update editable fields
POST   /admin/clients/:id/rotate-key        rotate API key (returns new raw key ONCE)
POST   /admin/clients/:id/suspend           deactivate
POST   /admin/clients/:id/reactivate        reactivate (requires balance > 0)
"""
import logging
import re
import secrets
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr

from app.dependencies.admin_auth import (
    get_audit_repo,
    get_client_repo,
    get_credit_service,
    get_current_admin,
    get_ledger_repo,
)
from app.models.client import Client
from app.repositories.admin_audit_repo import AdminAuditRepository
from app.repositories.client_repo import ClientRepository
from app.repositories.ledger_repo import LedgerRepository
from app.services.api_key_service import APIKeyService
from app.services.credit_service import CreditService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request / response models ─────────────────────────────────────────────────


class ClientCreateRequest(BaseModel):
    org_name: str
    contact_name: str
    contact_phone: str
    contact_email: EmailStr
    plan_tier: Literal["starter", "growth", "scale", "enterprise"]
    rate_limit_per_minute: int = 60
    rate_limit_per_day: int = 50000
    credit_alert_threshold: int = 2000
    whatsapp_number: str
    notes: Optional[str] = None


class ClientUpdateRequest(BaseModel):
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    plan_tier: Optional[Literal["starter", "growth", "scale", "enterprise"]] = None
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_day: Optional[int] = None
    credit_alert_threshold: Optional[int] = None
    whatsapp_number: Optional[str] = None
    notes: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _generate_client_id(org_name: str) -> str:
    """Generate a unique client_id slug from org_name."""
    slug = re.sub(r"[^a-z0-9]+", "_", org_name.lower()).strip("_")[:24]
    suffix = secrets.token_hex(4)
    return f"clnt_{slug}_{suffix}"


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("")
async def list_clients(
    active_only: bool = Query(default=True),
    admin: str = Depends(get_current_admin),
    repo: ClientRepository = Depends(get_client_repo),
) -> List[dict]:
    """Return all clients, optionally filtered to active only."""
    clients = await repo.list_clients(active_only=active_only)
    return [c.model_dump(mode="json") for c in clients]


@router.post("", status_code=201)
async def create_client(
    body: ClientCreateRequest,
    request: Request,
    admin: str = Depends(get_current_admin),
    repo: ClientRepository = Depends(get_client_repo),
    audit: AdminAuditRepository = Depends(get_audit_repo),
) -> dict:
    """
    Create a new B2B client and return the raw API key.
    The raw key is returned exactly once — it is never stored.
    """
    raw_key, key_hash, key_prefix = APIKeyService.generate_api_key()
    client_id = _generate_client_id(body.org_name)
    now = datetime.now(timezone.utc)

    client = Client(
        client_id=client_id,
        org_name=body.org_name,
        contact_name=body.contact_name,
        contact_phone=body.contact_phone,
        contact_email=body.contact_email,
        api_key_hash=key_hash,
        api_key_prefix=key_prefix,
        plan_tier=body.plan_tier,
        credit_balance=0,
        credit_alert_threshold=body.credit_alert_threshold,
        is_active=True,
        rate_limit_per_minute=body.rate_limit_per_minute,
        rate_limit_per_day=body.rate_limit_per_day,
        whatsapp_number=body.whatsapp_number,
        notes=body.notes,
        created_at=now,
        updated_at=now,
    )

    created = await repo.create_client(client)

    await audit.log(
        admin_user=admin,
        action="create_client",
        target_client_id=client_id,
        details={"org_name": body.org_name, "plan_tier": body.plan_tier},
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )

    return {"client": created.model_dump(mode="json"), "raw_api_key": raw_key}


@router.get("/{client_id}")
async def get_client(
    client_id: str,
    admin: str = Depends(get_current_admin),
    repo: ClientRepository = Depends(get_client_repo),
    ledger_repo: LedgerRepository = Depends(get_ledger_repo),
    credit_svc: CreditService = Depends(get_credit_service),
) -> dict:
    """Return full client detail including last 50 ledger entries and 30-day usage."""
    client = await repo.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    live_balance = await credit_svc.get_balance(client_id)
    ledger = await ledger_repo.get_entries_for_client(client_id, limit=50)
    usage_summary = await credit_svc.get_consumption_summary(client_id, days=30)

    return {
        "client": {**client.model_dump(mode="json"), "credit_balance": live_balance},
        "ledger": [e.model_dump(mode="json") for e in ledger],
        "usage_summary": usage_summary,
    }


@router.put("/{client_id}")
async def update_client(
    client_id: str,
    body: ClientUpdateRequest,
    request: Request,
    admin: str = Depends(get_current_admin),
    repo: ClientRepository = Depends(get_client_repo),
    audit: AdminAuditRepository = Depends(get_audit_repo),
) -> dict:
    """Update editable client fields. client_id and api_key cannot be changed here."""
    existing = await repo.get_client_by_id(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    updated = await repo.update_client(client_id, updates)

    await audit.log(
        admin_user=admin,
        action="update_client",
        target_client_id=client_id,
        details={"fields_changed": list(updates.keys())},
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )

    return updated.model_dump(mode="json")


@router.post("/{client_id}/rotate-key")
async def rotate_key(
    client_id: str,
    request: Request,
    admin: str = Depends(get_current_admin),
    repo: ClientRepository = Depends(get_client_repo),
    audit: AdminAuditRepository = Depends(get_audit_repo),
) -> dict:
    """
    Generate a new API key, invalidate the old one, and return the new raw key.
    The raw key is returned exactly once.
    """
    existing = await repo.get_client_by_id(client_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    raw_key, key_hash, key_prefix = APIKeyService.generate_api_key()
    now = datetime.now(timezone.utc).isoformat()
    await repo.update_client(
        client_id,
        {
            "api_key_hash": key_hash,
            "api_key_prefix": key_prefix,
            "updated_at": now,
        },
    )

    await audit.log(
        admin_user=admin,
        action="rotate_key",
        target_client_id=client_id,
        details={"new_key_prefix": key_prefix},
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )

    return {"client_id": client_id, "new_raw_api_key": raw_key, "new_key_prefix": key_prefix}


@router.post("/{client_id}/suspend")
async def suspend_client(
    client_id: str,
    request: Request,
    admin: str = Depends(get_current_admin),
    repo: ClientRepository = Depends(get_client_repo),
    audit: AdminAuditRepository = Depends(get_audit_repo),
) -> dict:
    """Deactivate a client. Sends a suspension WhatsApp alert (TODO: wire WhatsApp)."""
    client = await repo.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if not client.is_active:
        raise HTTPException(status_code=409, detail="Client is already suspended")

    await repo.deactivate_client(client_id, reason=f"suspended_by_admin:{admin}")

    await audit.log(
        admin_user=admin,
        action="suspend_client",
        target_client_id=client_id,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )

    # TODO: send WhatsApp suspension notice to client.whatsapp_number
    return {"client_id": client_id, "is_active": False}


@router.post("/{client_id}/reactivate")
async def reactivate_client(
    client_id: str,
    request: Request,
    admin: str = Depends(get_current_admin),
    repo: ClientRepository = Depends(get_client_repo),
    credit_svc: CreditService = Depends(get_credit_service),
    audit: AdminAuditRepository = Depends(get_audit_repo),
) -> dict:
    """Reactivate a suspended client. Requires balance > 0 to prevent immediate re-suspension."""
    client = await repo.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if client.is_active:
        raise HTTPException(status_code=409, detail="Client is already active")

    balance = await credit_svc.get_balance(client_id)
    if balance <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reactivate: credit balance is {balance}. Top up first.",
        )

    now = datetime.now(timezone.utc).isoformat()
    await repo.update_client(
        client_id,
        {"is_active": True, "notes": f"Reactivated by admin:{admin}", "updated_at": now},
    )

    await audit.log(
        admin_user=admin,
        action="reactivate_client",
        target_client_id=client_id,
        details={"balance_at_reactivation": balance},
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )

    return {"client_id": client_id, "is_active": True, "credit_balance": balance}
