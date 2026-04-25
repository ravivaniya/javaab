import os
import logging
from typing import Optional, List, Dict, Any

from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential

logger = logging.getLogger(__name__)


class SearchRepo:
    """
    Thin async wrapper around Azure AI Search for the textbook chunks index.
    Lazy init — degrades to empty results when not configured.
    """

    def __init__(self):
        self._client: Optional[SearchClient] = None
        self._init_attempted = False

    def _ensure_client(self) -> Optional[SearchClient]:
        if self._init_attempted:
            return self._client
        self._init_attempted = True

        endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT", "")
        key = os.getenv("AZURE_AI_SEARCH_KEY", "")
        index = os.getenv("AZURE_AI_SEARCH_INDEX_CHUNKS", "textbook_chunks")

        if not endpoint or not key or "example" in endpoint:
            logger.warning(
                "Azure AI Search not configured. SearchRepo running in degraded mode."
            )
            return None

        try:
            self._client = SearchClient(
                endpoint=endpoint,
                index_name=index,
                credential=AzureKeyCredential(key),
            )
        except Exception as e:
            logger.error(f"Failed to initialise SearchClient: {e}")
            self._client = None
        return self._client

    async def search_index(self, query: str, top: int = 5) -> List[Dict[str, Any]]:
        """Execute a keyword search against the textbook chunks index."""
        client = self._ensure_client()
        if client is None:
            return []
        try:
            results: List[Dict[str, Any]] = []
            async for doc in await client.search(search_text=query, top=top):
                results.append(dict(doc))
            return results
        except Exception as e:
            logger.error(f"search_index failed: {e}")
            return []
