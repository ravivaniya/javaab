from __future__ import annotations

import json
import logging
import os
import random
import re
import time
import uuid
from typing import Any

from openai import AsyncAzureOpenAI

from app.config import get_settings
from app.models.paper import (
    GeneratedQuestion,
    GeneratedPaper,
    PaperConfig,
    PaperVariant,
    QuestionType,
    SectionConfig,
)
from app.repositories.cosmos_repo import CosmosRepo

logger = logging.getLogger(__name__)

_VARIANT_LABELS = ["A", "B", "C"]

_TYPE_LABELS: dict[str, str] = {
    "mcq": "MCQ",
    "short": "Short Answer",
    "long": "Long Answer",
    "very_long": "Very Long Answer",
    "fill_blank": "Fill in the Blanks",
    "true_false": "True / False",
    "assertion_reason": "Assertion-Reason",
}

# Question types that need the full model (complex reasoning, extended writing)
_HEAVY_TYPES = {QuestionType.LONG, QuestionType.VERY_LONG, QuestionType.ASSERTION_REASON}
# Question types that work well with the nano model (factual, structured)
_LIGHT_TYPES = {QuestionType.MCQ, QuestionType.FILL_BLANK, QuestionType.TRUE_FALSE}


class PaperService:
    def __init__(self) -> None:
        settings = get_settings()
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_KEY", ""),
            api_version="2024-02-01",
        )
        self.settings = settings
        self.cosmos_repo = CosmosRepo()

    def _pick_model(self, section: SectionConfig, config: PaperConfig) -> str:
        """Return the cheapest model capable of generating this section well."""
        if section.question_type in _HEAVY_TYPES or config.difficulty_mix.hard > 40:
            return self.settings.AZURE_OPENAI_FULL_DEPLOYMENT
        if section.question_type in _LIGHT_TYPES and config.difficulty_mix.hard <= 20:
            return self.settings.AZURE_OPENAI_NANO_DEPLOYMENT
        return self.settings.AZURE_OPENAI_MINI_DEPLOYMENT

    async def generate_structured(
        self, config: PaperConfig
    ) -> tuple[list[PaperVariant], int, int]:
        """
        Generate question paper variants and return structured data.

        Unlike generate_paper this is synchronous (not a background task), does
        not touch Cosmos, and raises on failure so callers can return HTTP errors.

        Returns:
            (variants, total_prompt_tokens, total_completion_tokens)
        """
        total_prompt_tokens = 0
        total_completion_tokens = 0

        base_sections: dict[str, list[GeneratedQuestion]] = {}
        for section in config.sections:
            questions, pt, ct, _ = await self._generate_section_questions(section, config)
            if not questions:
                raise ValueError(
                    f"Failed to generate questions for section '{section.section_label}' "
                    f"(type={section.question_type.value}). Check chapters list."
                )
            base_sections[section.section_label] = questions
            total_prompt_tokens += pt
            total_completion_tokens += ct

        variants: list[PaperVariant] = []
        for i in range(config.num_variants):
            label = _VARIANT_LABELS[i]
            sections_questions: dict[str, list[GeneratedQuestion]] = {}
            for section_label, questions in base_sections.items():
                shuffled = list(questions)
                if i > 0:
                    random.shuffle(shuffled)
                sections_questions[section_label] = shuffled
            variants.append(PaperVariant(
                variant_label=f"Set {label}",
                sections=sections_questions,
            ))

        return variants, total_prompt_tokens, total_completion_tokens

    async def generate_paper(
        self, config: PaperConfig, teacher_id: str, paper_id: str
    ) -> None:
        """Background task — generates questions once, shuffles order per variant."""
        start_time = time.monotonic()
        total_prompt_tokens = 0
        total_completion_tokens = 0
        models_used: set[str] = set()

        try:
            # Generate base questions once (one API call per section)
            base_sections: dict[str, list[GeneratedQuestion]] = {}
            for section in config.sections:
                questions, pt, ct, model = await self._generate_section_questions(
                    section, config
                )
                base_sections[section.section_label] = questions
                total_prompt_tokens += pt
                total_completion_tokens += ct
                models_used.add(model)

            # Build each variant by shuffling question order within each section
            variants: list[PaperVariant] = []
            for i in range(config.num_variants):
                label = _VARIANT_LABELS[i]
                sections_questions: dict[str, list[GeneratedQuestion]] = {}
                for section_label, questions in base_sections.items():
                    shuffled = list(questions)
                    if i > 0:
                        random.shuffle(shuffled)
                    sections_questions[section_label] = shuffled

                variant = PaperVariant(
                    variant_label=f"Set {label}",
                    sections=sections_questions,
                )
                variant.paper_html = self._render_paper_html(variant, config)
                variant.answer_key_html = self._render_answer_key_html(variant, config)
                variant.marking_scheme_html = self._render_marking_scheme_html(
                    variant, config
                )
                variants.append(variant)

            elapsed = round(time.monotonic() - start_time, 1)
            generation_stats = {
                "time_seconds": elapsed,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "models_used": sorted(models_used),
            }

            variants_data = [v.model_dump(mode="json") for v in variants]
            await self.cosmos_repo.update_paper_status(
                paper_id,
                teacher_id,
                "ready",
                variants=variants_data,
                generation_stats=generation_stats,
            )
        except Exception as e:
            logger.error(f"Paper generation failed for {paper_id}: {e}")
            await self.cosmos_repo.update_paper_status(paper_id, teacher_id, "failed")

    async def _generate_section_questions(
        self,
        section: SectionConfig,
        config: PaperConfig,
    ) -> tuple[list[GeneratedQuestion], int, int, str]:
        """Call the appropriate model for this section. Returns (questions, prompt_tokens, completion_tokens, model_name)."""
        model = self._pick_model(section, config)
        system_prompt = self._build_system_prompt(config)
        user_prompt = self._build_user_prompt(section, config)

        for attempt in range(2):
            try:
                response = await self.openai_client.chat.completions.create(
                    model=model,
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
                questions = []
                for item in items:
                    q = GeneratedQuestion(
                        question_text=item.get("question_text", ""),
                        question_type=section.question_type,
                        marks=item.get("marks", section.marks_per_question),
                        difficulty=item.get("difficulty", "medium"),
                        chapter=item.get("chapter", config.chapters[0] if config.chapters else ""),
                        topic=item.get("topic", ""),
                        options=item.get("options", []),
                        correct_answer=item.get("correct_answer", ""),
                        marking_scheme=item.get("marking_scheme", ""),
                        bloom_level=item.get("bloom_level", "Understand"),
                    )
                    questions.append(q)
                pt = response.usage.prompt_tokens if response.usage else 0
                ct = response.usage.completion_tokens if response.usage else 0
                if questions:
                    return questions, pt, ct, model
            except Exception as e:
                if attempt == 1:
                    logger.error(f"Section generation failed after 2 attempts: {e}")
                    return [], 0, 0, model
                logger.warning(f"Generation attempt {attempt + 1} failed, retrying: {e}")
        return [], 0, 0, model

    def _build_system_prompt(self, config: PaperConfig) -> str:
        dm = config.difficulty_mix
        chapters_str = ", ".join(config.chapters)
        lang_note = {
            "gu": "Write in Gujarati script. Technical terms appear in English with Gujarati in brackets on first use.",
            "hi": "Write in Devanagari script. Technical terms appear in English with Hindi in brackets on first use.",
            "en": "Write in English.",
        }.get(config.language, "Write in English.")
        return f"""You are an expert question paper setter for Indian {config.board} board, Class {config.class_level}, Subject: {config.subject}. You follow the NCERT/GSEB syllabus exactly.
Your questions must:
- Be from these chapters/topics: {chapters_str}
- Match the board's official question format and terminology
- Use LaTeX for ALL mathematical expressions: inline \\( \\) and block \\[ \\]
- Be grammatically precise and unambiguous
- Match the difficulty distribution: Easy {dm.easy}%, Medium {dm.medium}%, Hard {dm.hard}%
- Follow Bloom's Taxonomy levels naturally across the paper
- For CBSE Class 10-12: follow the latest CBSE question paper blueprint strictly
- For GSEB: follow Gujarat Board paper pattern strictly
- MCQ options must have exactly one unambiguously correct answer
- All numerical answers must be verifiable

{lang_note}

Return ONLY valid JSON — no preamble, no markdown fences. The JSON must have a "questions" key with an array."""

    def _build_user_prompt(
        self, section: SectionConfig, config: PaperConfig
    ) -> str:
        chapters_str = ", ".join(config.chapters)
        dm = config.difficulty_mix
        type_instructions = {
            QuestionType.MCQ: "Each MCQ must have exactly 4 options labeled A), B), C), D). Only one option is correct.",
            QuestionType.SHORT: "Short answer questions requiring 2–3 sentences or brief working.",
            QuestionType.LONG: "Long answer questions requiring detailed explanation (5 marks each).",
            QuestionType.VERY_LONG: "Very long / extended response questions (8–10 marks each) with step-wise marking.",
            QuestionType.FILL_BLANK: "Fill-in-the-blank statements. The blank is shown as ________.",
            QuestionType.TRUE_FALSE: "True/False statements. State whether the assertion is True or False and give brief reason.",
            QuestionType.ASSERTION_REASON: (
                "Assertion-Reason format (CBSE standard). "
                "question_text must contain both 'Assertion (A): ...' and 'Reason (R): ...' statements. "
                "options must be exactly these 4 strings in this order: "
                "['A) Both A and R are true, and R is the correct explanation of A.', "
                "'B) Both A and R are true, but R is not the correct explanation of A.', "
                "'C) A is true, but R is false.', "
                "'D) A is false, but R is true.'] "
                "correct_answer must be one of: A, B, C, or D."
            ),
        }.get(section.question_type, "")

        return f"""Generate exactly {section.num_questions} questions of type "{section.question_type.value}" worth {section.marks_per_question} marks each for {config.subject}, Class {config.class_level}, {config.board}.
Chapters: {chapters_str}
{type_instructions}

Return ONLY valid JSON with this structure:
{{
  "questions": [
    {{
      "question_text": "...",
      "marks": {section.marks_per_question},
      "difficulty": "easy|medium|hard",
      "chapter": "exact chapter name from the list",
      "topic": "specific topic within chapter",
      "options": [],
      "correct_answer": "...",
      "marking_scheme": "Step 1 (1 mark): ...\\nStep 2...",
      "bloom_level": "Remember|Understand|Apply|Analyze|Evaluate|Create"
    }}
  ]
}}

Generate exactly {section.num_questions} questions. Vary topics across the listed chapters. Ensure difficulty matches {dm.easy}% easy / {dm.medium}% medium / {dm.hard}% hard."""

    # ── HTML rendering ─────────────────────────────────────────────────────────

    def _render_paper_html(self, variant: PaperVariant, config: PaperConfig) -> str:
        institute_block = (
            f"<h2 class='institute-name'>{config.institute_name}</h2>"
            if config.institute_name
            else "<h2 class='institute-name'>Javaab</h2>"
        )
        logo_block = (
            f"<img src='{config.institute_logo_url}' class='logo' alt='Logo'>"
            if config.institute_logo_url
            else ""
        )
        instructions = config.paper_instructions or (
            "1. All questions are compulsory unless stated otherwise.\n"
            "2. Write your name and roll number clearly.\n"
            "3. Marks are indicated against each question.\n"
            "4. Draw neat, labelled diagrams wherever necessary."
        )
        instructions_html = "".join(
            # Strip any leading "N." or "N)" so the <ol> numbering isn't duplicated
            f"<li>{re.sub(r'^\\d+[.)]\\s*', '', line.strip())}</li>"
            for line in instructions.split("\n")
            if line.strip()
        )

        sections_html = ""
        for section_label, questions in variant.sections.items():
            section_cfg = next(
                (s for s in config.sections if s.section_label == section_label), None
            )
            q_type_display = (
                _TYPE_LABELS.get(section_cfg.question_type.value, section_cfg.question_type.value.replace("_", " ").title())
                if section_cfg
                else ""
            )
            mpp = section_cfg.marks_per_question if section_cfg else 0
            instr = (
                f"<p class='section-instructions'>{section_cfg.instructions}</p>"
                if section_cfg and section_cfg.instructions
                else ""
            )
            qs_html = ""
            for idx, q in enumerate(questions, start=1):
                opts_html = ""
                if q.options:
                    if q.question_type == QuestionType.MCQ:
                        # 2×2 grid — AI already includes "A) …" labels in option text
                        opts_html = "<div class='options-grid'>" + "".join(
                            f"<span class='opt'>{opt}</span>" for opt in q.options
                        ) + "</div>"
                    elif q.question_type == QuestionType.ASSERTION_REASON:
                        # Vertical labeled list — options already include "A) …" labels
                        opts_html = "<ul class='options-ar'>" + "".join(
                            f"<li>{opt}</li>" for opt in q.options
                        ) + "</ul>"
                    else:
                        opts_html = "<ol class='options'>" + "".join(
                            f"<li>{opt}</li>" for opt in q.options
                        ) + "</ol>"
                qs_html += (
                    f"<div class='question'>"
                    f"<span class='q-num'>{idx}.</span> "
                    f"<span class='q-text'>{q.question_text}</span> "
                    f"<span class='marks'>[{q.marks}]</span>"
                    f"{opts_html}"
                    f"</div>"
                )
            sections_html += (
                f"<div class='section'>"
                f"<h3 class='section-title'>{section_label} — {q_type_display} Questions "
                f"({mpp} mark{'s' if mpp != 1 else ''} each)</h3>"
                f"{instr}{qs_html}</div>"
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{config.exam_title or 'Question Paper'}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body, {{delimiters:[{{left:'\\\\[',right:'\\\\]',display:true}},{{left:'\\\\(',right:'\\\\)',display:false}}]}})"></script>
<style>
  body {{ font-family: 'Times New Roman', Times, serif; font-size: 12pt; line-height: 1.6; max-width: 210mm; margin: 0 auto; padding: 20mm; color: #000; }}
  .header {{ text-align: center; border-bottom: 2px solid #000; padding-bottom: 10px; margin-bottom: 15px; }}
  .logo {{ max-height: 64px; margin-bottom: 8px; display: block; margin-left: auto; margin-right: auto; }}
  .institute-name {{ font-family: Arial, sans-serif; font-size: 18pt; font-weight: bold; margin: 0; }}
  .meta-table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 11pt; }}
  .meta-table td {{ padding: 4px 8px; }}
  .instructions {{ background: #f9f9f9; border: 1px solid #ccc; padding: 10px; margin-bottom: 20px; font-size: 10.5pt; }}
  .instructions ol {{ margin: 5px 0; padding-left: 20px; }}
  .section {{ margin-bottom: 25px; page-break-inside: avoid; }}
  .section-title {{ font-size: 12pt; font-weight: bold; text-decoration: underline; margin-bottom: 10px; }}
  .section-instructions {{ font-style: italic; color: #333; margin-bottom: 8px; }}
  .question {{ margin-bottom: 14px; }}
  .q-num {{ font-weight: bold; }}
  .marks {{ font-weight: bold; color: #333; float: right; }}
  /* MCQ 2×2 grid */
  .options-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px 32px; padding-left: 28px; margin: 6px 0 10px; }}
  .opt {{ font-size: 11pt; }}
  /* Assertion-Reason vertical labeled list */
  .options-ar {{ list-style: none; padding-left: 28px; margin: 8px 0 10px; }}
  .options-ar li {{ margin: 5px 0; font-size: 11pt; }}
  /* Fallback ordered list for other types */
  .options {{ list-style: none; padding-left: 28px; margin: 6px 0; }}
  .options li {{ margin: 3px 0; }}
  .set-badge {{ text-align: right; font-weight: bold; font-size: 14pt; }}
  /* @page margin:0 removes the browser's default header/footer strip (date, URL, file path).
     Body padding restores the white space around content. */
  @page {{ size: A4; margin: 0; }}
  @media print {{
    body {{ margin: 0; padding: 15mm; max-width: 100%; }}
    .section {{ page-break-inside: avoid; }}
    .header {{ page-break-after: avoid; }}
  }}
</style>
</head>
<body>
<div class="header">
  {logo_block}
  {institute_block}
</div>
<table class="meta-table">
  <tr>
    <td><b>Board:</b> {config.board}</td>
    <td><b>Class:</b> {config.class_level}</td>
    <td><b>Subject:</b> {config.subject}</td>
    <td class="set-badge"><b>Set:</b> {variant.variant_label}</td>
  </tr>
  <tr>
    <td><b>Exam:</b> {config.exam_title or '–'}</td>
    <td><b>Time:</b> {config.duration_minutes} min</td>
    <td><b>Max Marks:</b> {config.total_marks}</td>
    <td><b>Date:</b> ______________</td>
  </tr>
  <tr>
    <td colspan="2"><b>Student Name:</b> ____________________________</td>
    <td colspan="2"><b>Roll No:</b> ____________</td>
  </tr>
</table>
<div class="instructions">
  <b>General Instructions:</b>
  <ol>{instructions_html}</ol>
</div>
{sections_html}
</body>
</html>"""

    def _render_answer_key_html(self, variant: PaperVariant, config: PaperConfig) -> str:
        sections_html = ""
        for section_label, questions in variant.sections.items():
            rows = "".join(
                f"<tr><td>{i}</td><td>{q.question_text[:80]}…</td><td>{q.correct_answer}</td></tr>"
                for i, q in enumerate(questions, 1)
            )
            sections_html += (
                f"<h3>{section_label}</h3>"
                f"<table class='ak-table'><tr><th>#</th><th>Question</th><th>Answer</th></tr>{rows}</table>"
            )

        return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'>
<title>Answer Key — {config.exam_title} {variant.variant_label}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body)"></script>
<style>body{{font-family:Arial,sans-serif;padding:20mm;}} .ak-table{{width:100%;border-collapse:collapse;margin-bottom:20px;}} .ak-table td,.ak-table th{{border:1px solid #ccc;padding:6px 10px;font-size:10pt;}} .ak-table th{{background:#f0f0f0;}}</style>
</head><body>
<h1>Answer Key — {config.exam_title or 'Exam'} ({variant.variant_label})</h1>
<p>Board: {config.board} | Class: {config.class_level} | Subject: {config.subject}</p>
{sections_html}
</body></html>"""

    def _render_marking_scheme_html(self, variant: PaperVariant, config: PaperConfig) -> str:
        sections_html = ""
        for section_label, questions in variant.sections.items():
            qs_html = "".join(
                f"<div class='ms-item'><b>Q{i}.</b> {q.question_text[:100]}…"
                f"<br><em>Marks: {q.marks}</em><br><pre>{q.marking_scheme}</pre></div>"
                for i, q in enumerate(questions, 1)
            )
            sections_html += f"<h3>{section_label}</h3>{qs_html}"

        return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'>
<title>Marking Scheme — {config.exam_title} {variant.variant_label}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body)"></script>
<style>body{{font-family:Arial,sans-serif;padding:20mm;}} .ms-item{{border:1px solid #ddd;padding:10px;margin-bottom:12px;border-radius:6px;}} pre{{background:#f9f9f9;padding:8px;font-size:10pt;white-space:pre-wrap;}}</style>
</head><body>
<h1>Marking Scheme — {config.exam_title or 'Exam'} ({variant.variant_label})</h1>
<p>Board: {config.board} | Class: {config.class_level} | Subject: {config.subject}</p>
{sections_html}
</body></html>"""
