#!/usr/bin/env python3
"""
Seed two pilot clients into Cosmos and Redis for local/staging testing.

Usage:
    cd backend
    python scripts/seed_pilot_data.py

Safe to re-run: existing client_ids are skipped.
Writes to whatever Azure environment is configured in .env.
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.client import Client, LedgerEntry
from app.repositories.client_repo import ClientRepository
from app.repositories.ledger_repo import LedgerRepository
from app.services.api_key_service import APIKeyService
from app.services.credit_service import CreditService

_NOW = datetime.now(timezone.utc)


def _ago(days: int) -> datetime:
    return _NOW - timedelta(days=days)


_PILOT_SPECS: list[dict] = [
    {
        "client_id": "clnt_demo_school",
        "org_name": "Demo Public School",
        "contact_name": "Demo Admin",
        "contact_phone": "+919000000001",
        "contact_email": "demo@javaab.in",
        "plan_tier": "growth",
        "initial_credits": 50_000,
        "credit_alert_threshold": 5_000,
        "rate_limit_per_minute": 120,
        "rate_limit_per_day": 100_000,
        "whatsapp_number": "+919000000001",
        "notes": "Pilot demo client — all features, full quota",
    },
    {
        "client_id": "clnt_test_coaching",
        "org_name": "Test Coaching Institute",
        "contact_name": "Test Admin",
        "contact_phone": "+919000000002",
        "contact_email": "test@javaab.in",
        "plan_tier": "starter",
        "initial_credits": 5_000,
        "credit_alert_threshold": 500,
        "rate_limit_per_minute": 60,
        "rate_limit_per_day": 50_000,
        "whatsapp_number": "+919000000002",
        "notes": "Low-threshold test client for alert and suspension flow verification",
    },
]


def _build_client(spec: dict, key_hash: str, key_prefix: str) -> Client:
    """Construct the Client pydantic model from a spec dict and key material."""
    return Client(
        client_id=spec["client_id"],
        org_name=spec["org_name"],
        contact_name=spec["contact_name"],
        contact_phone=spec["contact_phone"],
        contact_email=spec["contact_email"],
        api_key_hash=key_hash,
        api_key_prefix=key_prefix,
        plan_tier=spec["plan_tier"],
        credit_balance=spec["initial_credits"],
        credit_alert_threshold=spec["credit_alert_threshold"],
        is_active=True,
        rate_limit_per_minute=spec["rate_limit_per_minute"],
        rate_limit_per_day=spec["rate_limit_per_day"],
        whatsapp_number=spec["whatsapp_number"],
        notes=spec["notes"],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _topup_entry(
    client_id: str, credits: int, days_ago: int, payment_ref: str
) -> LedgerEntry:
    return LedgerEntry(
        ledger_id=str(uuid.uuid4()),
        client_id=client_id,
        type="topup",
        credits=credits,
        balance_after=credits,
        amount_inr=credits // 2,
        payment_ref=payment_ref,
        note="Seed initial topup",
        created_by="seed_script",
        created_at=_ago(days_ago),
    )


def _consumption_entry(
    client_id: str,
    feature: str,
    credits: int,
    balance_after: int,
    days_ago: int,
) -> LedgerEntry:
    return LedgerEntry(
        ledger_id=str(uuid.uuid4()),
        client_id=client_id,
        type="consumption",
        credits=-credits,
        balance_after=balance_after,
        feature=feature,  # type: ignore[arg-type]
        tokens_input=credits * 600,
        tokens_output=credits * 400,
        request_id=str(uuid.uuid4()),
        created_by="system",
        created_at=_ago(days_ago),
    )


async def _seed_one(
    spec: dict,
    client_repo: ClientRepository,
    ledger_repo: LedgerRepository,
    credit_svc: CreditService,
) -> str:
    """
    Create one client + realistic ledger history. Returns raw API key (or sentinel
    if skipped).
    """
    client_id = spec["client_id"]

    existing = await client_repo.get_client_by_id(client_id)
    if existing is not None:
        print(f"  SKIP   {client_id} — already exists in Cosmos.")
        return "(key not shown — client already existed)"

    raw_key, key_hash, key_prefix = APIKeyService.generate_api_key()
    client = _build_client(spec, key_hash, key_prefix)
    await client_repo.create_client(client)
    print(f"  CREATE {client_id} ({spec['org_name']})")

    initial = spec["initial_credits"]
    await ledger_repo.append_entry(
        _topup_entry(client_id, initial, days_ago=30, payment_ref="SEED_UTR_INIT")
    )

    # Simulate ~10 % consumption spread across the last 4 weeks.
    consumed_per_feature = (initial // 10) // 4
    balance = initial
    samples = [
        ("chat_simple", consumed_per_feature, 28),
        ("chat_medium", consumed_per_feature, 21),
        ("qpg",         consumed_per_feature, 14),
        ("dpp",         consumed_per_feature, 7),
    ]
    for feature, credits, days in samples:
        balance -= credits
        await ledger_repo.append_entry(
            _consumption_entry(client_id, feature, credits, balance, days)
        )

    # Sync Redis from the authoritative ledger sum.
    synced_balance = await credit_svc.reconcile_from_ledger(client_id)
    await client_repo.update_balance_cache(client_id, synced_balance)
    print(f"         balance  : {synced_balance:,} credits (Redis + Cosmos snapshot synced)")

    return raw_key


async def main() -> None:
    """Entry point: seed all pilot clients sequentially."""
    client_repo = ClientRepository()
    ledger_repo = LedgerRepository()
    credit_svc = CreditService()

    print()
    print("Seeding pilot clients…")
    print()

    for spec in _PILOT_SPECS:
        raw_key = await _seed_one(spec, client_repo, ledger_repo, credit_svc)
        print(f"         API key  : {raw_key}")
        if not raw_key.startswith("("):
            print("         SAVE THIS KEY — it will not be shown again.")
        print()

    print("Done. Use the admin UI or Postman to verify.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
