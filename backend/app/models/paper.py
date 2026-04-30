from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class QuestionType(str, Enum):
    MCQ = "mcq"
    SHORT = "short"
    LONG = "long"
    VERY_LONG = "very_long"
    FILL_BLANK = "fill_blank"
    TRUE_FALSE = "true_false"
    ASSERTION_REASON = "assertion_reason"


class DifficultyMix(BaseModel):
    easy: int = 30
    medium: int = 50
    hard: int = 20

    @model_validator(mode="after")
    def must_sum_to_100(self) -> "DifficultyMix":
        total = self.easy + self.medium + self.hard
        if total != 100:
            raise ValueError(f"easy + medium + hard must equal 100 (got {total})")
        return self


class SectionConfig(BaseModel):
    section_label: str
    question_type: QuestionType
    num_questions: int = Field(..., gt=0)
    marks_per_question: int = Field(..., gt=0)
    instructions: str = ""


class PaperConfig(BaseModel):
    board: str
    class_level: int = Field(..., ge=6, le=12)
    subject: str
    chapters: list[str] = Field(..., min_length=1)
    difficulty_mix: DifficultyMix = Field(default_factory=DifficultyMix)
    sections: list[SectionConfig] = Field(..., min_length=1)
    total_marks: int = Field(..., gt=0)
    duration_minutes: int = Field(..., gt=0)
    num_variants: int = Field(default=1, ge=1, le=3)
    include_answer_key: bool = True
    include_marking_scheme: bool = True
    language: str = "en"
    institute_name: str = ""
    institute_logo_url: str = ""
    exam_title: str = ""
    paper_instructions: str = ""


class GeneratedQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str
    question_type: QuestionType
    marks: int
    difficulty: str
    chapter: str
    topic: str
    options: list[str] = []
    correct_answer: str
    marking_scheme: str
    bloom_level: str


class PaperVariant(BaseModel):
    variant_label: str
    sections: dict[str, list[GeneratedQuestion]] = {}
    paper_html: str = ""
    answer_key_html: str = ""
    marking_scheme_html: str = ""


class GeneratedPaper(BaseModel):
    paper_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    config: PaperConfig
    variants: list[PaperVariant] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str
    status: str = "generating"
