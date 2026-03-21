"""
src/api/routes/analyze.py
=========================
POST /analyze  — accepts a PDF URL or raw text, enqueues a pipeline job,
                 returns a task_id the frontend can poll.
Owner: AkashSamuel
"""

import uuid
from fastapi import APIRouter, HTTPException

from src.shared_schemas        import AnalyzeRequest, AnalyzeResponse, BillStatus
from src.api.services.mock_pipeline import mock_run_pipeline, task_store

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
async def analyze(request: AnalyzeRequest):
    """
    Submit a bill for analysis.

    - Provide either `pdf_url` **or** `raw_text`.
    - Returns a `task_id` you can poll at `GET /bills/{task_id}`.
    """
    if not request.pdf_url and not request.raw_text:
        raise HTTPException(
            status_code=422,
            detail="Provide either `pdf_url` or `raw_text`.",
        )

    task_id = str(uuid.uuid4())

    # v1.0: mock pipeline runs synchronously in-process
    # v2.0: replace with  celery_task.delay(task_id, request.dict())
    mock_run_pipeline(task_id, request)

    return AnalyzeResponse(
        task_id = task_id,
        status  = BillStatus.PENDING,
        message = "Job queued. Poll GET /api/v1/bills/{task_id} for results.",
    )
