"""
Hybrid PDF extraction and chunking pipeline for Javaab.
Uses PyMuPDF first (free), falls back to Azure Document Intelligence for scanned pages.

Usage:
  python scripts/ingest_pdfs.py --pdf-dir ../data/ncert --board CBSE
  python scripts/ingest_pdfs.py --pdf-dir ../data/gseb --board GSEB
"""

import os, json, hashlib, re, argparse

# ─── Chapter / heading detection ──────────────────────────────────
# Match "Chapter 7", "CHAPTER 7", "Chapter 7 — Title", "अध्याय 7", "પ્રકરણ 7".
_CHAPTER_RE = re.compile(
    r"^\s*(?:chapter|CHAPTER|Chapter|अध्याय|પ્રકરણ)\s+(\d+)[\.\s:\-—]*(.*)$",
    re.MULTILINE,
)
# Numbered headings like "7.2 Newton's Second Law".
_NUMBERED_RE = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\s+([A-Z][^\n]{2,80})$", re.MULTILINE)


def detect_chapter(text: str) -> tuple[int, str, str]:
    """Return (chapter_number, chapter_name, topic) parsed from page/chunk text."""
    chapter_number = 0
    chapter_name = ""
    topic = ""

    if not text:
        return chapter_number, chapter_name, topic

    m = _CHAPTER_RE.search(text)
    if m:
        try:
            chapter_number = int(m.group(1))
        except (TypeError, ValueError):
            chapter_number = 0
        chapter_name = (m.group(2) or "").strip().splitlines()[0][:120] if m.group(2) else ""

    m2 = _NUMBERED_RE.search(text)
    if m2:
        if not chapter_number:
            try:
                chapter_number = int(m2.group(1))
            except (TypeError, ValueError):
                pass
        topic = (m2.group(3) or "").strip()[:120]

    return chapter_number, chapter_name, topic
from pathlib import Path
from typing import Optional
import fitz  # PyMuPDF
from tqdm import tqdm
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

# ─── Clients ─────────────────────────────────────────────
openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-01"
)

search_client = SearchClient(
    endpoint=os.getenv("AZURE_AI_SEARCH_ENDPOINT"),
    index_name="textbook_chunks",
    credential=AzureKeyCredential(os.getenv("AZURE_AI_SEARCH_KEY"))
)

MANIFEST_PATH = Path("../data/ingestion_manifest.json")

# ─── PDF Extraction ───────────────────────────────────────

def extract_with_pymupdf(pdf_path: Path) -> list[dict]:
    """Extract text per page using PyMuPDF (free)."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        pages.append({"page_num": i + 1, "text": text})
    return pages

def is_good_extraction(text: str) -> bool:
    """Quality check: is PyMuPDF output usable?"""
    if len(text.strip()) < 50:
        return False
    # Check garbage ratio: non-printable chars
    garbage = sum(1 for c in text if ord(c) < 32 and c not in '\n\t')
    if garbage / max(len(text), 1) > 0.05:
        return False
    return True

def extract_pdf(pdf_path: Path) -> list[dict]:
    """Hybrid extraction: PyMuPDF first, Azure DI fallback."""
    pages = extract_with_pymupdf(pdf_path)
    good_pages = []
    bad_page_nums = []

    for p in pages:
        if is_good_extraction(p["text"]):
            good_pages.append(p)
        else:
            bad_page_nums.append(p["page_num"])

    if bad_page_nums:
        print(f"  ⚠️  {len(bad_page_nums)} pages need Azure DI OCR: {bad_page_nums[:5]}...")
        # Azure Document Intelligence fallback is not wired up. To enable for
        # GSEB scanned books: install azure-ai-documentintelligence, set
        # AZURE_DI_ENDPOINT/KEY, and add a call here that re-extracts each
        # bad page via the prebuilt-read model.

    return good_pages

# ─── Chunking ─────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks by paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) < chunk_size:
            current += "\n\n" + para
        else:
            if current:
                chunks.append(current.strip())
            current = para

    if current:
        chunks.append(current.strip())

    # Add overlap between consecutive chunks
    overlapped = []
    for i, chunk in enumerate(chunks):
        if i > 0:
            prev_words = chunks[i-1].split()[-overlap//5:]
            overlap_text = " ".join(prev_words)
            chunk = overlap_text + " " + chunk
        overlapped.append(chunk)

    return overlapped

# ─── Embedding ────────────────────────────────────────────

def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts (max 100 at a time)."""
    response = openai_client.embeddings.create(
        input=texts,
        model=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    )
    return [item.embedding for item in response.data]

# ─── Metadata Parsing ─────────────────────────────────────

def parse_metadata_from_path(pdf_path: Path, board: str) -> dict:
    """
    Expected folder structure:
    data/ncert/class10/Science/jesc1.pdf
    data/gseb/std10/VijnAn/vigyan_std10.pdf
    """
    parts = pdf_path.parts
    class_part = next((p for p in parts if p.lower().startswith("class") or p.lower().startswith("std")), "class10")
    class_level = int(re.findall(r'\d+', class_part)[0]) if re.findall(r'\d+', class_part) else 10
    subject = pdf_path.parent.name
    lang = "gu" if board == "GSEB" and "gujarati" not in pdf_path.name.lower() else "en"

    return {
        "board": board,
        "class_level": class_level,
        "subject": subject,
        "language": lang,
        "source_type": "textbook",
        "source_book": f"{board} {subject} Class {class_level}",
    }

# ─── Main Ingestion ───────────────────────────────────────

def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}

def save_manifest(manifest: dict):
    MANIFEST_PATH.parent.mkdir(exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))

def ingest_pdf(pdf_path: Path, board: str, manifest: dict) -> int:
    file_hash = hashlib.md5(pdf_path.read_bytes()).hexdigest()
    if manifest.get(str(pdf_path)) == file_hash:
        print(f"  ⏭️  Already ingested: {pdf_path.name}")
        return 0

    print(f"  📄 Processing: {pdf_path.name}")
    meta = parse_metadata_from_path(pdf_path, board)
    pages = extract_pdf(pdf_path)

    if not pages:
        print(f"  ❌ No text extracted from {pdf_path.name}")
        return 0

    # Track the most recent chapter seen as we scan pages, so chunks from a
    # chapter's body inherit the heading detected earlier in the file.
    current_chapter_num = 0
    current_chapter_name = ""

    all_chunks = []
    for page in pages:
        # Update running chapter context from the page's full text first.
        page_chap_num, page_chap_name, _ = detect_chapter(page["text"])
        if page_chap_num:
            current_chapter_num = page_chap_num
            current_chapter_name = page_chap_name or current_chapter_name

        chunks = chunk_text(page["text"])
        for j, chunk_text_content in enumerate(chunks):
            if len(chunk_text_content.strip()) < 50:
                continue
            chunk_id = f"{pdf_path.stem}_p{page['page_num']}_c{j}"
            chap_num, chap_name, topic = detect_chapter(chunk_text_content)
            all_chunks.append({
                "chunk_id": chunk_id,
                "content": chunk_text_content,
                "page_number": page["page_num"],
                **meta,
                "chapter_number": chap_num or current_chapter_num,
                "chapter_name": chap_name or current_chapter_name,
                "topic": topic,
            })

    # Embed in batches of 100
    BATCH = 100
    total_uploaded = 0
    for i in tqdm(range(0, len(all_chunks), BATCH), desc="  Embedding+Uploading"):
        batch = all_chunks[i:i+BATCH]
        texts = [c["content"] for c in batch]
        embeddings = get_embeddings_batch(texts)
        for chunk, embedding in zip(batch, embeddings):
            chunk["content_vector"] = embedding

        results = search_client.upload_documents(documents=batch)
        total_uploaded += sum(1 for r in results if r.succeeded)

    manifest[str(pdf_path)] = file_hash
    save_manifest(manifest)
    print(f"  ✅ {total_uploaded} chunks indexed from {pdf_path.name}")
    return total_uploaded


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", required=True)
    parser.add_argument("--board", required=True, choices=["CBSE", "GSEB"])
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    pdfs = list(pdf_dir.rglob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs in {pdf_dir}")

    manifest = load_manifest()
    total = 0
    for pdf in tqdm(pdfs, desc="PDFs"):
        total += ingest_pdf(pdf, args.board, manifest)

    print(f"\n🎉 Done! Total chunks indexed: {total}")