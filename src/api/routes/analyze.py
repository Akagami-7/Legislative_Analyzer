"""
src/api/routes/analyze.py
=========================
POST /analyze — real pipeline wired for v1.0
Owner: AkashSamuel (wired by Akagami)
"""

import threading
import uuid
from fastapi import APIRouter, HTTPException

from src.shared_schemas import AnalyzeRequest, AnalyzeResponse, BillStatus, BillDetailResponse
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

    # ✅ Initialize task
    task_store[task_id] = BillDetailResponse(
        bill_id=task_id,
        status=BillStatus.PROCESSING
    )

    # ✅ RUN IN BACKGROUND THREAD (KEY FIX)
    threading.Thread(
        target=real_run_pipeline,
        args=(task_id, request),
        daemon=True
    ).start()

    # ✅ Return immediately
    return AnalyzeResponse(
        task_id=task_id,
        status=BillStatus.PROCESSING,
        message="Analysis started. Poll /bills/{task_id}",
    )