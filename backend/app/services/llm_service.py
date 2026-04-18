import os
import json
import logging
import asyncio
from typing import AsyncGenerator, Optional
import httpx
from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletionChunk

logger = logging.getLogger(__name__)

# Constants
TIER_1_MODEL = os.getenv("AZURE_PHI_MINI_DEPLOYMENT", "phi-4-mini")
TIER_2_MODEL = os.getenv("AZURE_GPT4.1_MINI_DEPLOYMENT", "gpt-4.1-mini")
TIER_3_MODEL = os.getenv("AZURE_GPT4.1_DEPLOYMENT", "gpt-4.1")

class LlmService:
    """
    Unified LLM communication class for Azure AI Foundry and Azure OpenAI models.
    """
    def __init__(self):
        # OpenAI Client for GPT models
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_KEY", ""),
            api_version="2024-02-01"
        )
        
        # Foundry Configuration for Phi Models
        self.phi_endpoint = os.getenv("PHI4_MINI_ENDPOINT", "")
        self.phi_key = os.getenv("PHI4_MINI_KEY", "")
        
        # Reusable HTTPx strictly for Foundry endpoints
        # A timeout of 30s is appropriate for the ML endpoints.
        self.httpx_client = httpx.AsyncClient(timeout=30.0)

    async def _httpx_post_with_retry(self, url: str, headers: dict, json_payload: dict, stream: bool = False):
        """Standard bounded exponential backoff specific to HTTPx for Phi-4-mini calls."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if stream:
                    request = self.httpx_client.build_request("POST", url, headers=headers, json=json_payload)
                    response = await self.httpx_client.send(request, stream=True)
                    response.raise_for_status()
                    return response
                else:
                    response = await self.httpx_client.post(url, headers=headers, json=json_payload)
                    response.raise_for_status()
                    return response
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in [429, 500, 502, 503, 504]:
                    if attempt == max_retries - 1:
                        raise e
                else:
                    raise e
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                    
            await asyncio.sleep(2 ** attempt)

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
        model: str, 
        system_prompt: str, 
        user_message: str, 
        context: str, 
        image_base64: Optional[str] = None, 
        temperature: float = 0.15, 
        max_tokens: int = 1500, 
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Primary generation pipeline. Routes payload seamlessly between the HTTPx Foundry
        implementation and the Azure OpenAI implementation depending on the requested `model`.
        Yields standard SSE chunks back to the async caller.
        """
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

        if model == TIER_1_MODEL:
            # Azure AI Foundry logic using HTTPX
            headers = {
                "Authorization": f"Bearer {self.phi_key}",
                "Content-Type": "application/json"
            }
            # Many Foundry models expect OpenAI compat payloads
            payload = {
                "model": model, 
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }
            
            if stream:
                response = await self._httpx_post_with_retry(self.phi_endpoint, headers, payload, stream=True)
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            json_data = json.loads(data)
                            if "choices" in json_data and len(json_data["choices"]) > 0:
                                delta = json_data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except Exception as e:
                            # Safely ignore parse errors on malformed chunks or token usage reporting blocks at EOF
                            pass
                await response.aclose()
            else:
                response = await self._httpx_post_with_retry(self.phi_endpoint, headers, payload, stream=False)
                resp_json = response.json()
                yield resp_json["choices"][0]["message"]["content"]
                
        else:
            # Azure OpenAI Logic
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
        Runs a micro 10-token check against the Phi-4-mini endpoint to ascertain query complexity.
        """
        messages = [
            {
                "role": "system", 
                "content": "Reply ONLY with 'SIMPLE', 'MEDIUM' or 'COMPLEX'. 'SIMPLE' = factual concepts. 'COMPLEX' = advanced reasoning & logic."
            },
            {"role": "user", "content": query}
        ]
        headers = {
            "Authorization": f"Bearer {self.phi_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 10,
            "stream": False
        }
        try:
            response = await self._httpx_post_with_retry(self.phi_endpoint, headers, payload, stream=False)
            res = response.json()["choices"][0]["message"]["content"].strip().upper()
            if "COMPLEX" in res: return "COMPLEX"
            if "MEDIUM" in res: return "MEDIUM"
            return "SIMPLE"
        except Exception as e:
            logger.warning(f"Classification failed, assuming MEDIUM tier: {e}")
            return "MEDIUM"

    async def extract_text_from_image(self, image_base64: str) -> str:
        """
        Uses GPT-4.1-mini Vision primitives to OCR texts for the ingestion pipeline natively.
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
        response = await self._openai_with_retry(messages, TIER_2_MODEL, temperature=0.0, max_tokens=1000, stream=False)
        return response.choices[0].message.content

    async def translate_to_english(self, text: str) -> str:
        """
        Zero-temperature translation node hitting the cheap Phi-4 endpoints.
        """
        messages = [
            {
                "role": "system", 
                "content": "You are a translation subsystem. Translate the query to English. Output NOTHING ELSE."
            },
            {"role": "user", "content": text}
        ]
        headers = {
            "Authorization": f"Bearer {self.phi_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 50,
            "stream": False
        }
        try:
            response = await self._httpx_post_with_retry(self.phi_endpoint, headers, payload, stream=False)
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"Translation failed falling back to raw: {e}")
            return text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Safely destroy TCP loop instances for both abstractions."""
        if self.httpx_client:
            await self.httpx_client.aclose()
        if self.openai_client:
            await self.openai_client.close()
