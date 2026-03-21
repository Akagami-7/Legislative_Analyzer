import requests
import time
import tempfile
import os
from bs4 import BeautifulSoup

# ── Selenium imports ───────────────────────────────
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️  Selenium not installed — run: pip install selenium webdriver-manager")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

KNOWN_BILLS = {
    "dpdp": "https://egazette.gov.in/WriteReadData/2023/247654.pdf",
    "dpdp act": "https://egazette.gov.in/WriteReadData/2023/247654.pdf",
    "dpdp act 2023": "https://egazette.gov.in/WriteReadData/2023/247654.pdf",
    "digital personal data protection": "https://egazette.gov.in/WriteReadData/2023/247654.pdf",
    "bharatiya nyaya sanhita": "https://egazette.gov.in/WriteReadData/2023/248078.pdf",
    "bns 2023": "https://egazette.gov.in/WriteReadData/2023/248078.pdf",
    "bharatiya nagarik suraksha": "https://egazette.gov.in/WriteReadData/2023/248079.pdf",
    "bnss 2023": "https://egazette.gov.in/WriteReadData/2023/248079.pdf",
    "bharatiya sakshya": "https://egazette.gov.in/WriteReadData/2023/248080.pdf",
    "bsb 2023": "https://egazette.gov.in/WriteReadData/2023/248080.pdf",
    "telecommunications": "https://egazette.gov.in/WriteReadData/2023/247860.pdf",
    "telecommunications act 2023": "https://egazette.gov.in/WriteReadData/2023/247860.pdf",
}


# ════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ════════════════════════════════════════════════════

def scrape_bill(search_term: str) -> str:
    """
    Downloads a bill PDF and returns local file path.
    Accepts direct PDF URL, PRS page URL, or search term.
    """

    # Case 1 — Direct PDF URL
    if search_term.startswith("http") and search_term.endswith(".pdf"):
        print(f"🔗 Direct PDF URL detected")
        return _download_pdf(search_term)

    # Case 2 — Known bills fast path
    key = search_term.lower().strip()
    for known_key, known_url in KNOWN_BILLS.items():
        if known_key in key:
            print(f"✅ Found in known bills index: {known_url}")
            try:
                return _download_pdf(known_url)
            except Exception as e:
                print(f"  ⚠️  Known URL failed: {e}, trying dynamic...")
                break

    # Case 3 — Direct PRS page URL
    if search_term.startswith("http"):
        print(f"🌐 Direct page URL detected")
        try:
            return _extract_pdf_static(search_term)
        except ValueError:
            print(f"  ⚠️  Static failed, trying dynamic...")
            return _extract_pdf_dynamic(search_term)

    # Case 4 — Static search
    try:
        return _search_prs_static(search_term)
    except ValueError:
        print(f"  ⚠️  Static search failed, trying Selenium...")

    # Case 5 — Dynamic Selenium search
    try:
        return _search_prs_dynamic(search_term)
    except Exception as e:
        print(f"  ⚠️  Dynamic search also failed: {e}")

    raise ValueError(
        f"Could not find PDF for: '{search_term}'\n"
        f"All strategies failed. Options:\n"
        f"  1. Pass a direct PDF URL\n"
        f"  2. Pass the PRS India bill page URL\n"
        f"  3. Add it to KNOWN_BILLS in scraper.py"
    )


# ════════════════════════════════════════════════════
# STRATEGY 1 — STATIC (BeautifulSoup)
# ════════════════════════════════════════════════════

def _search_prs_static(search_term: str) -> str:
    """Search PRS India using requests + BeautifulSoup"""

    search_url = (
        f"https://prsindia.org/billtrack"
        f"?search={search_term.replace(' ', '+')}"
    )
    print(f"  📡 Static search: {search_url}")
    time.sleep(1)

    response = requests.get(search_url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    pdf_link = soup.find("a", href=lambda h: h and ".pdf" in str(h).lower())
    if pdf_link:
        pdf_url = pdf_link["href"]
        if not pdf_url.startswith("http"):
            pdf_url = "https://prsindia.org" + pdf_url
        print(f"  ✅ Static found PDF: {pdf_url}")
        return _download_pdf(pdf_url)

    raise ValueError(f"Static search found no PDF for: {search_term}")


def _extract_pdf_static(page_url: str) -> str:
    """Visit a bill page statically and extract PDF link"""

    print(f"  📄 Static page visit: {page_url}")
    time.sleep(1)

    response = requests.get(page_url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text().lower()
        if ".pdf" in href.lower():
            pdf_url = href if href.startswith("http") else "https://prsindia.org" + href
            print(f"  ✅ Static found PDF: {pdf_url}")
            return _download_pdf(pdf_url)
        if any(k in text for k in ["bill text", "original bill", "download"]):
            pdf_url = href if href.startswith("http") else "https://prsindia.org" + href
            print(f"  ✅ Static found bill link: {pdf_url}")
            return _download_pdf(pdf_url)

    raise ValueError(f"Static scraping found no PDF on: {page_url}")


# ════════════════════════════════════════════════════
# STRATEGY 2 — DYNAMIC (Selenium)
# Handles JavaScript-rendered pages
# ════════════════════════════════════════════════════

def _get_driver():
    """Create a headless Chrome driver"""
    if not SELENIUM_AVAILABLE:
        raise RuntimeError(
            "Selenium not installed.\n"
            "Run: pip install selenium webdriver-manager"
        )
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def _search_prs_dynamic(search_term: str) -> str:
    """Use Selenium to search PRS India dynamically"""

    search_url = (
        f"https://prsindia.org/billtrack"
        f"?search={search_term.replace(' ', '+')}"
    )
    print(f"  🤖 Dynamic search: {search_url}")

    driver = _get_driver()
    try:
        driver.get(search_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )
        time.sleep(2)

        links = driver.find_elements(By.TAG_NAME, "a")

        # Look for direct PDF links first
        for link in links:
            href = link.get_attribute("href") or ""
            if ".pdf" in href.lower():
                print(f"  ✅ Dynamic found PDF: {href}")
                driver.quit()
                return _download_pdf(href)

        # Look for bill page links matching search words
        search_words = search_term.lower().split()
        bill_urls = []
        for link in links:
            href = link.get_attribute("href") or ""
            text = link.text.lower()
            if "billtrack" in href and any(w in text for w in search_words):
                bill_urls.append(href)

        # Visit each bill page and look for PDF
        for bill_url in bill_urls[:3]:
            print(f"  → Dynamic visiting: {bill_url}")
            driver.get(bill_url)
            time.sleep(2)

            page_links = driver.find_elements(By.TAG_NAME, "a")
            for link in page_links:
                href = link.get_attribute("href") or ""
                text = link.text.lower()
                if ".pdf" in href.lower():
                    pdf_url = href if href.startswith("http") else "https://prsindia.org" + href
                    print(f"  ✅ Dynamic found PDF: {pdf_url}")
                    driver.quit()
                    return _download_pdf(pdf_url)
                if any(k in text for k in ["bill text", "original bill", "download", "view bill"]):
                    pdf_url = href if href.startswith("http") else "https://prsindia.org" + href
                    print(f"  ✅ Dynamic found bill link: {pdf_url}")
                    driver.quit()
                    return _download_pdf(pdf_url)

    finally:
        driver.quit()

    raise ValueError(f"Dynamic search found no PDF for: {search_term}")


def _extract_pdf_dynamic(page_url: str) -> str:
    """Visit a bill page dynamically and extract PDF link"""

    print(f"  🤖 Dynamic page visit: {page_url}")
    driver = _get_driver()

    try:
        driver.get(page_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )
        time.sleep(2)

        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href") or ""
            text = link.text.lower()
            if ".pdf" in href.lower():
                pdf_url = href if href.startswith("http") else "https://prsindia.org" + href
                print(f"  ✅ Dynamic found PDF: {pdf_url}")
                driver.quit()
                return _download_pdf(pdf_url)
            if any(k in text for k in ["bill text", "original bill", "download", "view bill"]):
                pdf_url = href if href.startswith("http") else "https://prsindia.org" + href
                print(f"  ✅ Dynamic found bill link: {pdf_url}")
                driver.quit()
                return _download_pdf(pdf_url)

    finally:
        driver.quit()

    raise ValueError(f"Dynamic scraping found no PDF on: {page_url}")


# ════════════════════════════════════════════════════
# DOWNLOADER
# ════════════════════════════════════════════════════

def _download_pdf(url: str) -> str:
    """Download PDF from URL and save to temp file"""

    print(f"  ⬇️  Downloading: {url}")
    time.sleep(1)

    response = requests.get(url, headers=HEADERS, timeout=30, stream=True)
    response.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    for chunk in response.iter_content(chunk_size=8192):
        tmp.write(chunk)
    tmp.close()

    size_kb = os.path.getsize(tmp.name) // 1024
    print(f"  ✅ Saved to: {tmp.name} ({size_kb} KB)")
    return tmp.name