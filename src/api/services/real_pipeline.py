"""
src/api/services/real_pipeline.py
===================================
Real pipeline — calls Akagami's compression + Rishi's ingestion.
Replaces mock_pipeline.py for v1.0 real demo.
"""

import json
import uuid
import tempfile
import os
import sys
sys.path.append('.')

from src.shared_schemas import (
    BillDetailResponse, BillStatus, CitizenSummary,
    CompressedDocument, RawDocument, SupportedLanguage,
    AnalyzeRequest
)

# Import real pipeline components
from src.compression.bm25_ranker import rank_and_filter
from src.compression.extractor import extractive_compress
from src.compression.prompt_assembler import assemble_prompt
from src.compression.token_logger import log_compression, track_pipeline_emissions
from src.compression.translator import translate_result
from src.ingestion.scraper import scrape_bill
from src.ingestion.pdf_parser import parse_pdf
from src.ingestion.ocr_engine import run_ocr
from src.ingestion.section_splitter import split_sections
from src.ingestion.ner_pipeline import extract_entities
from src.shared_schemas import IngestedBill
from src.compression.multi_llm_client import analyze_with_llm
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

# In-memory store — swap for Redis in v2.0
task_store = {}


def fix_sections(data: dict):
    import re
    fixed = []
    SECTION_PATTERN = re.compile(
        r'(?=(?:^|\n)\s*'
        r'(?:\d+\.\s+'
        r'|\d+[A-Z]\.\s+'
        r'|Section\s+\d+'
        r'))',
        re.MULTILINE
    )
    from src.shared_schemas import BillSection
    for chapter in data["sections"]:
        chapter_text  = chapter["section_text"]
        chapter_title = chapter["section_title"]
        splits = SECTION_PATTERN.split(chapter_text)
        splits = [s.strip() for s in splits if len(s.strip()) > 60]
        if len(splits) <= 1:
            fixed.append(BillSection(
                section_id=chapter["section_id"],
                section_title=chapter_title,
                section_text=chapter_text,
                token_count=len(enc.encode(chapter_text)),
                page_number=chapter["page_number"]
            ))
        else:
            for i, split_text in enumerate(splits):
                first_line = split_text.split('\n')[0][:60]
                fixed.append(BillSection(
                    section_id=f"{chapter['section_id']}_s{i}",
                    section_title=f"{chapter_title} — {first_line}",
                    section_text=split_text,
                    token_count=len(enc.encode(split_text)),
                    page_number=chapter["page_number"]
                ))
    return fixed


def real_run_pipeline(task_id: str, request: AnalyzeRequest) -> None:
    """
    Real pipeline replacing mock_run_pipeline.
    Calls Rishi's ingestion → Akagami's compression → Gemini LLM.
    """

    # Mark as processing
    task_store[task_id] = BillDetailResponse(
        bill_id=task_id,
        status=BillStatus.PROCESSING
    )

    try:
        # ── Step 1: Get PDF ───────────────────────────────────
        if request.pdf_url:
            pdf_path = scrape_bill(request.pdf_url)
        else:
            raise ValueError("pdf_url is required")

        # ── Step 2: Ingest ────────────────────────────────────
        parsed = parse_pdf(pdf_path)
        if parsed["is_scanned"]:
            parsed["pages"] = run_ocr(pdf_path)

        sections = split_sections(parsed["pages"])
        bill_id_slug = task_id.replace("-", "_")[:30]

        ingested = IngestedBill(
            bill_id=bill_id_slug,
            source_url=request.pdf_url or "",
            page_count=parsed["page_count"],
            sections=sections,
            total_token_count=sum(s.token_count for s in sections),
            has_tables=len(parsed["tables"]) > 0,
            tables=[]
        )

        # Save ingested JSON temporarily
        ingested_path = f"ingested_{bill_id_slug}.json"
        with open(ingested_path, "w", encoding="utf-8") as f:
            f.write(ingested.model_dump_json(indent=2))

        # ── Step 3: Compress ──────────────────────────────────
        data = json.loads(ingested.model_dump_json())
        fixed_sections = fix_sections(data)

        bill = IngestedBill(
            bill_id=ingested.bill_id,
            source_url=ingested.source_url,
            page_count=ingested.page_count,
            sections=fixed_sections,
            total_token_count=sum(s.token_count for s in fixed_sections),
            has_tables=ingested.has_tables,
            tables=[]
        )

        # Dynamic params
        section_count = len(bill.sections)
        if section_count < 50:
            keep_ratio = 0.7
            sentences  = 4
        elif section_count < 200:
            keep_ratio = 0.5
            sentences  = 3
        else:
            keep_ratio = 0.4
            sentences  = 2

        filtered   = rank_and_filter(bill.sections, keep_ratio=keep_ratio)
        compressed = extractive_compress(filtered, sentences_per_section=sentences)

        # Get ScaleDown settings from request
        use_scaledown     = getattr(request, 'use_scaledown', False)
        scaledown_api_key = getattr(request, 'scaledown_api_key', None)

        if use_scaledown and scaledown_api_key:
            print(f"\n⚡ Running ScaleDown compression...")
            from src.compression.scaledown_client import try_scaledown_compress
            compressed_text = "\n\n".join(
                f"[{s.section_title}]\n{s.section_text}"
                for s in compressed
            )
            sd_text, sd_metrics = try_scaledown_compress(
                text=compressed_text,
                api_key=scaledown_api_key,
                model="llama-3-1-70b",
                rate="auto"
            )
            from src.shared_schemas import BillSection
            enc2 = tiktoken.get_encoding("cl100k_base")
            compressed = [BillSection(
                section_id    = "scaledown_compressed",
                section_title = "ScaleDown Compressed",
                section_text  = sd_text,
                token_count   = len(enc2.encode(sd_text)),
                page_number   = 1
            )]

        prompt, prompt_tokens = assemble_prompt(bill, compressed)

        log_compression(bill.bill_id, bill.total_token_count, prompt_tokens)

        # ── Step 4: LLM Call ──────────────────────────────────
        provider = getattr(request, "llm_provider", "gemini")
        api_key  = getattr(request, "llm_api_key", None)

        try:
            analysis = track_pipeline_emissions(
                bill.bill_id,
                bill.total_token_count,
                prompt_tokens,
                analyze_with_llm,
                prompt,
                bill.total_token_count,
                prompt_tokens,
                provider=provider,
                api_key=api_key
            )

        except Exception as e:
            print(f"⚠️ LLM failed: {e}")

            # ✅ fallback to smaller Groq model
            try:
                print("🔁 Retrying with fallback model (llama-3.1-8b-instant)...")
                analysis = track_pipeline_emissions(
                    bill.bill_id,
                    bill.total_token_count,
                    prompt_tokens,
                    analyze_with_llm,
                    prompt,
                    bill.total_token_count,
                    prompt_tokens,
                    provider="groq",
                    api_key=api_key,
                    model="llama-3.1-8b-instant"
                )
            except Exception as e2:
                print(f"❌ Fallback also failed: {e2}")

                # Finally raise an explicit error to trigger the UI failure state gracefully
                raise ValueError("⚠️ Analysis failed due to API token limits on a very large document. Please retry in 1 minute or switch LLM providers.")

        # ── Step 5: Translate if needed ───────────────────────
        lang_code = request.language.value
        if lang_code != "en":
            # Get HF token from request or env
            hf_token = getattr(request, 'hf_token', None) or os.getenv("HUGGINGFACE_TOKEN")
            
            translated = translate_result(
                analysis, 
                target_lang=lang_code,
                hf_token=hf_token
            )
            citizen_summary_text = translated["citizen_summary"]
            key_points = translated["key_changes"]
            impact = translated["rights_impact"]
            overview = translated.get("overview")
        else:
            citizen_summary_text = analysis.citizen_summary
            key_points = analysis.key_changes
            impact = analysis.rights_impact
            overview = getattr(analysis, "overview", None)

        # ── Step 6: Build response in AkashSamuel's schema ───
        if prompt_tokens <= bill.total_token_count:
            compression_ratio = round(
                1 - (prompt_tokens / bill.total_token_count), 4
            )
        else:
            compression_ratio = 0.0  # ❗ no compression → avoid negative UI bug

        raw_doc = RawDocument(
            bill_id=task_id,
            source_url=request.pdf_url,
            raw_text=f"[Ingested {len(bill.sections)} sections]",
            token_count=bill.total_token_count,
            language_hint=SupportedLanguage.ENGLISH,
            metadata={
                "page_count": bill.page_count,
                "section_count": len(bill.sections)
            }
        )

        compressed_doc = CompressedDocument(
            bill_id=task_id,
            compressed_text=f"[Compressed to {prompt_tokens} tokens]",
            original_tokens=bill.total_token_count,
            compressed_tokens=prompt_tokens,
            compression_ratio=compression_ratio,
            carbon_saved_grams=getattr(analysis, "carbon_saved_grams", 0.0)
        )

        summary = CitizenSummary(
            bill_id=task_id,
            headline=citizen_summary_text.split('.')[0] + '.',
            key_points=key_points,
            impact_statement=impact,
            overview=overview,
            readability_score=None,
            language=request.language
        )

        task_store[task_id] = BillDetailResponse(
            bill_id=task_id,
            status=BillStatus.COMPLETED,
            raw_document=raw_doc,
            compressed_document=compressed_doc,
            summary=summary
        )

        # Cleanup temp files
        if os.path.exists(ingested_path):
            os.remove(ingested_path)

    except Exception as exc:
        task_store[task_id] = BillDetailResponse(
            bill_id=task_id,
            status=BillStatus.FAILED,
            error=str(exc)
        )
        raise
