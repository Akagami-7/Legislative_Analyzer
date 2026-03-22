"""
src/compression/rag_embedder.py
================================
Embeds ingested bill sections into ChromaDB.
Model priority:
  1. paraphrase-multilingual-mpnet-base-v2  (primary)
  2. paraphrase-multilingual-MiniLM-L12-v2  (secondary)
  3. intfloat/multilingual-e5-base           (tertiary)
v2.0 Sprint 1 Day 4-5
Owner: Akagami
"""

import json
import os
import sys
import gc
import torch
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["TOKENIZERS_PARALLELISM"]   = "false"

# ── ChromaDB persistent storage ───────────────────────────────────────────────
CHROMA_PATH = "./chroma_db"

# ── Model priority list ───────────────────────────────────────────────────────
EMBEDDING_MODELS = [
    "paraphrase-multilingual-mpnet-base-v2",   # primary   — 420MB, best quality
    "paraphrase-multilingual-MiniLM-L12-v2",   # secondary — 420MB, lighter
    "intfloat/multilingual-e5-base",            # tertiary  — 560MB, strong multilingual
]

_embed_model       = None
_loaded_model_name = None


def _get_device() -> str:
    """Return best available device."""
    if torch.cuda.is_available():
        free_vram = (
            torch.cuda.get_device_properties(0).total_memory
            - torch.cuda.memory_allocated()
        ) / 1024**3
        print(f"   GPU detected — {free_vram:.1f}GB VRAM free")
        return "cuda"
    print("   No GPU — using CPU")
    return "cpu"


def _get_embed_model() -> SentenceTransformer:
    """
    Load embedding model with fallback chain.
    Tries primary → secondary → tertiary.
    """
    global _embed_model, _loaded_model_name

    if _embed_model is not None:
        return _embed_model

    device = _get_device()

    for model_name in EMBEDDING_MODELS:
        try:
            print(f"   Loading: {model_name}...")
            _embed_model = SentenceTransformer(model_name, device=device)
            _loaded_model_name = model_name
            print(f"   ✅ Loaded: {model_name}")

            if device == "cuda":
                used = torch.cuda.memory_allocated() / 1024**3
                print(f"   VRAM used by model: {used:.2f}GB")

            return _embed_model

        except Exception as e:
            print(f"   ⚠️  Failed ({model_name}): {e}")
            _embed_model = None
            if device == "cuda":
                torch.cuda.empty_cache()
                gc.collect()
            continue

    raise RuntimeError(
        "All embedding models failed to load. "
        "Check your internet connection and dependencies."
    )


def _get_dynamic_batch_size() -> int:
    """
    Determine optimal batch size based on available VRAM or RAM.
    """
    if torch.cuda.is_available():
        free_vram = (
            torch.cuda.get_device_properties(0).total_memory
            - torch.cuda.memory_allocated()
        ) / 1024**3
        if free_vram > 10:
            return 256
        elif free_vram > 6:
            return 128
        elif free_vram > 3:
            return 64
        elif free_vram > 1.5:
            return 32
        else:
            return 16
    else:
        # CPU — use small batches
        import psutil
        free_ram = psutil.virtual_memory().available / 1024**3
        if free_ram > 4:
            return 32
        elif free_ram > 2:
            return 16
        else:
            return 8


def _get_chroma_client() -> chromadb.PersistentClient:
    """Get persistent ChromaDB client."""
    os.makedirs(CHROMA_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_PATH)


def _get_collection(client: chromadb.PersistentClient):
    """Get or create the bills collection."""
    return client.get_or_create_collection(
        name="indian_bills",
        metadata={"description": "Indian parliamentary bill sections — v2.0"}
    )


def embed_bill(json_path: str) -> int:
    """
    Embed all sections of a bill into ChromaDB.

    Args:
        json_path: Path to ingested bill JSON file

    Returns:
        Number of sections embedded
    """
    print(f"\n📥 Embedding: {json_path}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    bill_id  = data["bill_id"]
    sections = data["sections"]

    print(f"   Bill ID  : {bill_id}")
    print(f"   Sections : {len(sections)}")

    if len(sections) <= 2:
        print(f"   ⚠️  Too few sections — skipping")
        print(f"       (Rishi needs to fix ingestion for this bill)")
        return 0

    model      = _get_embed_model()
    client     = _get_chroma_client()
    collection = _get_collection(client)

    # ── Check existing ────────────────────────────────────────────────────────
    existing = set()
    try:
        result   = collection.get(where={"bill_id": bill_id})
        existing = set(result["ids"])
        if existing:
            print(f"   Already embedded: {len(existing)} sections — skipping")
            return 0
    except Exception:
        pass

    # ── Prepare data ──────────────────────────────────────────────────────────
    texts, ids, metadatas = [], [], []
    seen_ids = {}

    for section in sections:
        base_id = f"{bill_id}__{section['section_id']}"

        if base_id in seen_ids:
            seen_ids[base_id] += 1
            section_id = f"{base_id}_{seen_ids[base_id]}"
        else:
            seen_ids[base_id] = 0
            section_id = base_id

        if section_id in existing:
            continue

        text = section.get("section_text", "").strip()
        if len(text) < 30:
            continue

        # multilingual-e5-base needs "passage: " prefix for passages
        if _loaded_model_name == "intfloat/multilingual-e5-base":
            embed_text = f"passage: {text[:1000]}"
        else:
            embed_text = text[:1000]

        texts.append(embed_text)
        ids.append(section_id)
        metadatas.append({
            "bill_id"      : bill_id,
            "section_id"   : section["section_id"],
            "section_title": section.get("section_title", "")[:200],
            "page_number"  : section.get("page_number", 1),
            "token_count"  : section.get("token_count", 0)
        })

    if not texts:
        print(f"   ✅ Nothing new to embed")
        return 0

    # ── Embed with auto batch sizing ──────────────────────────────────────────
    print(f"   Embedding {len(texts)} sections...")

    batch_size     = _get_dynamic_batch_size()
    all_embeddings = []
    total_batches  = (len(texts) - 1) // batch_size + 1

    print(f"   Batch size: {batch_size} | Total batches: {total_batches}")

    for i in range(0, len(texts), batch_size):
        batch       = texts[i:i + batch_size]
        batch_num   = i // batch_size + 1
        retry_count = 0

        while retry_count < 3:
            try:
                with torch.no_grad():
                    embeddings = model.encode(
                        batch,
                        batch_size=batch_size,
                        show_progress_bar=False,
                        normalize_embeddings=True,
                        convert_to_numpy=True
                    )

                all_embeddings.extend(embeddings.tolist())

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()

                done = min(i + batch_size, len(texts))
                print(f"   Batch {batch_num}/{total_batches} "
                      f"[{done}/{len(texts)}] ✓", end="\r")
                break

            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    retry_count += 1
                    batch_size = max(4, batch_size // 2)

                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    gc.collect()

                    print(f"\n   ⚠️  OOM — retry {retry_count}/3 "
                          f"with batch_size={batch_size}")
                else:
                    raise e

        if retry_count == 3:
            print(f"\n   ❌ Batch {batch_num} failed after 3 retries — skipping")
            # Fill with zero embeddings to maintain index alignment
            zero_dim = len(all_embeddings[0]) if all_embeddings else 768
            for _ in batch:
                all_embeddings.append([0.0] * zero_dim)

    print()  # newline after \r progress

    # ── Store in ChromaDB (chunks of 500) ─────────────────────────────────────
    chunk_size = 500
    for i in range(0, len(ids), chunk_size):
        collection.add(
            ids       =ids[i:i + chunk_size],
            embeddings=all_embeddings[i:i + chunk_size],
            documents =texts[i:i + chunk_size],
            metadatas =metadatas[i:i + chunk_size]
        )

    print(f"   ✅ Embedded {len(texts)} sections")
    print(f"   📁 Saved to: {CHROMA_PATH}")
    print(f"   🧠 Model used: {_loaded_model_name}")
    return len(texts)


def embed_all_bills(bills_folder: str = "./ingested_bills") -> int:
    """
    Embed all bills in a folder.
    Skips already-embedded bills automatically.

    Args:
        bills_folder: Folder containing ingested bill JSONs

    Returns:
        Total sections embedded
    """
    if not os.path.exists(bills_folder):
        print(f"⚠️  Folder not found: {bills_folder}")
        return 0

    json_files = sorted([
        f for f in os.listdir(bills_folder)
        if f.endswith(".json")
    ])

    if not json_files:
        print(f"⚠️  No JSON files found in {bills_folder}")
        return 0

    print(f"\n📚 Embedding {len(json_files)} bills from {bills_folder}")
    print(f"   Model priority: {' → '.join(EMBEDDING_MODELS)}\n")

    total  = 0
    failed = []

    for fname in json_files:
        path = os.path.join(bills_folder, fname)
        try:
            count = embed_bill(path)
            total += count
        except Exception as e:
            print(f"   ❌ Failed: {fname} — {e}")
            failed.append(fname)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

    print(f"\n{'='*50}")
    print(f"✅ Total sections embedded : {total}")
    print(f"❌ Failed bills            : {len(failed)}")
    for f in failed:
        print(f"   • {f}")

    return total


def get_collection_stats() -> dict:
    """Show what's currently indexed in ChromaDB."""
    client     = _get_chroma_client()
    collection = _get_collection(client)
    count      = collection.count()

    print(f"\n📊 ChromaDB Stats:")
    print(f"   Total sections : {count}")
    print(f"   Storage path   : {CHROMA_PATH}")

    if count > 0:
        sample   = collection.get(limit=count)
        bill_ids = {}
        for m in sample["metadatas"]:
            bid = m["bill_id"]
            bill_ids[bid] = bill_ids.get(bid, 0) + 1

        print(f"   Bills indexed  : {len(bill_ids)}")
        print()
        for bid, cnt in sorted(bill_ids.items()):
            status = "✅" if cnt > 5 else "⚠️ "
            print(f"   {status} {bid}: {cnt} sections")

    return {"total_sections": count, "chroma_path": CHROMA_PATH}


def clear_collection() -> None:
    """Delete all data from ChromaDB. Use with caution."""
    client = _get_chroma_client()
    client.delete_collection("indian_bills")
    print("🗑️  Collection cleared")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        embed_bill(sys.argv[1])
    else:
        embed_all_bills("./ingested_bills")
        embed_bill("ingested_bill.json")
    get_collection_stats()