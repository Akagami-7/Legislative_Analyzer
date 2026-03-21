"""
src/api/routes/bills.py
=======================
GET /bills/{bill_id} — returns full analysis result
Owner: AkashSamuel (wired by Akagami)
"""

from fastapi import APIRouter, HTTPException
from src.shared_schemas import BillDetailResponse
from src.api.services.real_pipeline import task_store

router = APIRouter()


@router.get("/bills/{bill_id}", response_model=BillDetailResponse)
async def get_bill(bill_id: str):
    result = task_store.get(bill_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No job found with task_id='{bill_id}'.",
        )
    return result