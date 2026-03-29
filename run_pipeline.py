"""
run_pipeline.py — UPDATED FOR SYNCHRONIZATION
==============================================
Standalone CLI pipeline for batch processing bills.

✅ SYNCHRONIZED: Uses updated modules with consistent field names
- semantic_chunk_bill() → fixed sections
- Compression pipeline → AnalysisResult with key_changes
- Translation → CitizenSummary with key_points
- Output → JSON files with proper structure

Owner: All team members
"""

import json
import sys
import os
import argparse
sys.path.append('.')

from src.shared_schemas import IngestedBill, BillSection
from src.compression.semantic_chunker import semantic_chunk_bill
from src.compression.bm25_ranker import rank_and_filter
from src.compression.extractor import extractive_compress
from src.compression.prompt_assembler import assemble_prompt
from src.compression.token_logger import log_compression
from src.compression.llm_client import analyze_with_gemini
from src.compression.translator import translate_result, convert_analysis_to_citizen_summary
from src.compression.rag_embedder import embed_bill, get_collection_stats
from src.compression.rag_retriever import retrieve_context, format_rag_context
from src.compression.multi_llm_client import analyze_with_llm
from src.compression.scaledown_client import try_scaledown_compress
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")


def run_pipeline(json_path: str) -> None:
    """
    ✅ SYNCHRONIZED: Run complete pipeline with proper data flow
    
    Flow:
    1. Load ingested bill JSON
    2. Semantic chunking
    3. BM25 ranking
    4. Extractive compression
    5. [Optional] ScaleDown
    6. [Optional] RAG retrieval
    7. Prompt assembly
    8. LLM analysis → AnalysisResult
    9. Convert to CitizenSummary
    10. [Optional] Translation
    11. Export JSON results
    """

    print(f"\n{'='*60}")
    print("   AI LEGISLATIVE ANALYZER — COMPRESSION PIPELINE")
    print(f"{'='*60}")

    # ── 1. Load ───────────────────────────────────────────────
    print(f"\n📂 Loading: {json_path}")
    with open(json_path, encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    # ── 2. Semantic Chunking ──────────────────────────────────
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

    # ── 3. BM25 Filter ────────────────────────────────────────
    def get_keep_ratio(section_count: int) -> float:
        """Dynamic compression parameters"""
        if section_count < 50:
            return 0.7
        elif section_count < 200:
            return 0.5
        else:
            return 0.4

    keep_ratio = get_keep_ratio(len(bill.sections))
    filtered = rank_and_filter(bill.sections, keep_ratio=keep_ratio)

    # ── 4. Extractive Compress ────────────────────────────────
    def get_sentence_budget(total_tokens: int) -> int:
        """Dynamic sentence budget based on document size"""
        if total_tokens < 20000:
            return 4
        elif total_tokens < 60000:
            return 3
        else:
            return 2

    sentence_budget = get_sentence_budget(bill.total_token_count)
    compressed = extractive_compress(filtered, sentences_per_section=sentence_budget)

    # Build compressed text and check expansion
    compressed_text = "\n\n".join(
        f"[{s.section_title}]\n{s.section_text}"
        for s in compressed
    )

    compressed_tokens = len(enc.encode(compressed_text))

    if compressed_tokens >= bill.total_token_count:
        print("⚠️  Extractive compression expanded → reverting to original")
        compressed = bill.sections
        compressed_text = "\n\n".join(
            f"[{s.section_title}]\n{s.section_text}"
            for s in compressed
        )

    # ── 4.5 ScaleDown (optional) ──────────────────────────────
    scaledown_api_key = os.getenv("SCALEDOWN_API_KEY")
    use_scaledown     = scaledown_api_key is not None

    if use_scaledown:
        print(f"\n⚡ Running ScaleDown compression...")

        sd_text, sd_metrics = try_scaledown_compress(
            text=compressed_text,
            api_key=scaledown_api_key,
            model="llama-3-1-70b",
            rate="auto"
        )

        # 🔧 SAFETY CHECK
        orig_tokens = len(enc.encode(compressed_text))
        sd_tokens   = len(enc.encode(sd_text))

        if sd_tokens >= orig_tokens:
            print("⚠️  ScaleDown expanded → reverting")
            sd_text = compressed_text

        from src.shared_schemas import BillSection
        compressed = [BillSection(
            section_id    = "scaledown_compressed",
            section_title = "ScaleDown Compressed Content",
            section_text  = sd_text,
            token_count   = len(enc.encode(sd_text)),
            page_number   = 1
        )]

        compressed_text = sd_text

        print(f"   ScaleDown reduction: {sd_metrics.get('reduction_percent', 0)}%")
    else:
        print(f"\n   ScaleDown: disabled (no API key)")

    # ── 5. RAG Context Retrieval (optional) ───────────────────
    print(f"\nRetrieving RAG context...")

    civic_query = (
        f"{bill.bill_id} citizen rights penalty obligations "
        f"enforcement consent data protection"
    )

    retrieved = retrieve_context(
        query=civic_query,
        current_bill_id=bill.bill_id,
        top_k=5,
        use_reranker=True
    )

    # Dynamic token budget
    MAX_PROMPT_BUDGET = 8000
    RAG_LIMIT = 2000

    compressed_tokens = len(enc.encode(compressed_text))
    remaining_budget = MAX_PROMPT_BUDGET - compressed_tokens
    rag_token_budget = max(0, min(RAG_LIMIT, remaining_budget))

    rag_context = format_rag_context(
        retrieved,
        max_tokens=rag_token_budget
    )

    # ── 6. Assemble Prompt ────────────────────────────────────
    prompt, prompt_tokens = assemble_prompt(bill, compressed, rag_context)

    # 🔧 FINAL EXPANSION GUARD
    if prompt_tokens >= bill.total_token_count:
        print("⚠️  Final prompt expanded beyond original bill!")
        print("Removing RAG context to control size...")

        prompt, prompt_tokens = assemble_prompt(bill, compressed, rag_context="")

    # ── 7. Log Compression ────────────────────────────────────
    log_compression(bill.bill_id, bill.total_token_count, prompt_tokens)

    # ── 8. LLM Call ───────────────────────────────────────────
    from src.compression.token_logger import track_pipeline_emissions

    # ✅ SYNCHRONIZED: Use multi_llm_client with provider selection
    provider = os.getenv("LLM_PROVIDER", "gemini")
    api_key = os.getenv(f"{provider.upper()}_API_KEY")
    model = os.getenv("LLM_MODEL")

    result = track_pipeline_emissions(
        bill.bill_id,
        bill.total_token_count,
        prompt_tokens,
        analyze_with_llm,
        prompt,
        bill.total_token_count,
        prompt_tokens,
        provider=provider,
        api_key=api_key,
        model=model
    )

    # ✅ SYNCHRONIZED: result is AnalysisResult with key_changes

    # ── 9. Convert to CitizenSummary ─────────────────────────
    citizen_summary = convert_analysis_to_citizen_summary(result, language="en")

    # ── 10. Save Result ────────────────────────────────────────
    output_path = f"result_{bill.bill_id}.json"
    
    # Save as CitizenSummary (for frontend compatibility)
    output_data = {
        "bill_id": citizen_summary.bill_id,
        "headline": citizen_summary.headline,
        "key_points": citizen_summary.key_points,  # ✅ SYNCED
        "impact_statement": citizen_summary.impact_statement,
        "overview": citizen_summary.overview,
        "language": citizen_summary.language.value if hasattr(citizen_summary.language, 'value') else citizen_summary.language,
        "metadata": {
            "original_tokens": bill.total_token_count,
            "compressed_tokens": prompt_tokens,
            "compression_ratio": round(1 - (prompt_tokens / bill.total_token_count), 4),
            "carbon_saved_grams": result.carbon_saved_grams
        }
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print("   RESULT")
    print(f"{'='*60}")
    print(f"\nHeadline:\n{citizen_summary.headline}")

    print(f"\n🔑 Key Points:")
    for point in citizen_summary.key_points:
        print(f"   • {point}")

    print(f"\nImpact Statement:\n{citizen_summary.impact_statement}")

    if citizen_summary.overview:
        print(f"\nOverview:\n{citizen_summary.overview}")

    print(f"\nFull result saved to: {output_path}")

    # ── 11. Translate to Hindi (optional) ────────────────────
    hindi_result = translate_result(result, target_lang="hi")

    hindi_path = f"result_{bill.bill_id}_hindi.json"
    with open(hindi_path, "w", encoding="utf-8") as f:
        json.dump(hindi_result, f, ensure_ascii=False, indent=2)

    print(f"\n🇮🇳 Hindi translation saved to: {hindi_path}")
    print(f"\nHindi Headline:")
    print(f"   {hindi_result['headline']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the AI Legislative Analyzer compression pipeline."
    )
    parser.add_argument(
        "json_path",
        nargs="?",
        help="Path to the ingested bill JSON file."
    )
    args = parser.parse_args()

    json_path = args.json_path

    if not json_path:
        # Try to find a default file in 'ingested_bills' directory
        ingested_dir = "ingested_bills"
        if os.path.exists(ingested_dir):
            files = [f for f in os.listdir(ingested_dir) if f.endswith(".json")]
            if files:
                json_path = os.path.join(ingested_dir, files[0])
                print(f"No input file specified. Using default: {json_path}")
            else:
                print(f"❌ Error: No JSON files found in '{ingested_dir}' directory.")
                sys.exit(1)
        else:
            print(f"❌ Error: 'ingested_bills' directory does not exist.")
            print("Please specify a JSON file to process.")
            sys.exit(1)

    if not os.path.exists(json_path):
        print(f"❌ Error: File not found: {json_path}")
        # Suggest available files if possible
        if os.path.exists("ingested_bills"):
            files = [f for f in os.listdir("ingested_bills") if f.endswith(".json")]
            if files:
                print("\nAvailable bills in 'ingested_bills/':")
                for f in files[:10]:
                    print(f"  • ingested_bills/{f}")
                if len(files) > 10:
                    print(f"  ... and {len(files) - 10} more.")
        sys.exit(1)

    try:
        run_pipeline(json_path)
    except KeyboardInterrupt:
        print("\n👋 Pipeline stopped by user.")
    except Exception as e:
        print(f"\n💥 Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

