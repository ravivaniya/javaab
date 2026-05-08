"""B2B QPG endpoints: POST /api/v1/generate/question-paper[/pdf]."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, model_validator

from app.middleware.api_key_auth import verify_api_key
from app.models.client import Client
from app.models.paper import (
    DifficultyMix,
    PaperConfig,
    PaperVariant,
    QuestionType,
    SectionConfig,
)
from app.repositories.cosmos_repo import CosmosRepo
from app.services.credit_service import CreditService, tokens_to_credits
from app.services.paper_service import PaperService

logger = logging.getLogger(__name__)
router = APIRouter()

# Service singletons (lazy-init inside each service)
_cosmos = CosmosRepo()
_credits = CreditService()
_paper_service = PaperService()

# Credits reserved before generation starts; actual deduction is token-based.
_PREFLIGHT_CREDITS_PER_VARIANT = 15

# Standard CBSE/GSEB marks per question type.
_DEFAULT_MARKS: dict[str, int] = {
    "mcq": 1,
    "short": 3,
    "long": 5,
    "very_long": 8,
    "fill_blank": 1,
    "true_false": 1,
    "assertion_reason": 4,
}

_SECTION_LABELS = ["Section A", "Section B", "Section C", "Section D", "Section E"]


# ── Request schemas ───────────────────────────────────────────────────────────

class QuestionPaperRequest(BaseModel):
    """Request body for POST /api/v1/generate/question-paper."""

    board: Literal["cbse", "gseb"]
    class_level: int = Field(..., ge=6, le=12)
    subject: str
    chapters: list[str] = Field(..., min_length=1)
    difficulty_mix: dict = Field(
        default_factory=lambda: {"easy": 30, "medium": 50, "hard": 20}
    )
    question_distribution: dict  # {"mcq": 10, "short": 5, "long": 3} — type → count
    total_marks: int = Field(..., gt=0)
    duration_minutes: int = Field(..., gt=0)
    institute_name: Optional[str] = None
    institute_logo_url: Optional[str] = None
    num_variants: int = Field(default=1, ge=1, le=3)
    language: Literal["en", "hi", "gu"] = "en"
    include_answer_key: bool = True
    include_marking_scheme: bool = True

    @model_validator(mode="after")
    def _check_difficulty_mix(self) -> "QuestionPaperRequest":
        dm = self.difficulty_mix
        total = dm.get("easy", 0) + dm.get("medium", 0) + dm.get("hard", 0)
        if total != 100:
            raise ValueError(
                f"difficulty_mix easy+medium+hard must equal 100 (got {total})"
            )
        return self

    @model_validator(mode="after")
    def _check_question_distribution(self) -> "QuestionPaperRequest":
        valid = {qt.value for qt in QuestionType}
        for qtype in self.question_distribution:
            if qtype not in valid:
                raise ValueError(
                    f"Unknown question type '{qtype}'. Valid: {sorted(valid)}"
                )
        if not self.question_distribution:
            raise ValueError("question_distribution must have at least one entry.")
        return self


class QPGPdfRequest(BaseModel):
    """Request body for POST /api/v1/generate/question-paper/pdf."""

    variants: list[PaperVariantResponse]
    board: str
    class_level: int
    subject: str
    exam_title: str = ""
    total_marks: int
    duration_minutes: int
    institute_name: Optional[str] = None
    institute_logo_url: Optional[str] = None


# ── Response schemas ──────────────────────────────────────────────────────────

class Question(BaseModel):
    """A single question in the API response."""

    number: int
    type: str
    text: str
    marks: int
    difficulty: str
    chapter_ref: str
    options: Optional[list[str]] = None


class Answer(BaseModel):
    """An answer-key entry for a question."""

    number: int
    question_preview: str
    correct_answer: str
    marking_scheme: Optional[str] = None


class PaperVariantResponse(BaseModel):
    """One set (variant) of the generated paper in API response format."""

    variant_label: str
    questions: list[Question]
    answer_key: Optional[list[Answer]] = None
    marking_scheme: Optional[dict[str, str]] = None


class QuestionPaperResponse(BaseModel):
    """Response from POST /api/v1/generate/question-paper."""

    request_id: str
    variants: list[PaperVariantResponse]
    tokens_used: int
    credits_consumed: int
    credits_remaining: int


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_paper_config(req: QuestionPaperRequest) -> PaperConfig:
    """Translate the API request into the internal PaperConfig shape."""
    dm = DifficultyMix(
        easy=req.difficulty_mix.get("easy", 30),
        medium=req.difficulty_mix.get("medium", 50),
        hard=req.difficulty_mix.get("hard", 20),
    )
    sections: list[SectionConfig] = []
    for idx, (qtype, count) in enumerate(req.question_distribution.items()):
        if count <= 0:
            continue
        label = (
            _SECTION_LABELS[idx]
            if idx < len(_SECTION_LABELS)
            else f"Section {chr(65 + idx)}"
        )
        sections.append(
            SectionConfig(
                section_label=label,
                question_type=QuestionType(qtype),
                num_questions=int(count),
                marks_per_question=_DEFAULT_MARKS.get(qtype, 2),
            )
        )
    return PaperConfig(
        board=req.board,
        class_level=req.class_level,
        subject=req.subject,
        chapters=req.chapters,
        difficulty_mix=dm,
        sections=sections,
        total_marks=req.total_marks,
        duration_minutes=req.duration_minutes,
        num_variants=req.num_variants,
        include_answer_key=req.include_answer_key,
        include_marking_scheme=req.include_marking_scheme,
        language=req.language,
        institute_name=req.institute_name or "",
        institute_logo_url=req.institute_logo_url or "",
    )


def _flatten_variant(
    variant: PaperVariant,
    include_answer_key: bool,
    include_marking_scheme: bool,
) -> PaperVariantResponse:
    """Flatten internal PaperVariant sections into a numbered question list."""
    questions: list[Question] = []
    answers: list[Answer] = []
    marking: dict[str, str] = {}
    q_num = 1

    for qs in variant.sections.values():
        for q in qs:
            questions.append(
                Question(
                    number=q_num,
                    type=q.question_type.value,
                    text=q.question_text,
                    marks=q.marks,
                    difficulty=q.difficulty,
                    chapter_ref=q.chapter,
                    options=q.options if q.options else None,
                )
            )
            if include_answer_key:
                answers.append(
                    Answer(
                        number=q_num,
                        question_preview=q.question_text[:80],
                        correct_answer=q.correct_answer,
                        marking_scheme=q.marking_scheme if include_marking_scheme else None,
                    )
                )
            if include_marking_scheme and q.marking_scheme:
                marking[str(q_num)] = q.marking_scheme
            q_num += 1

    return PaperVariantResponse(
        variant_label=variant.variant_label,
        questions=questions,
        answer_key=answers if include_answer_key else None,
        marking_scheme=marking if include_marking_scheme else None,
    )


def _render_html(req: QPGPdfRequest, variant: PaperVariantResponse) -> str:
    """Render a print-ready HTML document for one paper variant."""
    logo_block = (
        f"<img src='{req.institute_logo_url}' class='logo' alt='Logo'>"
        if req.institute_logo_url
        else ""
    )
    institute_block = (
        f"<h2 class='institute-name'>{req.institute_name}</h2>"
        if req.institute_name
        else "<h2 class='institute-name'>Javaab</h2>"
    )

    qs_html = ""
    for q in variant.questions:
        opts_html = ""
        if q.options:
            opts_html = "<div class='options-grid'>" + "".join(
                f"<span class='opt'>{opt}</span>" for opt in q.options
            ) + "</div>"
        qs_html += (
            f"<div class='question'>"
            f"<span class='q-num'>{q.number}.</span> "
            f"<span class='q-text'>{q.text}</span> "
            f"<span class='marks'>[{q.marks}]</span>"
            f"{opts_html}"
            f"</div>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{req.exam_title or 'Question Paper'} — {variant.variant_label}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body,{{delimiters:[{{left:'\\\\[',right:'\\\\]',display:true}},{{left:'\\\\(',right:'\\\\)',display:false}}]}})"></script>
<style>
  body{{font-family:'Times New Roman',Times,serif;font-size:12pt;line-height:1.6;max-width:210mm;margin:0 auto;padding:20mm;color:#000;}}
  .header{{text-align:center;border-bottom:2px solid #000;padding-bottom:10px;margin-bottom:15px;}}
  .logo{{max-height:64px;margin:0 auto 8px;display:block;}}
  .institute-name{{font-family:Arial,sans-serif;font-size:18pt;font-weight:bold;margin:0;}}
  .meta-table{{width:100%;border-collapse:collapse;margin-bottom:15px;font-size:11pt;}}
  .meta-table td{{padding:4px 8px;}}
  .set-badge{{text-align:right;font-weight:bold;font-size:14pt;}}
  .question{{margin-bottom:14px;}}
  .q-num{{font-weight:bold;}}
  .marks{{font-weight:bold;color:#333;float:right;}}
  .options-grid{{display:grid;grid-template-columns:1fr 1fr;gap:4px 32px;padding-left:28px;margin:6px 0 10px;}}
  .opt{{font-size:11pt;}}
  @page{{size:A4;margin:0;}}
  @media print{{body{{margin:0;padding:15mm;max-width:100%;}}}}
</style>
</head>
<body>
<div class="header">
  {logo_block}
  {institute_block}
</div>
<table class="meta-table">
  <tr>
    <td><b>Board:</b> {req.board.upper()}</td>
    <td><b>Class:</b> {req.class_level}</td>
    <td><b>Subject:</b> {req.subject}</td>
    <td class="set-badge"><b>Set:</b> {variant.variant_label}</td>
  </tr>
  <tr>
    <td><b>Exam:</b> {req.exam_title or '–'}</td>
    <td><b>Time:</b> {req.duration_minutes} min</td>
    <td><b>Max Marks:</b> {req.total_marks}</td>
    <td><b>Date:</b> ______________</td>
  </tr>
  <tr>
    <td colspan="2"><b>Student Name:</b> ____________________________</td>
    <td colspan="2"><b>Roll No:</b> ____________</td>
  </tr>
</table>
{qs_html}
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/question-paper", response_model=QuestionPaperResponse)
async def generate_question_paper(
    request: QuestionPaperRequest,
    bg_tasks: BackgroundTasks,
    client: Client = Depends(verify_api_key),
) -> QuestionPaperResponse:
    """
    POST /api/v1/generate/question-paper

    Synchronously generates a curriculum-aligned question paper and returns
    structured JSON.  Credits are checked upfront (15 per variant) and actual
    token usage is billed on completion.
    """
    request_id = str(uuid.uuid4())
    logger.info(
        "POST /api/v1/generate/question-paper client=%s request_id=%s "
        "board=%s class=%d variants=%d",
        client.client_id,
        request_id,
        request.board,
        request.class_level,
        request.num_variants,
    )

    # Step 1: Pre-flight credit check — fast-reject before doing AI work.
    estimated = _PREFLIGHT_CREDITS_PER_VARIANT * request.num_variants
    if not await _credits.check_and_reserve(client.client_id, estimated):
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. At least {estimated} credits required.",
        )

    # Step 2: Translate request → internal config and generate.
    config = _build_paper_config(request)
    try:
        variants, prompt_tokens, completion_tokens = (
            await _paper_service.generate_structured(config)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(
            "QPG generation failed request_id=%s client=%s: %s",
            request_id,
            client.client_id,
            exc,
        )
        raise HTTPException(
            status_code=500, detail=f"Generation failed. Reference: {request_id}"
        )

    # Step 3: Deduct actual token-based credits.
    total_tokens = prompt_tokens + completion_tokens
    credits_consumed = tokens_to_credits(total_tokens) if total_tokens > 0 else estimated
    credits_remaining = await _credits.deduct(
        client_id=client.client_id,
        credits=credits_consumed,
        feature="qpg",
        tokens_input=prompt_tokens,
        tokens_output=completion_tokens,
        request_id=request_id,
    )

    # Step 4: Background audit log.
    bg_tasks.add_task(
        _cosmos.log_query_usage,
        {
            "user_id": client.client_id,
            "request_id": request_id,
            "feature": "qpg",
            "board": request.board,
            "class_level": request.class_level,
            "subject": request.subject,
            "num_variants": request.num_variants,
            "tokens_input": prompt_tokens,
            "tokens_output": completion_tokens,
            "credits_consumed": credits_consumed,
        },
    )

    return QuestionPaperResponse(
        request_id=request_id,
        variants=[
            _flatten_variant(v, request.include_answer_key, request.include_marking_scheme)
            for v in variants
        ],
        tokens_used=total_tokens,
        credits_consumed=credits_consumed,
        credits_remaining=credits_remaining,
    )


@router.post("/question-paper/pdf")
async def generate_question_paper_pdf(
    request: QPGPdfRequest,
    client: Client = Depends(verify_api_key),
) -> HTMLResponse:
    """
    POST /api/v1/generate/question-paper/pdf

    Accepts the structured JSON from /question-paper and returns print-ready
    HTML with embedded KaTeX.  One HTML document is returned per variant;
    if num_variants > 1 the client should call this endpoint once per variant.
    Returns the first variant's HTML when called with the full response body.
    """
    if not request.variants:
        raise HTTPException(status_code=400, detail="variants list is empty.")

    html = _render_html(request, request.variants[0])
    return HTMLResponse(content=html, status_code=200)
