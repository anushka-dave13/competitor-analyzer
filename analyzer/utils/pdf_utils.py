import pdfplumber

import tempfile
import os


def extract_text_with_pdfplumber(path):
    """Try to extract text using pdfplumber."""
    try:
        with pdfplumber.open(path) as pdf:
            text = ""
            for page in pdf.pages[:10]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
    except Exception as e:
        print(f"[pdfplumber] Error: {e}")
        return ""


def extpdf(path):
    """
    Attempts to extract text from a PDF.
    - Tries pdfplumber first.
    - Falls back to EasyOCR if pdfplumber returns no text.
    """
    
    text = extract_text_with_pdfplumber(path)
    if text:
        return text

    print("[Fallback] pdfplumber failed, trying OCR...")


    return ""
