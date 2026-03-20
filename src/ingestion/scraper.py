import requests
import time
import tempfile
from bs4 import BeautifulSoup

def scrape_bill(search_term: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}

    # If it's already a direct PDF URL, just download it
    if search_term.startswith("http") and search_term.endswith(".pdf"):
        r = requests.get(search_term, headers=headers)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(r.content)
        tmp.close()
        return tmp.name

    # Otherwise scrape PRS India
    search_url = f"https://prsindia.org/billtrack?search={search_term.replace(' ', '+')}"
    time.sleep(1)
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    pdf_link = soup.find("a", href=lambda h: h and h.endswith(".pdf"))
    if not pdf_link:
        raise ValueError(f"No PDF found for search term: {search_term}")

    pdf_url = pdf_link["href"]
    if not pdf_url.startswith("http"):
        pdf_url = "https://prsindia.org" + pdf_url

    time.sleep(1)
    r = requests.get(pdf_url, headers=headers)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(r.content)
    tmp.close()
    return tmp.name