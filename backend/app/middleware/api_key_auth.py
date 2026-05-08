import logging
from typing import Optional

from fastapi import Header, HTTPException

from app.models.client import Client
from app.repositories.client_repo import ClientRepository
from app.services.api_key_service import APIKeyService

logger = logging.getLogger(__name__)

# Module-level singleton — lazy-init handled inside ClientRepository.
_client_repo = ClientRepository()


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Client:
    """
    FastAPI dependency that authenticates an incoming API key.

    Reads the ``X-API-Key`` header, hashes it, and looks up the matching
    client in Cosmos DB.  Raises:
    - 401 if the header is absent or the key is unknown.
    - 403 if the client account is suspended.

    Returns the authenticated :class:`~app.models.client.Client` for use by
    downstream route handlers and the rate limiter.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via X-API-Key header.",
        )

    key_hash = APIKeyService.hash_api_key(x_api_key)
    client = await _client_repo.get_client_by_api_key_hash(key_hash)

    if client is None:
        # Avoid timing oracle: we already spent time hashing, so no extra delay needed.
        logger.warning("verify_api_key: unrecognised key hash (last 8): %s", key_hash[-8:])
        raise HTTPException(status_code=401, detail="Invalid API key.")

    if not client.is_active:
        logger.warning("verify_api_key: suspended client %s attempted access", client.client_id)
        raise HTTPException(status_code=403, detail="API key suspended. Contact support.")

    return client
