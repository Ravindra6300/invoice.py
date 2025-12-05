from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from .models import Invoice, ValidationResult, ValidationSummary
from .validator import validate_all, validate_invoice
from .extractor import extract_invoice
import shutil
import os
import tempfile

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Invoice QC Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="web"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('web/index.html')


@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/validate-json", response_model=dict)
def validate_json(invoices: List[Invoice]):
    results, summary = validate_all(invoices)
    return {
        "summary": summary,
        "results": results
    }

@app.post("/extract-and-validate-pdfs")
async def extract_and_validate_pdfs(files: List[UploadFile] = File(...)):
    invoices = []
    
    # Create a temp dir to save uploaded files
    with tempfile.TemporaryDirectory() as temp_dir:
        for file in files:
            temp_path = os.path.join(temp_dir, file.filename)
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            try:
                inv = extract_invoice(temp_path)
                invoices.append(inv)
            except Exception as e:
                # Handle error or skip
                pass
                
    results, summary = validate_all(invoices)
    
    return {
        "summary": summary,
        "results": results,
        "extracted_data": invoices
    }
