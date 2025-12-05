import typer
import json
from pathlib import Path
from typing import Optional
from .extractor import extract_invoices_from_dir, extract_invoice
from .validator import validate_all
from .models import Invoice

app = typer.Typer()

@app.command()
def extract(pdf_dir: Path, output: Path):
    """Extract invoices from a directory of PDFs to a JSON file."""
    typer.echo(f"Extracting invoices from {pdf_dir}...")
    invoices = extract_invoices_from_dir(str(pdf_dir))
    
    # Convert to dicts for JSON serialization
    data = [inv.model_dump(mode='json') for inv in invoices]
    
    with open(output, 'w') as f:
        json.dump(data, f, indent=2)
        
    typer.echo(f"Extracted {len(invoices)} invoices to {output}")

@app.command()
def validate(input_json: Path, report: Path):
    """Validate invoices from a JSON file and generate a report."""
    typer.echo(f"Validating invoices from {input_json}...")
    
    with open(input_json, 'r') as f:
        data = json.load(f)
        
    invoices = [Invoice(**item) for item in data]
    results, summary = validate_all(invoices)
    
    report_data = {
        "summary": summary.model_dump(),
        "details": [res.model_dump() for res in results]
    }
    
    with open(report, 'w') as f:
        json.dump(report_data, f, indent=2)
        
    typer.echo(f"Validation complete. Summary:")
    typer.echo(f"  Total: {summary.total_invoices}")
    typer.echo(f"  Valid: {summary.valid_invoices}")
    typer.echo(f"  Invalid: {summary.invalid_invoices}")
    typer.echo(f"Report saved to {report}")
    
    if summary.invalid_invoices > 0:
        raise typer.Exit(code=1)

@app.command()
def full_run(pdf_dir: Path, report: Path):
    """Extract and validate in one go."""
    typer.echo(f"Running full pipeline on {pdf_dir}...")
    
    # Extract
    invoices = extract_invoices_from_dir(str(pdf_dir))
    
    # Validate
    results, summary = validate_all(invoices)
    
    report_data = {
        "summary": summary.model_dump(),
        "details": [res.model_dump() for res in results],
        "extracted_data": [inv.model_dump(mode='json') for inv in invoices]
    }
    
    with open(report, 'w') as f:
        json.dump(report_data, f, indent=2)
        
    typer.echo(f"Full run complete.")
    typer.echo(f"  Total: {summary.total_invoices}")
    typer.echo(f"  Valid: {summary.valid_invoices}")
    typer.echo(f"  Invalid: {summary.invalid_invoices}")
    typer.echo(f"Report saved to {report}")
    
    if summary.invalid_invoices > 0:
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
