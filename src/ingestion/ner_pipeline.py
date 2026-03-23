import re
import spacy

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except:
            # Fallback for minimal environments
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            _nlp = spacy.load("en_core_web_sm")
    return _nlp

INDIAN_STATES = {
    "Delhi", "Mumbai", "Karnataka", "Kerala", "Tamil Nadu",
    "Maharashtra", "Rajasthan", "Gujarat", "Uttar Pradesh",
    "Bihar", "West Bengal", "Odisha", "Punjab", "Haryana",
    "Assam", "Telangana", "Andhra Pradesh", "Goa", "Uttarakhand",
    "Himachal Pradesh", "Jharkhand", "Chhattisgarh", "Tripura"
}

# ── Pattern 1: Acts ──────────────────────────────
# Clean single-line match only
ACT_PATTERN = re.compile(
    r'([A-Z][a-zA-Z ]{2,50}Act,?\s+\d{4})'
)

# ── Pattern 2: Money ─────────────────────────────
# BNS uses "fine of one lakh", "fine which may extend to"
MONEY_PATTERN = re.compile(
    r'(?:'
    r'fine\s+(?:of\s+)?(?:which\s+may\s+extend\s+to\s+)?'
    r'(?:one|two|three|four|five|six|seven|eight|nine|ten|twenty|fifty|hundred|[\d,]+)'
    r'\s*(?:lakh|crore|thousand|hundred)?'
    r'|Rs\.?\s*[\d,]+'
    r'|[\d,]+\s*(?:lakh|crore)\s*(?:rupees?)?'
    r')',
    re.IGNORECASE
)

# ── Pattern 3: Ministry ──────────────────────────
MINISTRY_PATTERN = re.compile(
    r'Ministry\s+of\s+[A-Z][a-zA-Z ]{3,50}',
)

# ── Pattern 4: Dates ─────────────────────────────
DATE_PATTERN = re.compile(
    r'(?:'
    r'\d{1,2}(?:st|nd|rd|th)?\s+'
    r'(?:January|February|March|April|May|June|July|'
    r'August|September|October|November|December)'
    r',?\s+\d{4}'
    r')',
    re.IGNORECASE
)

# ── Pattern 5: Punishment terms ──────────────────
# BNS specific — imprisonment durations
PUNISHMENT_PATTERN = re.compile(
    r'imprisonment\s+(?:for\s+)?(?:life|'
    r'(?:a\s+term\s+)?(?:which\s+may\s+extend\s+to\s+)?'
    r'(?:one|two|three|five|seven|ten|fourteen|twenty|[\d]+)'
    r'\s*years?)',
    re.IGNORECASE
)

def _clean(text: str) -> str:
    """Collapse all whitespace and newlines into single space"""
    return ' '.join(text.strip().split())

def extract_entities(sections: list) -> dict:
    result = {
        "ministries": [],
        "acts_referenced": [],
        "dates": [],
        "monetary_amounts": [],
        "states": [],
        "punishments": []        # bonus field for criminal bills
    }

    for section in sections:
        text = section.section_text

        # Ministries
        for match in MINISTRY_PATTERN.findall(text):
            result["ministries"].append(_clean(match).rstrip('.,'))

        # Acts — clean and dedupe multiline
        for match in ACT_PATTERN.findall(text):
            cleaned = _clean(match)
            if len(cleaned) < 80:
                result["acts_referenced"].append(cleaned)

        # Money
        for match in MONEY_PATTERN.findall(text):
            result["monetary_amounts"].append(_clean(match))

        # Dates
        for match in DATE_PATTERN.findall(text):
            result["dates"].append(_clean(match))

        # Punishments (BNS specific)
        for match in PUNISHMENT_PATTERN.findall(text):
            result["punishments"].append(_clean(match))

        # States via spaCy
        nlp = get_nlp()
        doc = nlp(text[:10000])
        for ent in doc.ents:
            if ent.label_ == "GPE" and ent.text in INDIAN_STATES:
                result["states"].append(ent.text)

    # Deduplicate all
    return {k: list(set(v)) for k, v in result.items()}