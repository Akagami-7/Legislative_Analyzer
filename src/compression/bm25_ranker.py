"""
src/compression/bm25_ranker.py
==============================
Combined BM25 + TF-IDF clause ranking.
v2.0: Added TF-IDF scoring alongside BM25 for better
      civic relevance detection.
Owner: Akagami
"""

from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.shared_schemas import BillSection
from typing import List

CIVIC_QUERY = [
    "citizen", "rights", "penalty", "fine", "obligation",
    "prohibited", "entitled", "shall", "offence", "consent",
    "data", "protection", "compensation", "enforcement",
    "child", "withdrawal", "breach", "notice", "personal",
    "imprisonment", "crore", "rupees", "death", "life",
    "fundamental", "privacy", "safety", "victim", "justice"
]

TFIDF_QUERY = (
    "citizen rights penalty fine obligation prohibited entitled "
    "shall offence consent data protection compensation enforcement "
    "child withdrawal breach notice personal imprisonment crore "
    "rupees death life fundamental privacy safety victim justice "
    "punishment award damages liable convicted acquitted"
)

BM25_WEIGHT  = 0.6
TFIDF_WEIGHT = 0.4


def _bm25_scores(sections: List[BillSection]) -> np.ndarray:
    """Compute BM25 scores for all sections against civic query."""
    corpus = [s.section_text.lower().split() for s in sections]
    bm25   = BM25Okapi(corpus)
    scores = bm25.get_scores(CIVIC_QUERY)

    # Normalise to 0-1
    max_score = max(scores) if max(scores) > 0 else 1
    return scores / max_score


def _tfidf_scores(sections: List[BillSection]) -> np.ndarray:
    """Compute TF-IDF cosine similarity scores against civic query."""
    corpus = [s.section_text for s in sections]
    docs   = corpus + [TFIDF_QUERY]   # query as last document

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),           # unigrams + bigrams
        max_features=10000,
        sublinear_tf=True             # log normalisation
    )

    tfidf_matrix = vectorizer.fit_transform(docs)
    query_vec    = tfidf_matrix[-1]       # last row = query
    section_vecs = tfidf_matrix[:-1]      # all other rows = sections

    similarities = cosine_similarity(section_vecs, query_vec).flatten()
    return similarities


def rank_and_filter(sections: List[BillSection],
                    keep_ratio: float = 0.7) -> List[BillSection]:
    """
    Rank sections using combined BM25 + TF-IDF score.
    Keep top keep_ratio% by combined score.
    """
    if not sections:
        return []

    bm25_scores  = _bm25_scores(sections)
    tfidf_scores = _tfidf_scores(sections)

    # Combined weighted score
    combined = (BM25_WEIGHT * bm25_scores) + (TFIDF_WEIGHT * tfidf_scores)

    print("\n📊 BM25 + TF-IDF Combined Section Scores:")
    print("-" * 60)

    scored = sorted(
        zip(combined, bm25_scores, tfidf_scores, sections),
        key=lambda x: x[0],
        reverse=True
    )

    for comb, bm25, tfidf, section in scored[:20]:
        print(
            f"  {comb:.3f} (bm25={bm25:.2f} tfidf={tfidf:.2f})"
            f"  →  {section.section_title[:55]}"
        )

    if len(scored) > 20:
        print(f"  ... and {len(scored) - 20} more sections")

    # Keep top keep_ratio
    keep_n = max(1, int(len(sections) * keep_ratio))
    kept   = [s for _, _, _, s in scored[:keep_n]]

    # Restore original page order
    kept.sort(key=lambda s: s.page_number)

    print(f"\n✅ Kept {len(kept)} / {len(sections)} sections "
          f"({keep_ratio*100:.0f}% ratio)")
    print(f"   Scoring: {BM25_WEIGHT*100:.0f}% BM25 + "
          f"{TFIDF_WEIGHT*100:.0f}% TF-IDF")

    return kept