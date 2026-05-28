import sys
import os

# Simulate PYTHONPATH=src
project_root = os.getcwd()
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, src_dir)

print(f"Simulating PYTHONPATH={src_dir}")
print(f"Current Sys Path (first 2): {sys.path[:2]}")

try:
    print("Testing 'import api.main'...")
    import api.main
    print("✅ 'import api.main' worked.")
except Exception as e:
    print(f"❌ 'import api.main' failed: {e}")

try:
    print("Testing 'import src.api.main'...")
    import src.api.main
    print("✅ 'import src.api.main' worked.")
except Exception as e:
    print(f"❌ 'import src.api.main' failed: {e}")
