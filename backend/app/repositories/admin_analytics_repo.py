"""
Cross-partition analytics queries on the ledger container.

All queries use enable_cross_partition_query=True and are intended for the
admin dashboard only — not in the hot path of any client-facing request.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

from app.config import get_settings

logger = logging.getLogger(__name__)


class AdminAnalyticsRepository:
    """Read-only cross-partition analytics over the ledger container."""

    def __init__(self) -> None:
        self._client: Optional[CosmosClient] = None
        self._ledger_container: Optional[Any] = None
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

        if not endpoint or not key or "example" in endpoint:
            logger.warning("AdminAnalyticsRepository: Cosmos not configured — degraded mode.")
            return

        try:
            self._client = CosmosClient(endpoint, credential=key)
            db = self._client.get_database_client(db_name)
            self._ledger_container = db.get_container_client(settings.COSMOS_CONTAINER_LEDGER)
            self._available = True
        except Exception as exc:
            logger.error("AdminAnalyticsRepository: init failed: %s", exc)

    def _container(self) -> Optional[Any]:
        self._ensure_init()
        return self._ledger_container if self._available else None

    async def get_platform_stats_since(self, since: datetime) -> Dict[str, Any]:
        """
        Aggregate ledger entries across all clients since *since*.

        Returns:
            total_credits_sold      int   sum of topup credits
            total_credits_consumed  int   sum of consumption credits (positive)
            total_revenue_inr       int   sum of amount_inr on topups
            by_client               dict  {client_id: credits_consumed}
        """
        container = self._container()
        result: Dict[str, Any] = {
            "total_credits_sold": 0,
            "total_credits_consumed": 0,
            "total_revenue_inr": 0,
            "by_client": {},
        }
        if container is None:
            return result

        query = (
            "SELECT c.client_id, c.type, c.credits, c.amount_inr "
            "FROM c WHERE c.created_at >= @since"
        )
        params = [{"name": "@since", "value": since.isoformat()}]

        try:
            async for doc in container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            ):
                entry_type = doc.get("type")
                credits = int(doc.get("credits") or 0)

                if entry_type == "topup":
                    result["total_credits_sold"] += credits
                    result["total_revenue_inr"] += int(doc.get("amount_inr") or 0)
                elif entry_type == "consumption":
                    consumed = abs(credits)
                    result["total_credits_consumed"] += consumed
                    cid = doc.get("client_id", "unknown")
                    result["by_client"][cid] = result["by_client"].get(cid, 0) + consumed

        except CosmosHttpResponseError as exc:
            logger.error("get_platform_stats_since failed: %s", exc)

        return result

    async def get_client_consumption_since(self, since: datetime) -> Dict[str, int]:
        """
        Return {client_id: total_credits_consumed} for all clients since *since*.
        Used to compute burn-rate in one cross-partition pass instead of N per-client queries.
        """
        container = self._container()
        by_client: Dict[str, int] = {}
        if container is None:
            return by_client

        query = (
            "SELECT c.client_id, c.credits "
            "FROM c WHERE c.type = 'consumption' AND c.created_at >= @since"
        )
        params = [{"name": "@since", "value": since.isoformat()}]

        try:
            async for doc in container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            ):
                cid = doc.get("client_id", "unknown")
                consumed = abs(int(doc.get("credits") or 0))
                by_client[cid] = by_client.get(cid, 0) + consumed
        except CosmosHttpResponseError as exc:
            logger.error("get_client_consumption_since failed: %s", exc)

        return by_client
