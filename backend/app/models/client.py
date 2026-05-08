from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr


class Client(BaseModel):
    """B2B API client record stored in the 'clients' Cosmos container."""

    client_id: str  # format: clnt_<slug>, e.g., clnt_iitjee_ahmedabad
    org_name: str
    contact_name: str
    contact_phone: str  # +91 format
    contact_email: EmailStr
    api_key_hash: str  # SHA-256 of the actual key; never store the raw key
    api_key_prefix: str  # first 8 chars of the key, for display, e.g., "jvb_live_a3f9..."
    plan_tier: Literal["starter", "growth", "scale", "enterprise"]
    credit_balance: int  # cached snapshot; Redis is the live source of truth
    credit_alert_threshold: int = 2000
    is_active: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_per_day: int = 50000
    whatsapp_number: str  # for low-credit and anomaly alerts
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LedgerEntry(BaseModel):
    """Append-only credit ledger entry stored in the 'ledger' Cosmos container."""

    ledger_id: str  # UUID v4
    client_id: str
    type: Literal["topup", "consumption", "adjustment", "refund"]
    credits: int  # positive for topup/refund; negative for consumption/adjustment
    balance_after: int

    # Topup / admin fields
    amount_inr: Optional[int] = None
    payment_ref: Optional[str] = None  # UTR / UPI reference
    note: Optional[str] = None

    # Consumption fields
    feature: Optional[
        Literal["chat_simple", "chat_medium", "chat_complex", "chat_image", "qpg", "dpp", "embedding"]
    ] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    request_id: Optional[str] = None

    created_by: str  # admin username or "system"
    created_at: datetime
