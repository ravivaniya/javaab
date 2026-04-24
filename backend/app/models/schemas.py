from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any

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

class ModelRouterResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    answer: str
    model_used: str
    tokens_in: int
    tokens_out: int
    cost: float
    confidence: str
    from_cache: bool
    sources: List[str]
    conversation_id: Optional[str] = None

class ImageExtractionResult(BaseModel):
    extracted_text: str
    detected_language: str
    detected_subject: str
    is_clear: bool

class TicketCreateRequest(BaseModel):
    user_id: str
    question: str
    image_base64: Optional[str] = None
    board: str
    class_level: int
    subject: Optional[str] = ""
    ai_attempts: List[str] = []

class TicketResponseRequest(BaseModel):
    teacher_id: str
    answer: str
    source_citation: Optional[str] = None

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
