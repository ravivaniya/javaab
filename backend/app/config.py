from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application wide configuration via pydantic-settings.
    """
    # Environment
    ENVIRONMENT: str = "development"

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = "https://example.openai.azure.com/"
    AZURE_OPENAI_KEY: str = ""
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"
    
    # Custom LLMs
    AZURE_OPENAI_MINI_DEPLOYMENT: str = Field(default="gpt-4.1-nano", alias="AZURE_OPENAI_GPT4.1_NANO_DEPLOYMENT")
    AZURE_OPENAI_MEDIUM_DEPLOYMENT: str = Field(default="gpt-4.1-mini", alias="AZURE_OPENAI_GPT4.1_MINI_DEPLOYMENT")
    AZURE_OPENAI_GPT4_DEPLOYMENT: str = Field(default="gpt-4.1", alias="AZURE_OPENAI_GPT4.1_DEPLOYMENT")
    
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
    
    # Blob Storage
    AZURE_BLOB_CONNECTION_STRING: str = ""
    AZURE_BLOB_CONTAINER_PDFS: str = "pdfs"
    
    # JWT Auth
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 168
    
    # Auth Mode
    AUTH_MODE: str = "mock"
    MOCK_OTP: str = "123456"

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """
    Retrieve application settings, cached.
    """
    return Settings()
