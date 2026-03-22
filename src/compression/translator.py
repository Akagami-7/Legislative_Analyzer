"""
src/compression/translator.py
================================
Translation with dual strategy:
  Primary   : IndicTrans2 via HuggingFace Inference API
              (ai4bharat/indictrans2-en-indic-dist-200M)
  Fallback  : deep_translator (Google Translate)

v2.0 Sprint 2
Owner: Akagami
"""

import os
import sys
import requests
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.shared_schemas import AnalysisResult
from typing import Optional

# ── HuggingFace Inference API ─────────────────────────────────────────────────
HF_API_URL = (
    "https://api-inference.huggingface.co/models/"
    "ai4bharat/indictrans2-en-indic-dist-200M"
)

# ── Language code mapping ─────────────────────────────────────────────────────
# deep_translator codes → IndicTrans2 Flores codes
LANG_MAP = {
    "hi": ("hin_Deva", "Hindi"),
    "te": ("tel_Telu", "Telugu"),
    "ta": ("tam_Taml", "Tamil"),
    "bn": ("ben_Beng", "Bengali"),
    "mr": ("mar_Deva", "Marathi"),
    "gu": ("guj_Gujr", "Gujarati"),
    "kn": ("kan_Knda", "Kannada"),
    "ml": ("mal_Mlym", "Malayalam"),
    "pa": ("pan_Guru", "Punjabi"),
    "or": ("ory_Orya", "Odia"),
    "as": ("asm_Beng", "Assamese"),
    "ur": ("urd_Arab", "Urdu"),
}

MAX_CHARS = 4500  # chunk limit for both APIs


def _translate_indictrans2(text: str,
                            tgt_lang_code: str,
                            hf_token: str) -> Optional[str]:
    """
    Translate using IndicTrans2 via HuggingFace Inference API.
    Returns translated text or None if failed.
    """
    if not text or not text.strip():
        return text

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type" : "application/json"
    }

    payload = {
        "inputs"    : text[:MAX_CHARS],
        "parameters": {
            "src_lang": "eng_Latn",
            "tgt_lang": tgt_lang_code
        }
    }

    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 503:
            # Model loading — wait and retry once
            print("   ⏳ IndicTrans2 model loading, waiting 20s...")
            time.sleep(20)
            response = requests.post(
                HF_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )

        if response.status_code == 401:
            print("   ⚠️  Invalid HuggingFace token")
            return None

        if response.status_code == 429:
            print("   ⚠️  HuggingFace rate limit — falling back")
            return None

        if not response.ok:
            print(f"   ⚠️  IndicTrans2 error {response.status_code}")
            return None

        result = response.json()

        # Response format: [{"translation_text": "..."}]
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("translation_text", None)

        # Alternative format: {"translation_text": "..."}
        if isinstance(result, dict):
            return result.get("translation_text", None)

        return None

    except requests.exceptions.Timeout:
        print("   ⚠️  IndicTrans2 timeout — falling back")
        return None
    except Exception as e:
        print(f"   ⚠️  IndicTrans2 error: {e} — falling back")
        return None


def _translate_deep(text: str, target_lang: str) -> str:
    """
    Fallback translation using deep_translator.
    Handles long text with chunking.
    """
    from deep_translator import GoogleTranslator

    if not text or not text.strip():
        return text

    if len(text) <= MAX_CHARS:
        try:
            result = GoogleTranslator(
                source="auto", target=target_lang
            ).translate(text)
            return result if result else text
        except Exception as e:
            print(f"   ⚠️  deep_translator error: {e}")
            return text

    # Chunk at sentence boundaries
    sentences = text.replace(". ", ".|").split("|")
    chunks    = []
    current   = ""

    for sentence in sentences:
        if len(current) + len(sentence) <= MAX_CHARS:
            current += sentence + " "
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sentence + " "
    if current.strip():
        chunks.append(current.strip())

    translated_chunks = []
    for chunk in chunks:
        try:
            t = GoogleTranslator(
                source="auto", target=target_lang
            ).translate(chunk)
            translated_chunks.append(t if t else chunk)
        except Exception:
            translated_chunks.append(chunk)

    return " ".join(translated_chunks)


def translate_result(result: AnalysisResult,
                     target_lang: str = "hi",
                     hf_token: Optional[str] = None) -> dict:
    """
    Translate AnalysisResult to target Indian language.

    Strategy:
      1. Try IndicTrans2 via HuggingFace API (if hf_token provided)
      2. Fall back to deep_translator automatically

    Args:
        result      : AnalysisResult to translate
        target_lang : Language code (hi, te, ta, bn, mr, gu, kn, ml, pa, or)
        hf_token    : HuggingFace API token (optional)
                      Falls back to HUGGINGFACE_TOKEN env var
    """
    if target_lang not in LANG_MAP:
        raise ValueError(
            f"Unsupported language: {target_lang}. "
            f"Supported: {list(LANG_MAP.keys())}"
        )

    flores_code, lang_name = LANG_MAP[target_lang]

    # Get HF token from arg or env
    token = hf_token or os.getenv("HUGGINGFACE_TOKEN")

    print(f"\n🌐 Translating to {lang_name}...")

    # Choose translation function
    if token:
        print(f"   Using IndicTrans2 (HuggingFace API)...")
        def translate(text: str) -> str:
            result_text = _translate_indictrans2(text, flores_code, token)
            if result_text:
                return result_text
            # Fallback
            print(f"   ↩️  Falling back to deep_translator")
            return _translate_deep(text, target_lang)
    else:
        print(f"   Using deep_translator (no HF token set)...")
        print(f"   💡 Set HUGGINGFACE_TOKEN in .env for better quality")
        def translate(text: str) -> str:
            return _translate_deep(text, target_lang)

    # Translate all fields
    translated = {
        "bill_id"            : result.bill_id,
        "language"           : lang_name,
        "language_code"      : target_lang,
        "citizen_summary"    : translate(result.citizen_summary),
        "key_changes"        : [translate(c) for c in result.key_changes],
        "affected_groups"    : [translate(g) for g in result.affected_groups[:3]],
        "rights_impact"      : translate(result.rights_impact),
        "overview"           : translate(getattr(result, "overview", "")) if getattr(result, "overview", None) else None,
        "implementation_date": result.implementation_date,
        "compression_ratio"  : result.compression_ratio,
        "carbon_saved_grams" : result.carbon_saved_grams
    }

    print(f"✅ Translation to {lang_name} complete")
    return translated