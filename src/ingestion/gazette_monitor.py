import requests
import schedule
import time
import os
import json
from datetime import datetime
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
GAZETTE_URL = "https://egazette.gov.in"
SEEN_FILE = "gazette_seen.json"

def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

def check_new_bills():
    print(f"[{datetime.now()}] Checking egazette for new bills...")
    seen = load_seen()
    new_found = []

    try:
        response = requests.get(GAZETTE_URL, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        # Find all PDF links
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" in href.lower() and href not in seen:
                text = a.get_text().lower()
                # Filter for bills and acts only
                if any(k in text for k in ["act", "bill", "code", "ordinance"]):
                    pdf_url = href if href.startswith("http") else GAZETTE_URL + href
                    new_found.append(pdf_url)
                    seen.add(href)
                    print(f"  🆕 New bill found: {pdf_url}")

        save_seen(seen)
        print(f"  Found {len(new_found)} new bills")

        # Auto ingest new bills
        if new_found:
            _auto_ingest(new_found)

    except Exception as e:
        print(f"  ❌ Monitor error: {e}")

def _auto_ingest(pdf_urls: list):
    """Auto ingest newly found PDFs"""
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ingestion.pdf_parser import parse_pdf
    from ingestion.section_splitter import split_sections
    from ingestion.ner_pipeline import extract_entities
    from ingestion.scraper import _download_pdf

    os.makedirs("ingested_bills", exist_ok=True)

    for url in pdf_urls:
        try:
            print(f"  ⬇️  Auto ingesting: {url}")
            pdf_path = _download_pdf(url)
            parsed = parse_pdf(pdf_path)
            sections = split_sections(parsed["pages"])
            entities = extract_entities(sections)

            bill_name = url.split("/")[-1].replace(".pdf", "").lower()
            bill_name = bill_name.replace("%20", "_").replace(" ", "_")

            output = {
                "bill_id": bill_name,
                "source_url": url,
                "page_count": parsed["page_count"],
                "sections": [s.model_dump() for s in sections],
                "total_token_count": sum(s.token_count for s in sections),
                "has_tables": len(parsed["tables"]) > 0,
                "entities": entities,
                "ingested_at": datetime.now().isoformat()
            }

            out_path = f"ingested_bills/{bill_name}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            print(f"  ✅ Saved: {out_path}")

        except Exception as e:
            print(f"  ❌ Failed to ingest {url}: {e}")

def monitor():
    """Start 24-hour monitoring loop"""
    print("🔍 Gazette monitor started — checking every 24 hours")
    check_new_bills()  # run once immediately
    schedule.every(24).hours.do(check_new_bills)
    while True:
        schedule.run_pending()
        time.sleep(3600)

if __name__ == "__main__":
    monitor()