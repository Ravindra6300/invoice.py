import pdfplumber
import sys
from pathlib import Path

def debug_pdf(pdf_path):
    print(f"--- Debugging: {pdf_path} ---")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                print("ERROR: No pages found in PDF.")
                return

            full_text = ""
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                print(f"\n[Page {i+1}] Text Content:")
                if text:
                    print(text)
                    full_text += text
                else:
                    print("<NO TEXT EXTRACTED - This page might be an image/scan>")
            
            print("\n--- End of Text ---")
            
            if not full_text.strip():
                print("\nDIAGNOSIS: No text could be extracted.")
                print("POSSIBLE CAUSE: This PDF is likely a scanned image, not a text PDF.")
                print("SOLUTION: You need an OCR (Optical Character Recognition) tool.")
            else:
                print("\nDIAGNOSIS: Text was found.")
                print("ACTION: Please share the text output above so we can fix the regex patterns.")

    except Exception as e:
        print(f"ERROR reading PDF: {e}")

if __name__ == "__main__":
    # Look for any PDF in the current directory or subdirectories
    pdf_files = list(Path(".").rglob("*.pdf"))
    
    if not pdf_files:
        print("No PDF files found in the current directory.")
    else:
        print(f"Found {len(pdf_files)} PDFs. Checking the first one: {pdf_files[0]}")
        debug_pdf(str(pdf_files[0]))
