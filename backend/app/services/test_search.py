# # backend/scripts/test_search.py
# import os, warnings
# warnings.filterwarnings("ignore", category=SyntaxWarning)
# 
# from dotenv import load_dotenv
# from openai import AzureOpenAI
# from azure.search.documents import SearchClient
# from azure.search.documents.models import VectorizedQuery
# from azure.core.credentials import AzureKeyCredential
# 
# load_dotenv()
# 
# openai_client = AzureOpenAI(
#     azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     api_key=os.getenv("AZURE_OPENAI_KEY"),
#     api_version="2024-02-01"
# )
# 
# search_client = SearchClient(
#     endpoint=os.getenv("AZURE_AI_SEARCH_ENDPOINT"),
#     index_name="textbook_chunks",
#     credential=AzureKeyCredential(os.getenv("AZURE_AI_SEARCH_KEY"))
# )
# 
# EMBEDDING_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
# 
# 
# def embed(text: str) -> list[float]:
#     return openai_client.embeddings.create(
#         input=text,
#         model=EMBEDDING_MODEL
#     ).data[0].embedding
# 
# 
# def confidence_label(score: float) -> str:
#     """Thresholds for VECTOR scores (cosine similarity), NOT RRF scores."""
#     if score >= 0.80: return "✅ HIGH"
#     if score >= 0.65: return "🟡 MED"
#     if score >= 0.50: return "🔴 LOW"
#     return "⛔ POOR"
# 
# 
# def search_chunks(
#     query: str,
#     board: str,
#     cls: int,
#     subject: str,
#     top: int = 5
# ) -> list[dict]:
#     """
#     Two-pass search returning VECTOR scores (not RRF).
# 
#     Why not use hybrid mode directly:
#       Azure AI Search hybrid returns RRF scores (always 0.01-0.10).
#       These are useless for confidence thresholds.
#       Instead we run vector search (which returns cosine similarity 0.0-1.0)
#       and use keyword search only as a tiebreaker for same-score chunks.
#     """
#     vector = embed(query)
#     filter_expr = f"board eq '{board}' and class_level eq {cls} and subject eq '{subject}'"
#     select_fields = ["chunk_id", "content", "source_book", "page_number", "chapter_name", "topic"]
# 
#     # Primary: vector search — scores are real cosine similarity (0.0 to 1.0)
#     vector_results = list(search_client.search(
#         search_text=None,
#         vector_queries=[VectorizedQuery(
#             vector=vector,
#             k_nearest_neighbors=top,
#             fields="content_vector"
#         )],
#         filter=filter_expr,
#         select=select_fields,
#         top=top
#     ))
# 
#     # Secondary: keyword search — catches exact term matches vector might miss
#     # (e.g. formula names, chapter numbers, specific terminology)
#     keyword_results = list(search_client.search(
#         search_text=query,
#         filter=filter_expr,
#         select=select_fields,
#         top=top
#     ))
# 
#     # Merge: vector results are primary, add keyword-only hits at the end
#     seen_ids = {r["chunk_id"] for r in vector_results}
#     keyword_only = [r for r in keyword_results if r["chunk_id"] not in seen_ids]
# 
#     # keyword_only chunks get a synthetic score of 0.45 (below LOW threshold)
#     # so they appear but are clearly marked as keyword-matched only
#     for r in keyword_only:
#         r["@search.score"] = 0.45
#         r["_match_type"] = "keyword"
# 
#     for r in vector_results:
#         r["_match_type"] = "vector"
# 
#     merged = vector_results + keyword_only
#     return sorted(merged, key=lambda x: x["@search.score"], reverse=True)[:top]
# 
# 
# def translate_to_english(text: str, subject: str = "", class_level: int = 0) -> str:
#     context = f"This is a Class {class_level} {subject} textbook query." if subject else ""
#     response = openai_client.chat.completions.create(
#         model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini"),
#         messages=[
#             {
#                 "role": "system",
#                 "content": (
#                     f"Translate this Indian student query to English for textbook search. "
#                     f"{context} Preserve scientific terms accurately — "
#                     f"'prakaash sanshleshan' in Science means 'photosynthesis' not 'light synthesis'. "
#                     f"'prakaash' alone means 'light'. Return only the translation."
#                 )
#             },
#             {"role": "user", "content": text}
#         ],
#         max_tokens=60,
#         temperature=0
#     ).choices[0].message.content.strip()
#     return response
# 
# 
# def is_non_english(text: str) -> bool:
#     """True if text contains non-ASCII chars or looks like Roman transliteration."""
#     if any(ord(c) > 127 for c in text):
#         return True
#     # Simple heuristic: common Roman Hindi/Gujarati patterns
#     indicators = ["kya", "hai", "kaise", "batao", "samjhao", "karo", "wala", "sanshleshan"]
#     lower = text.lower()
#     return any(word in lower for word in indicators)
# 
# 
# def full_search(query: str, board: str, cls: int, subject: str) -> list[dict]:
#     """
#     Full search with cross-lingual fallback.
#     If query is non-English, also search with English translation and merge.
#     """
#     results = search_chunks(query, board, cls, subject)
# 
#     if is_non_english(query):
#         translated = translate_to_english(query, subject, cls)
#         print(f"  🌐 Translated: '{translated}'")
# 
#         if translated.lower() != query.lower():
#             translated_results = search_chunks(translated, board, cls, subject)
# 
#             # Merge: keep highest score per chunk across both searches
#             all_chunks: dict[str, dict] = {r["chunk_id"]: r for r in results}
#             for r in translated_results:
#                 cid = r["chunk_id"]
#                 if cid not in all_chunks or r["@search.score"] > all_chunks[cid]["@search.score"]:
#                     all_chunks[cid] = r
# 
#             results = sorted(all_chunks.values(), key=lambda x: x["@search.score"], reverse=True)[:5]
# 
#     return results
# 
# 
# # ── Tests ──────────────────────────────────────────────────────────────────
# 
# TEST_QUERIES = [
#     ("What is photosynthesis?",          "CBSE", 10, "Science"),
#     ("Newton's second law of motion",     "CBSE", 9,  "Science"),
#     ("prakaash sanshleshan kya hai",      "CBSE", 10, "Science"),
#     ("What is quadratic equation?",       "CBSE", 10, "Mathematics"),
#     ("પ્રકાશ સંશ્લેષણ સમજાવો",           "CBSE", 10, "Science"),
# ]
# 
# print("=" * 70)
# for query, board, cls, subject in TEST_QUERIES:
#     print(f"\n🔍 Query : {query}")
#     print(f"   Filter: {board} | Class {cls} | {subject}")
# 
#     results = full_search(query, board, cls, subject)
# 
#     if not results:
#         print("   ⚠️  No results — this class/subject likely not ingested yet")
#         print("=" * 70)
#         continue
# 
#     for i, r in enumerate(results[:3], 1):
#         score = r["@search.score"]
#         match_type = r.get("_match_type", "vector")
#         chapter = r.get("chapter_name") or "—"
#         topic = r.get("topic") or "—"
#         page = r.get("page_number", "?")
#         preview = r["content"][:200].replace("\n", " ").strip()
# 
#         print(f"\n  [{i}] {confidence_label(score)} score={score:.4f} [{match_type}]")
#         print(f"       {r['source_book']} | Ch: {chapter} | Topic: {topic} | p.{page}")
#         print(f"       {preview}...")
# 
#     print("=" * 70)