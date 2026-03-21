"""
shared_schemas.py
=================
Team contract — Pydantic models shared across all three modules.
ALL 3 MEMBERS review changes before merging to dev.

Owner: AkashSamuel (initial creation)
"""


from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class BillStatus(str, Enum):
    PENDING   = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


class SupportedLanguage(str, Enum):
    ENGLISH    = "en"
    HINDI      = "hi"
    BENGALI    = "bn"
    TELUGU     = "te"
    MARATHI    = "mr"
    TAMIL      = "ta"
    URDU       = "ur"
    GUJARATI   = "gu"
    KANNADA    = "kn"
    ODIA       = "or"
    PUNJABI    = "pa"
    MALAYALAM  = "ml"
    ASSAMESE   = "as"
    MAITHILI   = "mai"
    SANTALI    = "sat"
    KASHMIRI   = "ks"
    NEPALI     = "ne"
    SINDHI     = "sd"
    KONKANI    = "kok"
    DOGRI      = "doi"
    MANIPURI   = "mni"
    BODO       = "brx"


# ─────────────────────────────────────────────
# INGESTION  (rishi produces → AkashSamuel consumes)
# ─────────────────────────────────────────────

class RawDocument(BaseModel):
    """Output of rishi's ingestion pipeline."""
    doc_id:        str
    source_url:    Optional[str]   = None
    raw_text:      str
    token_count:   int
    language_hint: SupportedLanguage = SupportedLanguage.ENGLISH
    metadata:      dict            = Field(default_factory=dict)


# ─────────────────────────────────────────────
# COMPRESSION  (Akagami produces → AkashSamuel consumes)
# ─────────────────────────────────────────────

class CompressedDocument(BaseModel):
    """Output of Akagami's token-compression pipeline."""
    doc_id:              str
    compressed_text:     str
    original_tokens:     int
    compressed_tokens:   int
    compression_ratio:   float          # compressed / original
    carbon_saved_grams:  Optional[float] = None


# ─────────────────────────────────────────────
# LLM SUMMARY  (Akagami's LLM step → AkashSamuel displays)
# ─────────────────────────────────────────────

class CitizenSummary(BaseModel):
    """Plain-language summary returned by the LLM."""
    doc_id:            str
    headline:          str
    key_points:        List[str]
    impact_statement:  str
    readability_score: Optional[float] = None   # rishi's scorer
    language:          SupportedLanguage = SupportedLanguage.ENGLISH


# ─────────────────────────────────────────────
# API CONTRACT  (AkashSamuel's FastAPI I/O)
# ─────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """POST /analyze — request body."""
    pdf_url:  Optional[str]           = None
    raw_text: Optional[str]           = None
    language: SupportedLanguage       = SupportedLanguage.ENGLISH


class AnalyzeResponse(BaseModel):
    """POST /analyze — response body (job ticket)."""
    task_id: str
    status:  BillStatus = BillStatus.PENDING
    message: str        = "Job queued successfully."


class BillDetailResponse(BaseModel):
    """GET /bills/{bill_id} — full result."""
    bill_id:            str
    status:             BillStatus
    raw_document:       Optional[RawDocument]       = None
    compressed_document: Optional[CompressedDocument] = None
    summary:            Optional[CitizenSummary]    = None
    error:              Optional[str]               = None

# ─────────────────────────────────────────────
# INGESTION INTERNALS  (Rishi → Akagami pipeline)
# Added for real pipeline integration — v1.0
# ─────────────────────────────────────────────

class BillSection(BaseModel):
    section_id:    str
    section_title: str
    section_text:  str
    token_count:   int
    page_number:   int


class IngestedBill(BaseModel):
    bill_id:            str
    source_url:         str
    page_count:         int
    sections:           List[BillSection]
    total_token_count:  int
    has_tables:         bool
    tables:             List[dict]


# ─────────────────────────────────────────────
# COMPRESSION OUTPUT  (Akagami's AnalysisResult)
# ─────────────────────────────────────────────

class AnalysisResult(BaseModel):
    bill_id:              str
    citizen_summary:      str
    key_changes:          List[str]
    affected_groups:      List[str]
    rights_impact:        str
    implementation_date:  str
    tokens_input:         int
    tokens_output:        int
    compression_ratio:    float
    carbon_saved_grams:   float