"""
tests/test_api.py
=================
pytest suite for AkashSamuel's FastAPI layer.
Run with:  pytest tests/test_api.py -v
Owner: AkashSamuel
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.services.mock_pipeline import task_store

client = TestClient(app)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_store():
    """Reset the in-memory task store before every test."""
    task_store.clear()
    yield
    task_store.clear()


# ── health ────────────────────────────────────────────────────────────────────

def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


# ── POST /analyze ─────────────────────────────────────────────────────────────

def test_analyze_with_raw_text():
    r = client.post(
        "/api/v1/analyze",
        json={"raw_text": "The Lok Sabha passed the Finance Bill today.", "language": "en"},
    )
    assert r.status_code == 202
    data = r.json()
    assert "task_id" in data
    assert data["status"] == "pending"


def test_analyze_with_pdf_url():
    r = client.post(
        "/api/v1/analyze",
        json={"pdf_url": "https://example.com/bill.pdf", "language": "hi"},
    )
    assert r.status_code == 202
    assert "task_id" in r.json()


def test_analyze_missing_input():
    r = client.post("/api/v1/analyze", json={"language": "en"})
    assert r.status_code == 422


# ── GET /bills/{bill_id} ──────────────────────────────────────────────────────

def test_get_bill_completed():
    # Submit a job first
    post_r = client.post(
        "/api/v1/analyze",
        json={"raw_text": "Some bill text.", "language": "en"},
    )
    task_id = post_r.json()["task_id"]

    # Retrieve it
    get_r = client.get(f"/api/v1/bills/{task_id}")
    assert get_r.status_code == 200

    data = get_r.json()
    assert data["status"] == "completed"
    assert data["summary"]["headline"] != ""
    assert len(data["summary"]["key_points"]) > 0
    assert data["compressed_document"]["compression_ratio"] < 1.0


def test_get_bill_not_found():
    r = client.get("/api/v1/bills/non-existent-id")
    assert r.status_code == 404


def test_compression_ratio_bounds():
    post_r = client.post(
        "/api/v1/analyze",
        json={"raw_text": "A " * 200, "language": "en"},
    )
    task_id = post_r.json()["task_id"]
    data    = client.get(f"/api/v1/bills/{task_id}").json()

    ratio = data["compressed_document"]["compression_ratio"]
    assert 0.0 < ratio <= 1.0, f"Unexpected compression ratio: {ratio}"


def test_carbon_saved_positive():
    post_r = client.post(
        "/api/v1/analyze",
        json={"raw_text": "Bill text " * 100, "language": "en"},
    )
    task_id = post_r.json()["task_id"]
    data    = client.get(f"/api/v1/bills/{task_id}").json()
    assert data["compressed_document"]["carbon_saved_grams"] >= 0
