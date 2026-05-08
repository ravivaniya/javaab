"""B2B usage / account-info endpoints: GET /api/v1/usage[/ledger]."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.middleware.api_key_auth import verify_api_key
from app.models.client import Client
from app.repositories.ledger_repo import LedgerEntry, LedgerRepository
from app.services.credit_service import CreditService

logger = logging.getLogger(__name__)
router = APIRouter()

_credits = CreditService()
_ledger_repo = LedgerRepository()


# ── Response schemas ──────────────────────────────────────────────────────────

class UsageResponse(BaseModel):
    """Response from GET /api/v1/usage."""

    client_id: str
    org_name: str
    plan_tier: str
    credits_remaining: int
    credits_alert_threshold: int
    is_active: bool
    rate_limits: dict               # {per_minute: int, per_day: int}
    consumption_30d: dict           # {by_feature: {...}, total_credits, total_tokens}
    daily_avg_credits: float
    forecasted_eom_credits: int
    last_topup: Optional[dict]      # {date, credits, payment_ref} or None
    estimated_days_remaining: Optional[int]


class LedgerEntryResponse(BaseModel):
    """Client-facing view of a single ledger entry."""

    ledger_id: str
    type: str
    credits: int
    balance_after: int
    feature: Optional[str] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    amount_inr: Optional[int] = None
    payment_ref: Optional[str] = None
    note: Optional[str] = None
    request_id: Optional[str] = None
    created_at: str                 # ISO 8601


class LedgerResponse(BaseModel):
    """Response from GET /api/v1/usage/ledger."""

    client_id: str
    entries: list[LedgerEntryResponse]
    count: int
    has_more: bool
    next_before: Optional[str] = None  # pass as ?before= in the next request


# ── Internal helpers ──────────────────────────────────────────────────────────

def _entry_to_response(entry: LedgerEntry) -> LedgerEntryResponse:
    return LedgerEntryResponse(
        ledger_id=entry.ledger_id,
        type=entry.type,
        credits=entry.credits,
        balance_after=entry.balance_after,
        feature=entry.feature,
        tokens_input=entry.tokens_input,
        tokens_output=entry.tokens_output,
        amount_inr=entry.amount_inr,
        payment_ref=entry.payment_ref,
        note=entry.note,
        request_id=entry.request_id,
        created_at=entry.created_at.isoformat(),
    )


def _last_topup_dict(entry: LedgerEntry) -> dict:
    return {
        "date": entry.created_at.isoformat(),
        "credits": entry.credits,
        "payment_ref": entry.payment_ref,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=UsageResponse)
async def get_usage(
    client: Client = Depends(verify_api_key),
) -> UsageResponse:
    """
    GET /api/v1/usage

    Returns live account status, 30-day consumption breakdown, and a
    forward-looking credit forecast — all scoped to the authenticated client.

    Credits come from the live Redis counter; the snapshot in the client
    document may lag by one request.
    """
    credits_remaining, summary, last_topup_entry = await asyncio.gather(
        _credits.get_balance(client.client_id),
        _credits.get_consumption_summary(client.client_id, days=30),
        _ledger_repo.get_last_topup(client.client_id),
    )

    daily_avg: float = summary["daily_avg"]
    forecasted_eom: int = summary["forecast_eom"]

    estimated_days_remaining: Optional[int] = None
    if daily_avg > 0 and credits_remaining > 0:
        estimated_days_remaining = int(credits_remaining / daily_avg)

    return UsageResponse(
        client_id=client.client_id,
        org_name=client.org_name,
        plan_tier=client.plan_tier,
        credits_remaining=credits_remaining,
        credits_alert_threshold=client.credit_alert_threshold,
        is_active=client.is_active,
        rate_limits={
            "per_minute": client.rate_limit_per_minute,
            "per_day": client.rate_limit_per_day,
        },
        consumption_30d={
            "by_feature": summary["by_feature"],
            "total_credits": summary["total_credits"],
            "total_tokens": summary["total_tokens"],
        },
        daily_avg_credits=daily_avg,
        forecasted_eom_credits=forecasted_eom,
        last_topup=_last_topup_dict(last_topup_entry) if last_topup_entry else None,
        estimated_days_remaining=estimated_days_remaining,
    )


@router.get("/ledger", response_model=LedgerResponse)
async def get_ledger(
    limit: int = Query(default=50, ge=1, le=200, description="Max entries to return"),
    before: Optional[str] = Query(
        None,
        description="ISO 8601 datetime — return entries created before this timestamp (for pagination)",
    ),
    client: Client = Depends(verify_api_key),
) -> LedgerResponse:
    """
    GET /api/v1/usage/ledger

    Returns paginated credit ledger entries (topups, consumption, adjustments)
    for the authenticated client, newest first.

    Use the returned ``next_before`` value as the ``before`` query parameter to
    fetch the next page.
    """
    before_dt: Optional[datetime] = None
    if before is not None:
        try:
            before_dt = datetime.fromisoformat(before.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid 'before' value: {before!r}. Use ISO 8601 format, e.g. 2025-01-15T10:30:00Z.",
            )

    entries = await _ledger_repo.get_entries_for_client(
        client.client_id,
        limit=limit,
        before=before_dt,
    )

    has_more = len(entries) == limit
    next_before: Optional[str] = None
    if has_more:
        next_before = entries[-1].created_at.isoformat()

    return LedgerResponse(
        client_id=client.client_id,
        entries=[_entry_to_response(e) for e in entries],
        count=len(entries),
        has_more=has_more,
        next_before=next_before,
    )
