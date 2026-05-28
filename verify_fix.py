import sys
import os

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.compression.multi_llm_client import get_available_models

def test_groq_models():
    print("Testing Groq models fetch...")
    try:
        # We use a dummy key. If requests is missing, this will raise NameError.
        # If requests is present, it will try the network call and likely fail with 401 or similar.
        result = get_available_models("groq", "dummy_key")
        print("Result:", result)
        if result.get("status") == "error" and "requests" in str(result.get("message")):
             print("FAILED: NameError or requests-related error still present in message.")
        else:
             print("SUCCESS: No NameError detected in function execution (or it hit a real network error, which is fine).")
    except NameError as e:
        print(f"FAILED: NameError caught: {e}")
    except Exception as e:
        print(f"Caught expected exception or other error: {e}")

if __name__ == "__main__":
    test_groq_models()
