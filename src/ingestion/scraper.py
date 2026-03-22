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
    # ── DPDP Act ───────────────────────────────
    "dpdp": "https://egazette.gov.in/WriteReadData/2023/248045.pdf",
    "dpdp act": "https://egazette.gov.in/WriteReadData/2023/248045.pdf",
    "dpdp act 2023": "https://egazette.gov.in/WriteReadData/2023/248045.pdf",
    "digital personal data protection": "https://egazette.gov.in/WriteReadData/2023/248045.pdf",

    # ── Bharatiya Nyaya Sanhita ────────────────
    "bharatiya nyaya sanhita": "https://egazette.gov.in/WriteReadData/2023/248078.pdf",
    "bns 2023": "https://egazette.gov.in/WriteReadData/2023/248078.pdf",

    # ── BNSS ───────────────────────────────────
    "bharatiya nagarik suraksha": "https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf",
    "bnss 2023": "https://www.mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf",

    # ── Bharatiya Sakshya ──────────────────────
    # ── Telecommunications Act ─────────────────
    "telecommunications act 2023": "https://www.indiacode.nic.in/bitstream/123456789/20101/1/A2023-44.pdf",
    "telecommunications": "https://www.indiacode.nic.in/bitstream/123456789/20101/1/A2023-44.pdf",

    # ── Consumer Protection ────────────────────
    "consumer protection act 2019": "https://egazette.gov.in/WriteReadData/2019/210422.pdf",
    "consumer protection": "https://egazette.gov.in/WriteReadData/2019/210422.pdf",

    # ── Forest Rights ──────────────────────────
    "forest rights act 2006": "https://tribal.nic.in/FRA/data/FRARulesBook.pdf",
    "forest rights": "https://tribal.nic.in/FRA/data/FRARulesBook.pdf",

    # ── Code on Wages ──────────────────────────
    "code on wages 2019": "https://egazette.gov.in/WriteReadData/2019/210356.pdf",
    "code on wages": "https://egazette.gov.in/WriteReadData/2019/210356.pdf",

    # ── RTI Act ────────────────────────────────
    "rti act 2005": "https://prsindia.org/files/bills_acts/acts_parliament/2005/the-right-to-information-act-2005.pdf",
    "rti act": "https://prsindia.org/files/bills_acts/acts_parliament/2005/the-right-to-information-act-2005.pdf",
    "right to information": "https://prsindia.org/files/bills_acts/acts_parliament/2005/the-right-to-information-act-2005.pdf",

    # ── Land Acquisition ───────────────────────
    "land acquisition act 2013": "https://prsindia.org/files/bills_acts/acts_parliament/2013/larr-act,-2013.pdf",
    "land acquisition": "https://prsindia.org/files/bills_acts/acts_parliament/2013/larr-act,-2013.pdf",

    # ── Competition Act ────────────────────────
    "competition act 2002": "https://prsindia.org/files/bills_acts/acts_parliament/2023/The%20Competition%20(Amendment)%20Act,%202023.pdf",
    "competition act": "https://prsindia.org/files/bills_acts/acts_parliament/2023/The%20Competition%20(Amendment)%20Act,%202023.pdf",

    # ── Right to Education ─────────────────────
    "right to education act 2009": "https://www.indiacode.nic.in/bitstream/123456789/2062/1/200935.pdf",
    "right to education": "https://www.indiacode.nic.in/bitstream/123456789/2062/1/200935.pdf",

    # ── Industrial Relations Code ──────────────

    # ── National Medical Commission ────────────
    "national medical commission act 2019": "https://www.indiacode.nic.in/bitstream/123456789/11820/1/A2019_30.pdf",
    "national medical commission": "https://www.indiacode.nic.in/bitstream/123456789/11820/1/A2019_30.pdf",

    # ── IT Act ─────────────────────────────────
    "it act 2000": "https://www.indiacode.nic.in/bitstream/123456789/1999/3/A2000-21.pdf",
    "it act": "https://www.indiacode.nic.in/bitstream/123456789/1999/3/A2000-21.pdf",
    "information technology act": "https://www.indiacode.nic.in/bitstream/123456789/1999/3/A2000-21.pdf",

    # ── Persons with Disabilities ──────────────
    "persons with disabilities act 2016": "https://www.indiacode.nic.in/bitstream/123456789/2145/1/A2016-49.pdf",
    "persons with disabilities": "https://www.indiacode.nic.in/bitstream/123456789/2145/1/A2016-49.pdf",

    # ── Jan Vishwas Act ────────────────────────
    "jan vishwas act 2023": "https://www.mod.gov.in/dod/sites/default/files/JanVishwasAct5923.pdf",
    "jan vishwas": "https://www.mod.gov.in/dod/sites/default/files/JanVishwasAct5923.pdf",
    # ── Replacement Acts ───────────────────────────
"environment protection act 1986": "https://www.indiacode.nic.in/bitstream/123456789/1596/1/A1986-29.pdf",
"environment protection": "https://www.indiacode.nic.in/bitstream/123456789/1596/1/A1986-29.pdf",

"posh act 2013": "https://www.indiacode.nic.in/bitstream/123456789/15341/1/sexual_harassment_of_women_at_workplace.pdf",
"posh act": "https://www.indiacode.nic.in/bitstream/123456789/15341/1/sexual_harassment_of_women_at_workplace.pdf",
"sexual harassment": "https://www.indiacode.nic.in/bitstream/123456789/15341/1/sexual_harassment_of_women_at_workplace.pdf",
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
                print(f"  ⚠️  Known URL failed: {e}, trying next...")
                break

    # Case 3 — Direct PRS page URL
    if search_term.startswith("http"):
        print(f"🌐 Direct page URL detected")
        try:
            return _extract_pdf_static(search_term)
        except ValueError:
            print(f"  ⚠️  Static failed, trying dynamic...")
            return _extract_pdf_dynamic(search_term)

    # Case 4 — Static PRS search
    try:
        return _search_prs_static(search_term)
    except ValueError:
        print(f"  ⚠️  Static search failed, trying Lok Sabha...")

    # Case 5 — Lok Sabha portal
    try:
        return _search_loksabha(search_term)
    except Exception:
        print(f"  ⚠️  Lok Sabha failed, trying Selenium...")

    # Case 6 — Dynamic Selenium search
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
# STRATEGY 2 — LOK SABHA PORTAL
# ════════════════════════════════════════════════════

def _search_loksabha(search_term: str) -> str:
    """Search Lok Sabha bills portal"""
    print(f"  🏛️  Searching Lok Sabha portal...")

    url = "https://loksabha.nic.in/Bills/AllBills.aspx"
    response = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    search_words = search_term.lower().split()
    for a in soup.find_all("a", href=True):
        text = a.get_text().lower()
        href = a["href"]
        if any(w in text for w in search_words) and ".pdf" in href.lower():
            pdf_url = href if href.startswith("http") else "https://loksabha.nic.in/" + href
            print(f"  ✅ Lok Sabha found: {pdf_url}")
            return _download_pdf(pdf_url)

    raise ValueError(f"Lok Sabha search found nothing for: {search_term}")


# ════════════════════════════════════════════════════
# STRATEGY 3 — DYNAMIC (Selenium)
# ════════════════════════════════════════════════════

def _get_driver():
    """Create a headless Chrome driver"""
    if not SELENIUM_AVAILABLE:
        raise RuntimeError("Selenium not installed. Run: pip install selenium webdriver-manager")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )


def _search_prs_dynamic(search_term: str) -> str:
    """Use Selenium to search PRS India dynamically"""
    search_url = f"https://prsindia.org/billtrack?search={search_term.replace(' ', '+')}"
    print(f"  🤖 Dynamic search: {search_url}")

    driver = _get_driver()
    try:
        driver.get(search_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )
        time.sleep(2)

        links = driver.find_elements(By.TAG_NAME, "a")

        for link in links:
            href = link.get_attribute("href") or ""
            if ".pdf" in href.lower():
                print(f"  ✅ Dynamic found PDF: {href}")
                driver.quit()
                return _download_pdf(href)

        search_words = search_term.lower().split()
        bill_urls = []
        for link in links:
            href = link.get_attribute("href") or ""
            text = link.text.lower()
            if "billtrack" in href and any(w in text for w in search_words):
                bill_urls.append(href)

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
# DOWNLOADER — allow_redirects=True fixes indiacode
# ════════════════════════════════════════════════════

def _download_pdf(url: str) -> str:
    """Download PDF from URL and save to temp file"""

    # ── Sanitize URL — remove any accidental duplications ──
    url = url.strip()
    print(f"  ⬇️  Downloading: {url}")
    time.sleep(1)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
        stream=True,
        allow_redirects=True
    )
    response.raise_for_status()

    content = response.content
    if content[:4] != b'%PDF':
        raise ValueError(
            f"Downloaded file is not a PDF (got HTML?) from: {url}"
        )

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(content)
    tmp.close()

    size_kb = os.path.getsize(tmp.name) // 1024
    print(f"  ✅ Saved to: {tmp.name} ({size_kb} KB)")
    return tmp.name
