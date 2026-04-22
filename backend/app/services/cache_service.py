import os
import json
import math
import logging
from typing import Optional, Dict, List
from pydantic import BaseModel

import redis.asyncio as redis
from openai import AsyncAzureOpenAI
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery

logger = logging.getLogger(__name__)



class CachedAnswer(BaseModel):
    cache_id: str
    question: str
    answers: Dict[str, str]
    board: str
    class_level: int
    subject: str
    chapter: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    source_citation: Optional[str] = None

class VerifiedAnswer(CachedAnswer):
    question_embedding: Optional[List[float]] = None

class CacheStats(BaseModel):
    total_count: int
    hit_rate: float
    top_uncached_questions: List[str]

class CacheService:
    def __init__(self):
        # OpenAI Client for embeddings
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_KEY", "")
        
        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version="2024-02-01"
        )
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
        
        # Azure AI Search Client
        search_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT", "")
        search_key = os.getenv("AZURE_AI_SEARCH_KEY", "")
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name="verified_answers",
            credential=AzureKeyCredential(search_key) if search_key else None
        )
        
        # Redis Client
        redis_host = os.getenv("AZURE_REDIS_HOST", "localhost")
        redis_port = int(os.getenv("AZURE_REDIS_PORT", "6380" if os.getenv("AZURE_REDIS_HOST") else "6379"))
        redis_password = os.getenv("AZURE_REDIS_KEY", None)
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=redis_port, 
            password=redis_password,
            ssl=(redis_port == 6380),
            decode_responses=True
        )

    async def _get_embedding(self, text: str) -> List[float]:
        try:
            response = await self.openai_client.embeddings.create(
                input=[text],
                model=self.embedding_deployment
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return []

    def _build_filter(self, board: str, class_level: int, subject: str) -> Optional[str]:
        conditions = []
        if board:
            conditions.append(f"board eq '{board}'")
        if class_level:
            conditions.append(f"class_level eq {class_level}")
        if subject:
            conditions.append(f"subject eq '{subject}'")
        
        if conditions:
            return " and ".join(conditions)
        return None

    async def check_cache(self, query: str, board: str, class_level: int, subject: str) -> Optional[CachedAnswer]:
        try:
            await self.redis_client.incr("cache_stats:total_requests")

            query_vector = await self._get_embedding(query)
            if not query_vector:
                return None

            filter_str = self._build_filter(board, class_level, subject)
            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=1,
                fields="question_vector"
            )
            
            # HNSW search in verified_answers index
            search_results = await self.search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                filter=filter_str,
                select=["cache_id"],
                top=1
            )
            
            best_match = None
            async for doc in search_results:
                best_match = doc
                break
                
            if best_match:
                sim = best_match.get("@search.score", 0.0)
                
                if sim >= 0.93:
                    cache_id = best_match.get("cache_id") or best_match.get("id")
                    if cache_id:
                        cached_json = await self.redis_client.get(cache_id)
                        if cached_json:
                            await self.redis_client.incr("cache_stats:hits")
                            return CachedAnswer.model_validate_json(cached_json)
            
            # Log uncached query for top list
            await self.redis_client.zincrby("cache_stats:uncached_queries", 1.0, query)
            return None
                
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return None

    async def store_verified_answer(self, answer: VerifiedAnswer):
        try:
            if not answer.question_embedding:
                answer.question_embedding = await self._get_embedding(answer.question)
                
            # Upsert into AI Search
            search_doc = {
                "id": str(answer.cache_id),  # Usually AI search requires string ids
                "cache_id": str(answer.cache_id),
                "question": answer.question,
                "question_vector": answer.question_embedding,
                "board": answer.board,
                "class_level": answer.class_level,
                "subject": answer.subject,
                "chapter": answer.chapter,
            }
            await self.search_client.merge_or_upload_documents(documents=[search_doc])
            
            # Save to Redis (exclude embedding to save space)
            redis_json = answer.model_dump_json(exclude={"question_embedding"})
            await self.redis_client.set(str(answer.cache_id), redis_json)
            
            # Update items count
            await self.redis_client.incr("cache_stats:total_items")
            
        except Exception as e:
            logger.error(f"Error storing verified answer: {e}")
            raise e

    async def get_cache_stats(self) -> CacheStats:
        try:
            total_items = int(await self.redis_client.get("cache_stats:total_items") or 0)
            total_requests = int(await self.redis_client.get("cache_stats:total_requests") or 0)
            hits = int(await self.redis_client.get("cache_stats:hits") or 0)
            
            hit_rate = (hits / total_requests) if total_requests > 0 else 0.0
            
            top_uncached = await self.redis_client.zrevrange("cache_stats:uncached_queries", 0, 9)
            
            return CacheStats(
                total_count=total_items,
                hit_rate=hit_rate,
                top_uncached_questions=top_uncached
            )
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return CacheStats(total_count=0, hit_rate=0.0, top_uncached_questions=[])
