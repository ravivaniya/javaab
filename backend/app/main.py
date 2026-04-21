from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.routes import chat, auth, subjects, tickets, admin
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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint to verify backend status.
    """
    return {"status": "ok"}
