import os
import re
import json
import logging
import httpx
import time
from typing import List, Dict, Any, Tuple

try:
    import tiktoken
except ImportError:
    tiktoken = None
    
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

logger = logging.getLogger(__name__)

class IngestionPipeline:
    """
    Core library orchestrating parsing, chunking, embeddings, and batch upload.
    Works for both NCERT and GSEB textbook processing pipelines.
    """
    def __init__(self):
        self.doc_ai_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
        self.doc_ai_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")
        
        self.openai_client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            api_key=os.getenv("AZURE_OPENAI_KEY", ""),
            api_version="2024-02-01"
        )
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
        
        search_endpoint = os.getenv("AZURE_AI_SEARCH_ENDPOINT", "")
        search_key = os.getenv("AZURE_AI_SEARCH_KEY", "")
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name="textbook_chunks",
            credential=AzureKeyCredential(search_key) if search_key else None
        )
        
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            logger.warning("tiktoken cl100k_base not available, text boundaries might be skewed natively.")
            self.tokenizer = None

    def evaluate_quality(self, text: str) -> bool:
        """
        Check PyMuPDF extraction quality. Returns True if VALID, False if GARBAGE (requires Azure OCR fallback).
        """
        if not text or len(text.strip()) < 50:
            return False
            
        garbage_chars = len(re.findall(r"[\uFFFD\u0000-\u0008\u000B\u000C\u000E-\u001F]", text))
        garbage_ratio = garbage_chars / len(text)
        
        if garbage_ratio > 0.05:
            return False
            
        return True

    def azure_document_read_fallback(self, image_data: bytes) -> str:
        """
        Uses Azure Document Intelligence "Read" API ($1.50/1000 pages) for complex/corrupted PDF pages.
        """
        try:
            url = f"{self.doc_ai_endpoint}/documentModels/prebuilt-read:analyze?api-version=2023-07-31"
            headers = {
                "Ocp-Apim-Subscription-Key": self.doc_ai_key,
                "Content-Type": "application/octet-stream"
            }
            
            with httpx.Client(timeout=30.0) as client:
                res = client.post(url, headers=headers, content=image_data)
                res.raise_for_status()
                
                operation_url = res.headers.get("Operation-Location")
                if not operation_url:
                    return ""
                    
                for _ in range(15):
                    time.sleep(2)
                    poll_res = client.get(operation_url, headers={"Ocp-Apim-Subscription-Key": self.doc_ai_key})
                    poll_json = poll_res.json()
                    
                    if poll_json.get("status") == "succeeded":
                        return poll_json.get("analyzeResult", {}).get("content", "")
                    elif poll_json.get("status") == "failed":
                        return ""
        except Exception as e:
            logger.error(f"Azure OCR fallback failed: {e}")
            return ""

    def extract_text_hybrid(self, pdf_path: str) -> List[Tuple[int, str]]:
        """
        Yields (page_number, text). Attempts FREE PyMuPDF locally, falls back to Azure Read OCR.
        """
        results = []
        try:
            if fitz is None:
                raise ImportError("PyMuPDF (fitz) is not installed. Native execution impossible.")
                
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text("text")
                
                if self.evaluate_quality(text):
                    results.append((page_num + 1, text.strip()))
                else:
                    logger.debug(f"{pdf_path} (Page {page_num+1}) failed validation tier. Escalating to Azure OCR.")
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    
                    ocr_text = self.azure_document_read_fallback(img_bytes)
                    results.append((page_num + 1, ocr_text.strip()))
            doc.close()
            return results
        except Exception as e:
            logger.error(f"Failed to process {pdf_path}: {e}")
            return []

    def chunk_text(self, text: str, min_tokens: int = 500, max_tokens: int = 800, overlap: int = 100) -> List[str]:
        """Simple greedy token chunking split by paragraphs approx to 500-800 bounds using tiktoken."""
        if not self.tokenizer:
            # Fallback to character bounds if uninstalled
            return [text[i:i+3000] for i in range(0, len(text), 2500)]
            
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0
        
        for p in paragraphs:
            p_len = len(self.tokenizer.encode(p))
            
            # Flush
            if current_length + p_len > max_tokens and current_chunk:
                joined = "\n\n".join(current_chunk).strip()
                if joined:
                    chunks.append(joined)
                
                # Approximate 100 token overlap from the tail
                overlap_text = joined[-400:] 
                current_chunk = [overlap_text + "\n\n" + p] if overlap_text else [p]
                current_length = len(self.tokenizer.encode(current_chunk[0]))
            else:
                current_chunk.append(p)
                current_length += p_len
                
        if current_chunk:
            joined = "\n\n".join(current_chunk).strip()
            if joined:
                chunks.append(joined)
            
        return chunks

    def compute_embedding(self, text: str) -> List[float]:
        """Generate OpenAI dense vectors (1536 dim default for text-embedding-3-small)."""
        try:
            response = self.openai_client.embeddings.create(
                input=[text],
                model=self.embedding_deployment
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding mapping failed: {e}")
            return []

    def batch_upload(self, documents: List[Dict[str, Any]]):
        """Synchronous batch push mapped exclusively to the textbook_chunks Azure Document Schema."""
        if not documents: return
        
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]
            try:
                self.search_client.merge_or_upload_documents(documents=batch)
                logger.info(f"Successfully uploaded batch of {len(batch)} chunks.")
            except Exception as e:
                logger.error(f"Search upload batch fault: {e}")
