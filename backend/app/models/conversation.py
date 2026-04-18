from pydantic import BaseModel
from typing import List, Dict

class Conversation(BaseModel):
    id: str
    student_id: str
    messages: List[Dict[str, str]]
    created_at: str
