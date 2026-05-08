import logging
from typing import Any, Dict, List, Optional

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from app.config import get_settings
from app.models.client import Client

logger = logging.getLogger(__name__)

_CONTAINER = "clients"


class ClientRepository:
    """
    Async repository for the 'clients' Cosmos container.

    Partition key: /client_id

    Degraded mode: if Cosmos credentials are absent or the SDK fails to
    initialise, every method logs a warning and returns a safe default so
    the service can start without Azure credentials in local dev.
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
                "ClientRepository: Cosmos DB not configured — running in degraded mode."
            )
            return

        try:
            self._client = CosmosClient(endpoint, credential=key)
            db = self._client.get_database_client(db_name)
            self._container_client = db.get_container_client(settings.COSMOS_CONTAINER_CLIENTS)
            self._available = True
        except Exception as exc:
            logger.error(f"ClientRepository: failed to initialise Cosmos client: {exc}")

    def _container(self) -> Optional[Any]:
        self._ensure_init()
        return self._container_client if self._available else None

    def _to_cosmos_doc(self, client: Client) -> dict:
        """Convert a Client to a Cosmos document (id = client_id)."""
        doc = client.model_dump(mode="json")
        doc["id"] = client.client_id
        return doc

    def _from_cosmos_doc(self, doc: dict) -> Client:
        """Hydrate a Client from a raw Cosmos document."""
        return Client.model_validate(doc)

    # ── Write operations ──────────────────────────────────────────────────────

    async def create_client(self, client: Client) -> Client:
        """Insert a new client document. Raises if the client_id already exists."""
        container = self._container()
        if container is None:
            logger.warning(f"[degraded] create_client: {client.client_id}")
            return client
        try:
            doc = self._to_cosmos_doc(client)
            result = await container.create_item(body=doc)
            return self._from_cosmos_doc(result)
        except CosmosHttpResponseError as exc:
            logger.error(f"create_client({client.client_id}) failed: {exc}")
            raise

    async def update_client(self, client_id: str, updates: Dict[str, Any]) -> Client:
        """
        Apply a partial update to a client document and return the updated Client.

        Only the keys present in *updates* are changed; all others are preserved.
        """
        container = self._container()
        if container is None:
            logger.warning(f"[degraded] update_client: {client_id}")
            raise RuntimeError("Cosmos DB unavailable")
        try:
            ops = [{"op": "set", "path": f"/{k}", "value": v} for k, v in updates.items()]
            result = await container.patch_item(
                item=client_id,
                partition_key=client_id,
                patch_operations=ops,
            )
            return self._from_cosmos_doc(result)
        except CosmosResourceNotFoundError:
            logger.error(f"update_client: client {client_id} not found")
            raise
        except CosmosHttpResponseError as exc:
            logger.error(f"update_client({client_id}) failed: {exc}")
            raise

    async def update_balance_cache(self, client_id: str, new_balance: int) -> None:
        """Write the latest credit balance snapshot back to the Cosmos document."""
        container = self._container()
        if container is None:
            logger.warning(f"[degraded] update_balance_cache: {client_id} -> {new_balance}")
            return
        try:
            await container.patch_item(
                item=client_id,
                partition_key=client_id,
                patch_operations=[
                    {"op": "set", "path": "/credit_balance", "value": new_balance},
                ],
            )
        except CosmosResourceNotFoundError:
            logger.error(f"update_balance_cache: client {client_id} not found")
        except CosmosHttpResponseError as exc:
            logger.error(f"update_balance_cache({client_id}) failed: {exc}")

    async def deactivate_client(self, client_id: str, reason: str) -> None:
        """Mark a client as inactive and record the reason in the notes field."""
        container = self._container()
        if container is None:
            logger.warning(f"[degraded] deactivate_client: {client_id}")
            return
        try:
            await container.patch_item(
                item=client_id,
                partition_key=client_id,
                patch_operations=[
                    {"op": "set", "path": "/is_active", "value": False},
                    {"op": "set", "path": "/notes", "value": f"Deactivated: {reason}"},
                ],
            )
            logger.info(f"deactivate_client: {client_id} — {reason}")
        except CosmosResourceNotFoundError:
            logger.error(f"deactivate_client: client {client_id} not found")
        except CosmosHttpResponseError as exc:
            logger.error(f"deactivate_client({client_id}) failed: {exc}")

    # ── Read operations ───────────────────────────────────────────────────────

    async def get_client_by_id(self, client_id: str) -> Optional[Client]:
        """Fetch a client by its primary client_id (point read — cheapest RU)."""
        container = self._container()
        if container is None:
            return None
        try:
            doc = await container.read_item(item=client_id, partition_key=client_id)
            return self._from_cosmos_doc(doc)
        except CosmosResourceNotFoundError:
            return None
        except CosmosHttpResponseError as exc:
            logger.error(f"get_client_by_id({client_id}) failed: {exc}")
            return None

    async def get_client_by_api_key_hash(self, api_key_hash: str) -> Optional[Client]:
        """
        Look up a client by the SHA-256 hash of their API key.

        Uses the api_key_hash index; cross-partition query is required because
        we only have the hash, not the client_id.
        """
        container = self._container()
        if container is None:
            return None
        try:
            query = "SELECT TOP 1 * FROM c WHERE c.api_key_hash = @hash AND c.is_active = true"
            params = [{"name": "@hash", "value": api_key_hash}]
            async for doc in container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            ):
                return self._from_cosmos_doc(doc)
            return None
        except CosmosHttpResponseError as exc:
            logger.error(f"get_client_by_api_key_hash failed: {exc}")
            return None

    async def list_clients(self, active_only: bool = True) -> List[Client]:
        """Return all clients, optionally filtered to active-only."""
        container = self._container()
        if container is None:
            return []
        try:
            if active_only:
                query = "SELECT * FROM c WHERE c.is_active = true ORDER BY c.org_name"
                params: List[dict] = []
            else:
                query = "SELECT * FROM c ORDER BY c.org_name"
                params = []
            results: List[Client] = []
            async for doc in container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            ):
                results.append(self._from_cosmos_doc(doc))
            return results
        except CosmosHttpResponseError as exc:
            logger.error(f"list_clients(active_only={active_only}) failed: {exc}")
            return []
