# 🤖 Smart Invoice Automation System

An AI-powered invoice processing system that automatically extracts data from PDF and image invoices, validates the information, detects duplicates, and provides a comprehensive dashboard for monitoring.

## ✨ Features

- **Multi-Format Support**: Process PDF, PNG, JPG, TIFF, and BMP files
- **Advanced OCR**: Uses PaddleOCR (primary) with Tesseract fallback for best accuracy
- **Smart Field Extraction**: Automatically extracts:
  - Vendor name
  - Invoice number
  - Invoice date & due date
  - Total, subtotal, and tax amounts
  - Currency detection
  - Line items (table extraction)
- **Data Validation**: 
  - Required field checks
  - Date validation (future date detection)
  - Amount threshold alerts
  - Duplicate invoice detection
  - Mathematical verification
- **Alert System**: 
  - Console notifications
  - Email alerts (configurable)
  - Slack notifications (configurable)
  - Duplicate detection alerts
  - High amount warnings
- **Storage Options**: SQLite database with CSV export capability
- **File Watcher**: Automatic processing when files are added to input folder
- **Dashboard**: Streamlit-based web interface for monitoring and analytics

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd invoice_automation_system

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install PaddleOCR dependencies (if using PaddleOCR)
pip install paddlepaddle paddleocr
```

### 2. Configuration

Edit `config/config.yaml` to customize:
- OCR engine selection (paddleocr, tesseract, or hybrid)
- Validation thresholds
- Alert settings
- File paths

### 3. Usage

#### Process a Single File
```bash
python run.py --file path/to/invoice.pdf
```

#### Process a Directory
```bash
python run.py --dir data/invoices
```

#### Start File Watcher (Auto-Processing)
```bash
python run.py --watch
```

#### Launch Dashboard
```bash
python run.py --dashboard
# Or directly:
streamlit run src/dashboard/app.py
```

## 📁 Project Structure

```
invoice_automation_system/
├── config/
│   └── config.yaml              # System configuration
├── data/
│   ├── invoices/                # Input folder (drop files here)
│   ├── processed/               # Processed files moved here
│   └── database/
│       └── invoices.db          # SQLite database
├── src/
│   ├── extractors/
│   │   ├── ocr_engine.py        # OCR implementations
│   │   ├── field_extractor.py   # Field extraction logic
│   │   └── pdf_processor.py     # PDF handling
│   ├── validators/
│   │   └── invoice_validator.py # Validation rules
│   ├── storage/
│   │   └── database.py          # Database operations
│   ├── alerts/
│   │   └── alert_manager.py     # Alert system
│   ├── watcher/
│   │   └── file_watcher.py      # File system watcher
│   ├── dashboard/
│   │   └── app.py               # Streamlit dashboard
│   ├── config_loader.py         # Configuration management
│   └── main_processor.py         # Main orchestrator
├── logs/
│   └── invoice_processor.log    # Processing logs
├── requirements.txt             # Python dependencies
├── run.py                       # Entry point
└── README.md                    # This file
```

## 🔧 Configuration Options

### OCR Engine Selection
```yaml
ocr:
  engine: "paddleocr"  # Options: paddleocr, tesseract, hybrid
  confidence_threshold: 0.6
```

### Validation Rules
```yaml
validation:
  thresholds:
    max_amount_alert: 10000.00  # Alert on invoices above this amount
    duplicate_check_days: 365   # Look back period for duplicates
```

### Alert Channels
```yaml
alerts:
  channels:
    - console
    - email
    - slack
  email:
    smtp_server: "smtp.gmail.com"
    username: "your-email@gmail.com"
    password: "your-app-password"
  slack:
    webhook_url: "https://hooks.slack.com/services/..."
```

## 📊 Dashboard Features

The Streamlit dashboard provides:
- **Real-time Metrics**: Total invoices, amounts processed, confidence scores
- **Status Overview**: Visual breakdown of invoice statuses
- **Recent Activity**: Table of recently processed invoices
- **Alert Feed**: Real-time notifications for duplicates and high amounts
- **Upload Interface**: Drag-and-drop file upload
- **Analytics Charts**: 
  - Invoice amounts over time
  - Vendor distribution
  - Processing statistics

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Test with sample invoice
python run.py --file tests/sample_invoice.pdf
```

## 📝 Sample Output

```
✅ Processing complete!
   Invoice ID: 42
   Vendor: Acme Corporation
   Number: INV-2024-001
   Amount: $1,234.56
   Status: valid
   Confidence: 0.92
```

## 🚨 Alert Examples

```
🚨 ALERT [DUPLICATE] CRITICAL
   Title: Duplicate Invoice Detected
   Message: Invoice INV-2024-001 from Acme Corp appears to be a duplicate
   Invoice: INV-2024-001
   Vendor: Acme Corp
   Amount: $1,234.56
```

## 🔒 Security Notes

- Store sensitive configuration (passwords, API keys) in environment variables
- Use app-specific passwords for email
- Restrict file permissions on database and log files
- Regular backup of the database file

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

MIT License - feel free to use in commercial and personal projects.

## 🆘 Support

For issues and questions:
1. Check the logs in `logs/invoice_processor.log`
2. Review configuration in `config/config.yaml`
3. Ensure all dependencies are installed
4. Verify file permissions on data directories

---

**Built with ❤️ using Python, PaddleOCR, and Streamlit**
