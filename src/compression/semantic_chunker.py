"""
src/compression/semantic_chunker.py
=====================================
Semantic chunking — splits bill text at topic boundaries
using sentence embeddings instead of regex patterns.
v2.0 Sprint 1 Day 3
Owner: Akagami
"""

import re
import sys
import os
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.shared_schemas import BillSection
from typing import List
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

# ── Global model cache — load once, reuse everywhere ─────────────────────────
_embedding_model = None

def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("   Loading embedding model (once)...")
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("   ✅ Embedding model loaded")
        except Exception as e:
            print(f"   ⚠️  SentenceTransformer failed: {e}")
            _embedding_model = "failed"
    return _embedding_model

# ── Indian legal section boundary patterns ────────────────────────────────────
HARD_BOUNDARY_PATTERN = re.compile(
    r'(?:^|\n)\s*(?:'
    r'\d{1,3}[A-Z]?\.\s+[A-Z]'      # 1. Title  or  4A. Title
    r'|Section\s+\d+'                 # Section 4
    r'|CHAPTER\s+[IVXLC\d]+'         # CHAPTER III
    r'|SCHEDULE\s+[IVXLC\d]+'        # SCHEDULE I
    r'|PART\s+[IVXLCA-Z]+'           # PART A
    r')',
    re.MULTILINE
)


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    # Handle legal numbering like (1), (a), (i) — don't split there
    text = re.sub(r'\s+', ' ', text)
    sentences = re.split(r'(?<=[.;])\s+(?=[A-Z(])', text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def _compute_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


def _get_embeddings(sentences: List[str]):
    """Get sentence embeddings using cached model."""
    model = _get_embedding_model()

    if model == "failed" or model is None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        try:
            vectorizer = TfidfVectorizer(max_features=500)
            embeddings = vectorizer.fit_transform(sentences).toarray()
            return embeddings, "tfidf-fallback"
        except Exception:
            return None, "failed"

    try:
        embeddings = model.encode(sentences, show_progress_bar=False)
        return embeddings, "sentence-transformers"
    except Exception:
        return None, "failed"


def semantic_chunk(text: str,
                   bill_id: str,
                   page_number: int = 1,
                   similarity_threshold: float = 0.45,
                   min_chunk_tokens: int = 40,
                   max_chunk_tokens: int = 800) -> List[BillSection]:
    """
    Split a large text block into semantically coherent sections.

    Args:
        text: Raw text to chunk
        bill_id: Bill identifier for section IDs
        page_number: Page this text came from
        similarity_threshold: Below this → topic has changed → new chunk
        min_chunk_tokens: Drop chunks smaller than this
        max_chunk_tokens: Force-split chunks larger than this

    Returns:
        List of BillSection objects
    """
    if not text or len(text.strip()) < 100:
        return []

    # ── Step 1: Hard boundaries first (legal section numbers) ────────────────
    hard_splits = HARD_BOUNDARY_PATTERN.split(text)
    hard_splits = [s.strip() for s in hard_splits if len(s.strip()) > 50]

    if len(hard_splits) <= 1:
        # No hard boundaries found — use full semantic splitting
        hard_splits = [text]

    all_sections = []
    chunk_counter = [0]

    def make_section(chunk_text: str, title_hint: str = "") -> BillSection:
        chunk_counter[0] += 1
        first_line = chunk_text.split('\n')[0][:80].strip()

        # Clean up word concatenation (Rishi's bug workaround)
        first_line = re.sub(r'\.([A-Z])', r'. \1', first_line)
        first_line = re.sub(r'([a-z])([A-Z])', r'\1 \2', first_line)
        first_line = re.sub(r'([A-Z]{2,})([A-Z][a-z])', r'\1 \2', first_line)

        title = title_hint or first_line or f"Section {chunk_counter[0]}"
        section_id = re.sub(r'\W+', '_', title.lower())[:60]

        return BillSection(
            section_id=f"{bill_id}_{section_id}_{chunk_counter[0]}",
            section_title=title[:100],
            section_text=chunk_text,
            token_count=len(enc.encode(chunk_text)),
            page_number=page_number
        )

    # ── Step 2: Semantic split each hard block ────────────────────────────────
    for block in hard_splits:
        block_tokens = len(enc.encode(block))

        # Small block — keep as is
        if block_tokens <= max_chunk_tokens:
            if block_tokens >= min_chunk_tokens:
                all_sections.append(make_section(block))
            continue

        # Large block — semantic split
        sentences = _split_into_sentences(block)

        if len(sentences) < 3:
            # Too few sentences to split semantically
            all_sections.append(make_section(block))
            continue

        embeddings, method = _get_embeddings(sentences)

        if embeddings is None or len(embeddings) < 2:
            # Embedding failed — keep block as is
            all_sections.append(make_section(block))
            continue

        # Find topic shift points
        current_chunk_sentences = [sentences[0]]
        current_tokens = len(enc.encode(sentences[0]))

        for i in range(1, len(sentences)):
            sim = _compute_similarity(embeddings[i-1], embeddings[i])
            sentence_tokens = len(enc.encode(sentences[i]))

            # Split if: topic changed OR chunk too large
            should_split = (
                (sim < similarity_threshold and current_tokens >= min_chunk_tokens)
                or (current_tokens + sentence_tokens > max_chunk_tokens)
            )

            if should_split and current_chunk_sentences:
                chunk_text = ' '.join(current_chunk_sentences)
                chunk_tokens = len(enc.encode(chunk_text))
                if chunk_tokens >= min_chunk_tokens:
                    all_sections.append(make_section(chunk_text))
                current_chunk_sentences = [sentences[i]]
                current_tokens = sentence_tokens
            else:
                current_chunk_sentences.append(sentences[i])
                current_tokens += sentence_tokens

        # Last chunk
        if current_chunk_sentences:
            chunk_text = ' '.join(current_chunk_sentences)
            if len(enc.encode(chunk_text)) >= min_chunk_tokens:
                all_sections.append(make_section(chunk_text))

    print(f"   Semantic chunker: {len(hard_splits)} hard blocks "
          f"→ {len(all_sections)} semantic chunks")

    return all_sections


def semantic_chunk_bill(data: dict) -> List[BillSection]:
    """
    Entry point — replaces fix_sections() in run_pipeline.py.
    Takes raw ingested bill JSON, returns semantically chunked sections.
    """
    bill_id  = data.get("bill_id", "unknown")
    sections = data.get("sections", [])

    print(f"\n🧠 Semantic chunking: {len(sections)} raw sections...")

    all_chunks = []

    for raw_section in sections:
        text       = raw_section.get("section_text", "")
        page_num   = raw_section.get("page_number", 1)
        token_count = raw_section.get("token_count", 0)

        # Already small enough — keep as is, just clean the title
        if token_count < 200:
            title = raw_section.get("section_title", "")
            title = re.sub(r'\.([A-Z])', r'. \1', title)
            title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title)

            all_chunks.append(BillSection(
                section_id=raw_section.get("section_id", f"sec_{len(all_chunks)}"),
                section_title=title[:100],
                section_text=text,
                token_count=token_count,
                page_number=page_num
            ))
            continue

        # Large section — semantic split
        chunks = semantic_chunk(
            text=text,
            bill_id=bill_id,
            page_number=page_num,
            similarity_threshold=0.45,
            min_chunk_tokens=40,
            max_chunk_tokens=600
        )
        all_chunks.extend(chunks)

    total_tokens = sum(c.token_count for c in all_chunks)
    print(f"✅ Semantic chunking complete:")
    print(f"   Raw sections  : {len(sections)}")
    print(f"   Semantic chunks: {len(all_chunks)}")
    print(f"   Total tokens  : {total_tokens:,}")

    return all_chunks
