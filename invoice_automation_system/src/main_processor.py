"""Main invoice processing orchestrator."""
import os
import time
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from config_loader import ConfigLoader
from extractors.ocr_engine import create_ocr_engine
from extractors.field_extractor import InvoiceFieldExtractor
from extractors.pdf_processor import PDFProcessor
from validators.invoice_validator import InvoiceValidator, ValidationResult
from storage.database import InvoiceDatabase
from alerts.alert_manager import AlertManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/invoice_processor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class InvoiceProcessor:
    """Main invoice processing pipeline."""

    def __init__(self, config_path: Optional[str] = None):
        self.config = ConfigLoader(config_path)
        self.ocr_engine = None
        self.field_extractor = InvoiceFieldExtractor()
        self.pdf_processor = PDFProcessor()
        self.validator = None
        self.database = None
        self.alert_manager = None
        self._initialized = False

    def initialize(self):
        """Initialize all components."""
        if self._initialized:
            return

        logger.info("Initializing Invoice Processor...")

        # Initialize OCR engine
        ocr_type = self.config.ocr_engine
        logger.info(f"Using OCR engine: {ocr_type}")
        self.ocr_engine = create_ocr_engine(ocr_type)

        # Initialize validator
        self.validator = InvoiceValidator(
            max_amount_threshold=self.config.get('validation.thresholds.max_amount_alert', 10000),
            duplicate_days=self.config.get('validation.thresholds.duplicate_check_days', 365)
        )

        # Initialize database
        db_path = self.config.database_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.database = InvoiceDatabase(db_path)

        # Initialize alert manager
        alert_config = {
            'thresholds': {
                'max_amount': self.config.get('validation.thresholds.max_amount_alert', 10000)
            },
            'email': {'enabled': False},  # Configure via config
            'slack': {'enabled': False}
        }
        self.alert_manager = AlertManager(alert_config)

        # Ensure directories exist
        os.makedirs(self.config.input_dir, exist_ok=True)
        os.makedirs(self.config.processed_dir, exist_ok=True)
        os.makedirs('logs', exist_ok=True)

        self._initialized = True
        logger.info("Initialization complete")

    def process_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Process a single invoice file."""
        self.initialize()

        start_time = time.time()
        file_name = Path(file_path).name

        logger.info(f"Processing file: {file_name}")

        try:
            # Step 1: Handle PDF conversion if needed
            image_paths = self._prepare_images(file_path)

            # Step 2: OCR extraction
            all_ocr_results = []
            for img_path in image_paths:
                ocr_results = self.ocr_engine.extract_text(img_path)
                all_ocr_results.extend(ocr_results)

            # Step 3: Field extraction
            extracted_fields = self.field_extractor.extract_all_fields(all_ocr_results)

            # Step 4: Prepare invoice data
            invoice_data = self._prepare_invoice_data(
                file_path, file_name, extracted_fields, all_ocr_results
            )

            # Step 5: Check for duplicates
            existing = self._check_duplicates(invoice_data)

            # Step 6: Validate
            validation_results = self.validator.validate(invoice_data, existing)
            invoice_data['validation_status'] = 'valid' if self.validator.is_valid_for_processing(validation_results) else 'invalid'
            invoice_data['validation_errors'] = [
                {'field': r.field, 'message': r.message, 'severity': r.severity.value}
                for r in validation_results if r.severity.value in ['error', 'warning']
            ]

            # Step 7: Save to database
            invoice_id = self.database.save_invoice(invoice_data)
            invoice_data['id'] = invoice_id

            # Step 8: Send alerts if needed
            self.alert_manager.check_and_alert(validation_results, invoice_data, existing)

            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)
            invoice_data['processing_time_ms'] = processing_time

            # Update with processing time
            self.database.update_status(invoice_id, 'validated' if invoice_data['validation_status'] == 'valid' else 'pending_review')

            logger.info(f"Successfully processed {file_name} in {processing_time}ms (ID: {invoice_id})")

            # Cleanup temp files
            if self.pdf_processor.is_pdf(file_path):
                self.pdf_processor.cleanup(image_paths)

            return invoice_data

        except Exception as e:
            logger.error(f"Error processing {file_name}: {e}", exc_info=True)
            self.alert_manager.send_alert(
                type('Alert', (), {
                    'alert_type': 'processing_error',
                    'severity': 'critical',
                    'title': 'Processing Error',
                    'message': f"Failed to process {file_name}: {str(e)}",
                    'invoice_number': None,
                    'vendor_name': None,
                    'amount': None,
                    'timestamp': datetime.now(),
                    'metadata': {'error': str(e)}
                })()
            )
            return None

    def _prepare_images(self, file_path: str) -> List[str]:
        """Prepare images from file (handle PDFs)."""
        if self.pdf_processor.is_pdf(file_path):
            return self.pdf_processor.pdf_to_images(file_path)
        else:
            return [file_path]

    def _prepare_invoice_data(self, file_path: str, file_name: str,
                             extracted_fields: Dict, ocr_results: List) -> Dict[str, Any]:
        """Prepare final invoice data structure."""
        # Calculate confidence scores
        confidence_scores = {
            field: data.confidence 
            for field, data in extracted_fields.items()
        }
        avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0
        confidence_scores['average'] = avg_confidence

        # Extract line items
        line_items = self.field_extractor.extract_line_items(ocr_results)

        invoice_data = {
            'file_name': file_name,
            'file_path': file_path,
            'vendor_name': extracted_fields.get('vendor_name', {}).value if 'vendor_name' in extracted_fields else None,
            'invoice_number': extracted_fields.get('invoice_number', {}).value if 'invoice_number' in extracted_fields else None,
            'invoice_date': extracted_fields.get('date', {}).value if 'date' in extracted_fields else None,
            'due_date': extracted_fields.get('due_date', {}).value if 'due_date' in extracted_fields else None,
            'total_amount': extracted_fields.get('total_amount', {}).value if 'total_amount' in extracted_fields else None,
            'subtotal': extracted_fields.get('subtotal', {}).value if 'subtotal' in extracted_fields else None,
            'tax_amount': extracted_fields.get('tax_amount', {}).value if 'tax_amount' in extracted_fields else None,
            'currency': extracted_fields.get('currency', {}).value if 'currency' in extracted_fields else 'USD',
            'line_items': line_items,
            'confidence_scores': confidence_scores,
            'ocr_engine': self.config.ocr_engine,
            'status': 'pending'
        }

        return invoice_data

    def _check_duplicates(self, invoice_data: Dict) -> List[Dict]:
        """Check for duplicate invoices."""
        invoice_num = invoice_data.get('invoice_number')
        vendor = invoice_data.get('vendor_name')

        if invoice_num and vendor:
            return self.database.find_duplicates(invoice_num, vendor)
        return []

    def batch_process(self, directory: str) -> List[Dict[str, Any]]:
        """Process all invoices in a directory."""
        self.initialize()

        results = []
        supported_ext = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}

        for file_path in Path(directory).iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_ext:
                result = self.process_file(str(file_path))
                if result:
                    results.append(result)

        logger.info(f"Batch processing complete: {len(results)} invoices processed")
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        self.initialize()
        return self.database.get_statistics()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Invoice Processing System')
    parser.add_argument('--file', help='Process single file')
    parser.add_argument('--dir', help='Process directory')
    parser.add_argument('--watch', action='store_true', help='Start file watcher')
    parser.add_argument('--dashboard', action='store_true', help='Launch dashboard')

    args = parser.parse_args()

    processor = InvoiceProcessor()

    if args.file:
        result = processor.process_file(args.file)
        if result:
            print(f"\n✅ Processing complete!")
            print(f"   Invoice ID: {result['id']}")
            print(f"   Vendor: {result['vendor_name']}")
            print(f"   Number: {result['invoice_number']}")
            print(f"   Amount: ${result['total_amount']}")
            print(f"   Status: {result['validation_status']}")

    elif args.dir:
        results = processor.batch_process(args.dir)
        print(f"\n✅ Batch processing complete: {len(results)} files processed")

    elif args.watch:
        from watcher.file_watcher import InvoiceWatcher

        config = ConfigLoader()
        watcher = InvoiceWatcher(
            config.input_dir,
            config.processed_dir,
            processor.process_file
        )
        print("👁️ Starting file watcher... (Press Ctrl+C to stop)")
        watcher.run_forever()

    elif args.dashboard:
        import subprocess
        dashboard_path = os.path.join(os.path.dirname(__file__), 'dashboard', 'app.py')
        subprocess.run(['streamlit', 'run', dashboard_path])

    else:
        print("Invoice Automation System")
        print("Usage:")
        print("  python main_processor.py --file <path>     Process single file")
        print("  python main_processor.py --dir <path>      Process directory")
        print("  python main_processor.py --watch           Start file watcher")
        print("  python main_processor.py --dashboard       Launch dashboard")


if __name__ == "__main__":
    main()
