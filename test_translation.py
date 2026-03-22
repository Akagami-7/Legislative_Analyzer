"""
Quick test: IndicTrans2 via HuggingFace API
Run with: python test_translation.py
"""
import sys, os
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv()

from src.compression.translator import translate_result
from src.shared_schemas import AnalysisResult

result = AnalysisResult(
    bill_id='test',
    citizen_summary='Every citizen has the right to information under this Act.',
    key_changes=['Companies must get consent before collecting data.'],
    affected_groups=['All citizens', 'Companies'],
    rights_impact='Strengthens right to privacy.',
    implementation_date='2024',
    tokens_input=100,
    tokens_output=20,
    compression_ratio=0.8,
    carbon_saved_grams=1.2
)

hf_token = os.getenv('HUGGINGFACE_TOKEN')
print(f'HF Token found: {bool(hf_token)} ({(hf_token[:8] + "...") if hf_token else "None"})')

translated = translate_result(result, target_lang='hi', hf_token=hf_token)

print()
print('=== HINDI TRANSLATION RESULT ===')
print(f'citizen_summary : {translated["citizen_summary"]}')
print(f'key_changes     : {translated["key_changes"]}')
print(f'rights_impact   : {translated["rights_impact"]}')
print(f'language        : {translated["language"]}')
