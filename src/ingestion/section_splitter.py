import re
import tiktoken
from src.shared_schemas import BillSection

SECTION_PATTERN = re.compile(
    r'(?:^|\n)\s*(?:'
    r'Section\s+\d+[A-Z]?\.'           # Section 1.
    r'|\d+\.\s+[A-Z][a-z]'             # 1. Short title
    r'|\d+\.\s+[A-Z]{2,}'              # 1. DEFINITIONS
    r'|CHAPTER\s+[IVXLC\d]+'           # CHAPTER I
    r'|SCHEDULE\s+[IVXLC\d]+'          # SCHEDULE I
    r'|PART\s+[IVXLCA-Z]+'             # PART A
    r'|Clause\s+\d+'                   # Clause 1
    r'|Article\s+\d+'                  # Article 1
    r'|\d+[A-Z]?\.\s+[A-Z][a-zA-Z]'   # 33A. Punishment
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
        cumulative += len(page) + 1

    full_text = "\n".join(pages)

    # Skip if text is too short — gazette wrapper
    if len(full_text.strip()) < 500:
        return []

    # Skip index/table of contents pages
    # Find where actual content starts
    content_start = 0
    lines = full_text.split('\n')
    for i, line in enumerate(lines):
        # Skip until we find actual section content
        if re.match(r'^\s*(?:CHAPTER\s+[IVX1]|1\.\s+Short title|Section\s+1)', line, re.IGNORECASE):
            content_start = full_text.find(line)
            break

    # Use content_start if found meaningful start
    search_text = full_text[content_start:] if content_start > 0 else full_text

    matches = list(SECTION_PATTERN.finditer(search_text))
    print(f"  [DEBUG] Regex matches found: {len(matches)}")
    if len(matches) < 5:
        print(f"  [DEBUG] First 500 chars: {full_text[:500]}")

    # If too few matches try looser pattern
    if len(matches) < 3:
        LOOSE_PATTERN = re.compile(
            r'(?:^|\n)\s*(\d+)\.\s+[A-Z]',
            re.MULTILINE
        )
        matches = list(LOOSE_PATTERN.finditer(search_text))

    sections = []
    for i, match in enumerate(matches):
        start = match.start() + content_start
        end = (matches[i + 1].start() + content_start) if i + 1 < len(matches) else len(full_text)
        text = full_text[start:end].strip()
        token_count = len(enc.encode(text))

        if token_count < 20:
            continue

        first_line = text.split('\n')[0].strip()
        section_title = first_line if first_line else match.group().strip()
        section_id = re.sub(r'\W+', '_', section_title.lower()).strip('_')[:80]

        # Find page number — iterate backwards
        page_num = 1
        for idx in range(len(page_start_chars) - 1, -1, -1):
            if page_start_chars[idx] <= start:
                page_num = idx + 1
                break

        sections.append(BillSection(
            section_id=section_id,
            section_title=section_title,
            section_text=text,
            token_count=token_count,
            page_number=page_num
        ))

    return sections