# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2024-01-15

### Added
- Initial release of Invoice Automation System
- Multi-engine OCR support (PaddleOCR, Tesseract, Hybrid)
- Automatic field extraction (vendor, invoice #, dates, amounts)
- Duplicate detection with configurable time windows
- Validation engine with customizable rules
- Alert system (Console, Email, Slack)
- SQLite database with CSV export
- File watcher for automatic processing
- Streamlit dashboard for monitoring
- REST API for integration
- Docker support with compose configuration
- Comprehensive documentation and examples

### Features
- PDF and image support (PNG, JPG, TIFF, BMP)
- Confidence scoring for all extractions
- Mathematical validation (subtotal + tax = total)
- Future date detection
- High amount threshold alerts
- Batch processing capability
- Real-time dashboard with analytics

### Security
- Input file validation
- SQL injection prevention
- XSS protection in dashboard
- Secure file handling

## [Unreleased]

### Planned
- LLM integration for complex layouts
- Multi-language support
- Advanced table extraction
- ML-based duplicate detection
- Mobile app companion
- Cloud storage integration (S3, Azure)
- Webhook notifications
- Custom plugin system
