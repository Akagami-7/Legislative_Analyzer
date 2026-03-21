import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.pdf_parser import parse_pdf
from src.ingestion.ocr_engine import run_ocr
from src.ingestion.section_splitter import split_sections
from src.ingestion.ner_pipeline import extract_entities
from src.shared_schemas import IngestedBill

def ingest_bill(pdf_path: str) -> IngestedBill:
    # Step 1 - Parse PDF
    parsed = parse_pdf(pdf_path)

    # Step 2 - OCR only if scanned
    if parsed["is_scanned"]:
        parsed["pages"] = run_ocr(pdf_path)

    # Step 3 - Split into sections
    sections = split_sections(parsed["pages"])

    # Step 4 - Extract entities
    entities = extract_entities(sections)
    print(f"Entities found: {entities}")

    # Step 5 - Build the final object
    return IngestedBill(
          bill_id="bharatiya_nyaya_sanhita_2023",
          source_url=pdf_path,
          page_count=parsed["page_count"],
          sections=sections,
          total_token_count=sum(s.token_count for s in sections),
          has_tables=len(parsed["tables"]) > 0,
          tables=[{"row": row} for row in parsed["tables"]]
          )

# Run it
result = ingest_bill("bns_2023.pdf")

print(f"✅ Sections found: {len(result.sections)}")
print(f"✅ Total tokens: {result.total_token_count}")
print(f"✅ Pages: {result.page_count}")

# Save the JSON file
with open("ingested_bill.json", "w", encoding="utf-8") as f:
    f.write(result.model_dump_json(indent=2))

print("✅ ingested_bill.json saved successfully!")