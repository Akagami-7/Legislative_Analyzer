# AI Legislative Analyzer
Citizen's Dashboard for Indian Parliamentary Bills

## Running Locally

### Backend
pip install -r requirements.txt
uvicorn src.api.main:app --reload --port 8000

### Frontend
Open frontend/index.html in your browser.

## Branch Structure
- main → protected releases
- dev  → integration (PR here)
- Akagami → compression, RAG, LLM, translation
- rishi → ingestion, OCR, NER
- AkashSamuel → API, frontend, dashboard
