import re
import tiktoken
from src.shared_schemas import BillSection

SECTION_PATTERN = re.compile(
    r'(?:^|\n)\s*(?:'
    r'Section\s+\d+[A-Z]?\.'        # Section 1. Section 33. Section 4A.
    r'|\d+\.\s+[A-Z]'               # 33. Punishment for... 
    r'|CHAPTER\s+[IVXLC\d]+'        # CHAPTER III
    r'|SCHEDULE\s+[IVXLC\d]+'       # SCHEDULE I
    r'|PART\s+[IVXLCA-Z]+'          # PART A
    r')',
    re.IGNORECASE | re.MULTILINE
)

enc = tiktoken.get_encoding("cl100k_base")

def split_sections(pages: list) -> list:
    # Track page numbers properly
    page_boundaries = []
    running_chars = 0
    for i, page in enumerate(pages):
        page_boundaries.append(running_chars)
        running_chars += len(page) + 1  # +1 for the \n join

    full_text = "\n".join(pages)
    matches = list(SECTION_PATTERN.finditer(full_text))
    sections = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        text = full_text[start:end].strip()
        title = match.group().strip()
        token_count = len(enc.encode(text))

        if token_count < 20:
            continue  # drop noise

        section_id = re.sub(r'\W+', '_', title.lower()).strip('_')

        # Fix 2 — proper page number tracking
        page_num = 1
        for p_idx, boundary in enumerate(page_boundaries):
            if boundary <= start:
                page_num = p_idx + 1
            else:
                break

        sections.append(BillSection(
            section_id=section_id,
            section_title=title,
            section_text=text,
            token_count=token_count,
            page_number=page_num
        ))

    return sections