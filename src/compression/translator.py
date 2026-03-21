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

def translate_result(result: AnalysisResult,
                     target_lang: str = "hi") -> dict:

    if target_lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {target_lang}. "
                         f"Choose from: {list(SUPPORTED_LANGUAGES.keys())}")

    translator = GoogleTranslator(source='auto', target=target_lang)
    lang_name = SUPPORTED_LANGUAGES[target_lang]

    print(f"\n🌐 Translating to {lang_name}...")

    # Simple cache dictionary to avoid repeated translations
    translation_cache = {}

    def cached_translate(text: str) -> str:
        if text in translation_cache:
            return translation_cache[text]
        translated_text = translator.translate(text)
        translation_cache[text] = translated_text
        return translated_text

    translated = {
        "bill_id"         : result.bill_id,
        "language"        : lang_name,
        "language_code"   : target_lang,
        "citizen_summary" : cached_translate(result.citizen_summary),
        "key_changes"     : [cached_translate(c) for c in result.key_changes],
        "affected_groups" : [cached_translate(g) for g in result.affected_groups[:3]],
        "rights_impact"   : cached_translate(result.rights_impact),
        "implementation_date": result.implementation_date,
        "compression_ratio"  : result.compression_ratio,
        "carbon_saved_grams" : result.carbon_saved_grams
    }

    print(f"✅ Translation to {lang_name} complete")
    return translated