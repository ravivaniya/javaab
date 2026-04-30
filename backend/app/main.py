from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.routes import chat, auth, tickets, admin, student, papers, worksheets
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.config import get_settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Javaab Backend API",
    description="Backend API for Javaab AI educational platform.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://app.tryjavaab.com",
        "https://polite-sand-0e7a7af10.7.azurestaticapps.net"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth + rate limiting. Registration order matters: the last registered
# middleware runs first on the inbound request, so RateLimiter is added
# before Auth — that way Auth runs first and populates request.state.user_id
# before RateLimiter reads it.
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(AuthMiddleware)

# Error handling middleware
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """
    Middleware to catch unhandled exceptions globally and return standardized JSON responses.
    """
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred."}
        )

# Routers
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(student.router, prefix="/student", tags=["student"])
app.include_router(papers.router, prefix="/admin/papers", tags=["papers"])
app.include_router(worksheets.router, prefix="/admin/worksheets", tags=["worksheets"])

@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint to verify backend status.
    """
    from datetime import datetime
    import redis.asyncio as redis
    from azure.cosmos.aio import CosmosClient
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes.aio import SearchIndexClient
    from app.config import get_settings

    settings = get_settings()
    
    status_openai = "not configured"
    status_search = "not configured"
    status_redis = "not configured"
    status_cosmos = "not configured"
    
    # 1. OpenAI Check
    if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_KEY:
        status_openai = "connected"
            
    # 2. Redis Check
    if settings.AZURE_REDIS_HOST and settings.AZURE_REDIS_KEY:
        try:
            r = redis.Redis(
                host=settings.AZURE_REDIS_HOST, 
                port=settings.AZURE_REDIS_PORT, 
                password=settings.AZURE_REDIS_KEY, 
                ssl=True, 
                socket_timeout=2.0,
                decode_responses=True
            )
            await r.ping()
            await r.aclose()
            status_redis = "connected"
        except Exception as e:
            status_redis = f"error: {str(e)}"
            
    # 3. Cosmos Check
    if settings.AZURE_COSMOS_ENDPOINT and settings.AZURE_COSMOS_KEY:
        try:
            c_client = CosmosClient(settings.AZURE_COSMOS_ENDPOINT, credential=settings.AZURE_COSMOS_KEY)
            async with c_client:
                # list databases async
                databases = [db async for db in c_client.list_databases()]
                status_cosmos = "connected"
        except Exception as e:
            status_cosmos = f"error: {str(e)}"
            
    # 4. Search Check
    if settings.AZURE_AI_SEARCH_ENDPOINT and settings.AZURE_AI_SEARCH_KEY:
        try:
            cred = AzureKeyCredential(settings.AZURE_AI_SEARCH_KEY)
            s_client = SearchIndexClient(endpoint=settings.AZURE_AI_SEARCH_ENDPOINT, credential=cred)
            async with s_client:
                await s_client.get_index(settings.AZURE_AI_SEARCH_INDEX_CHUNKS)
                status_search = "connected"
        except Exception as e:
            status_search = f"error: {str(e)}"
            
    return {
        "status": "ok",
        "auth_mode": settings.AUTH_MODE,
        "azure_openai": status_openai,
        "azure_search": status_search,
        "redis": status_redis,
        "cosmos": status_cosmos,
        "timestamp": datetime.utcnow().isoformat()
    }
