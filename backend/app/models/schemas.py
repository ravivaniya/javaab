from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any, Literal

class ChatRequest(BaseModel):
    user_id: str
    query: Optional[str] = ""
    image_base64: Optional[str] = None
    class_level: int
    board: str
    subject: Optional[str] = ""
    language: str = "en"
    conversation_id: Optional[str] = None
    retry_of: Optional[str] = None

class BookmarkRequest(BaseModel):
    message_id: str
    conversation_id: str
    user_id: str
    content: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    confidence: str
    sources: List[str] = []

class Source(BaseModel):
    """Reference to a textbook chunk or verified-answer source."""
    title: str
    chapter: Optional[str] = None
    page: Optional[int] = None
    score: Optional[float] = None

class ModelRouterResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    content: str
    model_used: str
    tier: int                       # 0=cache, 1=nano, 2=mini, 3=full
    tokens_input: int
    tokens_output: int
    tokens_total: int
    from_cache: bool
    confidence: str                 # "high" | "medium" | "low" | "none"
    sources: List[Source]
    conversation_id: Optional[str] = None
    classification_tokens: int = 0  # tokens spent on the complexity classifier
    embedding_tokens: int = 0       # tokens spent on RAG embedding (populated by caller)
    total_billable_tokens: int = 0  # tokens_total + classification_tokens + embedding_tokens
    cost: float = 0.0

class ImageExtractionResult(BaseModel):
    extracted_text: str
    detected_language: str
    detected_subject: str
    is_clear: bool

class TitleUpdateRequest(BaseModel):
    """PATCH /chat/{conversation_id}/title"""
    user_id: str
    title: str = Field(..., max_length=80)

class MessageEditRequest(BaseModel):
    """PATCH /chat/{conversation_id}/message/{message_id}"""
    user_id: str
    content: str = Field(..., min_length=1)

class DebugRoutingRequest(BaseModel):
    """POST /debug/routing — admin-only diagnostic endpoint"""
    query: str
    subject: str = ""
