from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application wide configuration via pydantic-settings.
    """
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = "https://example.openai.azure.com/"
    AZURE_OPENAI_KEY: str = ""
    
    # Azure AI Search
    AZURE_AI_SEARCH_ENDPOINT: str = "https://example.search.windows.net/"
    AZURE_AI_SEARCH_KEY: str = ""
    
    # Azure Redis Cache
    AZURE_REDIS_HOST: str = "example.redis.cache.windows.net"
    AZURE_REDIS_KEY: str = ""
    
    # Azure Cosmos DB
    AZURE_COSMOS_ENDPOINT: str = "https://example.documents.azure.com:443/"
    AZURE_COSMOS_KEY: str = ""
    
    # Blob Storage
    AZURE_BLOB_CONNECTION_STRING: str = ""
    
    # Custom LLMs
    PHI4_MINI_ENDPOINT: str = ""
    PHI4_MINI_KEY: str = ""

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """
    Retrieve application settings, cached.
    """
    return Settings()
