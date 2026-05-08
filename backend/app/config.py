from functools import lru_cache
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application wide configuration via pydantic-settings.
    AliasChoices lets each field accept either the new clean name OR the legacy
    dotted name already stored in Azure Key Vault — no Key Vault changes needed.
    """
    # Environment
    ENVIRONMENT: str = "development"

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = "https://example.openai.azure.com/"
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"

    # Model deployments — accepts new clean name OR legacy Key Vault dotted name
    AZURE_OPENAI_NANO_DEPLOYMENT: str = Field(
        default="gpt-4.1-nano",
        validation_alias=AliasChoices(
            "AZURE_OPENAI_NANO_DEPLOYMENT",
            "AZURE_OPENAI_GPT4.1_NANO_DEPLOYMENT",  # legacy Key Vault / .env name
        ),
    )
    AZURE_OPENAI_MINI_DEPLOYMENT: str = Field(
        default="gpt-4.1-mini",
        validation_alias=AliasChoices(
            "AZURE_OPENAI_MINI_DEPLOYMENT",
            "AZURE_OPENAI_GPT4.1_MINI_DEPLOYMENT",  # legacy Key Vault / .env name
        ),
    )
    AZURE_OPENAI_FULL_DEPLOYMENT: str = Field(
        default="gpt-4.1",
        validation_alias=AliasChoices(
            "AZURE_OPENAI_FULL_DEPLOYMENT",
            "AZURE_OPENAI_GPT4.1_DEPLOYMENT",        # legacy Key Vault / .env name
        ),
    )

    # Azure AI Search
    AZURE_AI_SEARCH_ENDPOINT: str = "https://example.search.windows.net/"
    AZURE_AI_SEARCH_KEY: str = ""
    AZURE_AI_SEARCH_INDEX_CHUNKS: str = "textbook_chunks"
    AZURE_AI_SEARCH_INDEX_CACHE: str = "verified_answers"

    # Azure Redis Cache
    AZURE_REDIS_HOST: str = "example.redis.cache.windows.net"
    AZURE_REDIS_PORT: int = 6380
    AZURE_REDIS_KEY: str = ""

    # Azure Cosmos DB
    AZURE_COSMOS_ENDPOINT: str = "https://example.documents.azure.com:443/"
    AZURE_COSMOS_KEY: str = ""
    AZURE_COSMOS_DATABASE: str = "javaab"
    # Container names — must match what is deployed in Azure
    COSMOS_CONTAINER_CLIENTS: str = "clients"      # partition key: /client_id
    COSMOS_CONTAINER_LEDGER: str = "ledger"        # partition key: /client_id
    COSMOS_CONTAINER_CONVERSATIONS: str = "conversations"
    COSMOS_CONTAINER_PAPERS: str = "papers"
    COSMOS_CONTAINER_WORKSHEETS: str = "worksheets"

    # Blob Storage
    AZURE_BLOB_CONNECTION_STRING: str = ""
    AZURE_BLOB_CONTAINER_PDFS: str = "pdfs"

    # JWT Auth (B2C / API clients)
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 168

    # Admin Auth (separate credentials, separate JWT secret)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = ""  # bcrypt hash; generate with: python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('yourpassword'))"
    ADMIN_JWT_SECRET: str = ""  # separate from JWT_SECRET; falls back to JWT_SECRET if blank
    ADMIN_JWT_EXPIRY_HOURS: int = 12

    # Cosmos containers
    COSMOS_CONTAINER_AUDIT_LOG: str = "admin_audit_log"  # partition key: /admin_user

    # QA safety cap — remove or raise before public launch
    DAILY_GLOBAL_CAP: int = 500

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
        "populate_by_name": True,  # allow access by field name AND alias
    }


@lru_cache()
def get_settings() -> Settings:
    """Retrieve application settings, cached."""
    return Settings()
