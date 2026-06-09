"""REST API for invoice automation system."""
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main_processor import InvoiceProcessor
from storage.database import InvoiceDatabase
from alerts.alert_manager import AlertManager

app = FastAPI(
    title="Invoice Automation API",
    description="AI-powered invoice processing API",
    version="1.0.0"
)

# Initialize components
processor = InvoiceProcessor()
db = InvoiceDatabase()
alert_manager = AlertManager()

class InvoiceResponse(BaseModel):
    id: int
    vendor_name: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[str]
    total_amount: Optional[float]
    status: str
    confidence_score: float
    validation_status: str

class ProcessingRequest(BaseModel):
    ocr_engine: Optional[str] = "paddleocr"
    validate: bool = True
    alert_on_high_amount: bool = True

class ValidationResult(BaseModel):
    field: str
    is_valid: bool
    message: str
    severity: str

@app.get("/")
def root():
    return {
        "message": "Invoice Automation API",
        "version": "1.0.0",
        "endpoints": [
            "/process - Upload and process invoice",
            "/invoices - List all invoices",
            "/invoices/{id} - Get specific invoice",
            "/stats - Processing statistics",
            "/health - Health check"
        ]
    }

@app.post("/process", response_model=Dict[str, Any])
async def process_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    options: Optional[ProcessingRequest] = None
):
    """Upload and process an invoice file."""
    try:
        # Save uploaded file
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)

        file_path = os.path.join(temp_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Process the file
        result = processor.process_file(file_path)

        if result is None:
            raise HTTPException(status_code=422, detail="Failed to process invoice")

        # Cleanup
        background_tasks.add_task(os.remove, file_path)

        return {
            "success": True,
            "invoice_id": result.get('id'),
            "vendor_name": result.get('vendor_name'),
            "invoice_number": result.get('invoice_number'),
            "invoice_date": result.get('invoice_date'),
            "total_amount": result.get('total_amount'),
            "currency": result.get('currency'),
            "status": result.get('status'),
            "validation_status": result.get('validation_status'),
            "confidence_score": result.get('confidence_scores', {}).get('average', 0),
            "processing_time_ms": result.get('processing_time_ms'),
            "alerts": []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/invoices", response_model=List[InvoiceResponse])
def list_invoices(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None
):
    """List all processed invoices."""
    invoices = db.get_all_invoices(limit=limit, offset=offset)

    results = []
    for inv in invoices:
        if status and inv.get('status') != status:
            continue

        results.append({
            "id": inv['id'],
            "vendor_name": inv.get('vendor_name'),
            "invoice_number": inv.get('invoice_number'),
            "invoice_date": inv.get('invoice_date'),
            "total_amount": inv.get('total_amount'),
            "status": inv.get('status', 'pending'),
            "confidence_score": inv.get('confidence_scores', {}).get('average', 0) if inv.get('confidence_scores') else 0,
            "validation_status": inv.get('validation_status', 'unknown')
        })

    return results

@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int):
    """Get specific invoice details."""
    invoice = db.get_invoice(invoice_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice

@app.put("/invoices/{invoice_id}/status")
def update_invoice_status(invoice_id: int, status: str):
    """Update invoice status (approve/reject)."""
    valid_statuses = ['pending', 'validated', 'approved', 'rejected']

    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    db.update_status(invoice_id, status)

    return {"message": f"Invoice {invoice_id} status updated to {status}"}

@app.get("/stats")
def get_statistics():
    """Get processing statistics."""
    stats = db.get_statistics()

    return {
        "total_invoices": stats.get('total_invoices', 0),
        "total_amount_processed": stats.get('total_amount', 0),
        "average_confidence": stats.get('avg_confidence', 0),
        "status_breakdown": stats.get('status_breakdown', {}),
        "recent_count_7d": stats.get('recent_count', 0)
    }

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "connected",
            "ocr_engine": processor.config.ocr_engine if hasattr(processor, 'config') else "unknown"
        }
    }

@app.post("/batch/process")
def batch_process(directory: str):
    """Process all invoices in a directory."""
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail="Directory not found")

    results = processor.batch_process(directory)

    return {
        "processed_count": len(results),
        "successful": len([r for r in results if r is not None]),
        "failed": len([r for r in results if r is None])
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
