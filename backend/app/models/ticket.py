from pydantic import BaseModel

class Ticket(BaseModel):
    id: str
    student_id: str
    question: str
    status: str = "open" # open, resolved
