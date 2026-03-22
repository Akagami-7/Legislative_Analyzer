"""
src/compression/rag_embedder.py
================================
Embeds ingested bill sections into ChromaDB using BGE-M3.
Run this once per bill to index it into the vector store.
v2.0 Sprint 1 Day 4-5
Owner: Akagami
"""

import json
import os
import sys
import torch
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from src.shared_schemas import BillSection
from typing import List
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

# ── ChromaDB persistent storage ───────────────────────────────────────────────
CHROMA_PATH = "./chroma_db"

# ── Embedding model ───────────────────────────────────────────────────────────
# BGE-M3 — multilingual, supports Hindi/Telugu/Tamil etc.
# Falls back to all-MiniLM-L6-v2 if BGE-M3 not available
BGE_MODEL_PRIMARY  = "Qwen/Qwen3-Embedding-0.6B"
BGE_MODEL_FALLBACK = "paraphrase-multilingual-MiniLM-L12-v2"

_embed_model = None

def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        try:
            print(f"   Loading Qwen3 embedding model...")
            _embed_model = SentenceTransformer(BGE_MODEL_PRIMARY)
            print(f"   ✅ Qwen3 loaded")
        except Exception as e:
            print(f"   ⚠️  Qwen3 failed ({e}), using fallback...")
            _embed_model = SentenceTransformer(BGE_MODEL_FALLBACK)
            print(f"   ✅ Fallback model loaded")
    return _embed_model


def _get_chroma_client() -> chromadb.PersistentClient:
    """Get persistent ChromaDB client."""
    os.makedirs(CHROMA_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_PATH)


def _get_collection(client: chromadb.PersistentClient):
    """Get or create the bills collection."""
    return client.get_or_create_collection(
        name="indian_bills",
        metadata={"description": "Indian parliamentary bill sections"}
    )


def embed_bill(json_path: str) -> int:
    """
    Embed all sections of a bill into ChromaDB.
    
    Args:
        json_path: Path to ingested_bill.json
        
    Returns:
        Number of sections embedded
    """
    print(f"\n📥 Embedding bill: {json_path}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    bill_id  = data["bill_id"]
    sections = data["sections"]

    print(f"   Bill ID  : {bill_id}")
    print(f"   Sections : {len(sections)}")

    model      = _get_embed_model()
    client     = _get_chroma_client()
    collection = _get_collection(client)

    # Check which sections already embedded — skip them
    existing = set()
    try:
        existing_ids = collection.get(
            where={"bill_id": bill_id}
        )["ids"]
        existing = set(existing_ids)
        if existing:
            print(f"   Already embedded: {len(existing)} sections — skipping")
    except Exception:
        pass

    # Prepare batch
    texts      = []
    ids        = []
    metadatas  = []

    seen_ids = {}  # track duplicates
    
    for idx, section in enumerate(sections):
        base_id    = f"{bill_id}__{section['section_id']}"
        
        # Make unique if duplicate
        if base_id in seen_ids:
            seen_ids[base_id] += 1
            section_id = f"{base_id}_{seen_ids[base_id]}"
        else:
            seen_ids[base_id] = 0
            section_id = base_id

        if section_id in existing:
            continue

        text = section["section_text"]
        if not text or len(text.strip()) < 30:
            continue

        texts.append(text)
        ids.append(section_id)
        metadatas.append({
            "bill_id"      : bill_id,
            "section_id"   : section["section_id"],
            "section_title": section["section_title"][:200],
            "page_number"  : section["page_number"],
            "token_count"  : section["token_count"]
        })

    if not texts:
        print(f"   ✅ All sections already embedded — nothing to do")
        return 0

    # Embed in batches of 64
    print(f"   Embedding {len(texts)} sections...")
    batch_size = 32
    while batch_size > 0:
        try:
            test_batch = texts[:batch_size]
            with torch.no_grad():
                model.encode(test_batch, batch_size=batch_size)

            print(f"✅ Using batch_size={batch_size}")
            break

        except RuntimeError as e:
            if "CUDA out of memory" in str(e):
                print(f"❌ OOM at batch_size={batch_size}")
                batch_size = max(1, batch_size // 2)
                torch.cuda.empty_cache()
                print(f"🔽 Retrying with batch_size={batch_size}")
            else:
                raise e

    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        with torch.no_grad():
            embeddings = model.encode(
                batch,
                batch_size=batch_size,
                show_progress_bar=False,
                normalize_embeddings=True
            )
        all_embeddings.extend(embeddings.tolist())
        print(f"   Batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1} done")
        torch.cuda.empty_cache()

    # Store in ChromaDB
    collection.add(
        ids        = ids,
        embeddings = all_embeddings,
        documents  = texts,
        metadatas  = metadatas
    )

    print(f"   ✅ Embedded {len(texts)} sections into ChromaDB")
    print(f"   📁 Stored at: {CHROMA_PATH}")
    return len(texts)


def embed_all_bills(bills_folder: str = "./ingested_bills") -> None:
    """
    Embed all bills in a folder.
    Use this when Rishi delivers his 15 bill JSONs.
    """
    if not os.path.exists(bills_folder):
        print(f"⚠️  Folder not found: {bills_folder}")
        print(f"   Create it and put ingested bill JSONs inside")
        return

    json_files = [
        f for f in os.listdir(bills_folder)
        if f.endswith(".json")
    ]

    if not json_files:
        print(f"⚠️  No JSON files found in {bills_folder}")
        return

    print(f"\n📚 Embedding {len(json_files)} bills...")
    total = 0

    for fname in json_files:
        path = os.path.join(bills_folder, fname)
        try:
            count = embed_bill(path)
            total += count
        except Exception as e:
            print(f"   ❌ Failed: {fname} — {e}")

    print(f"\n✅ Total sections embedded: {total}")


def get_collection_stats() -> dict:
    """Show what's currently in the vector DB."""
    client     = _get_chroma_client()
    collection = _get_collection(client)
    count      = collection.count()

    print(f"\n📊 ChromaDB Stats:")
    print(f"   Total sections: {count}")

    if count > 0:
        # Get unique bill IDs
        sample = collection.get(limit=count)
        bill_ids = set(m["bill_id"] for m in sample["metadatas"])
        print(f"   Bills indexed : {len(bill_ids)}")
        for bid in sorted(bill_ids):
            bill_count = sum(
                1 for m in sample["metadatas"]
                if m["bill_id"] == bid
            )
            print(f"     • {bid}: {bill_count} sections")

    return {"total_sections": count}


if __name__ == "__main__":
    # Embed the current ingested_bill.json
    embed_bill("ingested_bill.json")
    get_collection_stats()