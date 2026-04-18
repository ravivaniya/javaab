from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class ChatRequest(BaseModel):
    user_id: str
    query: Optional[str] = ""
    image_base64: Optional[str] = None
    class_level: int
    board: str
    subject: str
    language: str = "en"

class FeedbackRequest(BaseModel):
    message_id: str
    is_positive: bool
    reason: Optional[str] = None

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
    subject: str
    ai_attempts: List[str] = []

class TicketResponseRequest(BaseModel):
    teacher_id: str
    answer: str
    source_citation: Optional[str] = None
