"""
Admin analytics routes.

GET /admin/analytics/overview             platform-wide 30-day summary
GET /admin/analytics/clients-burning-fast clients projected to run out in < 7 days
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.dependencies.admin_auth import (
    get_analytics_repo,
    get_client_repo,
    get_credit_service,
    get_current_admin,
)
from app.repositories.admin_analytics_repo import AdminAnalyticsRepository
from app.repositories.client_repo import ClientRepository
from app.services.credit_service import CreditService

logger = logging.getLogger(__name__)
router = APIRouter()

_BURN_THRESHOLD_DAYS = 7


@router.get("/overview")
async def analytics_overview(
    admin: str = Depends(get_current_admin),
    client_repo: ClientRepository = Depends(get_client_repo),
    analytics_repo: AdminAnalyticsRepository = Depends(get_analytics_repo),
) -> dict:
    """
    Platform-wide 30-day summary:
    - total / active client counts
    - credits sold, consumed, revenue INR
    - top 5 clients by consumption
    """
    since_30d = datetime.now(timezone.utc) - timedelta(days=30)

    all_clients = await client_repo.list_clients(active_only=False)
    total_clients = len(all_clients)
    active_clients = sum(1 for c in all_clients if c.is_active)
    client_name_map = {c.client_id: c.org_name for c in all_clients}

    stats = await analytics_repo.get_platform_stats_since(since_30d)

    by_client: dict = stats.get("by_client", {})
    top_5 = sorted(by_client.items(), key=lambda kv: kv[1], reverse=True)[:5]

    return {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "total_credits_sold_30d": stats["total_credits_sold"],
        "total_credits_consumed_30d": stats["total_credits_consumed"],
        "total_revenue_inr_30d": stats["total_revenue_inr"],
        "top_5_clients_by_consumption": [
            {
                "client_id": cid,
                "org_name": client_name_map.get(cid, "Unknown"),
                "credits_consumed_30d": consumed,
            }
            for cid, consumed in top_5
        ],
    }


@router.get("/clients-burning-fast")
async def clients_burning_fast(
    admin: str = Depends(get_current_admin),
    client_repo: ClientRepository = Depends(get_client_repo),
    analytics_repo: AdminAnalyticsRepository = Depends(get_analytics_repo),
) -> list:
    """
    Return active clients projected to run out of credits in < 7 days based on
    their 7-day average consumption rate.

    Uses the Cosmos credit_balance snapshot (not Redis) to avoid N extra round
    trips — close enough for a dashboard projection.
    """
    since_7d = datetime.now(timezone.utc) - timedelta(days=7)

    active_clients = await client_repo.list_clients(active_only=True)
    if not active_clients:
        return []

    # Single cross-partition pass for all consumption in the window
    consumption_map = await analytics_repo.get_client_consumption_since(since_7d)

    at_risk = []
    for client in active_clients:
        total_consumed_7d = consumption_map.get(client.client_id, 0)
        daily_avg = total_consumed_7d / 7.0

        if daily_avg <= 0:
            continue  # Not consuming; not at risk

        balance = client.credit_balance  # Cosmos snapshot — fast, not Redis round-trip
        days_remaining = balance / daily_avg

        if days_remaining < _BURN_THRESHOLD_DAYS:
            at_risk.append(
                {
                    "client_id": client.client_id,
                    "org_name": client.org_name,
                    "whatsapp_number": client.whatsapp_number,
                    "credit_balance": balance,
                    "daily_avg_consumption": round(daily_avg, 1),
                    "days_remaining": round(days_remaining, 1),
                }
            )

    # Most urgent (fewest days remaining) first
    at_risk.sort(key=lambda x: x["days_remaining"])
    return at_risk
