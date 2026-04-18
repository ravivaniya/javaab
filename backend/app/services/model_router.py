import os
import time
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, List

from openai import AsyncAzureOpenAI
from app.services.cache_service import CacheService
from app.repositories.cosmos_repo import CosmosRepo
from app.models.schemas import ModelRouterResponse

logger = logging.getLogger(__name__)

# Model deployment names
TIER_1_MODEL = os.getenv("AZURE_PHI_MINI_DEPLOYMENT", "phi-4-mini")
TIER_2_MODEL = os.getenv("AZURE_GPT4.1_MINI_DEPLOYMENT", "gpt-4.1-mini")
TIER_3_MODEL = os.getenv("AZURE_GPT4.1_DEPLOYMENT", "gpt-4.1")

# Cost per 1M tokens (in, out) in USD
COSTS = {
    TIER_1_MODEL: (0.075, 0.30),
    TIER_2_MODEL: (0.15, 0.60),
    TIER_3_MODEL: (2.50, 10.00)
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
        # Clean up old
        self.failures[model_name] = [t for t in self.failures[model_name] if now - t <= self.window_sec]
        
    def is_tripped(self, model_name: str) -> bool:
        now = time.time()
        if model_name not in self.failures:
            return False
        recent = [t for t in self.failures[model_name] if now - t <= self.window_sec]
        return len(recent) >= self.failure_threshold

class ModelRouter:
    """
    Routes queries to the appropriate LLM tier based on difficulty and confidence.
    Incorporates Tier 0 (Cache), Tier 1-3 Model Selection, Streaming, Circuit Breakers,
    and Exponential Backoffs.
    """
    def __init__(self):
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_KEY", "")
        
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version="2024-02-01"
        )
        self.cache_service = CacheService()
        self.cosmos_repo = CosmosRepo()
        self.breaker = CircuitBreaker()

    def _calculate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        rate_in, rate_out = COSTS.get(model, (0.0, 0.0))
        return (tokens_in / 1_000_000 * rate_in) + (tokens_out / 1_000_000 * rate_out)

    async def _classify_complexity(self, query: str, has_image: bool) -> str:
        if has_image:
            return "MEDIUM"  # OCR required
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=TIER_1_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": "Reply ONLY with 'SIMPLE' or 'COMPLEX'. 'SIMPLE' = definitions, factual recall, short direct answers. 'COMPLEX' = math, multi-step reasoning, proofs."
                    },
                    {"role": "user", "content": query}
                ],
                max_tokens=10,
                temperature=0.0
            )
            classification = response.choices[0].message.content.strip().upper()
            if "COMPLEX" in classification:
                return "COMPLEX"
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
        has_image: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Executes the query via the appropriate tier. Yields chunks of text for SSE.
        Ends by yielding a final JSON string containing ModelRouterResponse.
        """
        # --- TIER 0: Cache Check ---
        cached_ans = await self.cache_service.check_cache(query, board, class_level, subject)
        if cached_ans:
            logger.info("cache_hit=True")
            ans_str = cached_ans.answers.get("en", "")
            if not ans_str and cached_ans.answers:
                ans_str = list(cached_ans.answers.values())[0]
            
            # Simulate streaming words
            words = ans_str.split(' ')
            for w in words:
                yield w + " "
                
            response_meta = ModelRouterResponse(
                answer=ans_str,
                model_used="cache",
                tokens_in=0,
                tokens_out=0,
                cost=0.0,
                confidence="HIGH",
                from_cache=True,
                sources=[cached_ans.source_citation] if cached_ans.source_citation else []
            )
            yield f"\\n\\n[METADATA]{response_meta.model_dump_json()}"
            return

        # --- MODEL SELECTION ---
        complexity = await self._classify_complexity(query, has_image)
        
        if complexity == "SIMPLE":
            target_model = TIER_1_MODEL
        elif complexity == "COMPLEX":
            target_model = TIER_3_MODEL
        else:
            target_model = TIER_2_MODEL
            
        # Circuit Breaker check
        if self.breaker.is_tripped(target_model):
            logger.warning(f"Circuit breaker tripped for {target_model}. Falling back.")
            if target_model == TIER_1_MODEL: target_model = TIER_2_MODEL
            elif target_model == TIER_3_MODEL: target_model = TIER_2_MODEL

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\\n{context}\\n\\nQuestion:\\n{query}"}
        ]

        # --- RETRY & STREAMING EXECUTION ---
        max_retries = 3
        full_response = ""
        tokens_in = len(str(messages)) // 4  # Safe approximation
        tokens_out = 0
        success = False
        
        for attempt in range(max_retries):
            try:
                stream = await self.openai_client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    stream=True,
                    temperature=0.1
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
                logger.error(f"Invocation failed on attempt {attempt+1}: {e}")
                
                if attempt == max_retries - 1:
                    # Final Fallback
                    if target_model == TIER_1_MODEL:
                        target_model = TIER_2_MODEL
                        logger.warning(f"Final fallback to {target_model}")
                    else:
                        yield "Sorry, I encountered an error. Please try again."
                        return
                else:
                    await asyncio.sleep(2 ** attempt) # Exponential backoff
        
        if success:
            cost = self._calculate_cost(target_model, tokens_in, tokens_out)
            
            # Async Logging
            asyncio.create_task(
                self.cosmos_repo.log_query_usage({
                    "timestamp": time.time(),
                    "model": target_model,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost": cost
                })
            )
            
            response_meta = ModelRouterResponse(
                answer=full_response,
                model_used=target_model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost=cost,
                confidence=confidence,
                from_cache=False,
                sources=[]
            )
            yield f"\\n\\n[METADATA]{response_meta.model_dump_json()}"
