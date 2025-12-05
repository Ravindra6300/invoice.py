from typing import List, Dict
from datetime import date, timedelta
from .models import Invoice, ValidationResult, ValidationSummary, Currency

def validate_invoice(invoice: Invoice) -> ValidationResult:
    res = ValidationResult(invoice_id=invoice.invoice_number or "UNKNOWN")
    
    # --- Completeness Rules ---
    if not invoice.invoice_number:
        res.is_valid = False
        res.errors.append("missing_field: invoice_number")
        
    if not invoice.invoice_date:
        res.is_valid = False
        res.errors.append("missing_field: invoice_date")
        
    if not invoice.seller_name:
        res.is_valid = False
        res.errors.append("missing_field: seller_name")
        
    if not invoice.buyer_name:
        res.is_valid = False
        res.errors.append("missing_field: buyer_name")
        
    if invoice.gross_total is None:
        res.is_valid = False
        res.errors.append("missing_field: gross_total")

    # --- Format Rules ---
    # Currency check
    if invoice.currency and invoice.currency not in [c.value for c in Currency]:
        res.is_valid = False
        res.errors.append(f"invalid_format: currency {invoice.currency} not supported")
    
    # Numeric checks
    if invoice.net_total is not None and invoice.net_total < 0:
        res.is_valid = False
        res.errors.append("invalid_format: net_total must be non-negative")
        
    if invoice.gross_total is not None and invoice.gross_total < 0:
        res.is_valid = False
        res.errors.append("invalid_format: gross_total must be non-negative")

    # --- Business Rules ---
    # Totals mismatch
    if invoice.net_total is not None and invoice.tax_amount is not None and invoice.gross_total is not None:
        calc_gross = invoice.net_total + invoice.tax_amount
        if abs(calc_gross - invoice.gross_total) > 0.05: # Tolerance
            res.is_valid = False
            res.errors.append(f"business_rule_failed: totals_mismatch (net {invoice.net_total} + tax {invoice.tax_amount} != gross {invoice.gross_total})")
            
    # Due date vs Invoice date
    if invoice.invoice_date and invoice.due_date:
        if invoice.due_date < invoice.invoice_date:
            res.is_valid = False
            res.errors.append("business_rule_failed: due_date_before_invoice_date")

    # --- Anomaly Rules ---
    if invoice.invoice_date:
        today = date.today()
        # More than 2 years old
        if (today - invoice.invoice_date) > timedelta(days=365*2):
            res.warnings.append("anomaly: invoice_date_too_old (> 2 years)")
        # Future date (more than 30 days ahead)
        if (invoice.invoice_date - today) > timedelta(days=30):
            res.warnings.append("anomaly: invoice_date_in_future")

    return res

def validate_all(invoices: List[Invoice]) -> tuple[List[ValidationResult], ValidationSummary]:
    results = []
    summary = ValidationSummary()
    
    summary.total_invoices = len(invoices)
    
    for inv in invoices:
        res = validate_invoice(inv)
        results.append(res)
        
        if res.is_valid:
            summary.valid_invoices += 1
        else:
            summary.invalid_invoices += 1
            
        for err in res.errors:
            summary.error_counts[err] = summary.error_counts.get(err, 0) + 1
            
    return results, summary
