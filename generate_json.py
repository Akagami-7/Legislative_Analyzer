import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.pdf_parser import parse_pdf
from src.ingestion.ocr_engine import run_ocr
from src.ingestion.section_splitter import split_sections
from src.ingestion.ner_pipeline import extract_entities
from src.ingestion.scraper import scrape_bill
from src.shared_schemas import IngestedBill

def ingest_bill(source: str, bill_id: str = None) -> dict:
    """
    source: either a local PDF path or a URL
    bill_id: optional name for the bill, auto-derived if not given
    """

    # If it's a URL, download it first
    if source.startswith("http"):
        print(f"⬇️  Downloading from URL: {source}")
        pdf_path = scrape_bill(source)
    else:
        pdf_path = source

    # Auto-derive bill_id from filename if not provided
    if not bill_id:
        bill_id = os.path.basename(pdf_path).replace(".pdf", "").replace(" ", "_").lower()

    # Step 1 - Parse
    parsed = parse_pdf(pdf_path)

    # Step 2 - OCR if scanned
    if parsed["is_scanned"]:
        parsed["pages"] = run_ocr(pdf_path)

    # Step 3 - Split sections
    sections = split_sections(parsed["pages"])

    # Step 4 - NER entities
    entities = extract_entities(sections)

    # Step 5 - Build IngestedBill
    bill = IngestedBill(
        bill_id=bill_id,
        source_url=source,
        page_count=parsed["page_count"],
        sections=sections,
        total_token_count=sum(s.token_count for s in sections),
        has_tables=len(parsed["tables"]) > 0,
        tables=[{"rows": t} for t in parsed["tables"]] if parsed["tables"] else []
    )

    # Step 6 - Combine bill + entities
    output = bill.model_dump()
    output["entities"] = entities

    return output


if __name__ == "__main__":
    # ── Change this to any URL or local path ──────────────────
    SOURCE  = "https://www.mha.gov.in/sites/default/files/250883_english_01042024.pdf"
    BILL_ID = "bharatiya_nyaya_sanhita_2023"
    # ──────────────────────────────────────────────────────────

    result = ingest_bill(SOURCE, BILL_ID)

    print(f"✅ Sections found    : {len(result['sections'])}")
    print(f"✅ Total tokens      : {result['total_token_count']:,}")
    print(f"✅ Pages             : {result['page_count']}")
    print(f"✅ Acts referenced   : {result['entities']['acts_referenced'][:3]}")
    print(f"✅ Amounts found     : {result['entities']['monetary_amounts'][:3]}")
    print(f"✅ Punishments found : {result['entities']['punishments'][:3]}")

    with open("ingested_bill.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("✅ ingested_bill.json saved!")