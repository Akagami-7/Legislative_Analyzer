import tiktoken
import re
from typing import List
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.shared_schemas import BillSection

enc = tiktoken.get_encoding("cl100k_base")

HIGH_VALUE_TERMS = [
    "shall", "right", "penalty", "fine", "consent", "prohibited",
    "entitled", "obligation", "crore", "offence", "breach",
    "citizen", "data principal", "withdraw", "erasure", "child",
    "protection", "compensation", "must", "cannot", "liable"
]

def score_sentence(sentence: str) -> float:
    sentence_lower = sentence.lower()
    score = 0.0
    for term in HIGH_VALUE_TERMS:
        if term in sentence_lower:
            score += 1.0
    if re.search(r'\d+', sentence):
        score += 0.5
    return score

def extractive_compress(sections: List[BillSection],
                        sentences_per_section: int = 4) -> List[BillSection]:

    compressed = []
    total_before = 0
    total_after = 0

    for section in sections:
        total_before += section.token_count

        # Too short — keep as is
        if section.token_count < 60:
            compressed.append(section)
            total_after += section.token_count
            continue

        # Split into sentences
        sentences = re.split(r'(?<=[.;])\s+', section.section_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

        if len(sentences) <= sentences_per_section:
            # Already short enough
            compressed.append(section)
            total_after += section.token_count
            continue

        # Score and pick top sentences
        scored = sorted(
            enumerate(sentences),
            key=lambda x: score_sentence(x[1]),
            reverse=True
        )
        top_indices = sorted([i for i, _ in scored[:sentences_per_section]])
        compressed_text = " ".join(sentences[i] for i in top_indices)

        new_tokens = len(enc.encode(compressed_text))
        total_after += new_tokens

        compressed.append(BillSection(
            section_id=section.section_id,
            section_title=section.section_title,
            section_text=compressed_text,
            token_count=new_tokens,
            page_number=section.page_number
        ))

    reduction = ((total_before - total_after) / max(total_before, 1)) * 100
    print(f"\n📉 Extractive compression:")
    print(f"   Before : {total_before:,} tokens")
    print(f"   After  : {total_after:,} tokens")
    print(f"   Savings: {reduction:.1f}%")

    return compressed