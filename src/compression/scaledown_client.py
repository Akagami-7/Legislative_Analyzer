"""
src/compression/scaledown_client.py
=====================================
ScaleDown integration — uses REST API directly.
API docs: https://docs.scaledown.ai/quickstart

When enabled:
  BM25+TF-IDF → Extractive → ScaleDown → Prompt Assembly → LLM

v2.0 Sprint 2
Owner: Akagami
"""

import os
import sys
import requests
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from typing import Optional, Tuple
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

SCALEDOWN_URL = "https://api.scaledown.xyz/compress/raw/"

SCALEDOWN_SUPPORTED_MODELS = [
    "gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini",
    "o3", "o4-mini",
    "claude-3-5-sonnet", "claude-3-5-sonnet-20240620",
    "claude-3-haiku", "claude-3-opus", "claude-3-sonnet",
    "llama-3-1-70b", "llama-3-1-8b", "llama-3-2-1b",
    "llama-3-2-3b", "llama-3-2-11b", "llama-3-2-90b",
    "titan-text-express", "titan-text-premier",
    "command-r", "command-r-plus",
    "mistral-7b", "mixtral-8x7b", "mistral-large"
]

SCALEDOWN_DEFAULT_MODEL = "llama-3-1-70b"

# Maps our internal model names → ScaleDown accepted model names
SCALEDOWN_MODEL_MAP = {
    "gemini-2.0-flash": "llama-3-1-70b",
    "gemini-2.0-flash-lite": "llama-3-1-70b",
    "gemini-1.5-flash": "llama-3-1-70b",
    "gemini-1.5-pro": "llama-3-1-70b",
    "claude-sonnet-4-6": "claude-3-5-sonnet",
    "claude-haiku-4-5-20251001": "claude-3-haiku",
    "claude-opus-4-6": "claude-3-opus",
    "llama-3.1-70b-versatile": "llama-3-1-70b",
    "llama-3.1-8b-instant": "llama-3-1-8b",
    "mixtral-8x7b-32768": "mixtral-8x7b",
    "gpt-4o-mini": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
}



def compress_with_scaledown(text: str,
                             api_key: str,
                             model: str = "gemini-2.0-flash",
                             rate: str = "auto") -> Tuple[str, dict]:
    """
    Compress text using ScaleDown REST API.

    Args:
        text    : Text to compress
        api_key : ScaleDown API key
        rate    : "auto", "high", "medium", "low"

    Returns:
        Tuple of (compressed_text, metrics_dict)
    """
    if not api_key:
        raise ValueError(
            "⚠️ ScaleDown API key required. "
            "Get one at https://scaledown.ai"
        )

    # Map our model name to ScaleDown accepted name
    scaledown_model = SCALEDOWN_MODEL_MAP.get(model, model)
    if scaledown_model not in SCALEDOWN_SUPPORTED_MODELS:
        print(f"   ⚠️  '{model}' not supported by ScaleDown → using llama-3-1-70b")
        scaledown_model = SCALEDOWN_DEFAULT_MODEL

    original_tokens = len(enc.encode(text))


    headers = {
        "x-api-key"   : api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "context": text,
        "prompt": (
            "Analyze this Indian parliamentary bill for citizen impact, "
            "key changes, affected groups, and rights implications."
        ),
        "model": scaledown_model,
        "scaledown": {
            "rate": rate
        }
    }


    try:
        print(f"⚡ ScaleDown compressing {original_tokens:,} tokens...")
        response = requests.post(
            SCALEDOWN_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=60
        )

    except requests.exceptions.ConnectionError:
        raise ValueError(
            "⚠️ Cannot reach ScaleDown API. "
            "Check your internet connection."
        )
    except requests.exceptions.Timeout:
        raise ValueError(
            "⚠️ ScaleDown API timed out. Try again."
        )

    # Handle HTTP errors
    if response.status_code == 401:
        raise ValueError(
            "⚠️ Invalid ScaleDown API key. "
            "Check your key at https://scaledown.ai"
        )
    elif response.status_code == 429:
        raise ValueError(
            "⚠️ ScaleDown quota exceeded. "
            "Check your plan at https://scaledown.ai"
        )
    elif response.status_code == 400:
        raise ValueError(
            f"⚠️ ScaleDown bad request: {response.text[:200]}"
        )
    elif not response.ok:
        raise ValueError(
            f"⚠️ ScaleDown error {response.status_code}: {response.text[:200]}"
        )

    result = response.json()

    if not result.get("successful", False):
        raise ValueError(
            f"⚠️ ScaleDown compression failed: {result}"
        )

    # ScaleDown wraps results in a "results" object + root tokens
    results_obj       = result.get("results", {})
    compressed_text   = results_obj.get("compressed_prompt", text)
    compressed_tokens = result.get("total_compressed_tokens",
                                   len(enc.encode(compressed_text)))
    original_tokens   = result.get("total_original_tokens", original_tokens)
    
    reduction         = round(
        (1 - compressed_tokens / max(original_tokens, 1)) * 100, 2
    )

    metrics = {
        "method"           : "scaledown",
        "original_tokens"  : original_tokens,
        "compressed_tokens": compressed_tokens,
        "reduction_percent": reduction,
        "latency_ms"       : result.get("latency_ms", 0),
        "rate"             : result.get("request_metadata", {}).get("compression_rate", rate)
    }

    print(f"   ✅ ScaleDown: {original_tokens:,} → {compressed_tokens:,} tokens "
          f"({reduction}% reduction) in {metrics['latency_ms']}ms")


    return compressed_text, metrics


def try_scaledown_compress(text: str,
                            api_key: Optional[str],
                            model: str = "gemini-2.0-flash",
                            rate: str = "auto") -> Tuple[str, dict]:
    """
    Safe wrapper — never crashes the pipeline.
    If ScaleDown fails, returns original text unchanged.
    """
    original_tokens = len(enc.encode(text))

    if not api_key:
        return text, {
            "method"           : "skipped",
            "reason"           : "no_api_key",
            "original_tokens"  : original_tokens,
            "compressed_tokens": original_tokens,
            "reduction_percent": 0
        }

    try:
        return compress_with_scaledown(text, api_key, model, rate)

    except ValueError as e:
        print(f"⚠️  ScaleDown skipped: {e}")
        return text, {
            "method"           : "skipped",
            "reason"           : str(e),
            "original_tokens"  : original_tokens,
            "compressed_tokens": original_tokens,
            "reduction_percent": 0
        }

    except Exception as e:
        print(f"⚠️  ScaleDown unexpected error: {e} — using original")
        return text, {
            "method"           : "error",
            "reason"           : str(e),
            "original_tokens"  : original_tokens,
            "compressed_tokens": original_tokens,
            "reduction_percent": 0
        }