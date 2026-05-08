"""
Admin credit management routes.

POST /admin/clients/:id/topup    add credits (logs admin user in ledger entry)
POST /admin/clients/:id/adjust   signed credit adjustment
GET  /admin/clients/:id/ledger   paginated ledger history
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.dependencies.admin_auth import (
    get_audit_repo,
    get_client_repo,
    get_credit_service,
    get_current_admin,
    get_ledger_repo,
)
from app.repositories.admin_audit_repo import AdminAuditRepository
from app.repositories.client_repo import ClientRepository
from app.repositories.ledger_repo import LedgerRepository
from app.services.credit_service import CreditService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request models ────────────────────────────────────────────────────────────


class TopupRequest(BaseModel):
    credits: int = Field(gt=0, description="Credits to add (must be positive)")
    amount_inr: int = Field(ge=0, description="INR amount received (0 for free credits)")
    payment_ref: str = Field(default="", description="UTR / UPI / invoice reference")
    note: Optional[str] = Field(default=None, max_length=500)


class AdjustRequest(BaseModel):
    credits: int = Field(description="Signed credit delta: positive to add, negative to deduct")
    reason: str = Field(min_length=3, max_length=500)


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/{client_id}/topup")
async def topup_credits(
    client_id: str,
    body: TopupRequest,
    request: Request,
    admin: str = Depends(get_current_admin),
    repo: ClientRepository = Depends(get_client_repo),
    credit_svc: CreditService = Depends(get_credit_service),
    audit: AdminAuditRepository = Depends(get_audit_repo),
) -> dict:
    """
    Add credits to a client's balance.
    Writes the admin username into the ledger entry for audit purposes.
    Triggers WhatsApp confirmation to the client (TODO: wire WhatsApp).
    """
    client = await repo.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    new_balance = await credit_svc.topup(
        client_id=client_id,
        credits=body.credits,
        amount_inr=body.amount_inr,
        payment_ref=body.payment_ref,
        note=body.note or "",
        admin_user=admin,
    )

    await audit.log(
        admin_user=admin,
        action="topup",
        target_client_id=client_id,
        details={
            "credits": body.credits,
            "amount_inr": body.amount_inr,
            "payment_ref": body.payment_ref,
            "new_balance": new_balance,
        },
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )

    # TODO: send WhatsApp topup confirmation to client.whatsapp_number
    return {
        "client_id": client_id,
        "credits_added": body.credits,
        "new_balance": new_balance,
        "payment_ref": body.payment_ref,
    }


@router.post("/{client_id}/adjust")
async def adjust_credits(
    client_id: str,
    body: AdjustRequest,
    request: Request,
    admin: str = Depends(get_current_admin),
    repo: ClientRepository = Depends(get_client_repo),
    credit_svc: CreditService = Depends(get_credit_service),
    audit: AdminAuditRepository = Depends(get_audit_repo),
) -> dict:
    """
    Manual admin credit adjustment. Positive = add, negative = deduct.
    Logged in the ledger as type=adjustment.
    """
    client = await repo.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if body.credits == 0:
        raise HTTPException(status_code=422, detail="Adjustment credits must be non-zero")

    new_balance = await credit_svc.adjust(
        client_id=client_id,
        credits=body.credits,
        reason=body.reason,
        admin_user=admin,
    )

    await audit.log(
        admin_user=admin,
        action="adjust_credits",
        target_client_id=client_id,
        details={"credits": body.credits, "reason": body.reason, "new_balance": new_balance},
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )

    return {"client_id": client_id, "credits_delta": body.credits, "new_balance": new_balance}


@router.get("/{client_id}/ledger")
async def get_ledger(
    client_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    before: Optional[datetime] = Query(default=None, description="ISO-8601 cursor for pagination"),
    admin: str = Depends(get_current_admin),
    repo: ClientRepository = Depends(get_client_repo),
    ledger_repo: LedgerRepository = Depends(get_ledger_repo),
) -> dict:
    """Return paginated ledger entries for a client, newest-first."""
    client = await repo.get_client_by_id(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    entries = await ledger_repo.get_entries_for_client(
        client_id=client_id,
        limit=limit,
        before=before,
    )

    return {
        "client_id": client_id,
        "entries": [e.model_dump(mode="json") for e in entries],
        "count": len(entries),
        "next_before": entries[-1].created_at.isoformat() if entries else None,
    }
