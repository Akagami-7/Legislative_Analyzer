from rank_bm25 import BM25Okapi
from typing import List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.shared_schemas import BillSection

CIVIC_QUERY = [
    "citizen", "rights", "penalty", "fine", "obligation",
    "prohibited", "entitled", "shall", "offence", "consent",
    "data", "protection", "compensation", "enforcement",
    "child", "withdrawal", "breach", "notice", "personal"
]

def rank_and_filter(sections: List[BillSection],
                    keep_ratio: float = 0.7) -> List[BillSection]:

    if not sections:
        return []

    corpus = [s.section_text.lower().split() for s in sections]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(CIVIC_QUERY)

    print("\n📊 BM25 Section Scores:")
    print("-" * 50)
    for score, section in sorted(zip(scores, sections), 
                                  key=lambda x: x[0], reverse=True):
        print(f"  {score:.3f}  →  {section.section_title[:50]}")

    scored = sorted(zip(scores, sections), 
                    key=lambda x: x[0], reverse=True)
    keep_n = max(1, int(len(sections) * keep_ratio))
    kept = [s for _, s in scored[:keep_n]]

    # Restore original page order
    kept.sort(key=lambda s: s.page_number)

    print(f"\n✅ Kept {len(kept)} / {len(sections)} sections "
          f"({keep_ratio*100:.0f}% ratio)")
    return kept