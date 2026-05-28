from urllib.parse import urlparse

def test_url_detection(url):
    parsed_url = urlparse(url)
    is_direct_pdf = parsed_url.scheme and parsed_url.path.lower().endswith(".pdf")
    print(f"URL: {url}")
    print(f"Is direct PDF? {'✅ YES' if is_direct_pdf else '❌ NO'}")
    return is_direct_pdf

if __name__ == "__main__":
    urls = [
        "https://sansad.in/uploads/LSPP_Questions_Procedure_rules_2c7312313c.pdf?updated_at=2022-09-14T06:16:54.310Z",
        "https://egazette.gov.in/WriteReadData/2023/248045.pdf",
        "https://prsindia.org/billtrack/the-digital-personal-data-protection-bill-2023"
    ]
    
    for url in urls:
        test_url_detection(url)
