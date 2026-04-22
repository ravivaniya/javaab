import os
import json
import logging
import asyncio
from typing import AsyncGenerator, Optional
from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletionChunk

from app.config import get_settings

logger = logging.getLogger(__name__)

class LlmService:
    """
    Unified LLM communication class for Azure OpenAI models.
    """
    def __init__(self):
        self.settings = get_settings()
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=self.settings.AZURE_OPENAI_ENDPOINT,
            api_key=self.settings.AZURE_OPENAI_KEY,
            api_version="2024-02-01"
        )
        
        self.model_tier_map = {
            "simple": self.settings.AZURE_OPENAI_MINI_DEPLOYMENT,
            "medium": self.settings.AZURE_OPENAI_MINI_DEPLOYMENT,
            "complex": self.settings.AZURE_OPENAI_GPT4_DEPLOYMENT,
        }

    async def _openai_with_retry(self, messages: list, model: str, temperature: float, max_tokens: int, stream: bool = False):
        """Exponential backoff natively hooking into the AsyncAzureOpenAI client."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await self.openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    stream_options={"include_usage": True} if stream else None
                )
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
            await asyncio.sleep(2 ** attempt)

    async def generate_response(
        self, 
        model_tier: str, 
        system_prompt: str, 
        user_message: str, 
        context: str, 
        image_base64: Optional[str] = None, 
        temperature: float = 0.15, 
        max_tokens: int = 1500, 
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Primary generation pipeline. Routes payload seamlessly between the Azure OpenAI implementation depending on the requested `model_tier`.
        Yields standard SSE chunks back to the async caller.
        """
        model = self.model_tier_map.get(model_tier, self.model_tier_map["medium"])
        
        messages = [{"role": "system", "content": system_prompt}]
        
        user_content = []
        user_content.append({
            "type": "text", 
            "text": f"Context:\n{context}\n\nQuestion:\n{user_message}"
        })
        
        if image_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
            })
            
        messages.append({"role": "user", "content": user_content})

        if stream:
            openai_stream = await self._openai_with_retry(messages, model, temperature, max_tokens, stream=True)
            async for chunk in openai_stream:
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            resp = await self._openai_with_retry(messages, model, temperature, max_tokens, stream=False)
            yield resp.choices[0].message.content

    async def classify_query(self, query: str) -> str:
        """
        Runs a micro 10-token check to ascertain query complexity.
        """
        messages = [
            {
                "role": "system", 
                "content": "Reply ONLY with 'SIMPLE', 'MEDIUM' or 'COMPLEX'. 'SIMPLE' = factual concepts. 'COMPLEX' = advanced reasoning & logic."
            },
            {"role": "user", "content": query}
        ]
        model = self.model_tier_map["simple"]
        try:
            response = await self._openai_with_retry(messages, model, temperature=0.0, max_tokens=10, stream=False)
            res = response.choices[0].message.content.strip().upper()
            if "COMPLEX" in res: return "COMPLEX"
            if "MEDIUM" in res: return "MEDIUM"
            return "SIMPLE"
        except Exception as e:
            logger.warning(f"Classification failed, assuming MEDIUM tier: {e}")
            return "MEDIUM"

    async def extract_text_from_image(self, image_base64: str) -> str:
        """
        Uses Vision primitives to OCR texts for the ingestion pipeline natively.
        """
        messages = [
            {"role": "user", "content": [
                {
                    "type": "text", 
                    "text": "Extract all readable text, formulas, or questions from this image exactly as written. Provide no other conversational text."
                },
                {
                    "type": "image_url", 
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                }
            ]}
        ]
        model = self.settings.AZURE_OPENAI_MEDIUM_DEPLOYMENT
        response = await self._openai_with_retry(messages, model, temperature=0.0, max_tokens=1000, stream=False)
        return response.choices[0].message.content

    async def translate_to_english(self, text: str) -> str:
        """
        Zero-temperature translation node.
        """
        messages = [
            {
                "role": "system", 
                "content": "You are a translation subsystem. Translate the query to English. Output NOTHING ELSE."
            },
            {"role": "user", "content": text}
        ]
        model = self.model_tier_map["simple"]
        try:
            response = await self._openai_with_retry(messages, model, temperature=0.0, max_tokens=50, stream=False)
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Translation failed falling back to raw: {e}")
            return text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Safely destroy TCP loop instances."""
        if self.openai_client:
            await self.openai_client.close()
