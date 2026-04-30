from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class WorksheetType(str, Enum):
    DPP = "dpp"
    WORKSHEET = "worksheet"
    REVISION = "revision"
    HOMEWORK = "homework"
    MCQ_DRILL = "mcq_drill"


class WorksheetConfig(BaseModel):
    board: str
    class_level: int = Field(..., ge=6, le=12)
    subject: str
    topic: str
    chapter: str
    worksheet_type: WorksheetType
    num_questions: int = Field(default=15, ge=1, le=50)
    difficulty: str = "mixed"
    include_theory_summary: bool = True
    include_hints: bool = False
    include_answer_key: bool = True
    language: str = "en"
    institute_name: str = ""
    date_field: bool = True
    student_name_field: bool = True


class WorksheetQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str
    question_type: str
    marks: int
    hint: str = ""
    correct_answer: str
    solution_steps: str


class GeneratedWorksheet(BaseModel):
    worksheet_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    config: WorksheetConfig
    theory_summary: str = ""
    questions: list[WorksheetQuestion] = []
    worksheet_html: str = ""
    answer_key_html: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str
    status: str = "generating"
