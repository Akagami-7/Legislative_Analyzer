import textstat

def score_section(text: str) -> dict:
    """Score readability of a section for citizens"""
    fre = textstat.flesch_reading_ease(text)
    return {
        "flesch_reading_ease": round(fre, 2),
        "grade_level": round(textstat.flesch_kincaid_grade(text), 2),
        "reading_time_seconds": textstat.reading_time(text, ms_per_char=14.69),
        "is_complex": fre < 30,
        "complexity_label": (
            "Very Easy" if fre >= 70
            else "Easy" if fre >= 60
            else "Moderate" if fre >= 50
            else "Difficult" if fre >= 30
            else "Very Complex"
        )
    }

def score_all_sections(sections: list) -> list:
    """Add readability scores to all sections"""
    scored = []
    for section in sections:
        s_dict = section.model_dump() if hasattr(section, 'model_dump') else section
        s_dict["readability"] = score_section(s_dict["section_text"])
        scored.append(s_dict)
    return scored