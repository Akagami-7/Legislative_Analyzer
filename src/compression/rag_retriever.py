"""
src/compression/rag_retriever.py
=================================
Retrieves relevant past bill sections from ChromaDB
using BGE-M3 semantic search + cross-encoder reranking.
v2.0 Sprint 1 Day 5
Owner: Akagami
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder
from typing import List, Dict
from src.compression.rag_embedder import (
    _get_embed_model, _get_chroma_client,
    _get_collection, CHROMA_PATH
)

_reranker = None

def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        try:
            print("   Loading cross-encoder reranker...")
            _reranker = CrossEncoder(
                "cross-encoder/ms-marco-MiniLM-L-6-v2"
            )
            print("   ✅ Reranker loaded")
        except Exception as e:
            print(f"   ⚠️  Reranker failed: {e}")
            _reranker = "failed"
    return _reranker


def retrieve_context(
    query: str,
    current_bill_id: str,
    top_k: int = 5,
    candidate_k: int = 20,
    use_reranker: bool = True
) -> List[Dict]:
    """
    Retrieve relevant sections from past bills using semantic search.
    Excludes sections from the current bill being analyzed.

    Args:
        query: The compressed prompt or civic query
        current_bill_id: Exclude this bill from results
        top_k: Final number of sections to return
        candidate_k: Number of candidates before reranking
        use_reranker: Whether to apply cross-encoder reranking

    Returns:
        List of dicts with section text and metadata
    """
    client     = _get_chroma_client()
    collection = _get_collection(client)

    total = collection.count()
    if total == 0:
        print("   ⚠️  ChromaDB is empty — no RAG context available")
        return []

    # ── Step 1: Semantic search ───────────────────────────────────────────────
    model = _get_embed_model()

    # Use first 512 chars of query for embedding (BGE-M3 optimal)
    query_text = query[:512]
    query_embedding = model.encode(
        query_text,
        normalize_embeddings=True
    ).tolist()

    # Retrieve candidates — exclude current bill
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(candidate_k, total),
            where={"bill_id": {"$ne": current_bill_id}}
        )
    except Exception:
        # If where filter fails (only 1 bill in DB), get all
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(candidate_k, total)
        )

    if not results["documents"][0]:
        print("   ⚠️  No relevant sections found in ChromaDB")
        return []

    candidates = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        candidates.append({
            "text"          : doc,
            "bill_id"       : meta.get("bill_id", ""),
            "section_title" : meta.get("section_title", ""),
            "page_number"   : meta.get("page_number", 1),
            "token_count"   : meta.get("token_count", 0),
            "similarity"    : 1 - dist   # convert distance to similarity
        })

    print(f"\n🔍 RAG: {len(candidates)} candidates retrieved")

    # ── Step 2: Cross-encoder reranking ──────────────────────────────────────
    if use_reranker and len(candidates) > top_k:
        reranker = _get_reranker()

        if reranker != "failed" and reranker is not None:
            pairs = [(query_text, c["text"]) for c in candidates]
            scores = reranker.predict(pairs)

            for i, score in enumerate(scores):
                candidates[i]["rerank_score"] = float(score)

            candidates.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
            print(f"   ✅ Reranked — top {top_k} selected")
        else:
            # No reranker — sort by similarity
            candidates.sort(key=lambda x: x["similarity"], reverse=True)

    final = candidates[:top_k]

    print(f"   📎 RAG context:")
    for c in final:
        print(f"      [{c['bill_id']}] {c['section_title'][:50]} "
              f"(sim={c['similarity']:.3f})")

    return final


def format_rag_context(retrieved: List[Dict], max_tokens: int = 2000) -> str:
    """
    Format retrieved sections into a context string
    to inject into the LLM prompt.
    """
    if not retrieved:
        return ""

    lines = [
        "RELEVANT CONTEXT FROM PAST INDIAN LEGISLATION:",
        "=" * 50
    ]

    total_tokens = 0
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")

    for item in retrieved:
        raw_text = item["text"]
        tokens = enc.encode(raw_text)
        truncated_tokens = tokens[:300]
        truncated_text = enc.decode(truncated_tokens)
        section_text = (
            f"\n[From: {item['bill_id']} — {item['section_title']}]\n"
            f"{truncated_text}\n"
        )
        section_tokens = len(enc.encode(section_text))

        if total_tokens + section_tokens > max_tokens:
            break

        lines.append(section_text)
        total_tokens += section_tokens

    lines.append("=" * 50)
    context = "\n".join(lines)

    print(f"   RAG context: {total_tokens} tokens injected")
    return context