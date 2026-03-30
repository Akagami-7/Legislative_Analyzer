"""
src/api/routes/analyze.py
=========================
POST /analyze — real pipeline wired for v1.0
Owner: AkashSamuel (wired by Akagami)
"""

import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks

from src.shared_schemas import AnalyzeRequest, AnalyzeResponse, BillStatus, BillDetailResponse
from src.api.services.real_pipeline import real_run_pipeline, task_store

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    if not request.pdf_url and not request.raw_text:
        raise HTTPException(
            status_code=422,
            detail="Provide either pdf_url or raw_text.",
        )

    task_id = str(uuid.uuid4())
    
    # Initialize task status in store (using correct Pydantic model to avoid 500 error)
    task_store[task_id] = BillDetailResponse(
        bill_id=task_id,
        status=BillStatus.PENDING
    )

    # Run pipeline as a background task to prevent proxy timeouts
    background_tasks.add_task(real_run_pipeline, task_id, request)

    return AnalyzeResponse(
        task_id=task_id,
        status=BillStatus.PENDING,
        message="Analysis started. Tracking via background polling.",
    )