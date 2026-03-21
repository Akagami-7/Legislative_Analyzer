"""
src/api/services/mock_pipeline.py
==================================
v1.0 mock — simulates the full ingestion → compression → LLM pipeline
so the frontend and API can be developed and tested independently
of rishi's and Akagami's real implementations.

Replace the internals of `mock_run_pipeline` when real modules are ready.
Owner: AkashSamuel
"""

import time
from typing import Dict

from src.shared_schemas import (
    AnalyzeRequest,
    BillDetailResponse,
    BillStatus,
    CitizenSummary,
    CompressedDocument,
    RawDocument,
    SupportedLanguage,
)

# In-memory store  →  swap for Redis in v2.0
task_store: Dict[str, BillDetailResponse] = {}


# ── helpers ──────────────────────────────────────────────────────────────────

def _fake_raw_document(task_id: str, text: str) -> RawDocument:
    return RawDocument(
        doc_id      = task_id,
        source_url  = None,
        raw_text    = text,
        token_count = len(text.split()),   # rough word count as proxy
        language_hint = SupportedLanguage.ENGLISH,
        metadata    = {"mock": True},
    )


def _fake_compressed_document(task_id: str, raw: RawDocument) -> CompressedDocument:
    # Simulates ~60 % compression
    compressed = raw.raw_text[: max(50, len(raw.raw_text) // 2)]
    orig  = raw.token_count
    compr = len(compressed.split())
    return CompressedDocument(
        doc_id             = task_id,
        compressed_text    = compressed,
        original_tokens    = orig,
        compressed_tokens  = compr,
        compression_ratio  = round(compr / orig, 3) if orig else 1.0,
        carbon_saved_grams = round((orig - compr) * 0.0004, 4),
    )


def _fake_summary(task_id: str, language: SupportedLanguage) -> CitizenSummary:
    return CitizenSummary(
        doc_id           = task_id,
        headline         = "Mock Bill: Digital Personal Data Protection (Amendment) Act, 2024",
        key_points       = [
            "All digital personal data must be collected with explicit consent.",
            "Citizens gain the right to erase their data from any platform.",
            "Companies face fines up to ₹250 crore for data breaches.",
            "A Data Protection Board will oversee compliance.",
        ],
        impact_statement = (
            "This bill strengthens your privacy rights online. "
            "You can now demand deletion of your personal data from any website or app, "
            "and companies that misuse it will face heavy penalties."
        ),
        readability_score = 72.4,
        language          = language,
    )


# ── public entry point ───────────────────────────────────────────────────────

def mock_run_pipeline(task_id: str, request: AnalyzeRequest) -> None:
    """
    Synchronous mock of the full pipeline.
    Sets task_store[task_id] to a completed BillDetailResponse.

    In v2.0 this becomes a Celery task:
        @celery_app.task
        def run_pipeline(task_id, request_dict): ...
    """
    # Mark as processing
    task_store[task_id] = BillDetailResponse(
        bill_id = task_id,
        status  = BillStatus.PROCESSING,
    )

    try:
        source_text = request.raw_text or (
            f"[Mock text fetched from: {request.pdf_url}] "
            "The Digital Personal Data Protection Bill seeks to establish a framework "
            "for the processing of digital personal data in India, balancing the right "
            "of individuals to protect their personal data with the need to process such "
            "data for lawful purposes and for matters connected therewith or incidental thereto."
        )

        raw        = _fake_raw_document(task_id, source_text)
        compressed = _fake_compressed_document(task_id, raw)
        summary    = _fake_summary(task_id, request.language)

        task_store[task_id] = BillDetailResponse(
            bill_id             = task_id,
            status              = BillStatus.COMPLETED,
            raw_document        = raw,
            compressed_document = compressed,
            summary             = summary,
        )

    except Exception as exc:  # noqa: BLE001
        task_store[task_id] = BillDetailResponse(
            bill_id = task_id,
            status  = BillStatus.FAILED,
            error   = str(exc),
        )
