from typing import List, Optional
from datetime import date
from enum import Enum
from pydantic import BaseModel, Field

class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    INR = "INR"

class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None

class Invoice(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    
    seller_name: Optional[str] = None
    seller_address: Optional[str] = None
    seller_tax_id: Optional[str] = None
    
    buyer_name: Optional[str] = None
    buyer_address: Optional[str] = None
    buyer_tax_id: Optional[str] = None
    
    currency: Optional[Currency] = None
    net_total: Optional[float] = None
    tax_amount: Optional[float] = None
    gross_total: Optional[float] = None
    
    line_items: List[LineItem] = Field(default_factory=list)
    raw_text: Optional[str] = Field(None) # Include in API response


class ValidationResult(BaseModel):
    invoice_id: Optional[str] = None
    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

class ValidationSummary(BaseModel):
    total_invoices: int = 0
    valid_invoices: int = 0
    invalid_invoices: int = 0
    error_counts: dict[str, int] = Field(default_factory=dict)
