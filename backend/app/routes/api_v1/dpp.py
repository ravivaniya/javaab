"""B2B DPP endpoints: POST /api/v1/generate/dpp[/pdf]."""

from __future__ import annotations

import logging
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.middleware.api_key_auth import verify_api_key
from app.models.client import Client
from app.models.worksheet import WorksheetConfig, WorksheetType
from app.repositories.cosmos_repo import CosmosRepo
from app.services.credit_service import CreditService, tokens_to_credits
from app.services.worksheet_service import WorksheetService

logger = logging.getLogger(__name__)
router = APIRouter()

# Service singletons (lazy-init inside each service)
_cosmos = CosmosRepo()
_credits = CreditService()
_worksheet_service = WorksheetService()

# Credits reserved before generation starts; actual deduction is token-based.
_PREFLIGHT_CREDITS = 12


# ── Request / Response schemas ────────────────────────────────────────────────

class DPPRequest(BaseModel):
    """Request body for POST /api/v1/generate/dpp."""

    board: Literal["cbse", "gseb"]
    class_level: int = Field(..., ge=6, le=12)
    subject: str
    chapter: int = Field(..., ge=1, description="Chapter number (single chapter focus)")
    topic: Optional[str] = Field(None, description="Narrower focus within the chapter")
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    num_questions: int = Field(default=10, ge=5, le=20)
    include_solutions: bool = True
    language: Literal["en", "hi", "gu"] = "en"
    institute_name: Optional[str] = None


class DPPQuestion(BaseModel):
    """A single DPP question in the API response."""

    number: int
    text: str
    difficulty: str
    solution: Optional[str] = None
    answer: Optional[str] = None
    concept_tags: list[str] = []


class DPPResponse(BaseModel):
    """Response from POST /api/v1/generate/dpp."""

    request_id: str
    questions: list[DPPQuestion]
    tokens_used: int
    credits_consumed: int
    credits_remaining: int


class DPPPdfRequest(BaseModel):
    """Request body for POST /api/v1/generate/dpp/pdf."""

    questions: list[DPPQuestion]
    board: str
    class_level: int
    subject: str
    chapter: int
    topic: Optional[str] = None
    institute_name: Optional[str] = None
    include_solutions: bool = True


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_worksheet_config(req: DPPRequest) -> WorksheetConfig:
    """Translate API request into the internal WorksheetConfig shape."""
    return WorksheetConfig(
        board=req.board,
        class_level=req.class_level,
        subject=req.subject,
        topic=req.topic or f"Chapter {req.chapter}",
        chapter=str(req.chapter),
        worksheet_type=WorksheetType.DPP,
        num_questions=req.num_questions,
        difficulty=req.difficulty,
        include_theory_summary=False,
        include_hints=False,
        include_answer_key=req.include_solutions,
        language=req.language,
        institute_name=req.institute_name or "",
    )


def _map_questions(
    items: list[dict],
    include_solutions: bool,
) -> list[DPPQuestion]:
    """Map raw LLM dicts to DPPQuestion response objects."""
    questions: list[DPPQuestion] = []
    for i, item in enumerate(items, 1):
        questions.append(
            DPPQuestion(
                number=i,
                text=item.get("question_text", ""),
                difficulty=item.get("difficulty", "medium"),
                solution=item.get("solution_steps") if include_solutions else None,
                answer=item.get("correct_answer") if include_solutions else None,
                concept_tags=item.get("concept_tags", []),
            )
        )
    return questions


def _render_dpp_html(req: DPPPdfRequest) -> str:
    """Render a print-ready HTML document for the DPP sheet."""
    institute = req.institute_name or "Javaab"
    chapter_label = f"Chapter {req.chapter}"
    topic_label = f" — {req.topic}" if req.topic else ""

    qs_html = ""
    for q in req.questions:
        tags_html = (
            f"<div class='tags'>{' '.join(f'<span>{t}</span>' for t in q.concept_tags)}</div>"
            if q.concept_tags
            else ""
        )
        qs_html += (
            f"<div class='question'>"
            f"<span class='q-num'>{q.number}.</span> "
            f"<span class='q-text'>{q.text}</span> "
            f"<span class='diff diff-{q.difficulty}'>[{q.difficulty}]</span>"
            f"{tags_html}"
            f"<div class='answer-space'></div>"
            f"</div>"
        )

    solutions_html = ""
    if req.include_solutions:
        rows = "".join(
            f"<tr>"
            f"<td>{q.number}</td>"
            f"<td>{q.text[:80]}{'…' if len(q.text) > 80 else ''}</td>"
            f"<td>{q.answer or ''}</td>"
            f"<td><pre>{q.solution or ''}</pre></td>"
            f"</tr>"
            for q in req.questions
        )
        solutions_html = f"""<div class='solutions'>
<h3>Answer Key</h3>
<table>
  <tr><th>#</th><th>Question</th><th>Answer</th><th>Solution</th></tr>
  {rows}
</table>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>DPP — {chapter_label}{topic_label}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body,{{delimiters:[{{left:'\\\\[',right:'\\\\]',display:true}},{{left:'\\\\(',right:'\\\\)',display:false}}]}})"></script>
<style>
  body{{font-family:'Arial',sans-serif;font-size:11pt;line-height:1.6;max-width:210mm;margin:0 auto;padding:15mm;color:#000;}}
  .header{{text-align:center;border-bottom:2px solid #000;padding-bottom:10px;margin-bottom:14px;}}
  .institute{{font-size:16pt;font-weight:bold;margin:0;}}
  .meta{{font-size:10.5pt;color:#333;}}
  .question{{margin-bottom:14px;}}
  .q-num{{font-weight:bold;}}
  .diff{{font-size:9pt;font-weight:bold;float:right;padding:1px 5px;border-radius:3px;}}
  .diff-easy{{background:#D1FAE5;color:#065F46;}}
  .diff-medium{{background:#FEF3C7;color:#92400E;}}
  .diff-hard{{background:#FEE2E2;color:#991B1B;}}
  .tags{{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;}}
  .tags span{{background:#EFF6FF;color:#1D4ED8;font-size:8.5pt;padding:1px 6px;border-radius:10px;}}
  .answer-space{{border-bottom:1px dashed #ccc;margin-top:8px;height:32px;}}
  .solutions{{margin-top:24px;border-top:2px solid #000;padding-top:12px;}}
  table{{width:100%;border-collapse:collapse;font-size:10pt;}}
  td,th{{border:1px solid #ccc;padding:5px 7px;vertical-align:top;}}
  th{{background:#f0f0f0;}}
  pre{{white-space:pre-wrap;margin:0;font-size:9.5pt;}}
  @page{{size:A4;margin:0;}}
  @media print{{body{{margin:0;padding:15mm;max-width:100%;}} .answer-space{{height:40px;}}}}
</style>
</head>
<body>
<div class="header">
  <p class="institute">{institute}</p>
  <div class="meta">{req.subject} | Class {req.class_level} | {req.board.upper()} | {chapter_label}{topic_label}</div>
  <div class="meta">DPP | Questions: {len(req.questions)}</div>
</div>
<p><b>Name:</b> ______________________________ &nbsp;&nbsp; <b>Date:</b> ______________</p>
{qs_html}
{solutions_html}
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/dpp", response_model=DPPResponse)
async def generate_dpp(
    request: DPPRequest,
    bg_tasks: BackgroundTasks,
    client: Client = Depends(verify_api_key),
) -> DPPResponse:
    """
    POST /api/v1/generate/dpp

    Generates a curriculum-aligned Daily Practice Problem (DPP) sheet and
    returns structured JSON.  Credits are checked upfront (12) and actual
    token usage is billed on completion.
    """
    request_id = str(uuid.uuid4())
    logger.info(
        "POST /api/v1/generate/dpp client=%s request_id=%s "
        "board=%s class=%d chapter=%d n=%d",
        client.client_id,
        request_id,
        request.board,
        request.class_level,
        request.chapter,
        request.num_questions,
    )

    # Step 1: Pre-flight credit check — fast-reject before any AI work.
    if not await _credits.check_and_reserve(client.client_id, _PREFLIGHT_CREDITS):
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. At least {_PREFLIGHT_CREDITS} credits required.",
        )

    # Step 2: Build WorksheetConfig and generate.
    config = _build_worksheet_config(request)
    try:
        items, prompt_tokens, completion_tokens = (
            await _worksheet_service.generate_dpp_structured(config)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(
            "DPP generation failed request_id=%s client=%s: %s",
            request_id,
            client.client_id,
            exc,
        )
        raise HTTPException(
            status_code=500, detail=f"Generation failed. Reference: {request_id}"
        )

    # Step 3: Deduct actual token-based credits.
    total_tokens = prompt_tokens + completion_tokens
    credits_consumed = tokens_to_credits(total_tokens) if total_tokens > 0 else _PREFLIGHT_CREDITS
    credits_remaining = await _credits.deduct(
        client_id=client.client_id,
        credits=credits_consumed,
        feature="dpp",
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
            "feature": "dpp",
            "board": request.board,
            "class_level": request.class_level,
            "subject": request.subject,
            "chapter": request.chapter,
            "num_questions": request.num_questions,
            "tokens_input": prompt_tokens,
            "tokens_output": completion_tokens,
            "credits_consumed": credits_consumed,
        },
    )

    return DPPResponse(
        request_id=request_id,
        questions=_map_questions(items, request.include_solutions),
        tokens_used=total_tokens,
        credits_consumed=credits_consumed,
        credits_remaining=credits_remaining,
    )


@router.post("/dpp/pdf")
async def generate_dpp_pdf(
    request: DPPPdfRequest,
    client: Client = Depends(verify_api_key),
) -> HTMLResponse:
    """
    POST /api/v1/generate/dpp/pdf

    Accepts the structured JSON from /dpp and returns a print-ready HTML
    document with embedded KaTeX for math rendering.  Clients can open this
    directly in a browser or pass it to a headless-Chrome PDF service.
    """
    if not request.questions:
        raise HTTPException(status_code=400, detail="questions list is empty.")

    html = _render_dpp_html(request)
    return HTMLResponse(content=html, status_code=200)
