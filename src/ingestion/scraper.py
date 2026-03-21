import re
import spacy

nlp = spacy.load("en_core_web_sm")

INDIAN_STATES = {
    "Delhi", "Mumbai", "Karnataka", "Kerala", "Tamil Nadu",
    "Maharashtra", "Rajasthan", "Gujarat", "Uttar Pradesh",
    "Bihar", "West Bengal", "Odisha", "Punjab", "Haryana",
    "Assam", "Telangana", "Andhra Pradesh", "Goa", "Uttarakhand",
    "Himachal Pradesh", "Jharkhand", "Chhattisgarh", "Tripura"
}

# Matches "X Act, 2000" — cleaned up, no multiline garbage
ACT_PATTERN = re.compile(
    r'(?<![a-z])([A-Z][a-zA-Z\s\(\)]{3,60}?Act,?\s+\d{4})',
)

# Indian money patterns
MONEY_PATTERN = re.compile(
    r'(?:'
    r'Rs\.?\s*[\d,]+'
    r'|(?:rupees?|fine)\s+(?:of\s+)?(?:which\s+may\s+extend\s+to\s+)?[\d,]+'
    r'|[\d,]+\s*(?:crore|lakh|thousand)\s*(?:rupees?)?'
    r'|fine\s+(?:which\s+may\s+extend\s+to\s+)?(?:one|two|three|five|ten)\s+(?:lakh|crore)'
    r')',
    re.IGNORECASE
)

# Ministry pattern
MINISTRY_PATTERN = re.compile(
    r'Ministry\s+of\s+[A-Z][a-zA-Z\s]{3,50}',
)

# Indian date formats
DATE_PATTERN = re.compile(
    r'\d{1,2}(?:st|nd|rd|th)\s+(?:January|February|March|April|May|June|'
    r'July|August|September|October|November|December),?\s+\d{4}',
    re.IGNORECASE
)

def extract_entities(sections: list) -> dict:
    result = {
        "ministries": [],
        "acts_referenced": [],
        "dates": [],
        "monetary_amounts": [],
        "states": []
    }

    for section in sections:
        text = section.section_text

        # Ministries
        for match in MINISTRY_PATTERN.findall(text):
            result["ministries"].append(match.strip().rstrip('.,'))

        # Acts — clean multiline
        for match in ACT_PATTERN.findall(text):
            clean = ' '.join(match.strip().split())  # collapse whitespace
            if len(clean) < 80:
                result["acts_referenced"].append(clean)

        # Money
        for match in MONEY_PATTERN.findall(text):
            result["monetary_amounts"].append(match.strip())

        # Dates
        for match in DATE_PATTERN.findall(text):
            result["dates"].append(match.strip())

        # States via spaCy
        doc = nlp(text[:10000])
        for ent in doc.ents:
            if ent.label_ == "GPE" and ent.text in INDIAN_STATES:
                result["states"].append(ent.text)

    return {k: list(set(v)) for k, v in result.items()}