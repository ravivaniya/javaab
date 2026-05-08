import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

from app.config import get_settings
from app.models.client import LedgerEntry

logger = logging.getLogger(__name__)

_CONTAINER = "ledger"


class LedgerRepository:
    """
    Async repository for the append-only 'ledger' Cosmos container.

    Partition key: /client_id

    Entries are never updated or deleted — only new documents are appended.
    Redis is the live credit counter; this ledger is the source of truth for
    reconciliation and audit.
    """

    def __init__(self) -> None:
        self._client: Optional[CosmosClient] = None
        self._container_client: Optional[Any] = None
        self._available = False
        self._init_attempted = False

    def _ensure_init(self) -> None:
        """Lazy-initialise the Cosmos client once."""
        if self._init_attempted:
            return
        self._init_attempted = True

        settings = get_settings()
        endpoint = settings.AZURE_COSMOS_ENDPOINT
        key = settings.AZURE_COSMOS_KEY
        db_name = settings.AZURE_COSMOS_DATABASE

        if not endpoint or not key or "example" in endpoint:
            logger.warning(
                "LedgerRepository: Cosmos DB not configured — running in degraded mode."
            )
            return

        try:
            self._client = CosmosClient(endpoint, credential=key)
            db = self._client.get_database_client(db_name)
            self._container_client = db.get_container_client(settings.COSMOS_CONTAINER_LEDGER)
            self._available = True
        except Exception as exc:
            logger.error(f"LedgerRepository: failed to initialise Cosmos client: {exc}")

    def _container(self) -> Optional[Any]:
        self._ensure_init()
        return self._container_client if self._available else None

    def _to_cosmos_doc(self, entry: LedgerEntry) -> dict:
        """Convert a LedgerEntry to a Cosmos document (id = ledger_id)."""
        doc = entry.model_dump(mode="json")
        doc["id"] = entry.ledger_id
        return doc

    def _from_cosmos_doc(self, doc: dict) -> LedgerEntry:
        """Hydrate a LedgerEntry from a raw Cosmos document."""
        return LedgerEntry.model_validate(doc)

    # ── Write operations ──────────────────────────────────────────────────────

    async def append_entry(self, entry: LedgerEntry) -> LedgerEntry:
        """
        Append a new ledger entry.  Never call patch or replace on existing
        entries — the ledger is immutable by design.
        """
        container = self._container()
        if container is None:
            logger.warning(f"[degraded] append_entry: {entry.ledger_id} for {entry.client_id}")
            return entry
        try:
            doc = self._to_cosmos_doc(entry)
            result = await container.create_item(body=doc)
            return self._from_cosmos_doc(result)
        except CosmosHttpResponseError as exc:
            logger.error(
                f"append_entry(ledger_id={entry.ledger_id}, client={entry.client_id}) failed: {exc}"
            )
            raise

    # ── Read operations ───────────────────────────────────────────────────────

    async def get_entries_for_client(
        self,
        client_id: str,
        limit: int = 100,
        before: Optional[datetime] = None,
    ) -> List[LedgerEntry]:
        """
        Return the most recent ledger entries for a client, newest-first.

        Pass *before* to page backwards through history (exclusive upper bound
        on created_at).
        """
        container = self._container()
        if container is None:
            return []
        try:
            if before is not None:
                query = (
                    "SELECT TOP @limit * FROM c "
                    "WHERE c.client_id = @cid AND c.created_at < @before "
                    "ORDER BY c.created_at DESC"
                )
                params = [
                    {"name": "@cid", "value": client_id},
                    {"name": "@limit", "value": limit},
                    {"name": "@before", "value": before.isoformat()},
                ]
            else:
                query = (
                    "SELECT TOP @limit * FROM c "
                    "WHERE c.client_id = @cid "
                    "ORDER BY c.created_at DESC"
                )
                params = [
                    {"name": "@cid", "value": client_id},
                    {"name": "@limit", "value": limit},
                ]
            results: List[LedgerEntry] = []
            async for doc in container.query_items(
                query=query,
                parameters=params,
                partition_key=client_id,
            ):
                results.append(self._from_cosmos_doc(doc))
            return results
        except CosmosHttpResponseError as exc:
            logger.error(f"get_entries_for_client({client_id}) failed: {exc}")
            return []

    async def get_balance_from_ledger(self, client_id: str) -> int:
        """
        Compute the authoritative credit balance by summing all ledger entries.

        This is a reconciliation helper — use Redis for the live runtime balance.
        """
        container = self._container()
        if container is None:
            return 0
        try:
            query = "SELECT VALUE SUM(c.credits) FROM c WHERE c.client_id = @cid"
            params = [{"name": "@cid", "value": client_id}]
            async for value in container.query_items(
                query=query,
                parameters=params,
                partition_key=client_id,
            ):
                return int(value or 0)
            return 0
        except CosmosHttpResponseError as exc:
            logger.error(f"get_balance_from_ledger({client_id}) failed: {exc}")
            return 0

    async def get_last_topup(self, client_id: str) -> Optional[LedgerEntry]:
        """Return the most recent topup entry for this client, or None."""
        container = self._container()
        if container is None:
            return None
        try:
            query = (
                "SELECT TOP 1 * FROM c "
                "WHERE c.client_id = @cid AND c.type = 'topup' "
                "ORDER BY c.created_at DESC"
            )
            params = [{"name": "@cid", "value": client_id}]
            async for doc in container.query_items(
                query=query,
                parameters=params,
                partition_key=client_id,
            ):
                return self._from_cosmos_doc(doc)
            return None
        except CosmosHttpResponseError as exc:
            logger.error(f"get_last_topup({client_id}) failed: {exc}")
            return None

    async def get_consumption_breakdown(
        self,
        client_id: str,
        since: datetime,
    ) -> Dict[str, Dict[str, int]]:
        """
        Return per-feature consumption stats since *since*.

        Returns a dict keyed by feature name:
            {
                "chat_simple": {"credits": -450, "tokens_input": 1200, "tokens_output": 300, "count": 3},
                ...
            }
        """
        container = self._container()
        if container is None:
            return {}
        try:
            query = (
                "SELECT c.feature, c.credits, c.tokens_input, c.tokens_output "
                "FROM c "
                "WHERE c.client_id = @cid "
                "AND c.type = 'consumption' "
                "AND c.created_at >= @since"
            )
            params = [
                {"name": "@cid", "value": client_id},
                {"name": "@since", "value": since.isoformat()},
            ]
            breakdown: Dict[str, Dict[str, int]] = {}
            async for doc in container.query_items(
                query=query,
                parameters=params,
                partition_key=client_id,
            ):
                feature = doc.get("feature") or "unknown"
                bucket = breakdown.setdefault(
                    feature, {"credits": 0, "tokens_input": 0, "tokens_output": 0, "count": 0}
                )
                bucket["credits"] += int(doc.get("credits") or 0)
                bucket["tokens_input"] += int(doc.get("tokens_input") or 0)
                bucket["tokens_output"] += int(doc.get("tokens_output") or 0)
                bucket["count"] += 1
            return breakdown
        except CosmosHttpResponseError as exc:
            logger.error(f"get_consumption_breakdown({client_id}) failed: {exc}")
            return {}
