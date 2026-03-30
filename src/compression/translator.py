"""
src/compression/translator.py
================================
Translation with dual strategy:
  Primary   : IndicTrans2 via HuggingFace Inference API
  Fallback  : deep_translator (Google Translate)

UPDATED: Compatible with CitizenSummary (no AnalysisResult)

Owner: Akagami
"""

import os
import sys
import requests
import time

from typing import Optional
from src.shared_schemas import CitizenSummary

# ── HuggingFace Inference API ────────────────────────────────────────────────
HF_API_URL = (
    "https://api-inference.huggingface.co/models/"
    "ai4bharat/indictrans2-en-indic-dist-200M"
)

# ── Language mapping ─────────────────────────────────────────────────────────
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

MAX_CHARS = 4500


# ─────────────────────────────────────────────────────────────────────────────
# IndicTrans2 (HuggingFace)
# ─────────────────────────────────────────────────────────────────────────────
def _translate_indictrans2(text: str, tgt_lang_code: str, hf_token: str) -> Optional[str]:
    if not text or not text.strip():
        return text

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": text[:MAX_CHARS],
        "parameters": {
            "src_lang": "eng_Latn",
            "tgt_lang": tgt_lang_code
        }
    }

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)

        if response.status_code == 503:
            print("   ⏳ Model loading, retrying in 20s...")
            time.sleep(20)
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)

        if response.status_code in [401, 429]:
            return None

        if not response.ok:
            return None

        result = response.json()

        if isinstance(result, list) and result:
            return result[0].get("translation_text")

        if isinstance(result, dict):
            return result.get("translation_text")

        return None

    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Google Translate fallback
# ─────────────────────────────────────────────────────────────────────────────
def _translate_deep(text: str, target_lang: str) -> str:
    from deep_translator import GoogleTranslator

    if not text or not text.strip():
        return text

    try:
        if len(text) <= MAX_CHARS:
            return GoogleTranslator(source="auto", target=target_lang).translate(text) or text

        # Chunk long text
        sentences = text.replace(". ", ".|").split("|")
        chunks, current = [], ""

        for s in sentences:
            if len(current) + len(s) <= MAX_CHARS:
                current += s + " "
            else:
                chunks.append(current)
                current = s + " "
        if current:
            chunks.append(current)

        return " ".join(
            GoogleTranslator(source="auto", target=target_lang).translate(c) or c
            for c in chunks
        )

    except Exception:
        return text


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TRANSLATION FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def translate_result(
    result: CitizenSummary,
    target_lang: str = "hi",
    hf_token: Optional[str] = None
) -> dict:

    if target_lang not in LANG_MAP:
        raise ValueError(f"Unsupported language: {target_lang}")

    flores_code, lang_name = LANG_MAP[target_lang]
    token = hf_token or os.getenv("HUGGINGFACE_TOKEN")

    print(f"\n🌐 Translating to {lang_name}...")

    # Choose translator
    if token:
        def translate(text: str) -> str:
            t = _translate_indictrans2(text, flores_code, token)
            return t if t else _translate_deep(text, target_lang)
    else:
        def translate(text: str) -> str:
            return _translate_deep(text, target_lang)

    # Detect structure (AnalysisResult vs CitizenSummary)
    is_analysis = hasattr(result, "citizen_summary")

    translated = {
        "bill_id": result.bill_id,
        "language": target_lang,
        "citizen_summary": translate(result.citizen_summary if is_analysis else result.headline),
        "key_changes": [translate(k) for k in (result.key_changes if is_analysis else result.key_points)],
        "rights_impact": translate(result.rights_impact if is_analysis else result.impact_statement),
        "overview": translate(result.overview) if result.overview else None
    }

    print(f"✅ Translation complete")
    return translated