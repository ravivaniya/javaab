"""B2B chat endpoint: POST /api/v1/chat."""

import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

from app.middleware.api_key_auth import verify_api_key
from app.models.client import Client
from app.models.schemas import Source
from app.prompts.system_prompt import build_system_message
from app.repositories.cosmos_repo import CosmosRepo
from app.services.cache_service import CacheService
from app.services.credit_service import CreditService, tokens_to_credits
from app.services.image_service import ImageService
from app.services.model_router import ModelRouter
from app.services.rag_service import RagService

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Service singletons (lazy-init inside each service) ────────────────────────
_cosmos = CosmosRepo()
_cache = CacheService()
_rag = RagService()
_model_router = ModelRouter()
_image = ImageService()
_credits = CreditService()

MIN_PREFLIGHT_CREDITS = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """B2B chat request for POST /api/v1/chat."""

    query: Optional[str] = None
    image_base64: Optional[str] = None
    board: Literal["cbse", "gseb"]
    class_level: int = Field(..., ge=6, le=12)
    subject: Optional[str] = None
    language: Optional[Literal["en", "hi", "gu"]] = None
    conversation_id: Optional[str] = None
    stream: bool = False

    @model_validator(mode="after")
    def require_query_or_image(self) -> "ChatRequest":
        if not self.query and not self.image_base64:
            raise ValueError("At least one of 'query' or 'image_base64' is required.")
        return self


class ChatResponse(BaseModel):
    """B2B chat response for POST /api/v1/chat (non-streaming)."""

    request_id: str
    conversation_id: str
    answer: str
    sources: List[Source]
    model_used: str
    confidence: str
    tokens_used: int
    credits_consumed: int
    credits_remaining: int


# ── Internal helpers ──────────────────────────────────────────────────────────

def _detect_language(text: str) -> str:
    """Script-based language detection — Devanagari → hi, Gujarati → gu, else en."""
    for ch in text:
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F:
            return "hi"
        if 0x0A80 <= cp <= 0x0AFF:
            return "gu"
    return "en"


def _tier_to_feature(tier: int, has_image: bool) -> str:
    if tier <= 1:
        return "chat_simple"
    if tier == 2:
        return "chat_image" if has_image else "chat_medium"
    return "chat_complex"


def _is_metadata_chunk(chunk: str) -> bool:
    return chunk.startswith("\n\n[METADATA]") or chunk.startswith("\\n\\n[METADATA]")


def _parse_metadata(chunk: str, confidence_score: float) -> dict:
    raw = chunk.replace("\\n\\n[METADATA]", "").replace("\n\n[METADATA]", "")
    meta = json.loads(raw)
    meta.setdefault("confidence_score", confidence_score)
    return meta


async def _prepare_context(request: ChatRequest, request_id: str) -> dict:
    """
    Run all pre-LLM stages: OCR, language detection, cache check, RAG, history.
    Raises HTTPException on validation/image errors.
    Returns a context dict consumed by both streaming and non-streaming paths.
    """
    query = request.query or ""
    subject = request.subject or ""
    has_image = bool(request.image_base64)

    # ── Image OCR ─────────────────────────────────────────────────────────────
    if has_image:
        try:
            image_bytes = base64.b64decode(request.image_base64)  # type: ignore[arg-type]
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data.")

        if not await _image.validate_image(image_bytes):
            raise HTTPException(
                status_code=400, detail="Image is corrupted or exceeds 5 MB."
            )

        await _image.optimize_image(image_bytes)
        extract = await _image.extract_question(request.image_base64)  # type: ignore[arg-type]
        if not extract.is_clear:
            raise HTTPException(
                status_code=400,
                detail="Image was too unclear to process. Please type the question.",
            )
        query = f"{query}\n\n[Extracted OCR]: {extract.extracted_text}".strip()

    # ── Language detection ────────────────────────────────────────────────────
    language: str = request.language or (_detect_language(query) if query else "en")

    # ── Cache check (Tier 0) ──────────────────────────────────────────────────
    cached = await _cache.check_cache(query, request.board, request.class_level, subject)

    context_str = ""
    confidence = "NONE"
    confidence_score = 0.0

    if not cached:
        # ── RAG retrieval ─────────────────────────────────────────────────────
        rag_data = await _rag.get_context(
            query,
            {"board": request.board, "class_level": request.class_level, "subject": subject},
            language,
        )
        context_str = rag_data.get("context", "")
        confidence = rag_data.get("confidence", "NONE")
        confidence_score = float(rag_data.get("confidence_score", 0.0))

    # ── Conversation history ──────────────────────────────────────────────────
    conv_history: list = []
    if request.conversation_id:
        try:
            conv_history = await _cosmos.get_conversation_history(
                request.conversation_id, max_turns=6, max_tokens=1500
            ) or []
        except Exception as exc:
            logger.warning(
                "get_conversation_history(%s) failed (request_id=%s): %s",
                request.conversation_id, request_id, exc,
            )

    # ── System prompt ─────────────────────────────────────────────────────────
    system_prompt = build_system_message(
        request.class_level, request.board, subject, "starter"
    )

    return {
        "query": query,
        "language": language,
        "subject": subject,
        "context_str": context_str,
        "confidence": confidence,
        "confidence_score": confidence_score,
        "conv_history": conv_history,
        "system_prompt": system_prompt,
        "has_image": has_image,
    }


async def _deduct_credits(
    client_id: str,
    request_id: str,
    meta: dict,
    has_image: bool,
) -> tuple[int, int]:
    """
    Compute credits from model metadata, deduct, return (credits_consumed, credits_remaining).
    Skips deduction for cache hits (total_billable_tokens == 0).
    """
    total_tokens: int = meta.get("total_billable_tokens", 0)
    credits_consumed = tokens_to_credits(total_tokens) if total_tokens > 0 else 0
    feature = _tier_to_feature(meta.get("tier", 2), has_image)

    if credits_consumed > 0:
        credits_remaining = await _credits.deduct(
            client_id=client_id,
            credits=credits_consumed,
            feature=feature,
            tokens_input=meta.get("tokens_input", 0),
            tokens_output=meta.get("tokens_output", 0),
            request_id=request_id,
        )
    else:
        credits_remaining = await _credits.get_balance(client_id)

    return credits_consumed, credits_remaining


# ── SSE streaming generator ───────────────────────────────────────────────────

async def _sse_pipeline(
    request: ChatRequest,
    client: Client,
    request_id: str,
    conversation_id: str,
    bg_tasks: BackgroundTasks,
) -> AsyncGenerator[str, None]:
    """Async generator that emits SSE events for the streaming path."""

    def _evt(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    # ── Pre-LLM stages ────────────────────────────────────────────────────────
    try:
        ctx = await _prepare_context(request, request_id)
    except HTTPException as exc:
        yield _evt({"type": "error", "status": exc.status_code, "detail": exc.detail})
        yield _evt({"type": "done"})
        return
    except Exception as exc:
        logger.error("SSE prepare error (request_id=%s): %s", request_id, exc)
        yield _evt({"type": "error", "status": 500, "detail": f"Internal error. Reference: {request_id}"})
        yield _evt({"type": "done"})
        return

    # ── Stream model router output ────────────────────────────────────────────
    full_text = ""
    meta: dict = {}
    try:
        ai_stream = _model_router.route_query_stream(
            query=ctx["query"],
            board=request.board,
            class_level=request.class_level,
            subject=ctx["subject"],
            context=ctx["context_str"],
            confidence=ctx["confidence"],
            system_prompt=ctx["system_prompt"],
            has_image=ctx["has_image"],
            conversation_history=ctx["conv_history"],
        )
        async for chunk in ai_stream:
            if _is_metadata_chunk(chunk):
                try:
                    meta = _parse_metadata(chunk, ctx["confidence_score"])
                except Exception as exc:
                    logger.error(
                        "SSE: metadata parse failed (request_id=%s): %s", request_id, exc
                    )
            else:
                full_text += chunk
                yield _evt({"type": "chunk", "content": chunk})
    except Exception as exc:
        logger.error("SSE AI error (request_id=%s): %s", request_id, exc)
        yield _evt({"type": "error", "status": 500, "detail": f"Internal error. Reference: {request_id}"})
        yield _evt({"type": "done"})
        return

    # ── Emit metadata + sources ───────────────────────────────────────────────
    yield _evt({
        "type": "metadata",
        "model_used": meta.get("model_used", "unknown"),
        "confidence": meta.get("confidence", "none"),
    })
    yield _evt({"type": "sources", "sources": meta.get("sources", [])})

    # ── Credit deduction ──────────────────────────────────────────────────────
    try:
        credits_consumed, credits_remaining = await _deduct_credits(
            client.client_id, request_id, meta, ctx["has_image"]
        )
    except Exception as exc:
        logger.error("SSE credit deduct failed (request_id=%s): %s", request_id, exc)
        credits_consumed, credits_remaining = 0, -1

    yield _evt({
        "type": "usage",
        "tokens_used": meta.get("total_billable_tokens", 0),
        "credits_consumed": credits_consumed,
        "credits_remaining": credits_remaining,
    })

    # ── Background: save conversation turn ────────────────────────────────────
    bg_tasks.add_task(
        _cosmos.save_conversation,
        {
            "id": request_id,
            "client_id": client.client_id,
            "conversation_id": conversation_id,
            "query": request.query or "",
            "reply": full_text,
            "metadata": meta,
            "created_at": _now_iso(),
        },
    )

    yield _evt({"type": "done"})


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("")
async def chat(
    request: ChatRequest,
    bg_tasks: BackgroundTasks,
    client: Client = Depends(verify_api_key),
):
    """
    POST /api/v1/chat

    Unified B2B AI tutoring endpoint.  Accepts text and/or image input,
    returns Markdown + LaTeX answer with source citations and credit accounting.

    Set ``stream=true`` for Server-Sent Events; otherwise returns JSON.
    """
    request_id = str(uuid.uuid4())
    logger.info(
        "POST /api/v1/chat client=%s request_id=%s board=%s class=%d stream=%s",
        client.client_id, request_id, request.board, request.class_level, request.stream,
    )

    # ── Step 2: Pre-flight credit check ───────────────────────────────────────
    if not await _credits.check_and_reserve(client.client_id, MIN_PREFLIGHT_CREDITS):
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits. Please top up.",
        )

    # ── Resolve / create conversation ─────────────────────────────────────────
    conversation_id = request.conversation_id or str(uuid.uuid4())
    if not request.conversation_id:
        bg_tasks.add_task(
            _cosmos.create_conversation,
            {
                "id": conversation_id,
                "client_id": client.client_id,
                "board": request.board,
                "class_level": request.class_level,
                "subject": request.subject or "",
                "language": request.language or "auto",
                "created_at": _now_iso(),
            },
        )

    # ── Streaming path ────────────────────────────────────────────────────────
    if request.stream:
        return StreamingResponse(
            _sse_pipeline(request, client, request_id, conversation_id, bg_tasks),
            media_type="text/event-stream",
            headers={"X-Request-ID": request_id},
        )

    # ── Non-streaming path ────────────────────────────────────────────────────
    try:
        ctx = await _prepare_context(request, request_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Pipeline prepare failed (request_id=%s client=%s): %s",
            request_id, client.client_id, exc,
        )
        raise HTTPException(
            status_code=500, detail=f"Internal error. Reference: {request_id}"
        )

    full_text = ""
    meta: dict = {}
    try:
        ai_stream = _model_router.route_query_stream(
            query=ctx["query"],
            board=request.board,
            class_level=request.class_level,
            subject=ctx["subject"],
            context=ctx["context_str"],
            confidence=ctx["confidence"],
            system_prompt=ctx["system_prompt"],
            has_image=ctx["has_image"],
            conversation_history=ctx["conv_history"],
        )
        async for chunk in ai_stream:
            if _is_metadata_chunk(chunk):
                try:
                    meta = _parse_metadata(chunk, ctx["confidence_score"])
                except Exception as exc:
                    logger.error(
                        "Metadata parse failed (request_id=%s): %s", request_id, exc
                    )
            else:
                full_text += chunk
    except Exception as exc:
        logger.error(
            "AI pipeline error (request_id=%s client=%s): %s",
            request_id, client.client_id, exc,
        )
        raise HTTPException(
            status_code=500, detail=f"Internal error. Reference: {request_id}"
        )

    # ── Steps 9–10: Credit deduction ──────────────────────────────────────────
    credits_consumed, credits_remaining = await _deduct_credits(
        client.client_id, request_id, meta, ctx["has_image"]
    )

    # ── Step 11: Background conversation save ─────────────────────────────────
    bg_tasks.add_task(
        _cosmos.save_conversation,
        {
            "id": request_id,
            "client_id": client.client_id,
            "conversation_id": conversation_id,
            "query": request.query or "",
            "reply": full_text,
            "metadata": meta,
            "created_at": _now_iso(),
        },
    )

    # ── Step 12: Return ChatResponse ──────────────────────────────────────────
    sources_raw = meta.get("sources", [])
    sources = [Source(**s) if isinstance(s, dict) else s for s in sources_raw]

    return ChatResponse(
        request_id=request_id,
        conversation_id=conversation_id,
        answer=full_text,
        sources=sources,
        model_used=meta.get("model_used", "unknown"),
        confidence=meta.get("confidence", "none"),
        tokens_used=meta.get("total_billable_tokens", 0),
        credits_consumed=credits_consumed,
        credits_remaining=credits_remaining,
    )
