import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.pdf_parser import parse_pdf
from src.ingestion.section_splitter import split_sections
from src.ingestion.scraper import scrape_bill

# Bills with low section counts
PROBLEM_BILLS = [
    ("telecommunications_act_2023",  "Telecommunications Act 2023"),
    ("bharatiya_nagarik_suraksha",   "Bharatiya Nagarik Suraksha"),
    ("jan_vishwas_act_2023",         "Jan Vishwas Act 2023"),
    ("industrial_relations_code",    "Industrial Relations Code 2020"),
    ("national_medical_commission",  "National Medical Commission Act 2019"),
]

for name, search in PROBLEM_BILLS:
    print(f"\n{'='*50}")
    print(f"BILL: {name}")
    try:
        pdf_path = scrape_bill(search)
        parsed = parse_pdf(pdf_path)
        print(f"  Pages        : {parsed['page_count']}")
        print(f"  Is scanned   : {parsed['is_scanned']}")
        print(f"  Avg chars/pg : {sum(len(p) for p in parsed['pages']) // max(parsed['page_count'],1)}")
        print(f"  First 300 chars of page 1:")
        print(f"  {parsed['pages'][0][:300]}")
        print(f"  ---")
        print(f"  First 300 chars of page 3:")
        print(f"  {parsed['pages'][2][:300] if len(parsed['pages']) > 2 else 'N/A'}")

        sections = split_sections(parsed["pages"])
        print(f"  Sections found: {len(sections)}")
        for s in sections[:3]:
            print(f"    - [{s.page_number}] {s.section_title[:60]}")
    except Exception as e:
        print(f"  ERROR: {e}")