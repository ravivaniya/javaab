import os
import glob
import uuid
import json
import argparse
import logging
from tqdm import tqdm
from lib_ingestion import IngestionPipeline

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def guess_metadata(filepath: str, board: str):
    """
    Very naive metadata extraction based on textbook filename conventions.
    Extracts data safely without runtime crashes if format deviates.
    Expects format similar to: Class10_Science_Ch1_Chemical_Reactions.pdf
    """
    base = os.path.basename(filepath).replace(".pdf", "")
    parts = base.split("_")
    
    cls_level = 10
    subj = "Unknown"
    chap_num = "1"
    
    for p in parts:
        lower_p = p.lower()
        if "class" in lower_p:
            try: cls_level = int(''.join(filter(str.isdigit, p)))
            except: pass
        if "science" in lower_p or "math" in lower_p or "social" in lower_p:
            subj = p
        if "ch" in lower_p:
            chap_num = ''.join(filter(str.isdigit, p))
            
    return {
        "board": board,
        "class_level": cls_level,
        "subject": subj,
        "chapter_number": chap_num,
        "chapter_name": base,
        "language": "gu",  # Defaulting GSEB base to Gujarati native code
        "source_type": "textbook"
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", required=True)
    parser.add_argument("--board", required=True, default="GSEB")
    args = parser.parse_args()
    
    pipeline = IngestionPipeline()
    manifest_path = f"manifest_{args.board.lower()}.json"
    
    processed = set()
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            processed = set(json.load(f))
            
    pdf_files = glob.glob(os.path.join(args.pdf_dir, "**/*.pdf"), recursive=True)
    pending_files = [f for f in pdf_files if f not in processed]
    
    print(f"Found {len(pdf_files)} PDFs total. {len(pending_files)} pending ingestion.")
    
    for file_path in tqdm(pending_files, desc=f"Ingesting {args.board}"):
        try:
            meta = guess_metadata(file_path, args.board)
            pages = pipeline.extract_text_hybrid(file_path)
            
            all_chunks = []
            for page_num, text in pages:
                if not text: continue
                
                chunks = pipeline.chunk_text(text)
                for i, c in enumerate(chunks):
                    vec = pipeline.compute_embedding(c)
                    
                    doc = {
                        "chunk_id": f"chunk_{uuid.uuid4().hex[:16]}",
                        "content": c,
                        "content_vector": vec,
                        "board": meta["board"],
                        "class_level": meta["class_level"],
                        "subject": meta["subject"],
                        "chapter_number": str(meta["chapter_number"]),
                        "chapter_name": meta["chapter_name"],
                        "topic": "General", 
                        "language": meta["language"],
                        "source_type": meta["source_type"],
                        "page_number": page_num,
                        "source_book": os.path.basename(file_path)
                    }
                    all_chunks.append(doc)
            
            # Push securely to vector DB
            if all_chunks:
                pipeline.batch_upload(all_chunks)
            
            # Record Success to local manifest JSON allowing graceful resumes
            processed.add(file_path)
            with open(manifest_path, "w") as f:
                json.dump(list(processed), f)
                
        except Exception as e:
            logger.error(f"Fatal crash processing {file_path}: {e}")

if __name__ == "__main__":
    main()
