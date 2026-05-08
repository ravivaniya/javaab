import hashlib
import secrets
import string

_ALPHABET = string.ascii_letters + string.digits
_PREFIX = "jvb_live_"
_RANDOM_LEN = 32


class APIKeyService:
    """Stateless helpers for API key generation and hashing."""

    @staticmethod
    def generate_api_key() -> tuple[str, str, str]:
        """
        Generate a new API key triple.

        Returns:
            (raw_key, key_hash, key_prefix)
            - raw_key   : ``jvb_live_<32 alphanumeric chars>`` — show ONCE, never store.
            - key_hash  : SHA-256 hex digest of raw_key — stored in Cosmos.
            - key_prefix: first 12 chars of raw_key (``jvb_live_xxx``) — safe to display.
        """
        random_part = "".join(secrets.choice(_ALPHABET) for _ in range(_RANDOM_LEN))
        raw_key = f"{_PREFIX}{random_part}"
        return raw_key, APIKeyService.hash_api_key(raw_key), raw_key[:12]

    @staticmethod
    def hash_api_key(raw_key: str) -> str:
        """Return the SHA-256 hex digest of *raw_key*."""
        return hashlib.sha256(raw_key.encode()).hexdigest()
