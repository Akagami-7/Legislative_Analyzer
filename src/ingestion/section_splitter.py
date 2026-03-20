import re
import tiktoken
from src.shared_schemas import BillSection

SECTION_PATTERN = re.compile(
    r'(?:^|\n)\s*(?:'
    r'Section\s+\d+[A-Z]?\.'
    r'|CHAPTER\s+[IVXLC\d]+'
    r'|SCHEDULE\s+[IVXLC\d]+'
    r'|PART\s+[IVXLCA-Z]+'
    r')',
    re.IGNORECASE | re.MULTILINE
)

enc = tiktoken.get_encoding("cl100k_base")

def split_sections(pages: list) -> list:
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
            continue  # drop noise/blank sections

        section_id = re.sub(r'\W+', '_', title.lower()).strip('_')
        page_num = full_text[:start].count('\n\n') // 3 + 1

        sections.append(BillSection(
            section_id=section_id,
            section_title=title,
            section_text=text,
            token_count=token_count,
            page_number=page_num
        ))

    return sections