"""
src/api/routes/models.py
=========================
GET /models/{provider} — fetch available models dynamically
GET /models/providers   — list all supported providers
"""

from fastapi import APIRouter, Query, Request
from typing import Optional
from pydantic import BaseModel
from src.compression.multi_llm_client import (
    get_available_models,
    SUPPORTED_PROVIDERS,
    DEFAULT_MODELS
)

class ModelRequest(BaseModel):
    api_key: Optional[str] = None

router = APIRouter()


@router.get("/models/providers")
def list_providers():
    """List all supported LLM providers."""
    return {
        "providers": [
            {
                "id"          : "gemini",
                "name"        : "Google Gemini",
                "free_tier"   : True,
                "get_key_url" : "https://aistudio.google.com/app/apikey",
                "default_model": DEFAULT_MODELS["gemini"]
            },
            {
                "id"          : "groq",
                "name"        : "Groq (Llama / Mixtral)",
                "free_tier"   : True,
                "get_key_url" : "https://console.groq.com",
                "default_model": DEFAULT_MODELS["groq"]
            },
            {
                "id"          : "claude",
                "name"        : "Anthropic Claude",
                "free_tier"   : False,
                "get_key_url" : "https://console.anthropic.com",
                "default_model": DEFAULT_MODELS["claude"]
            },
            {
                "id"          : "gpt",
                "name"        : "OpenAI GPT",
                "free_tier"   : False,
                "get_key_url" : "https://platform.openai.com/api-keys",
                "default_model": DEFAULT_MODELS["gpt"]
            },
            {
                "id"           : "ollama",
                "name"         : "Ollama (Local)",
                "free_tier"    : True,
                "get_key_url"  : "https://ollama.com",
                "default_model": "llama3.2",
                "note"         : "Runs locally — no API key needed"
            },
        ]
    }


@router.api_route("/models/{provider}", methods=["GET", "POST"])
async def get_models_for_provider(
    provider: str,
    request: Request,
    api_key: Optional[str] = Query(default=None)
):
    print(f"DEBUG: Fetching models for provider: {provider}")

    if provider not in SUPPORTED_PROVIDERS:
        return {
            "status": "error",
            "message": f"⚠️ Unknown provider: {provider}. Choose from: {SUPPORTED_PROVIDERS}",
            "models": []
        }

    try:
        # ✅ Handle POST body
        if request.method == "POST":
            try:
                body = await request.json()
                api_key = body.get("api_key")
            except Exception:
                pass

        print(f"DEBUG: API key provided: {'YES' if api_key else 'NO'}")
        print(f"DEBUG: Calling get_available_models({provider})")
        result = get_available_models(provider, api_key)
        print(f"DEBUG: Calling get_available_models({provider})")

        if not isinstance(result, dict):
            return {
                "status": "error",
                "message": "Invalid response from provider",
                "models": []
            }

        return result

    except Exception as e:
        print("DEBUG: Raw result:", result)
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Unexpected backend error: {str(e)}",
            "models": []
        }