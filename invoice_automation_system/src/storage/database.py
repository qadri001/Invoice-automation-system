"""Database storage for processed invoices."""
import sqlite3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class InvoiceDatabase:
    """SQLite database for invoice storage."""

    def __init__(self, db_path: str = "data/database/invoices.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main invoices table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT NOT NULL,
                    file_path TEXT,
                    vendor_name TEXT,
                    invoice_number TEXT,
                    invoice_date TEXT,
                    due_date TEXT,
                    total_amount REAL,
                    subtotal REAL,
                    tax_amount REAL,
                    currency TEXT DEFAULT 'USD',
                    line_items TEXT,  -- JSON array
                    confidence_scores TEXT,  -- JSON object
                    validation_status TEXT,
                    validation_errors TEXT,  -- JSON array
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ocr_engine TEXT,
                    processing_time_ms INTEGER,
                    status TEXT DEFAULT 'pending'  -- pending, validated, approved, rejected
                )
            """)

            # Duplicate detection index
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_invoice_number 
                ON invoices(invoice_number, vendor_name)
            """)

            # Audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER,
                    action TEXT,
                    details TEXT,
                    performed_by TEXT,
                    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
                )
            """)

            conn.commit()
            logger.info("Database initialized successfully")

    def save_invoice(self, invoice_data: Dict[str, Any]) -> int:
        """Save invoice to database. Returns invoice ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Convert complex fields to JSON
            line_items = json.dumps(invoice_data.get('line_items', []))
            confidence_scores = json.dumps(invoice_data.get('confidence_scores', {}))
            validation_errors = json.dumps(invoice_data.get('validation_errors', []))

            cursor.execute("""
                INSERT INTO invoices (
                    file_name, file_path, vendor_name, invoice_number,
                    invoice_date, due_date, total_amount, subtotal, tax_amount,
                    currency, line_items, confidence_scores, validation_status,
                    validation_errors, ocr_engine, processing_time_ms, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_data.get('file_name'),
                invoice_data.get('file_path'),
                invoice_data.get('vendor_name'),
                invoice_data.get('invoice_number'),
                invoice_data.get('invoice_date'),
                invoice_data.get('due_date'),
                invoice_data.get('total_amount'),
                invoice_data.get('subtotal'),
                invoice_data.get('tax_amount'),
                invoice_data.get('currency', 'USD'),
                line_items,
                confidence_scores,
                invoice_data.get('validation_status'),
                validation_errors,
                invoice_data.get('ocr_engine'),
                invoice_data.get('processing_time_ms'),
                invoice_data.get('status', 'pending')
            ))

            invoice_id = cursor.lastrowid
            conn.commit()

            # Log action
            self._log_action(conn, invoice_id, 'created', 'Invoice processed and saved')

            logger.info(f"Invoice saved with ID: {invoice_id}")
            return invoice_id

    def get_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve invoice by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

    def get_all_invoices(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all invoices with pagination."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM invoices 
                ORDER BY processed_at DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))

            return [dict(row) for row in cursor.fetchall()]

    def find_duplicates(self, invoice_number: str, vendor_name: str, 
                       days: int = 365) -> List[Dict[str, Any]]:
        """Find potential duplicate invoices."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM invoices 
                WHERE LOWER(invoice_number) = LOWER(?) 
                AND LOWER(vendor_name) = LOWER(?)
                AND processed_at >= datetime('now', '-{} days')
            """.format(days), (invoice_number, vendor_name))

            return [dict(row) for row in cursor.fetchall()]

    def update_status(self, invoice_id: int, status: str, 
                     performed_by: str = 'system'):
        """Update invoice status."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE invoices SET status = ? WHERE id = ?
            """, (status, invoice_id))

            conn.commit()
            self._log_action(conn, invoice_id, f'status_updated_to_{status}', 
                           f'Status changed to {status}', performed_by)

            logger.info(f"Invoice {invoice_id} status updated to {status}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stats = {}

            # Total count
            cursor.execute("SELECT COUNT(*) FROM invoices")
            stats['total_invoices'] = cursor.fetchone()[0]

            # Status breakdown
            cursor.execute("""
                SELECT status, COUNT(*) FROM invoices GROUP BY status
            """)
            stats['status_breakdown'] = dict(cursor.fetchall())

            # Average confidence
            cursor.execute("""
                SELECT AVG(
                    json_extract(confidence_scores, '$.average')
                ) FROM invoices
            """)
            result = cursor.fetchone()
            stats['avg_confidence'] = result[0] if result[0] else 0

            # Total amount processed
            cursor.execute("SELECT SUM(total_amount) FROM invoices")
            result = cursor.fetchone()
            stats['total_amount'] = result[0] if result[0] else 0

            # Recent activity (last 7 days)
            cursor.execute("""
                SELECT COUNT(*) FROM invoices 
                WHERE processed_at >= datetime('now', '-7 days')
            """)
            stats['recent_count'] = cursor.fetchone()[0]

            return stats

    def export_to_csv(self, output_path: str):
        """Export all invoices to CSV."""
        import pandas as pd

        invoices = self.get_all_invoices(limit=10000)
        df = pd.DataFrame(invoices)
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(invoices)} invoices to {output_path}")

    def _log_action(self, conn: sqlite3.Connection, invoice_id: int, 
                   action: str, details: str, performed_by: str = 'system'):
        """Log action to audit log."""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (invoice_id, action, details, performed_by)
            VALUES (?, ?, ?, ?)
        """, (invoice_id, action, details, performed_by))
        conn.commit()


class CSVStorage:
    """Alternative CSV storage for simple use cases."""

    def __init__(self, csv_path: str = "data/processed/invoices.csv"):
        self.csv_path = csv_path
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)

    def save_invoice(self, invoice_data: Dict[str, Any]):
        """Append invoice to CSV."""
        import pandas as pd

        # Flatten nested structures
        flat_data = {
            'file_name': invoice_data.get('file_name'),
            'vendor_name': invoice_data.get('vendor_name'),
            'invoice_number': invoice_data.get('invoice_number'),
            'invoice_date': invoice_data.get('invoice_date'),
            'due_date': invoice_data.get('due_date'),
            'total_amount': invoice_data.get('total_amount'),
            'subtotal': invoice_data.get('subtotal'),
            'tax_amount': invoice_data.get('tax_amount'),
            'currency': invoice_data.get('currency', 'USD'),
            'validation_status': invoice_data.get('validation_status'),
            'processed_at': datetime.now().isoformat(),
            'status': invoice_data.get('status', 'pending')
        }

        df = pd.DataFrame([flat_data])

        # Append to existing or create new
        if Path(self.csv_path).exists():
            df.to_csv(self.csv_path, mode='a', header=False, index=False)
        else:
            df.to_csv(self.csv_path, index=False)

        logger.info(f"Invoice appended to CSV: {self.csv_path}")
