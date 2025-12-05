
import os
from fastapi.testclient import TestClient
from invoice_qc.api import app

client = TestClient(app)

def test_raw_text_extraction():
    # Create a dummy PDF file for testing
    # Since we can't easily create a valid PDF with text without reportlab or similar, 
    # we will use the existing sample_pdf_1.pdf if it exists, or skip if not found.
    
    pdf_path = "sample_pdf_1.pdf"
    if not os.path.exists(pdf_path):
        print(f"Warning: {pdf_path} not found. Skipping test.")
        return

    with open(pdf_path, "rb") as f:
        files = {"files": ("sample.pdf", f, "application/pdf")}
        response = client.post("/extract-and-validate-pdfs", files=files)
    
    if response.status_code != 200:
        print(f"Error: API returned {response.status_code}")
        print(response.json())
        return

    data = response.json()
    
    if "extracted_data" not in data:
        print("Error: 'extracted_data' key missing in response")
        return

    extracted_list = data["extracted_data"]
    if not extracted_list:
        print("Error: extracted_data list is empty")
        return

    first_invoice = extracted_list[0]
    raw_text = first_invoice.get("raw_text")
    
    if raw_text:
        print("SUCCESS: raw_text found in response!")
        print(f"Preview: {raw_text[:50]}...")
    else:
        print("FAILURE: raw_text is missing or empty in response.")
        print(f"Keys found: {list(first_invoice.keys())}")

if __name__ == "__main__":
    test_raw_text_extraction()
