import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.ingestion.scraper import KNOWN_BILLS

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/pdf",
    "Referer": "https://www.indiacode.nic.in/"
}

TIMEOUT = 15


def is_pdf_response(response):
    content_type = response.headers.get("Content-Type", "").lower()
    return "application/pdf" in content_type


def fetch_url(url):
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            allow_redirects=True,
            timeout=TIMEOUT
        )
        return r
    except Exception as e:
        return e


def main():
    # ── Deduplicate URLs ─────────────────────────
    seen_urls = {}
    for key, url in KNOWN_BILLS.items():
        if url not in seen_urls:
            seen_urls[url] = key

    print("=" * 70)
    print(f"{'BILL':<45} {'SIZE':>8}  STATUS")
    print("=" * 70)

    ok = 0
    fail = 0
    not_pdf = 0

    results = []

    for url, name in seen_urls.items():
        result = fetch_url(url)

        if isinstance(result, Exception):
            print(f"{name:<45} {'':>8}  ❌ ERROR: {str(result)[:40]}")
            fail += 1
            results.append((name, url, "fail"))
            continue

        r = result

        # 🔥 IMPORTANT: treat redirected success also as valid
        if r.status_code in [200]:
            size_kb = int(r.headers.get("Content-Length", 0)) // 1024

            if is_pdf_response(r) or r.content[:4] == b"%PDF":
                print(f"{name:<45} {size_kb:>6} KB  ✅ PDF")
                ok += 1
                results.append((name, url, "ok"))
            else:
                print(f"{name:<45} {size_kb:>6} KB  ⚠️ NOT PDF")
                not_pdf += 1
                results.append((name, url, "not_pdf"))

        else:
            print(f"{name:<45} {'':>8}  ❌ HTTP {r.status_code}")
            fail += 1
            results.append((name, url, "fail"))

    print("=" * 70)
    print(f"✅ Valid PDFs  : {ok}")
    print(f"⚠️  Not PDF    : {not_pdf}")
    print(f"❌ Failed      : {fail}")
    print(f"Total URLs    : {ok + not_pdf + fail}")
    print("=" * 70)

    # ── Show issues ──────────────────────────────
    if not_pdf > 0 or fail > 0:
        print("\n🔧 NEEDS FIXING:")
        for name, url, status in results:
            if status != "ok":
                print(f"  - {name}")
                print(f"    URL: {url}")


if __name__ == "__main__":
    main()