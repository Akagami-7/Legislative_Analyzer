from pydantic import BaseModel
from typing import List, Optional

class BillSection(BaseModel):
    section_id: str
    section_title: str
    section_text: str
    token_count: int
    page_number: int

class IngestedBill(BaseModel):
    bill_id: str
    source_url: str
    page_count: int
    sections: List[BillSection]
    total_token_count: int
    has_tables: bool
    tables: List[dict]

class AnalysisResult(BaseModel):
    bill_id: str
    citizen_summary: str
    key_changes: List[str]
    affected_groups: List[str]
    rights_impact: str
    implementation_date: str
    tokens_input: int
    tokens_output: int
    compression_ratio: float
    carbon_saved_grams: float

class AnalyzeRequest(BaseModel):
    pdf_url: str
    bill_id: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    version: str