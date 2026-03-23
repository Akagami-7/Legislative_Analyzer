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
    version     = "2.0.0",
)
app.include_router(models_router, prefix="/api/v1", tags=["models"])

# ── Middleware ───────────────────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request, call_next):
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
app.include_router(analyze_router, prefix="/api/v1", tags=["analyze"])
app.include_router(bills_router,   prefix="/api/v1", tags=["bills"])


from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))

if os.path.exists(frontend_path):
    app.mount("/assets", StaticFiles(directory=frontend_path), name="frontend_assets")

    @app.get("/", tags=["frontend"])
    def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    @app.get("/", tags=["health"])
    def root():
        return {"status": "ok", "service": "AI Legislative Analyzer v1.0"}

@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}

