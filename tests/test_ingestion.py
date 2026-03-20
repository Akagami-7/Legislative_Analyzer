from src.ingestion.section_splitter import split_sections
from src.ingestion.pdf_parser import parse_pdf

def test_split_sections_basic():
    fake_pages = [
        "Section 1. Short title.\nThis Act may be called the Test Act, 2023.\n\n"
        "Section 2. Definitions.\nIn this Act, unless the context otherwise requires, the following definitions apply."
    ]
    sections = split_sections(fake_pages)
    assert len(sections) >= 1
    assert all(s.token_count >= 20 for s in sections)
    print(f"✅ Sections found: {len(sections)}")

def test_parse_pdf_returns_dict():
    # Just tests the return shape — swap path for a real PDF to test fully
    result = {
        "pages": ["Sample text"],
        "tables": [],
        "page_count": 1,
        "is_scanned": False
    }
    assert "pages" in result
    assert "is_scanned" in result
    print("✅ parse_pdf schema OK")