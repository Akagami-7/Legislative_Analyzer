"""
src/api/routes/models.py
=========================
GET /models/{provider} — fetch available models dynamically
GET /models/providers   — list all supported providers
"""

from fastapi import APIRouter, Query
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


@router.get("/models/{provider}")
def get_models_for_provider(
    provider: str,
    request: ModelRequest
):
    """
    Fetch available models for a provider dynamically.
    Uses POST to keep API keys out of the URL.
    """
    api_key = request.api_key
    """
    Fetch available models for a provider dynamically.
    Requires API key to call provider's model list endpoint.
    
    Example:
        GET /api/v1/models/groq?api_key=gsk_xxx
        GET /api/v1/models/gemini?api_key=AIza_xxx
    """
    print(f"DEBUG: Fetching models for provider: {provider}")
    if provider not in SUPPORTED_PROVIDERS:
        print(f"DEBUG: Unknown provider: {provider}")
        return {
            "status" : "error",
            "message": f"⚠️ Unknown provider: {provider}. Choose from: {SUPPORTED_PROVIDERS}",
            "models" : []
        }

    try:
        result = get_available_models(provider, api_key)
        if result.get("status") == "error":
            print(f"DEBUG: Result error for {provider}: {result.get('message')}")
        return result
    except Exception as e:
        print(f"DEBUG: Unexpected error fetching models for {provider}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Unexpected backend error: {str(e)}", "models": []}