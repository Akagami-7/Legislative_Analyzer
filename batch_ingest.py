import json
import os
import sys
import time
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.pdf_parser import parse_pdf
from src.ingestion.ocr_engine import run_ocr
from src.ingestion.section_splitter import split_sections
from src.ingestion.ner_pipeline import extract_entities
from src.ingestion.scraper import scrape_bill
from src.shared_schemas import IngestedBill

# ── Output folder ──────────────────────────────────
OUTPUT_DIR = "ingested_bills"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── All 15 bills ───────────────────────────────────
BILLS = [
    {"name": "rti_act_2005",                     "search": "RTI Act 2005"},
    {"name": "consumer_protection_act_2019",      "search": "Consumer Protection Act 2019"},
    {"name": "forest_rights_act_2006",            "search": "Forest Rights Act 2006"},
    {"name": "code_on_wages_2019",                "search": "Code on Wages 2019"},
    {"name": "industrial_relations_code_2020",    "search": "Industrial Relations Code 2020"},
    {"name": "national_medical_commission_2019",  "search": "National Medical Commission Act 2019"},
    {"name": "bharatiya_nagarik_suraksha_2023",   "search": "Bharatiya Nagarik Suraksha"},
    {"name": "bharatiya_sakshya_adhiniyam_2023",  "search": "Bharatiya Sakshya"},
    {"name": "telecommunications_act_2023",       "search": "Telecommunications Act 2023"},
    {"name": "it_act_2000",                       "search": "IT Act 2000"},
    {"name": "right_to_education_act_2009",       "search": "Right to Education Act 2009"},
    {"name": "persons_with_disabilities_act_2016","search": "Persons with Disabilities Act 2016"},
    {"name": "jan_vishwas_act_2023",              "search": "Jan Vishwas Act 2023"},
    {"name": "competition_act_2002",              "search": "Competition Act 2002"},
]
def ingest_bill(bill_name: str, pdf_path: str) -> dict:
    parsed = parse_pdf(pdf_path)

    if parsed["is_scanned"]:
        print(f"    📸 Scanned PDF — running OCR...")
        parsed["pages"] = run_ocr(pdf_path)

    sections = split_sections(parsed["pages"])
    entities = extract_entities(sections)

    # ── Convert tables List[List] → List[dict] ────
    clean_tables = []
    for table in parsed["tables"]:
        if not table or not isinstance(table, list) or len(table) < 2:
            continue
        headers = [
            str(h).strip() if h is not None else f"col_{i}"
            for i, h in enumerate(table[0])
        ]
        for row in table[1:]:
            if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                continue
            row_dict = {
                headers[i]: str(cell).strip() if cell is not None else ""
                for i, cell in enumerate(row)
                if i < len(headers)
            }
            if any(v for v in row_dict.values()):
                clean_tables.append(row_dict)

    bill = IngestedBill(
        bill_id=bill_name,
        source_url=pdf_path,
        page_count=parsed["page_count"],
        sections=sections,
        total_token_count=sum(s.token_count for s in sections),
        has_tables=len(clean_tables) > 0,
        tables=clean_tables
    )

    output = bill.model_dump()
    output["entities"] = entities
    return output

def run_batch():
    """Loop through all 15 bills and ingest each one"""

    results = {
        "success": [],
        "failed": []
    }

    print("=" * 60)
    print(f"BATCH INGESTION — {len(BILLS)} bills")
    print("=" * 60)

    for i, bill in enumerate(BILLS, 1):
        name = bill["name"]
        search = bill["search"]
        output_path = os.path.join(OUTPUT_DIR, f"{name}.json")

        print(f"\n[{i}/{len(BILLS)}] {name}")
        print(f"  🔍 Searching: {search}")

        # Skip if already ingested
        if os.path.exists(output_path):
            print(f"  ⏭️  Already exists — skipping")
            results["success"].append(name)
            continue

        try:
            # Download PDF
            pdf_path = scrape_bill(search)
            print(f"  ✅ Downloaded PDF")

            # Ingest
            output = ingest_bill(name, pdf_path)

            # Save JSON
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            print(f"  ✅ Saved: {output_path}")
            print(f"     Sections : {len(output['sections'])}")
            print(f"     Tokens   : {output['total_token_count']:,}")
            print(f"     Pages    : {output['page_count']}")

            results["success"].append(name)

            # Be polite to servers
            time.sleep(2)

        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            traceback.print_exc()
            results["failed"].append({
                "name": name,
                "error": str(e)
            })
            # Continue with next bill even if one fails
            continue

    # ── Final summary ──────────────────────────────
    print("\n" + "=" * 60)
    print("BATCH COMPLETE")
    print("=" * 60)
    print(f"  ✅ Success : {len(results['success'])}/{len(BILLS)}")
    print(f"  ❌ Failed  : {len(results['failed'])}/{len(BILLS)}")

    if results["failed"]:
        print("\nFailed bills:")
        for f in results["failed"]:
            print(f"  - {f['name']}: {f['error']}")

    # Save batch report
    with open("batch_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📊 Report saved: batch_report.json")

    return results


if __name__ == "__main__":
    run_batch()