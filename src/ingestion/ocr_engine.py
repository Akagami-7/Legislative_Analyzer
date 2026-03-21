from pdf2image import convert_from_path
import pytesseract

def run_ocr(pdf_path: str) -> list:
    images = convert_from_path(pdf_path, dpi=300)
    return [
        pytesseract.image_to_string(img, lang="hin+eng")
        for img in images
    ]