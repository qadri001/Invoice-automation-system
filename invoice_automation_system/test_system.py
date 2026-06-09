#!/usr/bin/env python3
"""Test script for the invoice automation system."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main_processor import InvoiceProcessor
from extractors.field_extractor import InvoiceFieldExtractor, ExtractedField
from validators.invoice_validator import InvoiceValidator, ValidationSeverity

def test_field_extraction():
    """Test field extraction with sample OCR data."""
    print("\n🧪 Testing Field Extraction...")

    extractor = InvoiceFieldExtractor()

    # Simulate OCR results
    sample_ocr = [
        {'text': 'Acme Corporation', 'confidence': 0.95, 'bbox': [100, 100, 200, 30]},
        {'text': 'Invoice # INV-2024-001', 'confidence': 0.88, 'bbox': [100, 200, 150, 25]},
        {'text': 'Date: 2024-01-15', 'confidence': 0.92, 'bbox': [100, 250, 120, 25]},
        {'text': 'Total: $1,234.56', 'confidence': 0.85, 'bbox': [100, 400, 130, 25]},
    ]

    fields = extractor.extract_all_fields(sample_ocr)

    print(f"   Found {len(fields)} fields:")
    for name, field in fields.items():
        print(f"   - {name}: {field.value} (confidence: {field.confidence:.2f})")

    return len(fields) > 0

def test_validation():
    """Test validation logic."""
    print("\n🧪 Testing Validation...")

    validator = InvoiceValidator(max_amount_threshold=1000)

    # Valid invoice
    valid_invoice = {
        'vendor_name': 'Acme Corp',
        'invoice_number': 'INV-001',
        'invoice_date': '2024-01-15',
        'total_amount': 500.00
    }

    results = validator.validate(valid_invoice)
    valid_count = sum(1 for r in results if r.is_valid)
    print(f"   Valid invoice: {valid_count}/{len(results)} checks passed")

    # Invalid invoice (high amount)
    invalid_invoice = {
        'vendor_name': 'Acme Corp',
        'invoice_number': 'INV-002',
        'invoice_date': '2024-01-15',
        'total_amount': 1500.00  # Exceeds threshold
    }

    results = validator.validate(invalid_invoice)
    warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
    print(f"   High amount invoice: {len(warnings)} warning(s) generated")

    return True

def test_database():
    """Test database operations."""
    print("\n🧪 Testing Database...")

    from storage.database import InvoiceDatabase

    db = InvoiceDatabase("test.db")

    # Insert test invoice
    test_data = {
        'file_name': 'test.pdf',
        'vendor_name': 'Test Vendor',
        'invoice_number': 'TEST-001',
        'invoice_date': '2024-01-15',
        'total_amount': 100.00,
        'confidence_scores': {'average': 0.85},
        'validation_status': 'valid',
        'validation_errors': [],
        'ocr_engine': 'test',
        'processing_time_ms': 1000,
        'status': 'pending'
    }

    invoice_id = db.save_invoice(test_data)
    print(f"   Saved invoice with ID: {invoice_id}")

    # Retrieve
    retrieved = db.get_invoice(invoice_id)
    print(f"   Retrieved: {retrieved['vendor_name']} - {retrieved['invoice_number']}")

    # Stats
    stats = db.get_statistics()
    print(f"   Total invoices in DB: {stats['total_invoices']}")

    # Cleanup
    os.remove("test.db")

    return True

def test_alerts():
    """Test alert system."""
    print("\n🧪 Testing Alert System...")

    from alerts.alert_manager import AlertManager, Alert, AlertType

    manager = AlertManager()

    # Create test alert
    alert = Alert(
        alert_type=AlertType.HIGH_AMOUNT,
        severity="warning",
        title="Test Alert",
        message="This is a test alert",
        invoice_number="TEST-001",
        vendor_name="Test Vendor",
        amount=9999.99
    )

    manager.send_alert(alert)
    print(f"   Alert sent: {alert.title}")
    print(f"   Recent alerts: {len(manager.get_recent_alerts())}")

    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("🚀 Invoice Automation System - Test Suite")
    print("=" * 60)

    tests = [
        ("Field Extraction", test_field_extraction),
        ("Validation", test_validation),
        ("Database", test_database),
        ("Alerts", test_alerts),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✅ PASSED" if success else "❌ FAILED"))
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append((name, f"❌ ERROR: {e}"))

    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print("=" * 60)
    for name, result in results:
        print(f"   {name}: {result}")

    passed = sum(1 for _, r in results if "PASSED" in r)
    print(f"\n   Total: {passed}/{len(results)} tests passed")

if __name__ == "__main__":
    main()
