"""
Append-only audit log for all admin actions.

Cosmos container: admin_audit_log
Partition key:    /admin_user

Schema:
    audit_id        str         UUID v4
    admin_user      str         username from JWT
    action          str         e.g. "create_client", "topup", "rotate_key"
    target_client_id str | None
    details         dict        action-specific context
    ip              str
    user_agent      str
    created_at      str         ISO-8601 UTC
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

from app.config import get_settings

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AdminAuditRepository:
    """Write-only repository for the admin_audit_log container."""

    def __init__(self) -> None:
        self._client: Optional[CosmosClient] = None
        self._container_client: Optional[Any] = None
        self._available = False
        self._init_attempted = False

    def _ensure_init(self) -> None:
        if self._init_attempted:
            return
        self._init_attempted = True

        settings = get_settings()
        endpoint = settings.AZURE_COSMOS_ENDPOINT
        key = settings.AZURE_COSMOS_KEY
        db_name = settings.AZURE_COSMOS_DATABASE
        container_name = settings.COSMOS_CONTAINER_AUDIT_LOG

        if not endpoint or not key or "example" in endpoint:
            logger.warning("AdminAuditRepository: Cosmos not configured — degraded mode.")
            return

        try:
            self._client = CosmosClient(endpoint, credential=key)
            db = self._client.get_database_client(db_name)
            self._container_client = db.get_container_client(container_name)
            self._available = True
        except Exception as exc:
            logger.error("AdminAuditRepository: init failed: %s", exc)

    def _container(self) -> Optional[Any]:
        self._ensure_init()
        return self._container_client if self._available else None

    async def log(
        self,
        *,
        admin_user: str,
        action: str,
        target_client_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip: str = "",
        user_agent: str = "",
    ) -> None:
        """Append one audit entry. Errors are logged but never raised to callers."""
        container = self._container()
        audit_id = str(uuid.uuid4())
        doc = {
            "id": audit_id,
            "audit_id": audit_id,
            "admin_user": admin_user,
            "action": action,
            "target_client_id": target_client_id,
            "details": details or {},
            "ip": ip,
            "user_agent": user_agent,
            "created_at": _now_iso(),
        }

        if container is None:
            logger.info("[degraded] audit: %s by %s on %s", action, admin_user, target_client_id)
            return

        try:
            await container.create_item(body=doc)
        except CosmosHttpResponseError as exc:
            logger.error("AdminAuditRepository.log failed: %s", exc)
