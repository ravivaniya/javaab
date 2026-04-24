import os
import logging
from typing import List, Dict, Any, Optional

from openai import AsyncAzureOpenAI
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery

logger = logging.getLogger(__name__)


class RagService:
    def __init__(self):
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.getenv("AZURE_OPENAI_KEY", "")

        self.openai_client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version="2024-02-01"
        )

        search_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT", "")
        search_key = os.getenv("AZURE_AI_SEARCH_KEY", "")

        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name="textbook_chunks",
            credential=AzureKeyCredential(search_key) if search_key else None
        )

        self.embedding_deployment = os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
        )
        self.translation_deployment = os.getenv(
            "AZURE_OPENAI_GPT4.1_NANO_DEPLOYMENT", "gpt-4.1-nano"
        )

    async def close(self):
        """Cleanly close all async HTTP clients to avoid 'Unclosed client session' warnings."""
        await self.openai_client.close()
        await self.search_client.close()

    async def _get_embedding(self, text: str) -> List[float]:
        response = await self.openai_client.embeddings.create(
            input=[text],
            model=self.embedding_deployment
        )
        return response.data[0].embedding

    async def _translate_to_english(self, query: str) -> str:
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.translation_deployment,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a translation assistant. Translate the following "
                            "user query to English. Return ONLY the English translation "
                            "without any extra formatting or conversational text."
                        )
                    },
                    {"role": "user", "content": query}
                ],
                max_tokens=50,
                temperature=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Translation via GPT-4.1-nano failed: {e}")
            return query

    def _build_filter(self, filters: Dict[str, Any]) -> Optional[str]:
        """Build an OData filter string from metadata filters."""
        conditions = []
        if filters.get("board"):
            conditions.append(f"board eq '{filters['board']}'")
        if filters.get("class_level"):
            conditions.append(f"class_level eq {filters['class_level']}")
        if filters.get("subject"):
            conditions.append(f"subject eq '{filters['subject']}'")
        return " and ".join(conditions) if conditions else None

    async def _search_hybrid(
        self,
        query: str,
        query_vector: List[float],
        filter_str: Optional[str]
    ) -> List[dict]:
        """
        Run a hybrid BM25 + vector search via Azure AI Search.

        content_vector is intentionally excluded from `select` — Azure marks
        embedding fields as non-retrievable to save bandwidth. We use
        @search.score (RRF-fused relevance score) for ranking instead.
        """
        try:
            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=50,
                fields="content_vector"
            )

            results = []
            async for doc in await self.search_client.search(
                search_text=query,
                vector_queries=[vector_query],
                filter=filter_str,
                select=[
                    "chunk_id",
                    "content",
                    "page_number",
                    "source_book",
                    "chapter_number"
                ],
                top=5
            ):
                results.append(doc)
            return results
        except Exception as e:
            logger.error(f"Azure index search failed: {e}")
            return []

    def _get_score(self, doc: dict) -> float:
        """Extract RRF relevance score from a search result document."""
        return doc.get("@search.score", 0.0)

    def _rrf_score_to_confidence(self, avg_score: float) -> str:
        """
        Map an average RRF @search.score to a confidence band.

        RRF scores from Azure hybrid search are typically in [0.01, 0.10],
        not [0, 1] like cosine similarity, so the thresholds are lower.
        Monitor the avg_score log line and tune these if needed.
        """
        if avg_score > 0.030:
            return "HIGH"
        elif avg_score >= 0.015:
            return "MEDIUM"
        elif avg_score >= 0.005:
            return "LOW"
        else:
            return "NONE"

    async def get_context(
        self,
        query: str,
        filters: Dict[str, Any],
        query_language: str = "en"
    ) -> Dict[str, Any]:
        """
        Retrieve the top RAG context chunks for a student query.

        Pipeline:
        1. Apply metadata filters (board, class_level, subject).
        2. Embed the query and run hybrid BM25+vector search.
        3. For non-English queries, also search the English translation
           so NCERT English chunks surface alongside vernacular ones.
        4. Deduplicate by chunk_id, keeping highest @search.score per chunk.
        5. Sort descending, take top 5.
        6. Derive confidence from average RRF score.
        7. Format and return context string with source citations.
        """
        try:
            filter_str = self._build_filter(filters)

            # Step 1: Search with original query
            query_vector = await self._get_embedding(query)
            results = await self._search_hybrid(query, query_vector, filter_str)

            # Step 2: Cross-lingual search for non-English input
            if query_language.lower() != "en":
                translated_query = await self._translate_to_english(query)
                if translated_query and translated_query.strip() != query.strip():
                    translated_vector = await self._get_embedding(translated_query)
                    en_results = await self._search_hybrid(
                        translated_query, translated_vector, filter_str
                    )
                    results.extend(en_results)

            if not results:
                return {"context": "", "confidence": "NONE", "confidence_score": 0.0}

            # Step 3: Deduplicate, keep best score per chunk
            unique_chunks: Dict[str, dict] = {}
            for doc in results:
                chunk_id = doc.get("chunk_id")
                if not chunk_id:
                    continue
                score = self._get_score(doc)
                if chunk_id not in unique_chunks or score > self._get_score(unique_chunks[chunk_id]):
                    unique_chunks[chunk_id] = doc

            # Step 4: Sort and take top 5
            top_5 = sorted(
                unique_chunks.values(),
                key=lambda d: self._get_score(d),
                reverse=True
            )[:5]

            if not top_5:
                return {"context": "", "confidence": "NONE", "confidence_score": 0.0}

            # Step 5: Confidence scoring
            avg_score = sum(self._get_score(c) for c in top_5) / len(top_5)
            confidence = self._rrf_score_to_confidence(avg_score)

            logger.info(
                f"RAG: {len(top_5)} chunks | avg_score={avg_score:.4f} | confidence={confidence}"
            )

            # Step 6: Build context string
            context_pieces = []
            for i, chunk in enumerate(top_5):
                source_book = chunk.get("source_book", "Unknown Source")
                chap = chunk.get("chapter_number", "")
                page = chunk.get("page_number", "")

                header_parts = [source_book]
                if chap:
                    header_parts.append(f"Ch.{chap}")
                if page:
                    header_parts.append(f"Page {page}")

                header = f"--- Source {i + 1}: {', '.join(header_parts)} ---"
                context_pieces.append(f"{header}\n{chunk.get('content', '')}")

            final_context = "\n\n".join(context_pieces)

            # Truncate to ~2,500 tokens (approx 10,000 chars)
            max_chars = 10_000
            if len(final_context) > max_chars:
                final_context = final_context[:max_chars] + "\n... [truncated for token limits]"

            return {"context": final_context, "confidence": confidence, "confidence_score": round(avg_score, 4)}

        except Exception as e:
            logger.error(f"RAG formulation process failed: {e}")
            return {"context": "", "confidence": "NONE", "confidence_score": 0.0}


# ---------------------------------------------------------------------------
# Diagnostic helpers — only used when running this file directly
# ---------------------------------------------------------------------------

async def _diagnose(service: RagService):
    """
    Step-by-step diagnosis to find why get_context returns empty results.
    Run this whenever you see Confidence: NONE to quickly pinpoint the cause.
    """
    search_key = os.getenv("AZURE_AI_SEARCH_KEY", "")
    search_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT", "")

    raw_client = SearchClient(
        endpoint=search_endpoint,
        index_name="textbook_chunks",
        credential=AzureKeyCredential(search_key)
    )

    print("\n" + "=" * 60)
    print("DIAGNOSTIC MODE")
    print("=" * 60)

    # ------------------------------------------------------------------
    # TEST 1: No filter, keyword only — confirms index has any documents
    # ------------------------------------------------------------------
    print("\n[TEST 1] Keyword search with NO filters (confirms index is populated)...")
    count = 0
    sample_doc = None
    async for doc in await raw_client.search(
        search_text="photosynthesis",
        select=["chunk_id", "board", "class_level", "subject", "source_book"],
        top=3
    ):
        count += 1
        sample_doc = doc
        print(f"  Found: chunk_id={doc.get('chunk_id')} | board={doc.get('board')!r} "
              f"| class_level={doc.get('class_level')!r} | subject={doc.get('subject')!r} "
              f"| source_book={doc.get('source_book')!r}")

    if count == 0:
        print("  ❌ Index returned 0 results even without filters.")
        print("     → The index may be empty or 'content' field is not searchable.")
        print("     → Re-run your ingestion pipeline and verify chunks were uploaded.")
        await raw_client.close()
        return

    print(f"  ✅ Index has documents ({count} returned).")
    print(f"     Actual stored board value: {sample_doc.get('board')!r}  <-- use this in your filters")

    # ------------------------------------------------------------------
    # TEST 2: Board filter using exact value from index
    # ------------------------------------------------------------------
    if sample_doc:
        actual_board = sample_doc.get("board", "")
        print(f"\n[TEST 2] Keyword search WITH board filter using actual stored value: board='{actual_board}'...")
        count2 = 0
        async for doc in await raw_client.search(
            search_text="photosynthesis",
            filter=f"board eq '{actual_board}'",
            select=["chunk_id", "board", "class_level", "subject"],
            top=3
        ):
            count2 += 1
            print(f"  Found: chunk_id={doc.get('chunk_id')} | subject={doc.get('subject')!r}")

        if count2 == 0:
            print(f"  ❌ Filter board='{actual_board}' returned nothing.")
            print("     → 'board' field may not be filterable. Check your index definition.")
        else:
            print(f"  ✅ Board filter works with value '{actual_board}'.")

    # ------------------------------------------------------------------
    # TEST 3: Full hybrid search with no filters — tests vector pipeline
    # ------------------------------------------------------------------
    print("\n[TEST 3] Full hybrid search with NO filters (tests embedding + vector field)...")
    query_vector = await service._get_embedding("photosynthesis")
    results_no_filter = await service._search_hybrid(
        "photosynthesis", query_vector, filter_str=None
    )
    if results_no_filter:
        print(f"  ✅ Hybrid search returned {len(results_no_filter)} result(s).")
        for r in results_no_filter:
            print(f"     chunk_id={r.get('chunk_id')} | score={r.get('@search.score', 0):.4f} "
                  f"| board={r.get('board')!r} | subject={r.get('subject')!r}")
    else:
        print("  ❌ Hybrid search returned 0 results without filters.")
        print("     → 'content_vector' field may not be configured for vector search.")
        print("     → Verify your index schema has a vectorSearch configuration on content_vector.")

    # ------------------------------------------------------------------
    # TEST 4: Hybrid search with the original failing filter
    # ------------------------------------------------------------------
    print("\n[TEST 4] Hybrid search WITH original filter (board='NCERT', class_level=10, subject='Science')...")
    original_filter = "board eq 'NCERT' and class_level eq 10 and subject eq 'Science'"
    results_filtered = await service._search_hybrid(
        "photosynthesis", query_vector, filter_str=original_filter
    )
    if results_filtered:
        print(f"  ✅ Filtered hybrid search returned {len(results_filtered)} result(s).")
    else:
        print("  ❌ Filtered hybrid search returned 0 results.")
        print("     → Filter values don't match what's stored. Use values from TEST 1.")

    await raw_client.close()
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE — fix filter values based on TEST 1 output above.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    logging.basicConfig(level=logging.INFO)

    async def run_test():
        print("Initializing RagService...")
        service = RagService()

        try:
            # Run diagnostics first to identify any filter/index issues
            await _diagnose(service)

            # Normal pipeline test
            query = "What is photosynthesis?"
            filters = {"board": "NCERT", "class_level": 10, "subject": "Science"}

            print(f"Testing get_context() with query: '{query}'")
            print(f"Filters: {filters}\n")

            result = await service.get_context(query=query, filters=filters)

            print("--- get_context() Results ---")
            print(f"Confidence: {result.get('confidence')}")
            print("Context:\n")
            print(result.get("context") or "(empty)")

        finally:
            # Always close to prevent 'Unclosed client session' warnings
            await service.close()

    asyncio.run(run_test())