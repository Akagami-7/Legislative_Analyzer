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

    # ✅ NEW SDK CLIENT
    client = genai.Client(api_key=api_key)

    print("\n🤖 Calling Gemini API...")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=SYSTEM_PROMPT + "\n\n" + prompt
    )

    text = response.text

    # 🧠 Extract JSON safely
    try:
        result_dict = json.loads(text)
    except Exception:
        # fallback: try to clean response
        start = text.find("{")
        end = text.rfind("}") + 1
        result_dict = json.loads(text[start:end])

    # ✅ Create Pydantic object
    result = AnalysisResult(
        bill_id=result_dict.get("bill_id", ""),
        citizen_summary=result_dict.get("citizen_summary", ""),
        key_changes=result_dict.get("key_changes", []),
        affected_groups=result_dict.get("affected_groups", []),
        rights_impact=result_dict.get("rights_impact", ""),
        implementation_date=result_dict.get("implementation_date", ""),
        tokens_input=original_tokens,
        tokens_output=compressed_tokens,
        compression_ratio=round(
            1 - (compressed_tokens / max(original_tokens, 1)), 4
        ),
        carbon_saved_grams=round(
            (1 - (compressed_tokens / max(original_tokens, 1))) * 15, 2
        )
    )

    print("✅ Gemini response received")

    return result