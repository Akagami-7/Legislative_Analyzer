"""
shared_schemas.py
=================
Team contract — Pydantic models shared across all three modules.
ALL 3 MEMBERS review changes before merging to dev.

Owner: AkashSamuel (initial creation)
UPDATED: Synchronized with multi_llm_client, translator, and pipeline modules
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
    DONE       = "done"  # Alternative for completed
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
    bill_id:        str
    source_url:     Optional[str] = None
    raw_text:       str
    token_count:    int
    language_hint:  SupportedLanguage = SupportedLanguage.ENGLISH
    metadata:       dict = Field(default_factory=dict)


# ─────────────────────────────────────────────
# COMPRESSION  (Akagami produces → AkashSamuel consumes)
# ─────────────────────────────────────────────

class CompressedDocument(BaseModel):
    bill_id:             str
    compressed_text:     str
    original_tokens:     int
    compressed_tokens:   int
    compression_ratio:   float
    carbon_saved_grams:  Optional[float] = None


# ─────────────────────────────────────────────
# LLM SUMMARY  (Akagami's LLM step → AkashSamuel displays)
# ✅ SYNCHRONIZED: Uses key_points (not key_changes) for consistency
# ─────────────────────────────────────────────

class CitizenSummary(BaseModel):
    bill_id:            str
    headline:           str
    key_points:         List[str]           # ✅ SYNCED with multi_llm_client output
    impact_statement:   str
    overview:           Optional[str] = None
    readability_score:  Optional[float] = None
    language:           SupportedLanguage = SupportedLanguage.ENGLISH


# ─────────────────────────────────────────────
# API CONTRACT  (AkashSamuel's FastAPI I/O)
# ─────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """POST /analyze — request body."""
    pdf_url:  Optional[str]           = None
    raw_text: Optional[str]           = None
    language: SupportedLanguage       = SupportedLanguage.ENGLISH
    llm_provider: str                 = "gemini"
    llm_api_key:  Optional[str]       = None
    llm_model:          Optional[str]     = None
    use_scaledown:      bool              = False
    scaledown_api_key:  Optional[str]     = None
    hf_token:           Optional[str]     = None


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
# LLM OUTPUT  (direct from multi_llm_client.py)
# ✅ SYNCHRONIZED: Matches TASK_INSTRUCTION in multi_llm_client.py
# ─────────────────────────────────────────────

class AnalysisResult(BaseModel):
    """Output from LLM analysis (from multi_llm_client.py)"""
    bill_id: str
    citizen_summary: str  # ✅ SYNCED: Detailed narrative explanation
    key_changes: List[str]  # ✅ SYNCED: 5 major changes with detailed 3-4 sentence explanations
    affected_groups: List[str]  # ✅ SYNCED: Groups affected by bill
    rights_impact: str  # ✅ SYNCED: Impact on fundamental rights
    overview: Optional[str] = None  # ✅ SYNCED: Concluding narrative (2+ paragraphs)
    implementation_date: str = "Not specified"  # ✅ SYNCED: When bill takes effect
    tokens_input: int = 0
    tokens_output: int = 0
    compression_ratio: float = 0.0
    carbon_saved_grams: float = 0.0


# ─────────────────────────────────────────────
# TRANSLATION OUTPUT  (from translator.py)
# ✅ SYNCHRONIZED: Matches translator.translate_result() output
# ─────────────────────────────────────────────

class TranslatedSummary(BaseModel):
    """Translated version of CitizenSummary"""
    bill_id: str
    language: str  # ✅ SYNCED: Target language code (e.g., "hi", "te")
    headline: str  # ✅ SYNCED: Translated headline
    key_points: List[str]  # ✅ SYNCED: Translated key points (from LLM's key_changes)
    impact_statement: str  # ✅ SYNCED: Translated impact statement
    overview: Optional[str] = None  # ✅ SYNCED: Translated overview
