# 🎯 Quick Reference Card

## Installation (30 seconds)
```bash
git clone <repo>
cd invoice_automation_system
pip install -r requirements.txt
pip install paddlepaddle paddleocr
python generate_samples.py
```

## Common Commands

| Command | Description |
|---------|-------------|
| `python run.py --file invoice.pdf` | Process single file |
| `python run.py --dir data/invoices` | Process directory |
| `python run.py --watch` | Auto-process new files |
| `python run.py --dashboard` | Launch web UI |
| `python -m uvicorn src.api:app` | Start REST API |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/process` | POST | Upload & process invoice |
| `/invoices` | GET | List all invoices |
| `/invoices/{id}` | GET | Get specific invoice |
| `/stats` | GET | Processing statistics |
| `/health` | GET | Health check |

## File Structure

```
📁 invoice_automation_system/
├── 📁 data/
│   ├── 📁 invoices/     # Drop files here
│   └── 📁 processed/    # Completed files
├── 📁 src/
│   ├── extractors/      # OCR & field extraction
│   ├── validators/      # Validation rules
│   ├── storage/         # Database
│   ├── alerts/          # Notifications
│   ├── watcher/         # File monitoring
│   └── dashboard/       # Web UI
├── 📄 config.yaml       # Settings
└── 📄 run.py           # Entry point
```

## Configuration Keys

```yaml
ocr:
  engine: paddleocr        # paddleocr | tesseract | hybrid
  confidence_threshold: 0.6

validation:
  thresholds:
    max_amount_alert: 10000
    duplicate_check_days: 365

alerts:
  channels: [console, email, slack]
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Low accuracy | Increase DPI, enable preprocessing |
| Database locked | Use WAL mode, add delays |
| OCR fails | Check Tesseract/Paddle install |
| False duplicates | Adjust fuzzy matching threshold |

## Docker

```bash
docker-compose up -d          # Start all services
docker-compose logs -f        # View logs
docker-compose down           # Stop services
```

## Support

- 📖 Full docs: README.md
- 🔧 Advanced: ADVANCED_GUIDE.md
- 🐛 Issues: Check logs/ folder
