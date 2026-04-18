import uuid
import json
import logging
import base64
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, FeedbackRequest
from app.repositories.cosmos_repo import CosmosRepo
from app.services.image_service import ImageService
from app.services.cache_service import CacheService
from app.services.rag_service import RagService
from app.services.model_router import ModelRouter
from app.prompts.system_prompt import build_system_message

logger = logging.getLogger(__name__)
router = APIRouter()

# Instantiate Singletons (Typically injected via Depends())
cosmos_repo = CosmosRepo()
image_service = ImageService()
cache_service = CacheService()
rag_service = RagService()
model_router = ModelRouter()

TIER_LIMITS = {
    "Free": 50,
    "Plus": 1000,
    "Pro": float("inf")
}

def _check_rate_limit(user: dict):
    tier = user.get("tier", "Free")
    used = user.get("monthly_queries_used", 0)
    limit = TIER_LIMITS.get(tier, 50)
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail="You've used all your free questions this month! 📚\n Upgrade to Javaab Plus for 1,000 questions/month."
        )

async def perform_background_logging(user_id: str, query: str, reply: str, meta: dict, message_id: str):
    """Executes safely outside the TCP Request via FastAPI BackgroundTasks"""
    await cosmos_repo.increment_user_usage(user_id)
    
    convo_data = {
        "id": message_id,
        "user_id": user_id,
        "query": query,
        "reply": reply,
        "metadata": meta
    }
    await cosmos_repo.save_conversation(convo_data)
    
    if meta.get("confidence") == "LOW":
        # Flagging logic natively sent to DB
        logger.warning(f"Flagging Low Confidence Answer for Review. msg_id={message_id}")
        await cosmos_repo.save_feedback({"message_id": message_id, "is_positive": False, "reason": "SYSTEM_FLAG_LOW_CONFIDENCE"})


async def ask_pipeline_generator(request: ChatRequest, user: dict, message_id: str, bg_tasks: BackgroundTasks) -> AsyncGenerator[str, None]:
    query = request.query or ""
    
    # 1. Image OCR & Validation Pipeline
    has_image = bool(request.image_base64)
    if has_image:
        try:
            image_bytes = base64.b64decode(request.image_base64)
            if not await image_service.validate_image(image_bytes):
                yield f"data: {json.dumps({'type': 'chunk', 'content': 'The image is corrupted or beyond 5MB. ⚠️'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            
            # Assuming optimize_image runs fast for bandwidth
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

    # 4. Check Cache Early to completely leapfrog RAG overhead
    cached_ans = await cache_service.check_cache(query, request.board, request.class_level, request.subject)
    
    context_str = ""
    confidence = "NONE"
    
    if not cached_ans:
        # 5. RAG Pipeline Trigger
        filters = {"board": request.board, "class_level": request.class_level, "subject": request.subject}
        rag_data = await rag_service.get_context(query, filters, request.language)
        context_str = rag_data.get("context", "")
        confidence = rag_data.get("confidence", "NONE")
    
    # 6. Prompt Engineering
    system_prompt = build_system_message(request.class_level, request.board, request.subject, user.get("tier", "Free"))
    
    # 7. Model Router (inherently handles Tier 0 if cached_ans exists upstream by querying again or directly yielding)
    ai_stream = model_router.route_query_stream(
        query=query,
        board=request.board,
        class_level=request.class_level,
        subject=request.subject,
        context=context_str,
        confidence=confidence,
        system_prompt=system_prompt,
        has_image=has_image
    )
    
    # 8. Transform output to Client SSE Dictionary Rules
    async for chunk in ai_stream:
        if chunk.startswith("\\n\\n[METADATA]") or chunk.startswith("\n\n[METADATA]"):
            try:
                # model_router ends its stream with a JSON block we must intercept
                meta_json_str = chunk.replace("\\n\\n[METADATA]", "").replace("\n\n[METADATA]", "")
                meta = json.loads(meta_json_str)
                
                yield f"data: {json.dumps({'type': 'metadata', 'model': meta.get('model_used'), 'confidence': meta.get('confidence')})}\n\n"
                yield f"data: {json.dumps({'type': 'sources', 'sources': meta.get('sources', [])})}\n\n"
                
                bg_tasks.add_task(perform_background_logging, request.user_id, query, meta.get("answer", ""), meta, message_id)
            except Exception as e:
                logger.error(f"Failed parsing meta tail: {e}")
                
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

@router.post("/ask")
async def ask_question(request: ChatRequest, bg_tasks: BackgroundTasks):
    """
    POST /chat/ask
    Unified orchestrator route wrapping validation, AI components, and strictly-typed SSE flows.
    """
    user = await cosmos_repo.get_user(request.user_id)
    _check_rate_limit(user)
    
    msg_id = str(uuid.uuid4())
    
    return StreamingResponse(
        ask_pipeline_generator(request, user, msg_id, bg_tasks),
        media_type="text/event-stream"
    )

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    POST /chat/feedback
    Submit user feedback on a specific response.
    """
    # Simple write operation. Advanced pipeline triggers >20% thresholds via Cosmos DB batch jobs.
    await cosmos_repo.save_feedback({
        "message_id": request.message_id,
        "is_positive": request.is_positive,
        "reason": request.reason
    })
    
    return {"status": "feedback received securely"}
