from google import genai
import os
import json
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.shared_schemas import AnalysisResult
from dotenv import load_dotenv
load_dotenv()

SYSTEM_PROMPT = """You are a legal analyst for Indian citizens.
Analyze the provided legislative text.
STRICT RULES:
- Return ONLY valid JSON
- No explanations
- No markdown
- No code blocks
- Must match this structure exactly:
{
  "bill_id": "",
  "citizen_summary": "",
  "key_changes": [],
  "affected_groups": [],
  "rights_impact": "",
  "implementation_date": ""
}
"""

def analyze_with_gemini(prompt: str,
                        original_tokens: int,
                        compressed_tokens: int) -> AnalysisResult:

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env")

    client = genai.Client(api_key=api_key)
    print("\n🤖 Calling Gemini API...")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=SYSTEM_PROMPT + "\n\n" + prompt
    )

    # ── Extract text safely from new SDK response format ──────
    text = None

    # Method 1: direct .text attribute
    if hasattr(response, 'text') and response.text:
        text = response.text

    # Method 2: candidates → parts
    if not text:
        try:
            text = response.candidates[0].content.parts[0].text
        except Exception:
            pass

    # Method 3: iterate parts
    if not text:
        try:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text') and part.text:
                    text = part.text
                    break
        except Exception:
            pass

    if not text:
        # Print full response for debugging
        print(f"DEBUG response: {response}")
        raise ValueError(
            "Gemini returned empty response. "
            "Check if the prompt exceeds safety filters or token limits."
        )

    print(f"DEBUG text preview: {text[:200]}")

    # ── Parse JSON ────────────────────────────────────────────
    try:
        # Strip markdown code blocks if present
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
            clean = clean.strip()

        result_dict = json.loads(clean)

    except Exception:
        # Last resort: find JSON boundaries
        try:
            start = text.find("{")
            end   = text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON object found in response")
            result_dict = json.loads(text[start:end])
        except Exception as e:
            print(f"Raw Gemini text was:\n{text}")
            raise ValueError(f"Could not parse Gemini response as JSON: {e}")

    # ── Build AnalysisResult ──────────────────────────────────
    compression_ratio = round(
        1 - (compressed_tokens / max(original_tokens, 1)), 4
    )

    result = AnalysisResult(
        bill_id             = result_dict.get("bill_id", ""),
        citizen_summary     = result_dict.get("citizen_summary", ""),
        key_changes         = result_dict.get("key_changes", []),
        affected_groups     = result_dict.get("affected_groups", []),
        rights_impact       = result_dict.get("rights_impact", ""),
        implementation_date = result_dict.get("implementation_date", ""),
        tokens_input        = original_tokens,
        tokens_output       = compressed_tokens,
        compression_ratio   = compression_ratio,
        carbon_saved_grams  = round(compression_ratio * 15, 2)
    )

    print("✅ Gemini response received")
    return result