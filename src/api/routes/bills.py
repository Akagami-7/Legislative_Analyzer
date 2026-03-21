"""
src/api/routes/bills.py
=======================
GET /bills/{bill_id}  — returns the full analysis result for a task.
Owner: AkashSamuel
"""

from fastapi import APIRouter, HTTPException

from src.shared_schemas                 import BillDetailResponse, BillStatus
from src.api.services.mock_pipeline     import task_store

router = APIRouter()


@router.get("/bills/{bill_id}", response_model=BillDetailResponse)
async def get_bill(bill_id: str):
    """
    Retrieve the analysis result for a previously submitted bill.

    Status flow: `pending` → `processing` → `completed` | `failed`
    """
    result = task_store.get(bill_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No job found with task_id='{bill_id}'.",
        )

    return result
