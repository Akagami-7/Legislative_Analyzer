import json
import sys
import os
sys.path.append('.')

from src.shared_schemas import IngestedBill, BillSection
from src.compression.semantic_chunker import semantic_chunk_bill
from src.compression.bm25_ranker import rank_and_filter
from src.compression.extractor import extractive_compress
from src.compression.prompt_assembler import assemble_prompt
from src.compression.token_logger import log_compression
from src.compression.llm_client import analyze_with_gemini
from src.compression.translator import translate_result
from src.compression.rag_embedder import embed_bill, get_collection_stats
from src.compression.rag_retriever import retrieve_context, format_rag_context
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

# def semantic_chunk_bill(data: dict):
#     """
#     Rishi's splitter only detected CHAPTER boundaries.
#     This re-splits each chapter into individual sections
#     using the actual Section numbering inside the text.
#     """
#     import re
#     fixed = []
#     counter = 0

#     SECTION_PATTERN = re.compile(
#         r'(?=(?:^|\n)\s*'
#         r'(?:\d+\.\s+'          # 1. Short title
#         r'|\d+[A-Z]\.\s+'       # 4A. Special provision  
#         r'|Section\s+\d+'       # Section 4
#         r'))',
#         re.MULTILINE
#     )

#     for chapter in data["sections"]:
#         chapter_text = chapter["section_text"]
#         chapter_title = chapter["section_title"]

#         # Try to split this chapter into individual sections
#         splits = SECTION_PATTERN.split(chapter_text)
#         splits = [s.strip() for s in splits if len(s.strip()) > 60]

#         if len(splits) <= 1:
#             # Could not split further — keep as is
#             fixed.append(BillSection(
#                 section_id=chapter["section_id"],
#                 section_title=chapter_title,
#                 section_text=chapter_text,
#                 token_count=len(enc.encode(chapter_text)),
#                 page_number=chapter["page_number"]
#             ))
#         else:
#             # Successfully split into individual sections
#             for i, split_text in enumerate(splits):
#                 # Extract section number from text start
#                 first_line = split_text.split('\n')[0][:60]
#                 fixed.append(BillSection(
#                     section_id=f"{chapter['section_id']}_s{i}",
#                     section_title=f"{chapter_title} — {first_line}",
#                     section_text=split_text,
#                     token_count=len(enc.encode(split_text)),
#                     page_number=chapter["page_number"]
#                 ))
#                 counter += 1

#     print(f"\n🔧 Section re-split: {len(data['sections'])} chapters "
#           f"→ {len(fixed)} individual sections")
#     return fixed

def run_pipeline(json_path: str) -> None:

    print(f"\n{'='*60}")
    print("   AI LEGISLATIVE ANALYZER — COMPRESSION PIPELINE")
    print(f"{'='*60}")

    # ── 1. Load ───────────────────────────────────────────────
    print(f"\n📂 Loading: {json_path}")
    with open(json_path, encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    sections = semantic_chunk_bill(data)
    bill = IngestedBill(
        bill_id=data["bill_id"],
        source_url=data["source_url"],
        page_count=data["page_count"],
        sections=sections,
        total_token_count=sum(s.token_count for s in sections),
        has_tables=data["has_tables"],
        tables=[]
    )

    print(f"   Bill ID      : {bill.bill_id}")
    print(f"   Sections     : {len(bill.sections)}")
    print(f"   Total tokens : {bill.total_token_count:,}")

    # ── 2. BM25 Filter ────────────────────────────────────────
    def get_keep_ratio(section_count: int) -> float:
        if section_count < 50:
            return 0.7   # small bill — keep more
        elif section_count < 200:
            return 0.5   # medium
        else:
            return 0.4   # large bill — filter harder

    keep_ratio = get_keep_ratio(len(bill.sections))
    filtered = rank_and_filter(bill.sections, keep_ratio=keep_ratio)

    # ── 3. Extractive Compress ────────────────────────────────
    def get_sentence_budget(total_tokens: int) -> int:
        if total_tokens < 20000:
            return 4   # small bill — keep more
        elif total_tokens < 60000:
            return 3   # medium bill
        else:
            return 2   # large bill — compress harder

    sentence_budget = get_sentence_budget(bill.total_token_count)
    compressed = extractive_compress(filtered, sentences_per_section=sentence_budget)

    # ── 3.5 RAG Context Retrieval ────────────────────────────
    print(f"\n🔍 Retrieving RAG context...")
    civic_query = (
        f"{bill.bill_id} citizen rights penalty obligations "
        f"enforcement consent data protection"
    )
    retrieved   = retrieve_context(
        query=civic_query,
        current_bill_id=bill.bill_id,
        top_k=5,
        use_reranker=True
    )
    rag_context = format_rag_context(retrieved, max_tokens=2000)

    # ── 4. Assemble Prompt ────────────────────────────────────
    prompt, prompt_tokens = assemble_prompt(bill, compressed, rag_context)

    # ── 5. Log Compression ────────────────────────────────────
    log_compression(bill.bill_id, bill.total_token_count, prompt_tokens)

    # ── 6. Claude API Call ────────────────────────────────────
    from src.compression.token_logger import track_pipeline_emissions

    result = track_pipeline_emissions(
        bill.bill_id,
        bill.total_token_count,
        prompt_tokens,
        analyze_with_gemini,      # function to track
        prompt,                   # its arguments
        bill.total_token_count,
        prompt_tokens
    )

    # ── 7. Save Result ────────────────────────────────────────
    output_path = f"result_{bill.bill_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.model_dump_json(indent=2))

    print(f"\n{'='*60}")
    print("   RESULT")
    print(f"{'='*60}")
    print(f"\n📋 Summary:\n{result.citizen_summary}")
    print(f"\n🔑 Key Changes:")
    for change in result.key_changes:
        print(f"   • {change}")
    print(f"\n👥 Affected Groups: {', '.join(result.affected_groups)}")
    print(f"\n⚖️  Rights Impact: {result.rights_impact}")
    print(f"\n📅 Implementation: {result.implementation_date}")
    print(f"\n💾 Full result saved to: {output_path}")

    # ── 9. Translate to Hindi (v1.0 demo) ────────────────────
    hindi_result = translate_result(result, target_lang="hi")

    hindi_path = f"result_{bill.bill_id}_hindi.json"
    with open(hindi_path, "w", encoding="utf-8") as f:
        json.dump(hindi_result, f, ensure_ascii=False, indent=2)

    print(f"\n🇮🇳 Hindi translation saved to: {hindi_path}")
    print(f"\n📋 Hindi Summary:")
    print(f"   {hindi_result['citizen_summary']}")

if __name__ == "__main__":
    run_pipeline("ingested_bill.json")
