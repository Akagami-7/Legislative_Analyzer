"""
src/api/routes/models.py
=========================
GET /models/{provider} — fetch available models dynamically
GET /models/providers   — list all supported providers
"""

from fastapi import APIRouter, Query, Request
from typing import Optional
import asyncio

from src.compression.multi_llm_client import (
    get_available_models,
    SUPPORTED_PROVIDERS,
    DEFAULT_MODELS
)

router = APIRouter()

# ✅ Simple in-memory cache (prevents repeated slow API calls)
MODEL_CACHE = {}


# ─────────────────────────────────────────────────────────────
# Providers List
# ─────────────────────────────────────────────────────────────
@router.get("/models/providers")
def list_providers():
    return {
        "providers": [
            {
                "id": "gemini",
                "name": "Google Gemini",
                "free_tier": True,
                "get_key_url": "https://aistudio.google.com/app/apikey",
                "default_model": DEFAULT_MODELS["gemini"]
            },
            {
                "id": "groq",
                "name": "Groq (Llama / Mixtral)",
                "free_tier": True,
                "get_key_url": "https://console.groq.com",
                "default_model": DEFAULT_MODELS["groq"]
            },
            {
                "id": "claude",
                "name": "Anthropic Claude",
                "free_tier": False,
                "get_key_url": "https://console.anthropic.com",
                "default_model": DEFAULT_MODELS["claude"]
            },
            {
                "id": "gpt",
                "name": "OpenAI GPT",
                "free_tier": False,
                "get_key_url": "https://platform.openai.com/api-keys",
                "default_model": DEFAULT_MODELS["gpt"]
            },
            {
                "id": "ollama",
                "name": "Ollama (Local)",
                "free_tier": True,
                "get_key_url": "https://ollama.com",
                "default_model": "llama3.2",
                "note": "Runs locally — no API key needed"
            },
        ]
    }


# ─────────────────────────────────────────────────────────────
# Fetch Models
# ─────────────────────────────────────────────────────────────
@router.api_route("/models/{provider}", methods=["GET", "POST"])
async def get_models_for_provider(
    provider: str,
    request: Request,
    api_key: Optional[str] = Query(default=None)
):
    print(f"--> Fetching models for provider: {provider}")

    # ✅ Validate provider
    if provider not in SUPPORTED_PROVIDERS:
        return {
            "status": "error",
            "message": f"Unknown provider: {provider}",
            "models": []
        }

    # ✅ Handle POST body (backward compatibility)
    if request.method == "POST":
        try:
            body = await request.json()
            api_key = body.get("api_key")
        except Exception:
            pass

    print(f"DEBUG: API key provided: {'YES' if api_key else 'NO'}")

    # ✅ Cache key (avoid repeated slow calls)
    cache_key = f"{provider}:{api_key or 'no_key'}"

    if cache_key in MODEL_CACHE:
        print("⚡ Returning cached models")
        return MODEL_CACHE[cache_key]

    try:
        # ✅ Run blocking function safely (VERY IMPORTANT for Render)
        result = await asyncio.wait_for(
            asyncio.to_thread(get_available_models, provider, api_key),
            timeout=12  # ⏱ keep under Render timeout
        )

        if not isinstance(result, dict):
            raise ValueError("Invalid response format from provider")

        # ✅ Store in cache
        MODEL_CACHE[cache_key] = result

        print(f"<-- Models fetched successfully ({provider})")
        return result

    except asyncio.TimeoutError:
        print("⏱ Model fetch timed out")

        return {
            "status": "error",
            "message": "Provider request timed out. Try again.",
            "models": []
        }

    except Exception as e:
        import traceback
        traceback.print_exc()

        return {
            "status": "error",
            "message": f"Backend error: {str(e)}",
            "models": []
        }