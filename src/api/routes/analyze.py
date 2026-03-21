"""
src/api/routes/analyze.py
=========================
POST /analyze — real pipeline wired for v1.0
Owner: AkashSamuel (wired by Akagami)
"""

import uuid
from fastapi import APIRouter, HTTPException

from src.shared_schemas import AnalyzeRequest, AnalyzeResponse, BillStatus
from src.api.services.real_pipeline import real_run_pipeline, task_store

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
async def analyze(request: AnalyzeRequest):
    if not request.pdf_url and not request.raw_text:
        raise HTTPException(
            status_code=422,
            detail="Provide either pdf_url or raw_text.",
        )

    task_id = str(uuid.uuid4())

    # v1.0: runs synchronously
    # v2.0: replace with celery_task.delay(task_id, request.dict())
    real_run_pipeline(task_id, request)

    return AnalyzeResponse(
        task_id=task_id,
        status=BillStatus.COMPLETED,
        message="Analysis complete. Fetch results at GET /api/v1/bills/{task_id}",
    )