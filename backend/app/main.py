from dotenv import load_dotenv
load_dotenv()

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.middleware.api_key_auth import verify_api_key
from app.middleware.rate_limiter import rate_limit
from app.routes import chat, papers, student, worksheets
from app.routes.admin import router as admin_router
from app.routes.api_v1 import chat as api_v1_chat
from app.routes.api_v1 import dpp as api_v1_dpp
from app.routes.api_v1 import qpg as api_v1_qpg
from app.routes.api_v1 import usage as api_v1_usage

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Javaab API",
    description="B2B AI infrastructure for Indian schools and coaching institutes.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5174",   # admin SPA (dev)
        "http://127.0.0.1:5174",  # admin SPA (dev)
        "https://app.tryjavaab.com",
        "https://polite-sand-0e7a7af10.7.azurestaticapps.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Catch unhandled exceptions and return a standardised JSON 500."""
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred."},
        )


# ── /api/v1/* — API key auth + rate limiting ─────────────────────────────────
#
# Both dependencies are listed explicitly so Swagger shows the X-API-Key lock
# icon on every route.  FastAPI caches dependency results within a request, so
# verify_api_key runs exactly once even though rate_limit also depends on it.

api_v1 = APIRouter(
    prefix="/api/v1",
    dependencies=[Depends(verify_api_key), Depends(rate_limit)],
)
api_v1.include_router(api_v1_chat.router, prefix="/chat", tags=["chat"])
api_v1.include_router(chat.router, prefix="/chat", tags=["chat"])
api_v1.include_router(student.router, prefix="/student", tags=["student"])
api_v1.include_router(api_v1_qpg.router, prefix="/generate", tags=["qpg"])
api_v1.include_router(api_v1_dpp.router, prefix="/generate", tags=["dpp"])
api_v1.include_router(api_v1_usage.router, prefix="/usage", tags=["usage"])
app.include_router(api_v1)


# ── /admin/* — admin JWT auth, no API key required ───────────────────────────

app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(papers.router, prefix="/admin/papers", tags=["papers"])
app.include_router(worksheets.router, prefix="/admin/worksheets", tags=["worksheets"])


# ── /health — public ─────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health_check():
    """Liveness probe: checks connectivity to all Azure dependencies."""
    import redis.asyncio as redis
    from azure.cosmos.aio import CosmosClient
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes.aio import SearchIndexClient

    settings = get_settings()

    status_openai = "not configured"
    status_search = "not configured"
    status_redis = "not configured"
    status_cosmos = "not configured"

    if settings.AZURE_OPENAI_ENDPOINT and "example" not in settings.AZURE_OPENAI_ENDPOINT:
        status_openai = "connected"

    if settings.AZURE_REDIS_HOST and "example" not in settings.AZURE_REDIS_HOST:
        try:
            r = redis.Redis(
                host=settings.AZURE_REDIS_HOST,
                port=settings.AZURE_REDIS_PORT,
                password=settings.AZURE_REDIS_KEY,
                ssl=True,
                socket_timeout=2.0,
                decode_responses=True,
            )
            await r.ping()
            await r.aclose()
            status_redis = "connected"
        except Exception as exc:
            status_redis = f"error: {exc}"

    if settings.AZURE_COSMOS_ENDPOINT and "example" not in settings.AZURE_COSMOS_ENDPOINT:
        try:
            async with CosmosClient(settings.AZURE_COSMOS_ENDPOINT, settings.AZURE_COSMOS_KEY) as c:
                _ = [db async for db in c.list_databases()]
            status_cosmos = "connected"
        except Exception as exc:
            status_cosmos = f"error: {exc}"

    if settings.AZURE_AI_SEARCH_ENDPOINT and "example" not in settings.AZURE_AI_SEARCH_ENDPOINT:
        try:
            cred = AzureKeyCredential(settings.AZURE_AI_SEARCH_KEY)
            async with SearchIndexClient(settings.AZURE_AI_SEARCH_ENDPOINT, cred) as s:
                await s.get_index(settings.AZURE_AI_SEARCH_INDEX_CHUNKS)
            status_search = "connected"
        except Exception as exc:
            status_search = f"error: {exc}"

    return {
        "status": "ok",
        "azure_openai": status_openai,
        "azure_search": status_search,
        "redis": status_redis,
        "cosmos": status_cosmos,
        "timestamp": datetime.utcnow().isoformat(),
    }
