import logging
import asyncio
from typing import Optional, Literal

from openai import AsyncAzureOpenAI
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Token-precise result from any Azure OpenAI non-streaming call."""
    content: str
    model: str
    tokens_input: int    # response.usage.prompt_tokens
    tokens_output: int   # response.usage.completion_tokens
    finish_reason: str


class LlmService:
    """
    Thin, typed wrapper over Azure OpenAI.

    call_nano / call_mini / call_full each map to a specific deployment and
    always return LLMResponse with real token counts from response.usage.
    Use the helper methods (classify_query, translate_to_english,
    extract_text_from_image) for internal pipeline steps.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = AsyncAzureOpenAI(
            azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
            api_key=self.settings.AZURE_OPENAI_KEY,
            api_version="2024-02-01",
        )

    # ── Core call with retry ──────────────────────────────────────────────────

    async def _call(
        self,
        model: str,
        messages: list,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Non-streaming call with exponential backoff. Raises on final failure."""
        last_exc: Exception = RuntimeError("No attempts made")
        for attempt in range(3):
            try:
                resp = await self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return LLMResponse(
                    content=resp.choices[0].message.content or "",
                    model=model,
                    tokens_input=resp.usage.prompt_tokens,
                    tokens_output=resp.usage.completion_tokens,
                    finish_reason=resp.choices[0].finish_reason or "stop",
                )
            except Exception as e:
                last_exc = e
                logger.warning(f"LlmService attempt {attempt + 1} failed for model={model}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        raise last_exc

    # ── Public model methods ──────────────────────────────────────────────────

    async def call_nano(
        self,
        messages: list,
        temperature: float = 0.15,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        """gpt-4.1-nano — cheapest tier, simple factual queries and utilities."""
        return await self._call(
            self.settings.AZURE_OPENAI_NANO_DEPLOYMENT,
            messages,
            temperature,
            max_tokens,
        )

    async def call_mini(
        self,
        messages: list,
        image_base64: Optional[str] = None,
        temperature: float = 0.15,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        """gpt-4.1-mini — medium tier, supports vision for image-based queries."""
        if image_base64:
            last = messages[-1]
            if last["role"] == "user" and isinstance(last.get("content"), str):
                messages = messages[:-1] + [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": last["content"]},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                            },
                        ],
                    }
                ]
        return await self._call(
            self.settings.AZURE_OPENAI_MINI_DEPLOYMENT,
            messages,
            temperature,
            max_tokens,
        )

    async def call_full(
        self,
        messages: list,
        temperature: float = 0.15,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        """gpt-4.1 — complex reasoning, Class 11-12 topics."""
        return await self._call(
            self.settings.AZURE_OPENAI_FULL_DEPLOYMENT,
            messages,
            temperature,
            max_tokens,
        )

    # ── Pipeline helpers ──────────────────────────────────────────────────────

    async def classify_query(self, query: str) -> Literal["simple", "medium", "complex"]:
        """
        Classify query complexity using gpt-4.1-nano (max 50 output tokens).
        Returns lowercase literal; callers needing token counts should use call_nano directly.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "Classify this student query into exactly one category. Reply with ONE WORD only.\n"
                    "SIMPLE: definitions, factual recall, vocabulary, Class 6-10 straightforward.\n"
                    "MEDIUM: concept explanations, comparisons, short derivations, image-based.\n"
                    "COMPLEX: multi-step calculations, proofs, Class 11-12 (calculus, organic chemistry)."
                ),
            },
            {"role": "user", "content": query},
        ]
        try:
            result = await self.call_nano(messages, temperature=0.0, max_tokens=50)
            raw = result.content.strip().upper()
            if "COMPLEX" in raw:
                return "complex"
            if "MEDIUM" in raw:
                return "medium"
            return "simple"
        except Exception as e:
            logger.warning(f"classify_query failed, defaulting to medium: {e}")
            return "medium"

    async def translate_to_english(self, text: str) -> str:
        """Translate input to English using gpt-4.1-nano. Returns translated text only."""
        messages = [
            {
                "role": "system",
                "content": "Translate the text to English. Output the translation ONLY, nothing else.",
            },
            {"role": "user", "content": text},
        ]
        try:
            result = await self.call_nano(messages, temperature=0.0, max_tokens=200)
            return result.content.strip()
        except Exception as e:
            logger.warning(f"translate_to_english failed, returning raw input: {e}")
            return text

    async def extract_text_from_image(self, image_base64: str) -> str:
        """OCR using gpt-4.1-mini vision. Returns extracted text verbatim."""
        messages = [
            {
                "role": "user",
                "content": (
                    "Extract all readable text, formulas, or questions from this image "
                    "exactly as written. Provide no other conversational text."
                ),
            }
        ]
        result = await self.call_mini(messages, image_base64=image_base64, temperature=0.0, max_tokens=1000)
        return result.content

    # ── Context manager ───────────────────────────────────────────────────────

    async def __aenter__(self) -> "LlmService":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._client.close()
