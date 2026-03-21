import re
import tiktoken
from src.shared_schemas import BillSection

SECTION_PATTERN = re.compile(
    r'(?:^|\n)\s*(?:'
    r'Section\s+\d+[A-Z]?\.'
    r'|\d+\.\s+[A-Z]'
    r'|CHAPTER\s+[IVXLC\d]+'
    r'|SCHEDULE\s+[IVXLC\d]+'
    r'|PART\s+[IVXLCA-Z]+'
    r')',
    re.IGNORECASE | re.MULTILINE
)

enc = tiktoken.get_encoding("cl100k_base")

def split_sections(pages: list) -> list:

    # Build exact char position where each page starts
    page_start_chars = []
    cumulative = 0
    for page in pages:
        page_start_chars.append(cumulative)
        cumulative += len(page) + 1  # +1 for \n

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
            continue

        section_id = re.sub(r'\W+', '_', title.lower()).strip('_')

        # Find page number — find the LAST boundary that is <= start
        page_num = 1
        for idx in range(len(page_start_chars) - 1, -1, -1):
            if page_start_chars[idx] <= start:
                page_num = idx + 1
                break

        sections.append(BillSection(
            section_id=section_id,
            section_title=title,
            section_text=text,
            token_count=token_count,
            page_number=page_num
        ))

    return sections