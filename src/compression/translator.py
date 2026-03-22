from deep_translator import GoogleTranslator
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.shared_schemas import AnalysisResult

SUPPORTED_LANGUAGES = {
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "or": "Odia"
}

MAX_CHARS = 4500  # deep_translator limit is 5000 — stay under it

def safe_translate(text: str, target_lang: str) -> str:
    """Translate text safely — chunk if too long."""
    if not text or not text.strip():
        return text

    translator = GoogleTranslator(source="auto", target=target_lang)

    # If short enough, translate directly
    if len(text) <= MAX_CHARS:
        try:
            result = translator.translate(text)
            return result if result else text
        except Exception as e:
            print(f"  ⚠️  Translation failed: {e} — returning original")
            return text

    # Split into chunks at sentence boundaries
    sentences = text.replace(". ", ".|").split("|")
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) <= MAX_CHARS:
            current += sentence + " "
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sentence + " "
    if current.strip():
        chunks.append(current.strip())

    # Translate each chunk
    translated_chunks = []
    for chunk in chunks:
        try:
            t = GoogleTranslator(source="auto", target=target_lang).translate(chunk)
            translated_chunks.append(t if t else chunk)
        except Exception as e:
            print(f"  ⚠️  Chunk translation failed: {e} — using original")
            translated_chunks.append(chunk)

    return " ".join(translated_chunks)


def translate_result(result: AnalysisResult,
                     target_lang: str = "hi") -> dict:

    if target_lang not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language: {target_lang}. "
            f"Choose from: {list(SUPPORTED_LANGUAGES.keys())}"
        )

    lang_name = SUPPORTED_LANGUAGES[target_lang]
    print(f"\n🌐 Translating to {lang_name}...")

    translated = {
        "bill_id"             : result.bill_id,
        "language"            : lang_name,
        "language_code"       : target_lang,
        "citizen_summary"     : safe_translate(result.citizen_summary, target_lang),
        "key_changes"         : [safe_translate(c, target_lang) for c in result.key_changes],
        "affected_groups"     : [safe_translate(g, target_lang) for g in result.affected_groups[:3]],
        "rights_impact"       : safe_translate(result.rights_impact, target_lang),
        "implementation_date" : result.implementation_date,
        "compression_ratio"   : result.compression_ratio,
        "carbon_saved_grams"  : result.carbon_saved_grams
    }

    print(f"✅ Translation to {lang_name} complete")
    return translated