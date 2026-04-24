from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Message(BaseModel):
    id: str
    role: str                           # "user" | "assistant"
    content: str
    created_at: str
    confidence: Optional[str] = None    # "HIGH" | "MEDIUM" | "LOW" | "NONE"
    model_used: Optional[str] = None
    from_cache: Optional[bool] = False
    source_citation: Optional[str] = None
    image_base64: Optional[str] = None  # TODO: migrate to Azure Blob URL for production
    # Edit tracking (one-time edit allowed per user message)
    is_edited: bool = False
    original_text: Optional[str] = None
    # Feedback fields
    needs_review: bool = False
    dislike_count: int = 0
    is_cache_candidate: bool = False

class Conversation(BaseModel):
    id: str
    student_id: str
    title: str = "New chat"             # max 80 chars; auto-generated from first user message
    messages: List[Message] = []
    subject: Optional[str] = None
    board: Optional[str] = None
    class_level: Optional[int] = None
    language: Optional[str] = "en"
    created_at: str
    updated_at: Optional[str] = None
