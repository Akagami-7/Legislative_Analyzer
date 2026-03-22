"""
src/api/main.py
===============
FastAPI application entry point.
Owner: AkashSamuel
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.analyze import router as analyze_router
from src.api.routes.bills   import router as bills_router

from src.api.routes.models import router as models_router

app = FastAPI(
    title       = "AI Legislative Analyzer API",
    description = "Citizen's Dashboard — plain-language summaries of Indian parliamentary bills.",
    version     = "1.0.0",
)
app.include_router(models_router, prefix="/api/v1", tags=["models"])

# ── CORS (allow the Next.js frontend on any localhost port) ──────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(analyze_router, prefix="/api/v1", tags=["analyze"])
app.include_router(bills_router,   prefix="/api/v1", tags=["bills"])


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "AI Legislative Analyzer v1.0"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
