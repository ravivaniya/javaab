from pydantic import BaseModel
from typing import Optional

class Student(BaseModel):
    id: str
    phone_number: str
    is_pro: bool = False
    pro_days_remaining: int = 0
