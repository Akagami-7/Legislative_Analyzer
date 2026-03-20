import re
import spacy

nlp = spacy.load("en_core_web_sm")

INDIAN_STATES = {
    "Delhi", "Mumbai", "Karnataka", "Kerala", "Tamil Nadu",
    "Maharashtra", "Rajasthan", "Gujarat", "Uttar Pradesh",
    "Bihar", "West Bengal", "Odisha", "Punjab", "Haryana",
    "Assam", "Telangana", "Andhra Pradesh", "Goa"
}

ACT_PATTERN = re.compile(r'[\w\s]+ Act,?\s+\d{4}')

def extract_entities(sections: list) -> dict:
    result = {
        "ministries": [],
        "acts_referenced": [],
        "dates": [],
        "monetary_amounts": [],
        "states": []
    }

    for section in sections:
        doc = nlp(section.section_text[:50000])  # spaCy token limit guard

        for ent in doc.ents:
            if ent.label_ == "ORG" and "ministry" in ent.text.lower():
                result["ministries"].append(ent.text)
            elif ent.label_ == "DATE":
                result["dates"].append(ent.text)
            elif ent.label_ == "MONEY":
                result["monetary_amounts"].append(ent.text)
            elif ent.label_ == "GPE" and ent.text in INDIAN_STATES:
                result["states"].append(ent.text)

        for match in ACT_PATTERN.findall(section.section_text):
            result["acts_referenced"].append(match.strip())

    # Deduplicate all lists
    return {k: list(set(v)) for k, v in result.items()}