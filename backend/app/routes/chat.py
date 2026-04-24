import uuid
import json
import logging
import base64
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.models.schemas import (
    ChatRequest,
    BookmarkRequest,
    TitleUpdateRequest,
    MessageEditRequest,
    DebugRoutingRequest,
)
from app.repositories.cosmos_repo import CosmosRepo
from app.repositories.redis_repo import RedisRepo
from app.services.image_service import ImageService
from app.services.cache_service import CacheService
from app.services.rag_service import RagService
from app.services.model_router import ModelRouter
from app.prompts.system_prompt import build_system_message

logger = logging.getLogger(__name__)
router = APIRouter()

settings = get_settings()

cosmos_repo = CosmosRepo()
redis_repo = RedisRepo()
image_service = ImageService()
cache_service = CacheService()
rag_service = RagService()
model_router = ModelRouter()

TIER_LIMITS = {
    "Free": 50,
    "Plus": 1000,
    "Pro": float("inf"),
}

_now_iso = lambda: datetime.now(timezone.utc).isoformat()


def _check_rate_limit(user: dict):
    tier = user.get("tier", "Free")
    used = user.get("monthly_queries_used", 0)
    limit = TIER_LIMITS.get(tier, 50)
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=(
                "You've used all your free questions this month! 📚\n"
                " Upgrade to Javaab Plus for 1,000 questions/month."
            ),
        )


async def perform_background_logging(
    user_id: str,
    query: str,
    reply: str,
    meta: dict,
    message_id: str,
    conversation_id: str,
    is_retry: bool = False,
):
    """Runs outside the TCP request via FastAPI BackgroundTasks."""
    if not is_retry:
        await cosmos_repo.increment_user_usage(user_id)

    message_doc = {
        "id": message_id,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "query": query,
        "reply": reply,
        "metadata": meta,
        "created_at": _now_iso(),
    }
    await cosmos_repo.save_conversation(message_doc)

    if meta.get("confidence") == "LOW":
        score = meta.get("confidence_score", 0.0)
        logger.warning(
            f"[low-confidence] chat_id={conversation_id} msg_id={message_id} "
            f"confidence=LOW score={score:.4f}"
        )
        await cosmos_repo.save_feedback(
            {"message_id": message_id, "is_positive": False, "reason": "SYSTEM_FLAG_LOW_CONFIDENCE"}
        )


async def ask_pipeline_generator(
    request: ChatRequest,
    user: dict,
    message_id: str,
    conversation_id: str,
    bg_tasks: BackgroundTasks,
) -> AsyncGenerator[str, None]:
    """Unified pipeline: image → cache → RAG → model → SSE stream."""
    query = request.query or ""

    # ── 1. Image OCR & validation ──────────────────────────────────────────
    has_image = bool(request.image_base64)
    if has_image:
        try:
            image_bytes = base64.b64decode(request.image_base64)
            if not await image_service.validate_image(image_bytes):
                yield f"data: {json.dumps({'type': 'chunk', 'content': 'The image is corrupted or beyond 5MB. ⚠️'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            image_bytes = await image_service.optimize_image(image_bytes)
            extract_result = await image_service.extract_question(request.image_base64)
            if extract_result.is_clear:
                query = f"{query}\n\n[Extracted OCR]: {extract_result.extracted_text}".strip()
            else:
                yield f"data: {json.dumps({'type': 'chunk', 'content': 'The image was a bit unclear. Could you also type out the question?'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
        except Exception as e:
            logger.error(f"Image pipeline fault: {e}")

    # ── 2. Emit conversation_id so the frontend can store it ───────────────
    yield f"data: {json.dumps({'type': 'conversation_id', 'id': conversation_id})}\n\n"

    # ── 3. Cache check (Tier 0) ────────────────────────────────────────────
    cached_ans = await cache_service.check_cache(
        query, request.board, request.class_level, request.subject
    )

    context_str = ""
    confidence = "NONE"
    confidence_score = 0.0

    if not cached_ans:
        # ── 4. RAG retrieval ───────────────────────────────────────────────
        filters = {
            "board": request.board,
            "class_level": request.class_level,
            "subject": request.subject,
        }
        rag_data = await rag_service.get_context(query, filters, request.language)
        context_str = rag_data.get("context", "")
        confidence = rag_data.get("confidence", "NONE")
        confidence_score = rag_data.get("confidence_score", 0.0)

    # ── 5. Conversation history ────────────────────────────────────────────
    conversation_history = []
    if request.conversation_id:
        conversation_history = await cosmos_repo.get_conversation_history(
            request.conversation_id, max_turns=6, max_tokens=1500
        )

    # ── 6. System prompt ──────────────────────────────────────────────────
    system_prompt = build_system_message(
        request.class_level, request.board, request.subject, user.get("tier", "Free")
    )

    # ── 7. Model router (streaming) ───────────────────────────────────────
    ai_stream = model_router.route_query_stream(
        query=query,
        board=request.board,
        class_level=request.class_level,
        subject=request.subject,
        context=context_str,
        confidence=confidence,
        system_prompt=system_prompt,
        has_image=has_image,
        conversation_history=conversation_history,
    )

    # ── 8. Transform chunks to SSE ────────────────────────────────────────
    async for chunk in ai_stream:
        if chunk.startswith("\\n\\n[METADATA]") or chunk.startswith("\n\n[METADATA]"):
            try:
                meta_json_str = chunk.replace("\\n\\n[METADATA]", "").replace("\n\n[METADATA]", "")
                meta = json.loads(meta_json_str)
                meta["conversation_id"] = conversation_id
                meta.setdefault("confidence_score", confidence_score)

                conf_label = meta.get('confidence', 'NONE')
                conf_score = meta.get('confidence_score', confidence_score)
                logger.info(
                    f"[chat] chat_id={conversation_id} msg_id={message_id} "
                    f"confidence={conf_label} score={conf_score:.4f} "
                    f"model={meta.get('model_used')} from_cache={meta.get('from_cache', False)}"
                )
                yield f"data: {json.dumps({'type': 'metadata', 'model': meta.get('model_used'), 'confidence': conf_label, 'confidence_score': conf_score, 'from_cache': meta.get('from_cache', False), 'conversation_id': conversation_id})}\n\n"
                yield f"data: {json.dumps({'type': 'sources', 'sources': meta.get('sources', [])})}\n\n"

                is_retry = bool(request.retry_of)
                bg_tasks.add_task(
                    perform_background_logging,
                    request.user_id,
                    query,
                    meta.get("answer", ""),
                    meta,
                    message_id,
                    conversation_id,
                    is_retry,
                )
            except Exception as e:
                logger.error(f"Failed parsing meta tail: {e}")

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"


# ─────────────────────────────────────────────────────────────────────────────
# POST /chat/ask
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/ask")
async def ask_question(request: ChatRequest, bg_tasks: BackgroundTasks):
    """
    POST /chat/ask
    Unified orchestrator: validation → AI pipeline → SSE stream.
    """
    # ── Daily global cap (O) ───────────────────────────────────────────────
    cap = settings.DAILY_GLOBAL_CAP
    allowed = await redis_repo.check_and_increment_daily_cap(cap)
    if not allowed:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "capacity_limit",
                "message": "Javaab is taking a short break. Try again in a little while!",
                # TODO: Remove or raise DAILY_GLOBAL_CAP before public launch
            },
        )

    user = await cosmos_repo.get_user(request.user_id)
    _check_rate_limit(user)

    # ── Per-message word limit (H) ─────────────────────────────────────────
    query_words = request.query.split() if request.query else []
    if len(query_words) > 150:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "message_too_long",
                "message": "Question must be under 150 words. Please break it into smaller questions.",
            },
        )

    # ── Session word limit (H) ─────────────────────────────────────────────
    if request.conversation_id:
        session_words = await redis_repo.get_session_word_count(request.conversation_id)
        if session_words + len(query_words) > 7500:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "session_limit_reached",
                    "message": (
                        "This conversation has reached its 7,500-word limit. "
                        "Please start a new chat."
                    ),
                },
            )
        await redis_repo.increment_session_words(request.conversation_id, len(query_words))

    # ── Resolve or create conversation ────────────────────────────────────
    conversation_id = request.conversation_id
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        await cosmos_repo.create_conversation(
            {
                "id": conversation_id,
                "student_id": request.user_id,
                "board": request.board,
                "class_level": request.class_level,
                "subject": request.subject,
                "language": request.language,
                "created_at": _now_iso(),
            }
        )

    msg_id = str(uuid.uuid4())

    return StreamingResponse(
        ask_pipeline_generator(request, user, msg_id, conversation_id, bg_tasks),
        media_type="text/event-stream",
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /chat/bookmark
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/bookmark")
async def bookmark_message(request: BookmarkRequest):
    """
    POST /chat/bookmark
    Save or unsave an assistant message for quick reference.
    """
    await cosmos_repo.save_bookmark(
        {
            "message_id": request.message_id,
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
            "content": request.content,
            "bookmarked_at": _now_iso(),
        }
    )
    return {"success": True}


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /chat/{conversation_id}/title  (A — Chat Rename)
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/{conversation_id}/title")
async def update_conversation_title(conversation_id: str, request: TitleUpdateRequest):
    """
    PATCH /chat/{conversation_id}/title
    Owner-only: update the human-readable title of a conversation.
    """
    conversation = await cosmos_repo.get_conversation(conversation_id)
    if conversation and conversation.get("student_id") != request.user_id:
        raise HTTPException(status_code=403, detail="You don't own this conversation.")

    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty.")

    await cosmos_repo.update_conversation_title(conversation_id, title)
    return {"success": True, "title": title}


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /chat/{conversation_id}/message/{message_id}  (B — One-Time Edit)
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/{conversation_id}/message/{message_id}")
async def edit_message(
    conversation_id: str,
    message_id: str,
    request: MessageEditRequest,
    bg_tasks: BackgroundTasks,
):
    """
    PATCH /chat/{conversation_id}/message/{message_id}
    One-time edit of a user message. Truncates subsequent messages and
    re-triggers the AI pipeline as a streaming response.
    """
    conversation = await cosmos_repo.get_conversation(conversation_id)
    if conversation and conversation.get("student_id") != request.user_id:
        raise HTTPException(status_code=403, detail="You don't own this conversation.")

    message = await cosmos_repo.get_message(conversation_id, message_id)

    if message is None:
        # Stub: allow edit to proceed (real impl would 404)
        logger.warning(f"Message {message_id} not found in conversation {conversation_id} (stub)")
    else:
        if message.get("role") != "user":
            raise HTTPException(status_code=400, detail="Only user messages can be edited.")
        if message.get("is_edited"):
            raise HTTPException(status_code=403, detail="Already edited once.")

    # Persist the edit
    await cosmos_repo.update_message(
        conversation_id,
        message_id,
        {
            "is_edited": True,
            "original_text": (message or {}).get("content", ""),
            "content": request.content.strip(),
            "updated_at": _now_iso(),
        },
    )

    # Remove all messages after this one ("branch from here")
    await cosmos_repo.delete_messages_after(conversation_id, message_id)

    # Re-trigger AI pipeline for the edited message
    user = await cosmos_repo.get_user(request.user_id)
    fake_request = ChatRequest(
        user_id=request.user_id,
        query=request.content.strip(),
        class_level=(conversation or {}).get("class_level", 10),
        board=(conversation or {}).get("board", "cbse"),
        subject=(conversation or {}).get("subject", ""),
        language=(conversation or {}).get("language", "en"),
        conversation_id=conversation_id,
    )
    new_msg_id = str(uuid.uuid4())

    return StreamingResponse(
        ask_pipeline_generator(fake_request, user, new_msg_id, conversation_id, bg_tasks),
        media_type="text/event-stream",
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /debug/routing  (J — admin-only diagnostic)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/debug/routing")
async def debug_routing(request: DebugRoutingRequest):
    """
    POST /debug/routing
    Admin-only: returns how the model router would classify a query.
    """
    from app.services.model_router import FORCE_COMPLEX_TOPICS, TIER_1_MODEL, TIER_2_MODEL, TIER_3_MODEL

    query_lower = request.query.lower()
    subject_lower = request.subject.lower()

    # Check force override
    force_override = False
    override_complexity = None
    topic_list = FORCE_COMPLEX_TOPICS.get(subject_lower, [])
    for keyword in topic_list:
        if keyword in query_lower:
            force_override = True
            override_complexity = "COMPLEX"
            break

    if force_override:
        classified_as = "COMPLEX"
        classifier_response_raw = f"FORCE_OVERRIDE: keyword matched in {subject_lower}"
    else:
        classified_as = await model_router._classify_complexity(request.query, has_image=False)
        classifier_response_raw = classified_as

    model_map = {"SIMPLE": TIER_1_MODEL, "MEDIUM": TIER_2_MODEL, "COMPLEX": TIER_3_MODEL}
    model_selected = model_map.get(classified_as, TIER_2_MODEL)

    return {
        "classified_as": classified_as,
        "force_override": force_override,
        "model_selected": model_selected,
        "classifier_response_raw": classifier_response_raw,
    }
