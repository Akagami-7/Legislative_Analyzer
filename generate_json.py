import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.pdf_parser import parse_pdf
from src.ingestion.ocr_engine import run_ocr
from src.ingestion.section_splitter import split_sections
from src.ingestion.ner_pipeline import extract_entities
from src.shared_schemas import IngestedBill

def ingest_bill(pdf_path: str) -> dict:
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
        bill_id="bharatiya_nyaya_sanhita_2023",
        source_url=pdf_path,
        page_count=parsed["page_count"],
        sections=sections,
        total_token_count=sum(s.token_count for s in sections),
        has_tables=len(parsed["tables"]) > 0,
        tables=parsed["tables"]
    )

    # Step 6 - Combine bill + entities into final output
    output = bill.model_dump()
    output["entities"] = entities  # ← this adds NER to JSON

    return output

# Run it
result = ingest_bill("bns_2023.pdf")

print(f"✅ Sections found    : {len(result['sections'])}")
print(f"✅ Total tokens      : {result['total_token_count']}")
print(f"✅ Pages             : {result['page_count']}")
print(f"✅ Acts referenced   : {result['entities']['acts_referenced'][:3]}")
print(f"✅ Dates found       : {result['entities']['dates'][:3]}")
print(f"✅ Ministries found  : {result['entities']['ministries'][:3]}")
print(f"✅ Acts referenced   : {result['entities']['acts_referenced'][:3]}")
print(f"✅ Dates found       : {result['entities']['dates'][:3]}")
print(f"✅ Amounts found     : {result['entities']['monetary_amounts'][:3]}")
print(f"✅ Punishments found : {result['entities']['punishments'][:3]}")
# Save
with open("ingested_bill.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("✅ ingested_bill.json saved!")