import subprocess
import os

def test_command(cmd_name):
    print(f"Testing command: {cmd_name}")
    try:
        # shell=True often helps on Windows if it's a batch file, 
        # but 193 usually means something else is wrong.
        subprocess.run([cmd_name, "--version"], capture_output=True, text=True)
        print(f"  ✅ {cmd_name} is working.")
    except Exception as e:
        print(f"  ❌ {cmd_name} failed: {e}")

if __name__ == "__main__":
    print("--- Diagnostic for WinError 193 ---")
    test_command("tesseract")
    test_command("pdftoppm")
    test_command("git")
    test_command("python")
    
    # Check for shadowing
    for cmd in ["tesseract", "pdftoppm"]:
        if os.path.exists(cmd):
            print(f"  ⚠️ Warning: A file or directory named '{cmd}' exists in the current directory. This might shadow the executable!")
        
    import pytesseract
    try:
        print(f"Pytesseract version: {pytesseract.get_tesseract_version()}")
    except Exception as e:
        print(f"Pytesseract error: {e}")
