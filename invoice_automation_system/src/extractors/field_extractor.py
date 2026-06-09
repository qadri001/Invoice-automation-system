"""Field extraction from OCR text using regex and NLP."""
import re
import dateparser
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractedField:
    """Represents an extracted field with metadata."""
    name: str
    value: Any
    raw_text: str
    confidence: float
    method: str  # 'regex', 'nlp', 'llm', 'heuristic'


class InvoiceFieldExtractor:
    """Extracts structured fields from invoice OCR text."""

    # Comprehensive regex patterns for invoice fields
    PATTERNS = {
        'invoice_number': [
            r'(?i)(?:invoice|inv|bill|document)[\s#:]*(?:number|no|num|#)?[:\s]*([A-Z0-9][A-Z0-9\-]{3,20})',
            r'(?i)(?:invoice|inv)[\s#:]*([A-Z0-9]{5,25})',
            r'(?i)#\s*([A-Z0-9]{5,20})',
            r'(?i)no[.\s:]+([A-Z0-9\-]{5,25})',
        ],
        'date': [
            r'(?i)(?:invoice\s*)?date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?i)(?:invoice\s*)?date[:\s]*(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
            r'(?i)(?:issued|created|document\s*date)[:\s]*(\d{1,2}\s+[A-Za-z]{3,}\s+\d{4})',
            r'(?i)date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ],
        'due_date': [
            r'(?i)(?:due\s*date|payment\s*due|pay\s*by)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?i)(?:due\s*date|payment\s*due)[:\s]*(\d{1,2}\s+[A-Za-z]{3,}\s+\d{4})',
        ],
        'total_amount': [
            r'(?i)(?:total|amount\s*due|grand\s*total|balance\s*due)[:\s]*[$€£¥]?\s*([0-9,]+\.?[0-9]{0,2})',
            r'(?i)(?:total\s*amount|amount)[:\s]*[$€£¥]?\s*([0-9,]+\.?[0-9]{0,2})',
            r'(?i)total[:\s]*[$€£¥]?\s*([0-9,]+\.?[0-9]{0,2})',
        ],
        'subtotal': [
            r'(?i)(?:subtotal|sub\s*total|net\s*amount)[:\s]*[$€£¥]?\s*([0-9,]+\.?[0-9]{0,2})',
        ],
        'tax_amount': [
            r'(?i)(?:tax|vat|gst|sales\s*tax)[:\s]*[$€£¥]?\s*([0-9,]+\.?[0-9]{0,2})',
            r'(?i)tax\s*(?:amount|total)?[:\s]*[$€£¥]?\s*([0-9,]+\.?[0-9]{0,2})',
        ],
        'currency': [
            r'[$]',
            r'[€]',
            r'[£]',
            r'(?i)(USD|EUR|GBP|JPY|CAD|AUD)',
        ],
    }

    def __init__(self):
        self.confidence_threshold = 0.6

    def extract_all_fields(self, ocr_results: List[Dict[str, Any]]) -> Dict[str, ExtractedField]:
        """Extract all invoice fields from OCR results."""
        # Combine all text
        full_text = ' '.join([r['text'] for r in ocr_results])
        lines = [r['text'] for r in ocr_results]

        extracted = {}

        # Extract each field type
        for field_name in self.PATTERNS.keys():
            field = self._extract_field(field_name, full_text, lines, ocr_results)
            if field:
                extracted[field_name] = field

        # Post-processing and validation
        extracted = self._post_process(extracted, full_text)

        return extracted

    def _extract_field(self, field_name: str, full_text: str, 
                       lines: List[str], ocr_results: List[Dict]) -> Optional[ExtractedField]:
        """Extract a specific field using regex patterns."""
        patterns = self.PATTERNS.get(field_name, [])

        best_match = None
        best_confidence = 0

        for pattern in patterns:
            matches = re.finditer(pattern, full_text)
            for match in matches:
                value = match.group(1) if match.groups() else match.group(0)
                confidence = self._calculate_confidence(field_name, value, match, ocr_results)

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = (value, match.group(0), confidence)

        if best_match:
            value, raw_text, confidence = best_match
            parsed_value = self._parse_value(field_name, value)

            return ExtractedField(
                name=field_name,
                value=parsed_value,
                raw_text=raw_text,
                confidence=confidence,
                method='regex'
            )

        return None

    def _calculate_confidence(self, field_name: str, value: str, 
                             match: re.Match, ocr_results: List[Dict]) -> float:
        """Calculate confidence score for extraction."""
        confidence = 0.7  # Base confidence for regex match

        # Adjust based on field-specific heuristics
        if field_name == 'invoice_number':
            # Prefer alphanumeric with reasonable length
            if len(value) >= 5 and any(c.isdigit() for c in value):
                confidence += 0.2
            if re.match(r'^[A-Z0-9\-]+$', value):
                confidence += 0.1

        elif field_name in ['total_amount', 'subtotal', 'tax_amount']:
            # Prefer values that look like currency
            if re.match(r'^[\d,]+\.?\d{0,2}$', value):
                confidence += 0.2
            # Prefer larger values for total
            try:
                num_val = float(value.replace(',', ''))
                if num_val > 0:
                    confidence += 0.1
            except:
                pass

        elif field_name in ['date', 'due_date']:
            # Validate date can be parsed
            parsed = dateparser.parse(value)
            if parsed:
                confidence += 0.2

        return min(confidence, 1.0)

    def _parse_value(self, field_name: str, value: str) -> Any:
        """Parse extracted value into appropriate type."""
        if field_name in ['total_amount', 'subtotal', 'tax_amount']:
            # Clean and convert to float
            cleaned = value.replace(',', '').replace('$', '').replace('€', '').replace('£', '')
            try:
                return float(cleaned)
            except:
                return value

        elif field_name in ['date', 'due_date']:
            parsed = dateparser.parse(value)
            if parsed:
                return parsed.strftime('%Y-%m-%d')
            return value

        elif field_name == 'currency':
            currency_map = {'$': 'USD', '€': 'EUR', '£': 'GBP'}
            return currency_map.get(value, value.upper() if value else 'USD')

        return value.strip()

    def _post_process(self, extracted: Dict[str, ExtractedField], full_text: str) -> Dict[str, ExtractedField]:
        """Post-process extracted fields."""
        # Try to extract vendor name if not found
        if 'vendor_name' not in extracted:
            vendor = self._extract_vendor_heuristic(full_text)
            if vendor:
                extracted['vendor_name'] = ExtractedField(
                    name='vendor_name',
                    value=vendor,
                    raw_text=vendor,
                    confidence=0.6,
                    method='heuristic'
                )

        # Calculate overall confidence
        if extracted:
            avg_confidence = sum(f.confidence for f in extracted.values()) / len(extracted)
            logger.info(f"Average extraction confidence: {avg_confidence:.2f}")

        return extracted

    def _extract_vendor_heuristic(self, text: str) -> Optional[str]:
        """Extract vendor name using heuristics."""
        lines = text.split('\n')

        # Common patterns for vendor names
        # Usually in first few lines, often all caps or title case
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if len(line) > 2 and len(line) < 50:
                # Skip common non-vendor lines
                skip_patterns = ['invoice', 'bill to', 'ship to', 'date', 'page', 'tel', 'fax', 'email']
                if not any(pattern in line.lower() for pattern in skip_patterns):
                    # Prefer lines that look like company names
                    if re.match(r'^[A-Z][A-Za-z0-9\s&.,]+(Inc|LLC|Ltd|Corp|Company|Co\.|GmbH)?\.?$', line):
                        return line
                    if line.isupper() and len(line) > 3:
                        return line

        # Fallback: return first substantial line
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 3 and len(line) < 40:
                return line

        return None

    def extract_line_items(self, ocr_results: List[Dict[str, Any]]) -> List[Dict]:
        """Extract line items from invoice tables."""
        # This is a simplified implementation
        # Real implementation would use table structure detection
        line_items = []

        # Pattern for line items: description, qty, unit_price, total
        text = ' '.join([r['text'] for r in ocr_results])

        # Look for patterns like: "Item description 2 $50.00 $100.00"
        pattern = r'([A-Za-z].{10,60})\s+(\d+)\s+[$]?([0-9,.]+)\s+[$]?([0-9,.]+)'
        matches = re.finditer(pattern, text)

        for match in matches:
            line_items.append({
                'description': match.group(1).strip(),
                'quantity': int(match.group(2)),
                'unit_price': float(match.group(3).replace(',', '')),
                'total': float(match.group(4).replace(',', ''))
            })

        return line_items
