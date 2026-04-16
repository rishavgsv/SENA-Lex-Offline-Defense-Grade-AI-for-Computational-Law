import fitz  # PyMuPDF
import logging
import re
from typing import List, Dict
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logging.warning("spacy model 'en_core_web_sm' not found. Falling back to regex-only.")
    nlp = None

def extract_legal_hierarchies(text: str, page_num: int, filename: str) -> List[Dict]:
    """Parse text aggressively targeting legal clause structures instead of raw paragraphs."""
    chunks = []
    
    # Regex to detect clause heads like '1. ', '1.1 ', 'Article 4', 'Section II'
    clause_pattern = re.compile(r"^\s*((?:Section|Article|Clause)\s+[A-Z0-9]+|\d+(?:\.\d+)*\s*\.?)\s*(.*)", re.IGNORECASE)
    
    lines = text.split('\n')
    current_clause_id = "General"
    current_clause_title = ""
    buffer = []
    para_id = 0
    
    def flush_buffer():
        nonlocal buffer, para_id
        if not buffer: return
        content = " ".join(buffer).strip()
        if len(content) > 20: 
            clause_type = "Standard"
            if nlp:
                lower_c = content.lower()
                if "liabl" in lower_c or "indemn" in lower_c or "damag" in lower_c or "penalty" in lower_c:
                    clause_type = "Liability"
                elif "pay" in lower_c or "fee" in lower_c or "compensation" in lower_c:
                    clause_type = "Payment"
                elif "terminat" in lower_c or "cancel" in lower_c or "expire" in lower_c:
                    clause_type = "Termination"

            chunks.append({
                "text": content,
                "page_no": page_num,
                "paragraph_id": para_id,
                "document": filename,
                "clause_id": current_clause_id,
                "clause_title": current_clause_title[:100], # Keep title short
                "clause_type": clause_type
            })
            para_id += 1
        buffer.clear()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        match = clause_pattern.match(line)
        if match:
            flush_buffer()
            current_clause_id = match.group(1).strip()
            current_clause_title = match.group(2).strip()
            buffer.append(line)
        else:
            buffer.append(line)
            
    flush_buffer()
    return chunks


def _chunks_from_pdf_bytes(file_bytes: bytes, filename: str) -> List[Dict]:
    """Parse a PDF from raw bytes into clause-based chunks with metadata."""
    try:
        doc = fitz.open("pdf", file_bytes)
    except Exception as e:
        logging.error(f"Failed to open PDF '{filename}': {e}")
        return []

    chunks = []
    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text").strip()
        if not text:
            continue
        chunks.extend(extract_legal_hierarchies(text, page_num + 1, filename))
    return chunks


def _chunks_from_txt_bytes(file_bytes: bytes, filename: str) -> List[Dict]:
    """Parse a plain-text file into clause-based chunks."""
    try:
        text = file_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        logging.error(f"Failed to decode text file '{filename}': {e}")
        return []

    return extract_legal_hierarchies(text, 1, filename)


def _chunks_from_docx_bytes(file_bytes: bytes, filename: str) -> List[Dict]:
    """Parse a DOCX file into clause-based chunks."""
    try:
        import io
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
    except ImportError:
        logging.error("python-docx not installed – cannot parse .docx files. Run: pip install python-docx")
        return []
    except Exception as e:
        logging.error(f"Failed to open DOCX '{filename}': {e}")
        return []

    lines = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
    full_text = "\n".join(lines)
    return extract_legal_hierarchies(full_text, 1, filename)


def get_chunks_from_bytes(file_bytes: bytes, filename: str) -> List[Dict]:
    """
    Main entry point. Dispatches to the correct parser based on file extension.
    Supports: .pdf, .txt, .docx
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        return _chunks_from_pdf_bytes(file_bytes, filename)
    elif ext == "txt":
        return _chunks_from_txt_bytes(file_bytes, filename)
    elif ext == "docx":
        return _chunks_from_docx_bytes(file_bytes, filename)
    else:
        logging.warning(f"Unsupported file type '.{ext}' for '{filename}'. Trying as plain text.")
        return _chunks_from_txt_bytes(file_bytes, filename)
