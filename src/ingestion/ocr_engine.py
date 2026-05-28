from pdf2image import convert_from_path
import pytesseract
import subprocess
import shutil

def run_ocr(pdf_path: str) -> list:
    """
    Run OCR on a PDF file. 
    Checks for system dependencies (tesseract-ocr and poppler) to avoid cryptic WinError 193.
    """
    # ── 1. Check for pdftoppm (poppler) ──────────────────────
    if not shutil.which("pdftoppm"):
        # Common poppler path on Windows if not in PATH
        raise RuntimeError(
            "⚠️ Poppler (pdftoppm) is not installed or not in PATH. "
            "Analysis of scanned PDFs requires Poppler. Please install it."
        )

    # ── 2. Check for tesseract ───────────────────────────────
    if not shutil.which("tesseract"):
        raise RuntimeError(
            "⚠️ Tesseract-OCR is not installed or not in PATH. "
            "Analysis of scanned PDFs requires Tesseract. "
            "Please install it from: https://github.com/UB-Mannheim/tesseract/wiki"
        )

    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=300)
        
        # Run OCR on each page
        return [
            pytesseract.image_to_string(img, lang="hin+eng")
            for img in images
        ]
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"⚠️ OCR engine failed during processing: {str(e)}")
    except Exception as e:
        if "WinError 193" in str(e):
             raise RuntimeError(
                 "⚠️ Analysis failed ([WinError 193]). This usually means a dependency (Tesseract or Poppler) "
                 "is pointing to a non-executable file. Please verify your installations."
             )
        raise e