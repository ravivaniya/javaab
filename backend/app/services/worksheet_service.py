from __future__ import annotations

import json
import logging
import os
import uuid

from openai import AsyncAzureOpenAI

from app.config import get_settings
from app.models.worksheet import GeneratedWorksheet, WorksheetConfig, WorksheetQuestion, WorksheetType
from app.repositories.cosmos_repo import CosmosRepo

logger = logging.getLogger(__name__)

_TYPE_MIX: dict[WorksheetType, str] = {
    WorksheetType.DPP: "40% MCQ, 30% short answer, 20% fill in the blank, 10% assertion/reason",
    WorksheetType.WORKSHEET: "30% MCQ, 40% short answer, 30% long/numerical",
    WorksheetType.MCQ_DRILL: "100% MCQ",
    WorksheetType.REVISION: "50% MCQ, 30% fill in the blank, 20% true/false",
    WorksheetType.HOMEWORK: "30% MCQ, 40% short answer, 30% long/numerical",
}


class WorksheetService:
    def __init__(self) -> None:
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_KEY", ""),
            api_version="2024-02-01",
        )
        self.settings = get_settings()
        self.cosmos_repo = CosmosRepo()

    async def generate_worksheet(
        self, config: WorksheetConfig, teacher_id: str, ws_id: str
    ) -> None:
        """Background task entry point — generates worksheet and updates Cosmos."""
        try:
            theory_summary = ""
            if config.include_theory_summary:
                theory_summary = await self._generate_theory_summary(config)

            questions = await self._generate_questions(config)

            ws_html = self._render_worksheet_html(config, theory_summary, questions)
            answer_key_html = self._render_answer_key_html(config, questions) if config.include_answer_key else ""

            await self.cosmos_repo.update_worksheet_status(
                ws_id,
                teacher_id,
                "ready",
                data={
                    "theory_summary": theory_summary,
                    "questions": [q.model_dump(mode="json") for q in questions],
                    "worksheet_html": ws_html,
                    "answer_key_html": answer_key_html,
                },
            )
        except Exception as e:
            logger.error(f"Worksheet generation failed for {ws_id}: {e}")
            await self.cosmos_repo.update_worksheet_status(ws_id, teacher_id, "failed")

    async def _generate_theory_summary(self, config: WorksheetConfig) -> str:
        prompt = (
            f"Provide a 5-line concept summary for '{config.topic}' from {config.subject} "
            f"Class {config.class_level} {config.board}. Format as bullet points. "
            "Use LaTeX for formulas (inline \\( \\)). Keep it concise — "
            "this goes at the top of a student worksheet as a quick reference."
        )
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.settings.AZURE_OPENAI_MINI_DEPLOYMENT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Theory summary generation failed: {e}")
            return ""

    async def _generate_questions(self, config: WorksheetConfig) -> list[WorksheetQuestion]:
        mix_desc = _TYPE_MIX.get(config.worksheet_type, "mixed question types")
        hint_note = "Include a brief hint for each question in the 'hint' field." if config.include_hints else "Leave the 'hint' field empty."
        lang_note = {
            "gu": "Write in Gujarati script.",
            "hi": "Write in Devanagari script.",
            "en": "Write in English.",
        }.get(config.language, "Write in English.")

        system_prompt = (
            f"You are an expert question setter for Indian {config.board} board, "
            f"Class {config.class_level}, Subject: {config.subject}. "
            "You follow the NCERT/GSEB syllabus exactly. "
            "Use LaTeX for all mathematical expressions: inline \\( \\) and block \\[ \\]. "
            f"{lang_note}"
        )
        user_prompt = f"""Generate {config.num_questions} practice questions on the topic: "{config.topic}"
(from {config.chapter}, {config.subject}, Class {config.class_level}, {config.board}).
Worksheet type: {config.worksheet_type.value}.
Difficulty: {config.difficulty}.

Mix question types for this worksheet type: {mix_desc}
{hint_note}

Return ONLY valid JSON:
{{
  "questions": [
    {{
      "question_text": "...",
      "question_type": "mcq|short|fill_blank|true_false|long",
      "marks": 1,
      "hint": "",
      "correct_answer": "...",
      "solution_steps": "Step 1: ...\\nStep 2: ..."
    }}
  ]
}}"""

        for attempt in range(2):
            try:
                response = await self.openai_client.chat.completions.create(
                    model=self.settings.AZURE_OPENAI_FULL_DEPLOYMENT,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7,
                )
                raw = response.choices[0].message.content or "{}"
                data = json.loads(raw)
                items = data if isinstance(data, list) else data.get("questions", [])
                return [
                    WorksheetQuestion(
                        question_text=item.get("question_text", ""),
                        question_type=item.get("question_type", "short"),
                        marks=item.get("marks", 1),
                        hint=item.get("hint", "") if config.include_hints else "",
                        correct_answer=item.get("correct_answer", ""),
                        solution_steps=item.get("solution_steps", ""),
                    )
                    for item in items
                ]
            except Exception as e:
                if attempt == 1:
                    logger.error(f"Worksheet question generation failed: {e}")
                    return []
                logger.warning(f"Attempt {attempt + 1} failed, retrying: {e}")
        return []

    def _render_worksheet_html(
        self,
        config: WorksheetConfig,
        theory_summary: str,
        questions: list[WorksheetQuestion],
    ) -> str:
        theory_html = ""
        if theory_summary:
            lines = theory_summary.strip().split("\n")
            items = "".join(f"<li>{line.lstrip('•- ').strip()}</li>" for line in lines if line.strip())
            theory_html = f"""<div class='theory-box'>
<b>📖 Key Concepts: {config.topic}</b>
<ul>{items}</ul>
</div>"""

        name_field = "<p><b>Name:</b> ______________________________ <b>Date:</b> ______________</p>" if config.student_name_field or config.date_field else ""
        institute = f"<p class='institute'>{config.institute_name}</p>" if config.institute_name else "<p class='institute'>Javaab</p>"

        qs_html = ""
        for i, q in enumerate(questions, 1):
            hint_html = f"<div class='hint'>💡 Hint: {q.hint}</div>" if q.hint else ""
            answer_space = "<div class='answer-space'></div>"
            qs_html += f"<div class='question'><span class='q-num'>{i}.</span> <span class='q-text'>{q.question_text}</span> <span class='marks'>[{q.marks}]</span>{hint_html}{answer_space}</div>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{config.worksheet_type.value.upper()} — {config.topic}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body, {{delimiters:[{{left:'\\\\[',right:'\\\\]',display:true}},{{left:'\\\\(',right:'\\\\)',display:false}}]}})"></script>
<style>
  body {{ font-family: 'Arial', sans-serif; font-size: 11pt; line-height: 1.6; max-width: 210mm; margin: 0 auto; padding: 15mm; color: #000; }}
  .header {{ text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 12px; }}
  .institute {{ font-size: 16pt; font-weight: bold; margin: 0; }}
  .ws-meta {{ font-size: 10.5pt; color: #333; }}
  .theory-box {{ background: #FFF9E6; border-left: 4px solid #FFD700; border-radius: 6px; padding: 10px 14px; margin-bottom: 18px; font-size: 10.5pt; }}
  .theory-box ul {{ margin: 6px 0; padding-left: 18px; }}
  .question {{ margin-bottom: 14px; }}
  .q-num {{ font-weight: bold; }}
  .marks {{ float: right; font-weight: bold; color: #555; }}
  .hint {{ background: #EFF6FF; border-radius: 4px; padding: 4px 8px; font-size: 9.5pt; margin-top: 4px; color: #1D4ED8; }}
  .answer-space {{ border-bottom: 1px dashed #ccc; margin-top: 8px; height: 32px; }}
  @media print {{ body {{ margin: 0; }} .answer-space {{ height: 40px; }} }}
</style>
</head>
<body>
<div class="header">
  {institute}
  <div class="ws-meta">{config.subject} | Class {config.class_level} | {config.board} | Topic: {config.topic}</div>
  <div class="ws-meta">Type: {config.worksheet_type.value.upper()} | Questions: {len(questions)} | Difficulty: {config.difficulty.title()}</div>
</div>
{name_field}
{theory_html}
{qs_html}
</body>
</html>"""

    async def generate_dpp_structured(
        self, config: WorksheetConfig
    ) -> tuple[list[dict], int, int]:
        """
        Synchronous DPP generation (not a background task).

        Returns (question_dicts, prompt_tokens, completion_tokens).
        Each dict contains: question_text, difficulty, solution_steps,
        correct_answer, concept_tags.
        Raises on failure so the caller can return an HTTP error.
        """
        lang_note = {
            "gu": "Write in Gujarati script.",
            "hi": "Write in Devanagari script.",
            "en": "Write in English.",
        }.get(config.language, "Write in English.")

        system_prompt = (
            f"You are an expert question setter for Indian {config.board} board, "
            f"Class {config.class_level}, Subject: {config.subject}. "
            "You follow the NCERT/GSEB syllabus exactly. "
            "Use LaTeX for all mathematical expressions: inline \\( \\) and block \\[ \\]. "
            f"{lang_note}"
        )

        topic_hint = (
            f"\nNarrow focus within chapter: \"{config.topic}\"."
            if config.topic
            else ""
        )
        difficulty_note = (
            "Generate a mix of easy, medium, and hard questions."
            if config.difficulty == "mixed"
            else f"All questions should be {config.difficulty} difficulty."
        )
        user_prompt = f"""Generate {config.num_questions} DPP (Daily Practice Problem) questions.
Chapter: {config.chapter}, {config.subject}, Class {config.class_level}, {config.board.upper()}.{topic_hint}
{difficulty_note}
Type mix: 40% MCQ, 30% short answer, 20% fill in the blank, 10% assertion/reason.

Return ONLY valid JSON:
{{
  "questions": [
    {{
      "question_text": "...",
      "difficulty": "easy|medium|hard",
      "solution_steps": "Step 1: ...\\nStep 2: ...",
      "correct_answer": "...",
      "concept_tags": ["tag1", "tag2"]
    }}
  ]
}}"""

        for attempt in range(2):
            try:
                response = await self.openai_client.chat.completions.create(
                    model=self.settings.AZURE_OPENAI_FULL_DEPLOYMENT,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7,
                )
                usage = response.usage
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0
                raw = response.choices[0].message.content or "{}"
                data = json.loads(raw)
                items: list[dict] = data if isinstance(data, list) else data.get("questions", [])
                if not items:
                    raise ValueError("LLM returned zero questions.")
                return items, prompt_tokens, completion_tokens
            except Exception as e:
                if attempt == 1:
                    logger.error(f"generate_dpp_structured failed: {e}")
                    raise
                logger.warning(f"generate_dpp_structured attempt {attempt + 1} failed, retrying: {e}")

        return [], 0, 0  # unreachable; satisfies type checker

    def _render_answer_key_html(
        self, config: WorksheetConfig, questions: list[WorksheetQuestion]
    ) -> str:
        rows = "".join(
            f"<tr><td>{i}</td><td>{q.question_text[:80]}…</td><td>{q.correct_answer}</td><td><pre>{q.solution_steps}</pre></td></tr>"
            for i, q in enumerate(questions, 1)
        )
        return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'>
<title>Answer Key — {config.topic}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body)"></script>
<style>body{{font-family:Arial,sans-serif;padding:15mm;}} table{{width:100%;border-collapse:collapse;}} td,th{{border:1px solid #ccc;padding:6px 8px;font-size:10pt;vertical-align:top;}} th{{background:#f0f0f0;}} pre{{white-space:pre-wrap;margin:0;font-size:9.5pt;}}</style>
</head><body>
<h2>Answer Key — {config.topic}</h2>
<p>{config.subject} | Class {config.class_level} | {config.board}</p>
<table><tr><th>#</th><th>Question</th><th>Answer</th><th>Solution</th></tr>{rows}</table>
</body></html>"""
