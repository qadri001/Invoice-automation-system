# 📚 Advanced Usage Guide

## System Architecture

The Invoice Automation System follows a modular pipeline architecture:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Input Files   │────▶│  OCR Extraction │────▶│ Field Extraction│
│ (PDF/Images)    │     │ (Paddle/Tesseract)│    │ (Regex + NLP)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Alert System  │◀────│   Validation    │◀────│  Data Structuring│
│ (Email/Slack)   │     │ (Rules Engine)  │     │  (JSON/SQLite)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Dashboard     │
                       │ (Streamlit)     │
                       └─────────────────┘
```

## 🔧 Advanced Configuration

### Custom Field Extraction Patterns

Edit `src/extractors/field_extractor.py` to add custom patterns:

```python
# Add custom patterns for specific vendors
CUSTOM_PATTERNS = {
    'amazon': {
        'invoice_number': r'Order\s*#:\s*(\d{3}-\d{7}-\d{7})',
        'total_amount': r'Grand\s*Total:\s*\$?([0-9,]+\.\d{2})'
    }
}
```

### Confidence Score Tuning

Adjust confidence thresholds in `config/config.yaml`:

```yaml
extraction:
  confidence_weights:
    vendor_name: 0.8      # Higher weight for critical fields
    invoice_number: 0.9
    total_amount: 0.7
    date: 0.6
```

## 🚀 API Integration Examples

### Python Client

```python
import requests

# Upload and process invoice
with open('invoice.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/process',
        files={'file': f}
    )

result = response.json()
print(f"Extracted: {result['vendor_name']} - ${result['total_amount']}")
```

### cURL

```bash
# Process single file
curl -X POST "http://localhost:8000/process" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@invoice.pdf"

# Get statistics
curl "http://localhost:8000/stats"

# List recent invoices
curl "http://localhost:8000/invoices?limit=10"
```

### JavaScript/TypeScript

```typescript
async function processInvoice(file: File): Promise<InvoiceResult> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8000/process', {
    method: 'POST',
    body: formData
  });

  return await response.json();
}
```

## 🐳 Docker Deployment

### Production Deployment

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale processor workers
docker-compose up -d --scale invoice-processor=3

# Update configuration
docker-compose restart
```

### Environment Variables

Create `.env` file for production:

```env
# OCR Settings
OCR_ENGINE=paddleocr
CONFIDENCE_THRESHOLD=0.7

# Database
DATABASE_PATH=/data/invoices.db

# Security
API_KEY=your-secret-key
JWT_SECRET=your-jwt-secret

# External Services
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
EMAIL_API_KEY=SG.xxx
SLACK_WEBHOOK=https://hooks.slack.com/xxx
```

## 📊 Performance Optimization

### Batch Processing

For large volumes, use batch processing:

```python
from main_processor import InvoiceProcessor

processor = InvoiceProcessor()

# Process 1000 invoices
results = processor.batch_process(
    directory='data/invoices',
    batch_size=50,
    parallel=True,
    max_workers=4
)
```

### Database Indexing

For high-volume processing, add database indexes:

```sql
-- Add composite index for duplicate detection
CREATE INDEX idx_vendor_invoice_date 
ON invoices(vendor_name, invoice_number, invoice_date);

-- Add index for date range queries
CREATE INDEX idx_invoice_date 
ON invoices(invoice_date);
```

### Caching

Enable Redis caching for OCR results:

```python
# config/config.yaml
cache:
  enabled: true
  backend: redis
  host: localhost
  port: 6379
  ttl: 3600  # 1 hour
```

## 🔒 Security Best Practices

### 1. File Validation

```python
# Add to file_watcher.py
def validate_file(self, file_path: str) -> bool:
    # Check file size
    if os.path.getsize(file_path) > 50 * 1024 * 1024:  # 50MB
        return False

    # Check magic bytes
    with open(file_path, 'rb') as f:
        header = f.read(4)
        # PDF: %PDF, PNG: PNG, JPEG: ÿØÿ
        valid_headers = [b'%PDF', b'\x89PNG', b'\xff\xd8\xff']
        return any(header.startswith(h) for h in valid_headers)
```

### 2. Input Sanitization

```python
# Sanitize extracted text
def sanitize_text(text: str) -> str:
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32)
    # Limit length
    return text[:1000]
```

### 3. Audit Logging

```python
# Log all processing attempts
import hashlib

def log_processing(file_path: str, result: dict):
    file_hash = hashlib.sha256(open(file_path, 'rb').read()).hexdigest()[:16]
    logger.info(f"Processed: {file_path} [hash: {file_hash}] Result: {result['status']}")
```

## 🧪 Testing Strategy

### Unit Tests

```python
# tests/test_extraction.py
import pytest
from extractors.field_extractor import InvoiceFieldExtractor

def test_invoice_number_extraction():
    extractor = InvoiceFieldExtractor()

    test_cases = [
        ("Invoice # INV-2024-001", "INV-2024-001"),
        ("Inv No: ABC123", "ABC123"),
        ("Bill Number: 12345", "12345"),
    ]

    for text, expected in test_cases:
        ocr_results = [{'text': text, 'confidence': 0.9}]
        fields = extractor.extract_all_fields(ocr_results)
        assert fields['invoice_number'].value == expected
```

### Integration Tests

```python
# tests/test_pipeline.py
def test_full_pipeline():
    processor = InvoiceProcessor()

    result = processor.process_file("tests/sample_invoice.pdf")

    assert result is not None
    assert result['vendor_name'] is not None
    assert result['total_amount'] > 0
    assert result['confidence_scores']['average'] > 0.5
```

### Load Testing

```bash
# Using locust
pip install locust

# locustfile.py
from locust import HttpUser, task

class InvoiceUser(HttpUser):
    @task
    def upload_invoice(self):
        with open('test.pdf', 'rb') as f:
            self.client.post('/process', files={'file': f})

# Run: locust -f locustfile.py --host=http://localhost:8000
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Low OCR Accuracy

**Symptoms**: Poor text extraction, missing fields

**Solutions**:
- Increase image resolution (300+ DPI)
- Enable image preprocessing in config
- Try hybrid OCR mode
- Manually review low-confidence extractions

```yaml
ocr:
  preprocessing:
    denoise: true
    deskew: true
    contrast_enhance: true
    resize_dpi: 300
```

#### 2. Duplicate Detection False Positives

**Symptoms**: Valid invoices flagged as duplicates

**Solutions**:
- Adjust duplicate check window
- Use fuzzy matching for vendor names
- Include amount in duplicate check

```python
# validators/invoice_validator.py
def _check_duplicates(self, data, existing):
    # Use fuzzy matching
    from fuzzywuzzy import fuzz

    for inv in existing:
        vendor_match = fuzz.ratio(
            data['vendor_name'].lower(),
            inv['vendor_name'].lower()
        ) > 80

        if vendor_match and data['invoice_number'] == inv['invoice_number']:
            return True
```

#### 3. Database Locking

**Symptoms**: "database is locked" errors

**Solutions**:
- Use write-ahead logging (WAL)
- Implement connection pooling
- Add retry logic

```python
# storage/database.py
def save_invoice(self, data):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                # ... save logic
                return invoice_id
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))
                continue
            raise
```

### Debug Mode

Enable detailed logging:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or in config
system:
  debug: true
  log_level: "DEBUG"
```

## 📈 Monitoring & Analytics

### Prometheus Metrics

Add metrics export:

```python
from prometheus_client import Counter, Histogram, Gauge

invoices_processed = Counter('invoices_total', 'Total invoices processed')
processing_time = Histogram('processing_seconds', 'Time spent processing')
confidence_score = Gauge('ocr_confidence', 'OCR confidence score')

@processing_time.time()
def process_file(self, file_path):
    result = self._process(file_path)
    invoices_processed.inc()
    confidence_score.set(result['confidence'])
    return result
```

### Grafana Dashboard

Import dashboard JSON for visualization of:
- Processing volume
- Error rates
- Confidence distribution
- Processing time trends

## 🔄 CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: pytest --cov=src tests/

      - name: Build Docker
        run: docker build -t invoice-automation .
```

---

**Need help?** Check the logs in `logs/invoice_processor.log` or open an issue on GitHub.
