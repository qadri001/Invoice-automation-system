"""Invoice validation logic."""
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation check."""
    field: str
    is_valid: bool
    message: str
    severity: ValidationSeverity
    suggestion: Optional[str] = None


class InvoiceValidator:
    """Validates extracted invoice data."""

    REQUIRED_FIELDS = ['vendor_name', 'invoice_number', 'invoice_date', 'total_amount']

    def __init__(self, max_amount_threshold: float = 10000.0, 
                 duplicate_days: int = 365):
        self.max_amount_threshold = max_amount_threshold
        self.duplicate_days = duplicate_days
        self.validation_history: List[Dict] = []

    def validate(self, extracted_data: Dict[str, Any], 
                 existing_invoices: Optional[List[Dict]] = None) -> List[ValidationResult]:
        """Run all validation checks on extracted invoice data."""
        results = []

        # Check required fields
        results.extend(self._validate_required_fields(extracted_data))

        # Validate specific fields
        if 'invoice_date' in extracted_data:
            results.append(self._validate_date(extracted_data['invoice_date']))

        if 'due_date' in extracted_data:
            results.append(self._validate_due_date(
                extracted_data.get('invoice_date'), 
                extracted_data['due_date']
            ))

        if 'total_amount' in extracted_data:
            results.append(self._validate_amount(extracted_data['total_amount']))

        if 'invoice_number' in extracted_data:
            results.append(self._validate_invoice_number(extracted_data['invoice_number']))

        # Check for duplicates
        if existing_invoices:
            results.extend(self._check_duplicates(extracted_data, existing_invoices))

        # Validate calculations
        results.extend(self._validate_calculations(extracted_data))

        return results

    def _validate_required_fields(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Check that all required fields are present."""
        results = []
        for field in self.REQUIRED_FIELDS:
            if field not in data or not data[field]:
                results.append(ValidationResult(
                    field=field,
                    is_valid=False,
                    message=f"Missing required field: {field}",
                    severity=ValidationSeverity.ERROR,
                    suggestion=f"Please review the invoice and manually extract {field}"
                ))
            else:
                results.append(ValidationResult(
                    field=field,
                    is_valid=True,
                    message=f"Field {field} is present",
                    severity=ValidationSeverity.INFO
                ))
        return results

    def _validate_date(self, date_value: Any) -> ValidationResult:
        """Validate invoice date."""
        try:
            if isinstance(date_value, str):
                date_obj = datetime.strptime(date_value, '%Y-%m-%d')
            else:
                date_obj = date_value

            # Check if date is in the future
            if date_obj > datetime.now():
                return ValidationResult(
                    field='invoice_date',
                    is_valid=False,
                    message=f"Invoice date {date_value} is in the future",
                    severity=ValidationSeverity.WARNING,
                    suggestion="Verify the date format or check for data entry errors"
                )

            # Check if date is too old (more than 1 year)
            if date_obj < datetime.now() - timedelta(days=365):
                return ValidationResult(
                    field='invoice_date',
                    is_valid=True,
                    message=f"Invoice date {date_value} is more than 1 year old",
                    severity=ValidationSeverity.WARNING
                )

            return ValidationResult(
                field='invoice_date',
                is_valid=True,
                message=f"Valid invoice date: {date_value}",
                severity=ValidationSeverity.INFO
            )

        except Exception as e:
            return ValidationResult(
                field='invoice_date',
                is_valid=False,
                message=f"Invalid date format: {date_value}",
                severity=ValidationSeverity.ERROR,
                suggestion="Date should be in YYYY-MM-DD format"
            )

    def _validate_due_date(self, invoice_date: Any, due_date: Any) -> ValidationResult:
        """Validate due date is after invoice date."""
        try:
            if isinstance(invoice_date, str):
                inv_date = datetime.strptime(invoice_date, '%Y-%m-%d')
            else:
                inv_date = invoice_date

            if isinstance(due_date, str):
                due = datetime.strptime(due_date, '%Y-%m-%d')
            else:
                due = due_date

            if due < inv_date:
                return ValidationResult(
                    field='due_date',
                    is_valid=False,
                    message="Due date is before invoice date",
                    severity=ValidationSeverity.ERROR
                )

            return ValidationResult(
                field='due_date',
                is_valid=True,
                message=f"Valid due date: {due_date}",
                severity=ValidationSeverity.INFO
            )

        except Exception as e:
            return ValidationResult(
                field='due_date',
                is_valid=False,
                message=f"Invalid due date: {due_date}",
                severity=ValidationSeverity.ERROR
            )

    def _validate_amount(self, amount: Any) -> ValidationResult:
        """Validate total amount."""
        try:
            if isinstance(amount, str):
                amount = float(amount.replace(',', ''))

            if amount <= 0:
                return ValidationResult(
                    field='total_amount',
                    is_valid=False,
                    message=f"Amount must be positive: {amount}",
                    severity=ValidationSeverity.ERROR
                )

            if amount > self.max_amount_threshold:
                return ValidationResult(
                    field='total_amount',
                    is_valid=True,
                    message=f"Amount {amount} exceeds threshold {self.max_amount_threshold}",
                    severity=ValidationSeverity.WARNING,
                    suggestion="Flag for management approval"
                )

            return ValidationResult(
                field='total_amount',
                is_valid=True,
                message=f"Valid amount: {amount}",
                severity=ValidationSeverity.INFO
            )

        except Exception as e:
            return ValidationResult(
                field='total_amount',
                is_valid=False,
                message=f"Invalid amount format: {amount}",
                severity=ValidationSeverity.ERROR
            )

    def _validate_invoice_number(self, invoice_num: str) -> ValidationResult:
        """Validate invoice number format."""
        if not invoice_num or len(invoice_num) < 3:
            return ValidationResult(
                field='invoice_number',
                is_valid=False,
                message="Invoice number too short",
                severity=ValidationSeverity.WARNING
            )

        # Check for suspicious patterns
        if re.match(r'^[0]+$', invoice_num.replace('-', '')):
            return ValidationResult(
                field='invoice_number',
                is_valid=False,
                message="Suspicious invoice number (all zeros)",
                severity=ValidationSeverity.WARNING
            )

        return ValidationResult(
            field='invoice_number',
            is_valid=True,
            message=f"Valid invoice number: {invoice_num}",
            severity=ValidationSeverity.INFO
        )

    def _check_duplicates(self, data: Dict[str, Any], 
                         existing: List[Dict]) -> List[ValidationResult]:
        """Check for duplicate invoices."""
        results = []

        invoice_num = data.get('invoice_number', '').lower()
        vendor = data.get('vendor_name', '').lower()
        amount = data.get('total_amount')

        for existing_inv in existing:
            # Check invoice number match
            if (existing_inv.get('invoice_number', '').lower() == invoice_num and 
                existing_inv.get('vendor_name', '').lower() == vendor):
                results.append(ValidationResult(
                    field='invoice_number',
                    is_valid=False,
                    message=f"Duplicate invoice detected: {invoice_num} from {vendor}",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Verify if this is a correction or duplicate submission"
                ))
                return results

            # Check for same vendor, amount, and date (within 7 days)
            if (existing_inv.get('vendor_name', '').lower() == vendor and
                abs(existing_inv.get('total_amount', 0) - amount) < 0.01):
                existing_date = existing_inv.get('invoice_date', '')
                current_date = data.get('invoice_date', '')
                if existing_date and current_date:
                    try:
                        d1 = datetime.strptime(existing_date, '%Y-%m-%d')
                        d2 = datetime.strptime(current_date, '%Y-%m-%d')
                        if abs((d2 - d1).days) <= 7:
                            results.append(ValidationResult(
                                field='duplicate_check',
                                is_valid=False,
                                message=f"Potential duplicate: Same vendor/amount within 7 days",
                                severity=ValidationSeverity.WARNING
                            ))
                    except:
                        pass

        if not results:
            results.append(ValidationResult(
                field='duplicate_check',
                is_valid=True,
                message="No duplicates found",
                severity=ValidationSeverity.INFO
            ))

        return results

    def _validate_calculations(self, data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate mathematical calculations."""
        results = []

        subtotal = data.get('subtotal')
        tax = data.get('tax_amount')
        total = data.get('total_amount')

        if subtotal is not None and tax is not None and total is not None:
            try:
                calculated_total = float(subtotal) + float(tax)
                if abs(calculated_total - float(total)) > 0.01:
                    results.append(ValidationResult(
                        field='calculations',
                        is_valid=False,
                        message=f"Math error: {subtotal} + {tax} ≠ {total}",
                        severity=ValidationSeverity.WARNING,
                        suggestion="Verify line items and calculations"
                    ))
                else:
                    results.append(ValidationResult(
                        field='calculations',
                        is_valid=True,
                        message="Calculations verified",
                        severity=ValidationSeverity.INFO
                    ))
            except:
                pass

        return results

    def is_valid_for_processing(self, results: List[ValidationResult]) -> bool:
        """Check if validation results allow processing."""
        for result in results:
            if result.severity == ValidationSeverity.ERROR:
                return False
        return True
