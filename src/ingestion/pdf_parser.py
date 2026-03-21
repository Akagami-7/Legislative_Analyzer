import pdfplumber
import fitz  # PyMuPDF

def parse_pdf(path: str) -> dict:
    pages, tables = [], []

    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
                tables.extend(page.extract_tables() or [])
    except Exception:
        pages = []

    # Fallback to PyMuPDF if text is too sparse
    avg_len = sum(len(p) for p in pages) / max(len(pages), 1)
    if avg_len < 100:
        doc = fitz.open(path)
        pages = [page.get_text() for page in doc]

    is_scanned = all(len(p.strip()) < 50 for p in pages)

    return {
        "pages": pages,
        "tables": tables,
        "page_count": len(pages),
        "is_scanned": is_scanned
    }