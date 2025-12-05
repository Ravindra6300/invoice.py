import pdfplumber
import re
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from .models import Invoice, LineItem, Currency

def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def parse_date(date_str: str) -> Optional[datetime.date]:
    if not date_str:
        return None
    # Try common formats
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None

def parse_currency(text: str) -> Optional[Currency]:
    text = text.upper()
    if "USD" in text or "$" in text:
        return Currency.USD
    if "EUR" in text or "€" in text:
        return Currency.EUR
    if "GBP" in text or "£" in text:
        return Currency.GBP
    if "INR" in text or "₹" in text:
        return Currency.INR
    return None

def extract_invoice(pdf_path: str) -> Invoice:
    text = extract_text_from_pdf(pdf_path)
    lines = text.split('\n')
    
    invoice = Invoice()
    invoice.raw_text = text
    
    # Debug: Print first 500 chars to see what we are working with
    print(f"--- Extracted Text for {pdf_path} ---\n{text[:500]}...\n--------------------------------")

    # Invoice Number
    # Patterns: "Invoice No:", "Invoice #", "Inv:", or just "Invoice" followed by a number
    inv_patterns = [
        r'(?i)invoice\s*(?:no\.?|number|#|id)?\s*[:#]?\s*([A-Z0-9\-/]+)',
        r'(?i)inv\.?\s*(?:no\.?|number|#)?\s*[:#]?\s*([A-Z0-9\-/]+)'
    ]
    for p in inv_patterns:
        match = re.search(p, text)
        if match:
            invoice.invoice_number = match.group(1).strip()
            break
        
    # Dates
    # Look for "Date:", "Invoice Date:", "Dated:"
    date_patterns = [
        r'(?i)invoice\s*date\s*[:\.]?\s*([\d/\-\sA-Za-z,]+)',
        r'(?i)date\s*[:\.]?\s*([\d/\-\sA-Za-z,]+)',
        r'(?i)dated\s*[:\.]?\s*([\d/\-\sA-Za-z,]+)'
    ]
    for p in date_patterns:
        match = re.search(p, text)
        if match:
            parsed = parse_date(match.group(1))
            if parsed:
                invoice.invoice_date = parsed
                break
        
    due_match = re.search(r'(?i)due\s*date\s*[:\.]?\s*([\d/\-\sA-Za-z,]+)', text)
    if due_match:
        invoice.due_date = parse_date(due_match.group(1))

    # Parties
    # Heuristic: "Bill To:" or "To:" for Buyer
    bill_to_idx = -1
    lines = [l.strip() for l in lines if l.strip()] # Clean empty lines
    
    for i, line in enumerate(lines):
        if re.search(r'(?i)^(bill\s*to|to|buyer):?$', line):
            bill_to_idx = i
            break
            
    if bill_to_idx != -1 and bill_to_idx + 1 < len(lines):
        invoice.buyer_name = lines[bill_to_idx + 1]
        if bill_to_idx + 2 < len(lines):
            invoice.buyer_address = lines[bill_to_idx + 2]
    
    # Seller: Often the very first line, or after "From:"
    from_idx = -1
    for i, line in enumerate(lines):
        if re.search(r'(?i)^(from|seller):?$', line):
            from_idx = i
            break
    
    if from_idx != -1 and from_idx + 1 < len(lines):
        invoice.seller_name = lines[from_idx + 1]
    else:
        # Fallback: First line that isn't "Invoice"
        for line in lines[:3]:
            if len(line) > 3 and "invoice" not in line.lower():
                invoice.seller_name = line
                break

    # Totals
    # Clean text for amount search (remove currency symbols for easier regex)
    clean_text = text.replace('$', '').replace('€', '').replace('£', '').replace('₹', '')
    
    # Net Total
    net_match = re.search(r'(?i)(?:net\s*total|sub\s*total|subtotal)\s*[:\.]?\s*([\d,]+\.?\d*)', clean_text)
    if net_match:
        try:
            invoice.net_total = float(net_match.group(1).replace(',', ''))
        except:
            pass
            
    # Tax Amount
    tax_match = re.search(r'(?i)(?:tax|vat|gst|hst)\s*(?:amount|total)?\s*[:\.]?\s*([\d,]+\.?\d*)', clean_text)
    if tax_match:
        try:
            invoice.tax_amount = float(tax_match.group(1).replace(',', ''))
        except:
            pass
            
    # Gross Total
    # Look for "Total", "Grand Total", "Amount Due", "Total Amount"
    gross_patterns = [
        r'(?i)(?:grand\s*total|total\s*amount|amount\s*due)\s*[:\.]?\s*([\d,]+\.?\d*)',
        r'(?i)^total\s*[:\.]?\s*([\d,]+\.?\d*)' # "Total" at start of line
    ]
    for p in gross_patterns:
        match = re.search(p, clean_text, re.MULTILINE)
        if match:
            try:
                invoice.gross_total = float(match.group(1).replace(',', ''))
                break
            except:
                pass

    # --- GERMAN / SPECIFIC INVOICE SUPPORT ---
    
    # Invoice Number (German: Bestellung / Auftrag / Rechnung)
    if not invoice.invoice_number:
        # "Bestellung AUFNR34343"
        de_inv_match = re.search(r'(?i)(?:Bestellung|Auftrag|Rechnung)\s*(?:Nr\.?|Nummer)?\s*([A-Z0-9]+)', text)
        if de_inv_match:
            invoice.invoice_number = de_inv_match.group(1)

    # Date (German: "vom 22.05.2024")
    if not invoice.invoice_date:
        de_date_match = re.search(r'(?i)(?:vom|Datum)\s*[:\s]*(\d{2}\.\d{2}\.\d{4})', text)
        if de_date_match:
            # Replace dots with dashes for parser or handle custom
            try:
                d_str = de_date_match.group(1)
                invoice.invoice_date = datetime.strptime(d_str, "%d.%m.%Y").date()
            except:
                pass

    # Totals (German number format: 1.234,56)
    # Helper to parse German float: "76,16" -> 76.16
    def parse_de_float(s):
        try:
            return float(s.replace('.', '').replace(',', '.'))
        except:
            return None

    # Net Total ("Gesamtwert EUR 64,00")
    if invoice.net_total is None:
        net_match = re.search(r'(?i)Gesamtwert\s*(?:EUR|€)?\s*([\d\.,]+)', text)
        if net_match:
            invoice.net_total = parse_de_float(net_match.group(1))

    # Tax ("MwSt. 19,00% EUR 12,16")
    if invoice.tax_amount is None:
        tax_match = re.search(r'(?i)MwSt\..*?EUR\s*([\d\.,]+)', text)
        if tax_match:
            invoice.tax_amount = parse_de_float(tax_match.group(1))

    # Gross Total ("Gesamtwert inkl. MwSt. EUR 76,16")
    if invoice.gross_total is None:
        gross_match = re.search(r'(?i)Gesamtwert\s*inkl\.\s*MwSt\..*?EUR\s*([\d\.,]+)', text)
        if gross_match:
            invoice.gross_total = parse_de_float(gross_match.group(1))

    # Buyer (Heuristic for this specific layout)
    # "Bitte liefern Sie an:" -> Next lines
    if not invoice.buyer_name:
        delivery_match = re.search(r'(?i)Bitte liefern Sie an:', text)
        if delivery_match:
            # Look at lines after this match
            # Find the line index
            for i, line in enumerate(lines):
                if "Bitte liefern Sie an" in line:
                    # The buyer name is likely 1-2 lines down, skipping "Zentraleinkauf" or similar
                    if i + 2 < len(lines):
                         invoice.buyer_name = lines[i+2].strip() # "Beispielname Unternehmen"
                    break

    # Seller (Top line often)
    if not invoice.seller_name and len(lines) > 0:
        # "ABC Corporation" is at the start
        invoice.seller_name = lines[0].strip()

    # --- END GERMAN SUPPORT ---

    # --- FALLBACKS ---
    
    # Fallback Invoice Number: Look for any token starting with INV- or similar
    if not invoice.invoice_number:
        fallback_match = re.search(r'\b(INV-?\d+)\b', text)
        if fallback_match:
            invoice.invoice_number = fallback_match.group(1)
            
    # Fallback Date: First date-like string found
    if not invoice.invoice_date:
        # Regex for YYYY-MM-DD or DD-MM-YYYY
        date_fallback = re.search(r'\b(\d{4}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})\b', text)
        if date_fallback:
            invoice.invoice_date = parse_date(date_fallback.group(1))

    # Fallback Buyer: If we have a seller but no buyer, assume the text block with "Address" or "Street" below seller is buyer
    if not invoice.buyer_name and invoice.seller_name:
        # This is a wild guess: look for lines containing "Street" or "Road" or "Box"
        for line in lines:
            if any(x in line.lower() for x in ['street', 'road', 'box', 'ave', 'lane']) and line != invoice.seller_address:
                # Assume the line above address is name
                idx = lines.index(line)
                if idx > 0:
                    invoice.buyer_name = lines[idx-1]
                    invoice.buyer_address = line
                break

    # Fallback Gross Total: Largest number in the text
    if invoice.gross_total is None:
         numbers = re.findall(r'\b\d+\.\d{2}\b', clean_text)
         if numbers:
             try:
                 floats = [float(n) for n in numbers]
                 invoice.gross_total = max(floats)
             except:
                 pass

    return invoice

def extract_invoices_from_dir(directory: str) -> List[Invoice]:
    invoices = []
    path = Path(directory)
    for pdf_file in path.glob("*.pdf"):
        try:
            inv = extract_invoice(str(pdf_file))
            invoices.append(inv)
        except Exception as e:
            print(f"Error extracting {pdf_file}: {e}")
            # Optionally add a partial invoice or log error
    return invoices
