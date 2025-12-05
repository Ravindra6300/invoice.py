import sys
import os
sys.path.append(os.getcwd())

from invoice_qc.models import Invoice
from invoice_qc.validator import validate_invoice
from datetime import date

def test_validation():
    print("Testing validation logic...")
    
    # Valid Invoice
    inv = Invoice(
        invoice_number="INV-001",
        invoice_date=date(2024, 1, 1),
        seller_name="Seller",
        buyer_name="Buyer",
        gross_total=100.0,
        net_total=90.0,
        tax_amount=10.0,
        currency="USD"
    )
    res = validate_invoice(inv)
    assert res.is_valid, f"Expected valid, got errors: {res.errors}"
    print("Valid invoice passed.")
    
    # Invalid Invoice (missing number)
    inv_bad = Invoice(
        invoice_date=date(2024, 1, 1),
        seller_name="Seller",
        buyer_name="Buyer",
        gross_total=100.0
    )
    res_bad = validate_invoice(inv_bad)
    assert not res_bad.is_valid, "Expected invalid"
    assert "missing_field: invoice_number" in res_bad.errors
    print("Invalid invoice passed check.")
    
    # Business Rule Fail
    inv_mismatch = Invoice(
        invoice_number="INV-002",
        invoice_date=date(2024, 1, 1),
        seller_name="Seller",
        buyer_name="Buyer",
        gross_total=100.0,
        net_total=50.0,
        tax_amount=10.0, # 50+10 != 100
        currency="USD"
    )
    res_mismatch = validate_invoice(inv_mismatch)
    assert not res_mismatch.is_valid
    assert any("totals_mismatch" in e for e in res_mismatch.errors)
    print("Business rule check passed.")

if __name__ == "__main__":
    try:
        test_validation()
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
