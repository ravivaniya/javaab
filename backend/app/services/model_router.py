import os
import time
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional

from openai import AsyncAzureOpenAI
from app.config import get_settings
from app.services.cache_service import CacheService
from app.repositories.cosmos_repo import CosmosRepo
from app.models.schemas import ModelRouterResponse

logger = logging.getLogger(__name__)

# ── Model deployment names ────────────────────────────────────────────────────
# Read via Settings so AliasChoices resolves both old dotted Key Vault names
# and new clean names automatically — no Key Vault changes needed.
_settings = get_settings()
TIER_1_MODEL = _settings.AZURE_OPENAI_NANO_DEPLOYMENT
TIER_2_MODEL = _settings.AZURE_OPENAI_MINI_DEPLOYMENT
TIER_3_MODEL = _settings.AZURE_OPENAI_FULL_DEPLOYMENT

# ── Cost per 1M tokens (input, output) in USD ────────────────────────────────
COSTS = {
    TIER_1_MODEL: (0.075, 0.30),
    TIER_2_MODEL: (0.15, 0.60),
    TIER_3_MODEL: (2.50, 10.00),
}

# ── Classifier prompt ─────────────────────────────────────────────────────────
CLASSIFIER_PROMPT = """Classify this student query into exactly one category. Reply with ONE WORD only.

SIMPLE: definitions, "what is", "who invented", direct factual questions, \
vocabulary, dates, naming, listing (Class 6-10 level straightforward)
MEDIUM: concept explanations, comparisons, "why/how", short derivations, \
image-based questions
COMPLEX: multi-step calculations, proofs, numericals with multiple unknowns, \
Class 11-12 topics (calculus, organic chemistry, electromagnetism), \
questions with 3+ steps

Query: {query}

Reply with exactly: SIMPLE, MEDIUM, or COMPLEX"""

# ── Force-complex topic keywords (bypass classifier) ─────────────────────────
FORCE_COMPLEX_TOPICS: Dict[str, List[str]] = {
    "mathematics": [
        "integration", "differentiation", "matrices", "determinants",
        "probability", "trigonometry class 11", "vectors", "3d geometry",
    ],
    "physics": [
        "electrostatics", "current electricity", "magnetism", "optics",
        "dual nature", "atoms", "nuclei", "semiconductor",
    ],
    "chemistry": [
        "equilibrium", "electrochemistry", "chemical kinetics",
        "coordination", "organic reactions", "p-block", "d-block",
    ],
}


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, window_sec: int = 60):
        self.failure_threshold = failure_threshold
        self.window_sec = window_sec
        self.failures: Dict[str, List[float]] = {}

    def log_failure(self, model_name: str):
        now = time.time()
        if model_name not in self.failures:
            self.failures[model_name] = []
        self.failures[model_name].append(now)
        self.failures[model_name] = [
            t for t in self.failures[model_name] if now - t <= self.window_sec
        ]

    def is_tripped(self, model_name: str) -> bool:
        now = time.time()
        if model_name not in self.failures:
            return False
        recent = [t for t in self.failures[model_name] if now - t <= self.window_sec]
        return len(recent) >= self.failure_threshold


class ModelRouter:
    """
    Routes queries to the appropriate LLM tier based on complexity.
    Tier 0: verified cache | Tier 1: SIMPLE | Tier 2: MEDIUM | Tier 3: COMPLEX
    """

    def __init__(self):
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_KEY", "")

        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version="2024-02-01",
        )
        self.cache_service = CacheService()
        self.cosmos_repo = CosmosRepo()
        self.breaker = CircuitBreaker()

    def _calculate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        rate_in, rate_out = COSTS.get(model, (0.0, 0.0))
        return (tokens_in / 1_000_000 * rate_in) + (tokens_out / 1_000_000 * rate_out)

    def _check_force_complex(self, query: str, subject: str) -> Optional[str]:
        """Return 'COMPLEX' if a force-override keyword matches, else None."""
        subject_lower = subject.lower()
        query_lower = query.lower()
        for topic_keywords in FORCE_COMPLEX_TOPICS.get(subject_lower, []):
            if topic_keywords in query_lower:
                return "COMPLEX"
        return None

    async def _classify_complexity(self, query: str, has_image: bool, subject: str = "") -> str:
        if has_image:
            return "MEDIUM"

        # Force-override check before calling the classifier model
        forced = self._check_force_complex(query, subject)
        if forced:
            logger.info(f"Force-override to COMPLEX for subject='{subject}' | query preview: {query[:60]}")
            return forced

        try:
            response = await self.openai_client.chat.completions.create(
                model=TIER_1_MODEL,
                messages=[
                    {"role": "system", "content": CLASSIFIER_PROMPT.format(query=query)},
                    {"role": "user", "content": "Classify the query above."},
                ],
                max_tokens=10,
                temperature=0.0,
            )
            raw = response.choices[0].message.content.strip().upper()
            if "COMPLEX" in raw:
                return "COMPLEX"
            if "MEDIUM" in raw:
                return "MEDIUM"
            return "SIMPLE"
        except Exception as e:
            logger.warning(f"Classification failed, defaulting to MEDIUM: {e}")
            return "MEDIUM"

    async def route_query_stream(
        self,
        query: str,
        board: str,
        class_level: int,
        subject: str,
        context: str,
        confidence: str,
        system_prompt: str,
        has_image: bool = False,
        conversation_history: Optional[List[Dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Classifies the query, selects a model tier, and streams the response.
        Ends by yielding a METADATA JSON block for the caller to parse.
        """
        # ── Tier 0: Cache check ───────────────────────────────────────────
        cached_ans = await self.cache_service.check_cache(query, board, class_level, subject)
        if cached_ans:
            logger.info("cache_hit=True")
            ans_str = cached_ans.answers.get("en", "")
            if not ans_str and cached_ans.answers:
                ans_str = list(cached_ans.answers.values())[0]

            for word in ans_str.split(" "):
                yield word + " "

            response_meta = ModelRouterResponse(
                answer=ans_str,
                model_used="cache",
                tokens_in=0,
                tokens_out=0,
                cost=0.0,
                confidence="HIGH",
                from_cache=True,
                sources=[cached_ans.source_citation] if cached_ans.source_citation else [],
            )
            yield f"\\n\\n[METADATA]{response_meta.model_dump_json()}"
            return

        # ── Model selection ───────────────────────────────────────────────
        complexity = await self._classify_complexity(query, has_image, subject)

        if complexity == "SIMPLE":
            target_model = TIER_1_MODEL
        elif complexity == "COMPLEX":
            target_model = TIER_3_MODEL
        else:
            target_model = TIER_2_MODEL

        # Circuit breaker fallback
        if self.breaker.is_tripped(target_model):
            logger.warning(f"Circuit breaker tripped for {target_model}. Falling back to {TIER_2_MODEL}.")
            target_model = TIER_2_MODEL

        logger.info(f"Query classified: {complexity} | Model: {target_model} | Preview: {query[:80]}")

        # ── Build message history ─────────────────────────────────────────
        current_user_content = (
            f"[Relevant textbook context:\n{context}\n]\n\nStudent: {query}"
            if context
            else query
        )

        messages: List[Dict] = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": current_user_content})

        # ── Streaming with retry ──────────────────────────────────────────
        max_retries = 3
        full_response = ""
        tokens_in = sum(len(str(m.get("content", ""))) for m in messages) // 4
        tokens_out = 0
        success = False

        for attempt in range(max_retries):
            try:
                stream = await self.openai_client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    stream=True,
                    temperature=0.1,
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        full_response += text
                        tokens_out += max(1, len(text) // 4)
                        yield text

                success = True
                break

            except Exception as e:
                self.breaker.log_failure(target_model)
                logger.error(f"Invocation failed on attempt {attempt + 1}: {e}")

                if attempt == max_retries - 1:
                    if target_model == TIER_1_MODEL:
                        target_model = TIER_2_MODEL
                        logger.warning(f"Final fallback to {target_model}")
                    else:
                        yield "Sorry, I encountered an error. Please try again."
                        return
                else:
                    await asyncio.sleep(2**attempt)

        if success:
            cost = self._calculate_cost(target_model, tokens_in, tokens_out)

            asyncio.create_task(
                self.cosmos_repo.log_query_usage(
                    {
                        "timestamp": time.time(),
                        "model": target_model,
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "cost": cost,
                    }
                )
            )

            response_meta = ModelRouterResponse(
                answer=full_response,
                model_used=target_model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost=cost,
                confidence=confidence,
                from_cache=False,
                sources=[],
            )
            yield f"\\n\\n[METADATA]{response_meta.model_dump_json()}"
