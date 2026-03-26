"""
src/compression/multi_llm_client.py
=====================================
Multi-LLM router — supports Gemini, Claude, GPT-4o, Groq.
User provides their own API key and selects model.
v2.0 Sprint 2
Owner: Akagami
"""

import os
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.shared_schemas import AnalysisResult
from typing import Optional
from src.compression.scaledown_client import (
    SCALEDOWN_SUPPORTED_MODELS,
    SCALEDOWN_MODEL_MAP
)

def _check_scaledown_support(model_id: str) -> bool:
    """Check if ScaleDown supports this model (direct or via mapping)."""
    if model_id in SCALEDOWN_SUPPORTED_MODELS:
        return True
    return SCALEDOWN_MODEL_MAP.get(model_id) in SCALEDOWN_SUPPORTED_MODELS

SUPPORTED_PROVIDERS = ["gemini", "claude", "gpt", "groq", "ollama"]

# ── Available models per provider ─────────────────────────────────────────────
PROVIDER_MODELS = {
    "gemini": [
        {"id": "gemini-2.0-flash",      "name": "Gemini 2.0 Flash",      "free": True,  "scaledown_support": True},
        {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite", "free": True,  "scaledown_support": True},
        {"id": "gemini-1.5-pro",        "name": "Gemini 1.5 Pro",        "free": False, "scaledown_support": True, "status": "warning", "warning": "Low credits"},
    ],
    "claude": [
        {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5",  "free": False, "scaledown_support": True},
        {"id": "claude-sonnet-4-6",         "name": "Claude Sonnet 4.6", "free": False, "scaledown_support": True},
        {"id": "claude-opus-4-6",           "name": "Claude Opus 4.6",   "free": False, "scaledown_support": True},
    ],
    "gpt": [
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "free": False, "scaledown_support": True},
        {"id": "gpt-4o",      "name": "GPT-4o",      "free": False, "scaledown_support": True},
        {"id": "o3-mini",     "name": "o3 Mini",      "free": False, "scaledown_support": True},
    ],
    "groq": [
        {"id": "llama-3.1-8b-instant",    "name": "Llama 3.1 8B (Fast)", "free": True, "scaledown_support": True},
        {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B",       "free": True, "scaledown_support": True},
        {"id": "mixtral-8x7b-32768",      "name": "Mixtral 8x7B",        "free": True, "scaledown_support": True},
    ],
    "ollama": []  # populated dynamically via /api/tags
}

DEFAULT_MODELS = {
    "gemini": "gemini-2.0-flash",
    "claude": "claude-sonnet-4-6",
    "gpt"   : "gpt-4o-mini",
    "groq"  : "llama-3.3-70b-versatile",
    "ollama": "llama3.2"
}

def get_available_models(provider: str,
                         api_key: Optional[str] = None) -> dict:
    """
    Fetch available models dynamically from provider API.
    Returns dict with models list and status.
    """
    provider = provider.lower().strip()

    try:
        if provider == "gemini":
            return _get_gemini_models(api_key)
        elif provider == "claude":
            return _get_claude_models(api_key)
        elif provider == "gpt":
            return _get_gpt_models(api_key)
        elif provider == "groq":
            return _get_groq_models(api_key)
        elif provider == "ollama":
            return _get_ollama_models(api_key)
        else:
            return {
                "status" : "error",
                "message": f"⚠️ Unknown provider: {provider}",
                "models" : []
            }
    except Exception as e:
        return {
            "status" : "error",
            "message": str(e),
            "models" : []
        }


def _get_gemini_models(api_key: Optional[str] = None) -> dict:
    from google import genai

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return {
            "status" : "error",
            "message": "⚠️ Gemini API key required",
            "models" : []
        }

    try:
        client = genai.Client(api_key=key)
        models = client.models.list()

        filtered = []
        for m in models:
            name = m.name  # e.g. "models/gemini-2.0-flash"
            # Only include models that support generateContent
            supported = getattr(m, "supported_actions", []) or []
            if "generateContent" not in str(supported) and "generateContent" not in str(getattr(m, "supported_generation_methods", [])):
                continue
            # Only include gemini models, skip embedding/vision-only
            if "gemini" not in name.lower():
                continue

            display_id = name.replace("models/", "")
            filtered.append({
                "id"          : display_id,
                "name"        : getattr(m, "display_name", display_id),
                "description" : getattr(m, "description", ""),
                "free"        : "flash" in display_id.lower() or "lite" in display_id.lower(),
                "scaledown_support": _check_scaledown_support(display_id),
                "status"      : "warning" if "pro" in display_id.lower() else "ok",
                "warning"     : "Credits may apply" if "pro" in display_id.lower() else None
            })

        return {
            "status"  : "ok",
            "provider": "gemini",
            "count"   : len(filtered),
            "models"  : filtered
        }

    except Exception as e:
        err = str(e)
        if "API_KEY_INVALID" in err or "PERMISSION_DENIED" in err:
            return {
                "status" : "error",
                "message": "⚠️ Invalid Gemini API key",
                "models" : []
            }
        return {
            "status" : "error",
            "message": f"⚠️ Gemini error: {err[:100]}",
            "models" : []
        }


def _get_claude_models(api_key: Optional[str] = None) -> dict:
    import anthropic

    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return {
            "status" : "error",
            "message": "⚠️ Anthropic API key required",
            "models" : []
        }

    try:
        client = anthropic.Anthropic(api_key=key)
        models = client.models.list()

        filtered = []
        for m in models.data:
            filtered.append({
                "id"         : m.id,
                "name"       : getattr(m, "display_name", m.id),
                "description": "",
                "free"       : False,
                "scaledown_support": _check_scaledown_support(m.id),
                "status"     : "ok"
            })

        return {
            "status"  : "ok",
            "provider": "claude",
            "count"   : len(filtered),
            "models"  : filtered
        }

    except Exception as e:
        err = str(e)
        if "401" in err or "authentication" in err.lower():
            return {
                "status" : "error",
                "message": "⚠️ Invalid Anthropic API key",
                "models" : []
            }
        return {
            "status" : "error",
            "message": f"⚠️ Claude error: {err[:100]}",
            "models" : []
        }


def _get_gpt_models(api_key: Optional[str] = None) -> dict:
    from openai import OpenAI

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        return {
            "status" : "error",
            "message": "⚠️ OpenAI API key required",
            "models" : []
        }

    try:
        client = OpenAI(api_key=key)
        models = client.models.list()

        # Filter to only chat models
        chat_keywords = ["gpt-4", "gpt-3.5", "o1", "o3", "chatgpt"]
        filtered = []
        for m in models.data:
            if any(k in m.id.lower() for k in chat_keywords):
                filtered.append({
                    "id"         : m.id,
                    "name"       : m.id,
                    "description": "",
                    "free"       : False,
                    "scaledown_support": _check_scaledown_support(m.id),
                    "status"     : "ok"
                })

        # Sort by name
        filtered.sort(key=lambda x: x["id"])

        return {
            "status"  : "ok",
            "provider": "gpt",
            "count"   : len(filtered),
            "models"  : filtered
        }

    except Exception as e:
        err = str(e)
        if "401" in err or "invalid_api_key" in err.lower():
            return {
                "status" : "error",
                "message": "⚠️ Invalid OpenAI API key",
                "models" : []
            }
        return {
            "status" : "error",
            "message": f"⚠️ OpenAI error: {err[:100]}",
            "models" : []
        }


def _get_groq_models(api_key: Optional[str] = None) -> dict:
    from groq import Groq

    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        return {
            "status" : "error",
            "message": "⚠️ Groq API key required",
            "models" : []
        }

    try:
        client = Groq(api_key=key)
        models = client.models.list()

        # Filter to text generation models only
        filtered = []
        for m in models.data:
            # Skip whisper, vision-only models
            if any(skip in m.id.lower() for skip in ["whisper", "vision", "guard"]):
                continue
            filtered.append({
                "id"          : m.id,
                "name"        : getattr(m, "id", m.id),
                "description" : "",
                "free"        : True,
                "scaledown_support": _check_scaledown_support(m.id),
                "status"      : "ok"
            })

        filtered.sort(key=lambda x: x["id"])

        return {
            "status"  : "ok",
            "provider": "groq",
            "count"   : len(filtered),
            "models"  : filtered
        }

    except Exception as e:
        err = str(e)
        if "401" in err or "invalid" in err.lower():
            return {
                "status" : "error",
                "message": "⚠️ Invalid Groq API key",
                "models" : []
            }
        return {
            "status" : "error",
            "message": f"⚠️ Groq error: {err[:100]}",
            "models" : []
        }


def _get_ollama_models(api_key: Optional[str] = None,
                       base_url: Optional[str] = None) -> dict:
    """
    Fetch locally installed Ollama models.
    If api_key is provided and starts with http, it is used as the base_url.
    """
    import requests

    if api_key and api_key.startswith("http"):
        base_url = api_key.rstrip("/")
    elif not base_url:
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    try:
        response = requests.get(
            f"{base_url}/api/tags",
            timeout=5
        )
    except requests.exceptions.ConnectionError:
        return {
            "status" : "error",
            "message": (
                "⚠️ Ollama is not running. "
                "Start it with: ollama serve"
            ),
            "models" : [],
            "install_url": "https://ollama.com"
        }
    except requests.exceptions.Timeout:
        return {
            "status" : "error",
            "message": "⚠️ Ollama not responding. Is it running?",
            "models" : []
        }

    if not response.ok:
        return {
            "status" : "error",
            "message": f"⚠️ Ollama error: {response.status_code}",
            "models" : []
        }

    data   = response.json()
    models = data.get("models", [])

    if not models:
        return {
            "status" : "error",
            "message": (
                "⚠️ No models installed in Ollama. "
                "Run: ollama pull llama3.2"
            ),
            "models" : [],
            "install_url": "https://ollama.com/library"
        }

    filtered = []
    for m in models:
        name = m.get("name", "")
        filtered.append({
            "id"         : name,
            "name"       : name,
            "description": f"Local model — {m.get('size', 0) // 1024**3:.1f}GB",
            "free"       : True,
            "local"      : True,
            "size_bytes" : m.get("size", 0),
            "scaledown_support": _check_scaledown_support(name),
            "status"     : "ok"
        })

    return {
        "status"  : "ok",
        "provider": "ollama",
        "count"   : len(filtered),
        "models"  : filtered,
        "base_url": base_url
    }

TASK_INSTRUCTION = """

Analyze this Indian parliamentary bill and return ONLY a JSON object with these exact fields:
{
  "bill_id": "string",
  "citizen_summary": "A detailed, comprehensive, easy-to-understand explanation of the bill's purpose and background. REQUIRED: Minimum of 3 detailed paragraphs.",
  "key_changes": [
    "1st major change. REQUIRED: Write a detailed 3-4 sentence explanation of the context, the change, and why it matters.",
    "2nd major change. REQUIRED: Write a detailed 3-4 sentence explanation of the context, the change, and why it matters.",
    "3rd major change. REQUIRED: Write a detailed 3-4 sentence explanation of the context, the change, and why it matters.",
    "4th major change. REQUIRED: Write a detailed 3-4 sentence explanation of the context, the change, and why it matters.",
    "5th major change. REQUIRED: Write a detailed 3-4 sentence explanation of the context, the change, and why it matters."
  ],
  "affected_groups": ["group 1", "group 2", "group 3", "group 4"],
  "rights_impact": "Detailed, multi-sentence explanation of how this impacts fundamental rights of ordinary citizens.",
  "overview": "A concluding narrative overview summarizing the overall impact and significance of the bill, at least 2 paragraphs.",
  "implementation_date": "date or Not specified",
  "tokens_input": 0,
  "tokens_output": 0,
  "compression_ratio": 0.0,
  "carbon_saved_grams": 0.0
}
Return ONLY the JSON. No markdown, no explanation, no code blocks.
"""


def _parse_json_result(text: str,
                       orig_tokens: int,
                       comp_tokens: int) -> AnalysisResult:
    """Parse LLM response text into AnalysisResult."""
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in response: {text[:200]}")

    data = json.loads(text[start:end])
    data["tokens_input"]       = orig_tokens
    data["tokens_output"]      = comp_tokens
    data["compression_ratio"]  = round(1 - comp_tokens / max(orig_tokens, 1), 4)
    data["carbon_saved_grams"] = round(data["compression_ratio"] * 15, 2)
    return AnalysisResult(**data)


# ── Gemini ────────────────────────────────────────────────────────────────────
def _analyze_gemini(prompt: str,
                    orig_tokens: int,
                    comp_tokens: int,
                    api_key: Optional[str] = None,
                    model: Optional[str] = None) -> AnalysisResult:
    from google import genai
    from google.genai import types

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "⚠️ Gemini API key not provided. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )

    selected_model = model or DEFAULT_MODELS["gemini"]

    try:
        client   = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=selected_model,
            contents=prompt + TASK_INSTRUCTION,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048
            )
        )
    except Exception as e:
        err = str(e)
        if "NOT_FOUND" in err or "not found" in err.lower():
            raise ValueError(
                f"⚠️ Model '{selected_model}' not available on your Gemini plan. "
                f"Try: gemini-2.0-flash or gemini-2.0-flash-lite (both free)"
            )
        elif "PERMISSION_DENIED" in err or "API_KEY_INVALID" in err:
            raise ValueError(
                "⚠️ Invalid Gemini API key. "
                "Get a free key at https://aistudio.google.com/app/apikey"
            )
        elif "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
            raise ValueError(
                "⚠️ Gemini quota exceeded. "
                "Upgrade your plan or switch to Groq (free, unlimited)."
            )
        else:
            raise ValueError(f"⚠️ Gemini error: {err[:200]}")

    text = response.text
    if text is None:
        raise ValueError("⚠️ Gemini returned empty response — try again")

    return _parse_json_result(text, orig_tokens, comp_tokens)


# ── Claude ────────────────────────────────────────────────────────────────────
def _analyze_claude(prompt: str,
                    orig_tokens: int,
                    comp_tokens: int,
                    api_key: Optional[str] = None,
                    model: Optional[str] = None) -> AnalysisResult:
    import anthropic

    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "⚠️ Anthropic API key not provided. "
            "Get one at https://console.anthropic.com"
        )

    selected_model = model or DEFAULT_MODELS["claude"]

    try:
        client   = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model=selected_model,
            max_tokens=2048,
            temperature=0.1,
            messages=[{
                "role"   : "user",
                "content": prompt + TASK_INSTRUCTION
            }]
        )
    except Exception as e:
        err = str(e)
        if "authentication" in err.lower() or "401" in err:
            raise ValueError(
                "⚠️ Invalid Anthropic API key. "
                "Check your key at https://console.anthropic.com"
            )
        elif "credit" in err.lower() or "402" in err or "insufficient" in err.lower():
            raise ValueError(
                "⚠️ Insufficient Anthropic credits. "
                "Add credits at https://console.anthropic.com/settings/billing"
            )
        elif "overloaded" in err.lower() or "529" in err:
            raise ValueError(
                "⚠️ Claude API is overloaded. Please try again in a moment."
            )
        elif "not_found" in err.lower() or "404" in err:
            raise ValueError(
                f"⚠️ Model '{selected_model}' not available. "
                f"Try: claude-sonnet-4-6 or claude-haiku-4-5-20251001"
            )
        else:
            raise ValueError(f"⚠️ Claude error: {err[:200]}")

    text = response.content[0].text
    return _parse_json_result(text, orig_tokens, comp_tokens)


# ── GPT ───────────────────────────────────────────────────────────────────────
def _analyze_gpt(prompt: str,
                 orig_tokens: int,
                 comp_tokens: int,
                 api_key: Optional[str] = None,
                 model: Optional[str] = None) -> AnalysisResult:
    from openai import OpenAI

    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "⚠️ OpenAI API key not provided. "
            "Get one at https://platform.openai.com/api-keys"
        )

    selected_model = model or DEFAULT_MODELS["gpt"]

    try:
        client   = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model=selected_model,
            temperature=0.1,
            max_tokens=2048,
            messages=[{
                "role"   : "user",
                "content": prompt + TASK_INSTRUCTION
            }]
        )
    except Exception as e:
        err = str(e)
        if "401" in err or "invalid_api_key" in err.lower():
            raise ValueError(
                "⚠️ Invalid OpenAI API key. "
                "Check your key at https://platform.openai.com/api-keys"
            )
        elif "insufficient_quota" in err.lower() or "429" in err:
            raise ValueError(
                "⚠️ OpenAI quota exceeded. "
                "Add credits at https://platform.openai.com/settings/billing"
            )
        elif "model_not_found" in err.lower() or "404" in err:
            raise ValueError(
                f"⚠️ Model '{selected_model}' not available on your OpenAI plan. "
                f"Try: gpt-4o-mini (cheaper) or gpt-4o"
            )
        else:
            raise ValueError(f"⚠️ OpenAI error: {err[:200]}")

    text = response.choices[0].message.content
    return _parse_json_result(text, orig_tokens, comp_tokens)


# ── Groq ──────────────────────────────────────────────────────────────────────
def _analyze_groq(prompt: str,
                  orig_tokens: int,
                  comp_tokens: int,
                  api_key: Optional[str] = None,
                  model: Optional[str] = None) -> AnalysisResult:
    from groq import Groq

    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError(
            "⚠️ Groq API key not provided. "
            "Get a free key at https://console.groq.com"
        )

    import time
    selected_model = model or DEFAULT_MODELS["groq"]
    max_retries = 2
    retry_delay = 2  # seconds

    for attempt in range(max_retries + 1):
        try:
            client   = Groq(api_key=key)
            response = client.chat.completions.create(
                model=selected_model,
                temperature=0.1,
                max_tokens=2048,
                messages=[{
                    "role"   : "user",
                    "content": prompt + TASK_INSTRUCTION
                }]
            )
            text = response.choices[0].message.content
            return _parse_json_result(text, orig_tokens, comp_tokens)

        except Exception as e:
            err = str(e)
            if ("429" in err or "rate" in err.lower()) and attempt < max_retries:
                print(f"⚠️ Groq rate limit hit. Retrying in {retry_delay}s (Attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue
            
            if "401" in err or "invalid" in err.lower():
                raise ValueError(
                    "⚠️ Invalid Groq API key. "
                    "Get a free key at https://console.groq.com"
                )
            elif "429" in err or "rate" in err.lower():
                raise ValueError(
                    "⚠️ Groq rate limit hit. "
                    "Wait 1 minute and retry, or switch to llama-3.1-8b-instant (faster limits)"
                )
            elif "model" in err.lower() and "not found" in err.lower():
                raise ValueError(
                    f"⚠️ Model '{selected_model}' not available on Groq. "
                    f"Try: llama-3.3-70b-versatile or llama-3.1-8b-instant"
                )
            else:
                raise ValueError(f"⚠️ Groq error: {err[:200]}")


def _analyze_ollama(prompt: str,
                    orig_tokens: int,
                    comp_tokens: int,
                    api_key: Optional[str] = None,
                    model: Optional[str] = None,
                    base_url: Optional[str] = None) -> AnalysisResult:
    """
    Call local or remote Ollama instance using OpenAI-compatible API.
    """
    import requests

    if api_key and api_key.startswith("http"):
        base_url = api_key.rstrip("/")
    elif not base_url:
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    selected_model = model or DEFAULT_MODELS["ollama"]

    # Check Ollama is running
    try:
        health = requests.get(f"{base_url}/api/tags", timeout=5)
        if not health.ok:
            raise ValueError("⚠️ Ollama is not running. Start with: ollama serve")
    except requests.exceptions.ConnectionError:
        raise ValueError(
            "⚠️ Ollama is not running on localhost:11434. "
            "Install from https://ollama.com and run: ollama serve"
        )

    # Check model is installed
    tags = health.json().get("models", [])
    installed = [m["name"] for m in tags]

    # Handle model name with/without tag
    model_base = selected_model.split(":")[0]
    model_installed = any(
        m.startswith(model_base) for m in installed
    )

    if not model_installed:
        available = ", ".join(installed[:5]) or "none"
        raise ValueError(
            f"⚠️ Model '{selected_model}' not installed in Ollama. "
            f"Run: ollama pull {selected_model}\n"
            f"Installed models: {available}"
        )

    # Make the API call using OpenAI-compatible endpoint
    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json={
                "model"      : selected_model,
                "messages"   : [{
                    "role"   : "user",
                    "content": prompt + TASK_INSTRUCTION
                }],
                "temperature": 0.1,
                "stream"     : False
            },
            timeout=120   # local models can be slow
        )
    except requests.exceptions.Timeout:
        raise ValueError(
            f"⚠️ Ollama timed out on model '{selected_model}'. "
            f"Try a smaller model like phi3 or gemma2."
        )

    if not response.ok:
        raise ValueError(
            f"⚠️ Ollama error {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    text = data["choices"][0]["message"]["content"]

    return _parse_json_result(text, orig_tokens, comp_tokens)



# ── Router ────────────────────────────────────────────────────────────────────
def analyze_with_llm(prompt: str,
                     orig_tokens: int,
                     comp_tokens: int,
                     provider: str = "gemini",
                     api_key: Optional[str] = None,
                     model: Optional[str] = None) -> AnalysisResult:
    """
    Route LLM call to the correct provider.

    Args:
        prompt      : Compressed bill prompt
        orig_tokens : Original token count
        comp_tokens : Compressed token count
        provider    : gemini / claude / gpt / groq
        api_key     : User API key (overrides .env)
        model       : Specific model ID (uses default if None)

    Returns:
        AnalysisResult

    Raises:
        ValueError with ⚠️ prefix — safe to show directly in UI
    """
    provider = provider.lower().strip()
    selected = model or DEFAULT_MODELS.get(provider, "default")

    print(f"\n🤖 Calling {provider.upper()} — {selected}...")

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"⚠️ Unknown provider: '{provider}'. "
            f"Choose from: {SUPPORTED_PROVIDERS}"
        )

    if provider == "gemini":
        result = _analyze_gemini(prompt, orig_tokens, comp_tokens, api_key, model)
    elif provider == "claude":
        result = _analyze_claude(prompt, orig_tokens, comp_tokens, api_key, model)
    elif provider == "gpt":
        result = _analyze_gpt(prompt, orig_tokens, comp_tokens, api_key, model)
    elif provider == "groq":
        result = _analyze_groq(prompt, orig_tokens, comp_tokens, api_key, model)
    elif provider == "ollama":
        result = _analyze_ollama(prompt, orig_tokens, comp_tokens, api_key, model)

    print(f"✅ {provider.upper()} response received")
    return result
