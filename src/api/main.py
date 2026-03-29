"""
main.py — UPDATED FOR SYNCHRONIZATION
src/api/main.py
===============
FastAPI application entry point.
✅ SYNCHRONIZED: Routes properly handle AnalyzeRequest and return consistent responses

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

# ── Middleware ───────────────────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request, call_next):
    """
    ✅ SYNCHRONIZED: Log all requests consistently
    """
    from fastapi import Request
    import time
    
    start_time = time.time()
    method = request.method
    path = request.url.path
    
    print(f"--> Incoming {method} to {path}")
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        status   = response.status_code
        print(f"<-- Response {status} for {method} {path} ({duration:.3f}s)")
        return response
    except Exception as e:
        print(f"!!! CRASH during {method} {path}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e


app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
# ✅ SYNCHRONIZED: Register all routes with correct prefixes

# Models endpoint (for provider listing and model discovery)
app.include_router(models_router, prefix="/api/v1", tags=["models"])

# Analysis endpoint (submit bill for analysis)
app.include_router(analyze_router, prefix="/api/v1", tags=["analyze"])

# Bills endpoint (poll result status)
app.include_router(bills_router, prefix="/api/v1", tags=["bills"])


# ── Static File Serving ──────────────────────────────────────────────────────
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

if os.path.exists(frontend_path):
    app.mount("/assets", StaticFiles(directory=frontend_path), name="frontend_assets")

    @app.get("/", tags=["frontend"])
    def serve_frontend():
        """
        ✅ SYNCHRONIZED: Serve frontend SPA
        """
        return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    @app.get("/", tags=["health"])
    def root():
        return {"status": "ok", "service": "AI Legislative Analyzer v1.0"}


# ── Health Checks ────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health():
    """
    ✅ SYNCHRONIZED: Health check endpoint for monitoring
    """
    return {"status": "healthy"}


# ── Optional: Startup/Shutdown Events ────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """
    ✅ SYNCHRONIZED: Initialize on startup
    """
    print("\n" + "="*60)
    print("🚀 AI Legislative Analyzer API Starting...")
    print("="*60)
    print("✓ FastAPI server initialized")
    print("✓ CORS enabled for all origins (dev mode)")
    print("✓ Available endpoints:")
    print("  - GET  /api/v1/models/providers")
    print("  - POST /api/v1/models/{provider}")
    print("  - POST /api/v1/analyze")
    print("  - GET  /api/v1/bills/{task_id}")
    print("="*60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """
    ✅ SYNCHRONIZED: Cleanup on shutdown
    """
    print("\n" + "="*60)
    print("👋 AI Legislative Analyzer API Shutting Down...")
    print("="*60 + "\n")
