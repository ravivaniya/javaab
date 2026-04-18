import logging

logger = logging.getLogger(__name__)

class SearchRepo:
    """
    Data access layer for Azure AI Search.
    Handles raw index queries.
    """
    def __init__(self):
        pass

    async def search_index(self, query: str) -> list:
        """
        Execute search query against AI Search.
        """
        # TODO: Implement search lookup
        return []
