import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SAMPLE_PDF = os.path.join(os.path.dirname(__file__), "sample.pdf")

# ─────────────────────────────────────────────────
# TEST 1: PDF PARSER — actually calls parse_pdf()
# ─────────────────────────────────────────────────

class TestPdfParser:

    def test_parse_pdf_actually_runs(self):
        """Actually calls parse_pdf on a real PDF file"""
        from src.ingestion.pdf_parser import parse_pdf
        result = parse_pdf(SAMPLE_PDF)
        assert isinstance(result, dict)

    def test_parse_pdf_has_pages(self):
        """pages must be a non-empty list"""
        from src.ingestion.pdf_parser import parse_pdf
        result = parse_pdf(SAMPLE_PDF)
        assert len(result["pages"]) > 0

    def test_parse_pdf_page_count_matches(self):
        """page_count must equal len(pages)"""
        from src.ingestion.pdf_parser import parse_pdf
        result = parse_pdf(SAMPLE_PDF)
        assert result["page_count"] == len(result["pages"])

    def test_parse_pdf_is_scanned_is_bool(self):
        """is_scanned must be a boolean"""
        from src.ingestion.pdf_parser import parse_pdf
        result = parse_pdf(SAMPLE_PDF)
        assert isinstance(result["is_scanned"], bool)

    def test_parse_pdf_pages_are_strings(self):
        """Every page must be a string"""
        from src.ingestion.pdf_parser import parse_pdf
        result = parse_pdf(SAMPLE_PDF)
        assert all(isinstance(p, str) for p in result["pages"])

    def test_parse_pdf_tables_is_list(self):
        """tables must be a list"""
        from src.ingestion.pdf_parser import parse_pdf
        result = parse_pdf(SAMPLE_PDF)
        assert isinstance(result["tables"], list)


# ─────────────────────────────────────────────────
# TEST 2: SECTION SPLITTER — page numbers fix
# ─────────────────────────────────────────────────

class TestSectionSplitter:

    def test_sections_not_empty(self):
        """Must find at least 1 section from real PDF"""
        from src.ingestion.pdf_parser import parse_pdf
        from src.ingestion.section_splitter import split_sections
        result = parse_pdf(SAMPLE_PDF)
        sections = split_sections(result["pages"])
        assert len(sections) >= 1

    def test_page_numbers_not_all_one(self):
        """Page numbers must NOT all be 1 — this was the bug"""
        from src.ingestion.pdf_parser import parse_pdf
        from src.ingestion.section_splitter import split_sections
        result = parse_pdf(SAMPLE_PDF)
        sections = split_sections(result["pages"])
        page_numbers = [s.page_number for s in sections]
        # At least one section should be on a page > 1
        assert max(page_numbers) > 1, \
            f"All sections show page_number=1, fix not working! Pages: {page_numbers}"

    def test_no_noise_sections(self):
        """No section should have less than 20 tokens"""
        from src.ingestion.pdf_parser import parse_pdf
        from src.ingestion.section_splitter import split_sections
        result = parse_pdf(SAMPLE_PDF)
        sections = split_sections(result["pages"])
        for s in sections:
            assert s.token_count >= 20

    def test_section_ids_slugified(self):
        """Section IDs must have no special characters"""
        import re
        from src.ingestion.pdf_parser import parse_pdf
        from src.ingestion.section_splitter import split_sections
        result = parse_pdf(SAMPLE_PDF)
        sections = split_sections(result["pages"])
        for s in sections:
            assert re.match(r'^[a-z0-9_]+$', s.section_id), \
                f"Bad section_id: {s.section_id}"

    def test_detects_individual_section_numbers(self):
        """Must split on individual section numbers like 33. 34."""
        from src.ingestion.section_splitter import split_sections
        fake_pages = [
            "33. Punishment for theft.\nWhoever commits theft shall be punished.\n\n"
            "34. Acts done by several persons.\nWhen a criminal act is done by several persons.\n\n"
            "35. When such an act is criminal.\nAn act is criminal when done with intent.\n\n"
        ]
        sections = split_sections(fake_pages)
        assert len(sections) >= 3, \
            f"Expected 3+ sections from numbered list, got {len(sections)}"


# ─────────────────────────────────────────────────
# TEST 3: NER PIPELINE — must return real entities
# ─────────────────────────────────────────────────

class TestNerPipeline:

    def test_ner_returns_all_keys(self):
        """extract_entities must return all 5 required keys"""
        from src.ingestion.pdf_parser import parse_pdf
        from src.ingestion.section_splitter import split_sections
        from src.ingestion.ner_pipeline import extract_entities
        result = parse_pdf(SAMPLE_PDF)
        sections = split_sections(result["pages"])
        entities = extract_entities(sections)
        assert "ministries" in entities
        assert "acts_referenced" in entities
        assert "dates" in entities
        assert "monetary_amounts" in entities
        assert "states" in entities

    def test_ner_not_all_empty(self):
        """At least one entity category must have results"""
        from src.ingestion.pdf_parser import parse_pdf
        from src.ingestion.section_splitter import split_sections
        from src.ingestion.ner_pipeline import extract_entities
        result = parse_pdf(SAMPLE_PDF)
        sections = split_sections(result["pages"])
        entities = extract_entities(sections)
        total = sum(len(v) for v in entities.values())
        assert total > 0, \
            f"NER found nothing! All empty: {entities}"

    def test_ner_no_duplicates(self):
        """All entity lists must be deduplicated"""
        from src.ingestion.pdf_parser import parse_pdf
        from src.ingestion.section_splitter import split_sections
        from src.ingestion.ner_pipeline import extract_entities
        result = parse_pdf(SAMPLE_PDF)
        sections = split_sections(result["pages"])
        entities = extract_entities(sections)
        for key, value in entities.items():
            assert len(value) == len(set(value)), \
                f"Duplicates found in {key}: {value}"


# ─────────────────────────────────────────────────
# TEST 4: SCRAPER — actually downloads from PRS
# ─────────────────────────────────────────────────

class TestScraper:

    def test_scraper_downloads_pdf(self):
        """scrape_bill must return a real local PDF path"""
        from src.ingestion.scraper import scrape_bill
        path = scrape_bill("DPDP Act 2023")
        assert path.endswith(".pdf"), \
            f"Expected a .pdf path, got: {path}"
        assert os.path.exists(path), \
            f"File not found at path: {path}"
        assert os.path.getsize(path) > 1000, \
            f"Downloaded file too small, probably failed: {path}"
        print(f"✅ Downloaded to: {path}")

    def test_scraper_direct_url(self):
        """scrape_bill must handle direct PDF URLs"""
        from src.ingestion.scraper import scrape_bill
        url = "https://egazette.gov.in/WriteReadData/2023/247654.pdf"
        path = scrape_bill(url)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 1000
        print(f"✅ Direct URL downloaded to: {path}")