"""Alert management system for invoice processing."""
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AlertType(Enum):
    DUPLICATE = "duplicate"
    HIGH_AMOUNT = "high_amount"
    VALIDATION_ERROR = "validation_error"
    LOW_CONFIDENCE = "low_confidence"
    PROCESSING_ERROR = "processing_error"


@dataclass
class Alert:
    """Represents an alert."""
    alert_type: AlertType
    severity: str  # critical, warning, info
    title: str
    message: str
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    amount: Optional[float] = None
    timestamp: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class AlertManager:
    """Manages alerts for the invoice processing system."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup alert handlers based on configuration."""
        self.handlers = []

        # Always add console handler
        self.handlers.append(ConsoleAlertHandler())

        # Email handler if configured
        if self.config.get('email', {}).get('enabled'):
            self.handlers.append(EmailAlertHandler(self.config['email']))

        # Slack handler if configured
        if self.config.get('slack', {}).get('enabled'):
            self.handlers.append(SlackAlertHandler(self.config['slack']))

    def send_alert(self, alert: Alert):
        """Send alert through all configured channels."""
        self.alerts.append(alert)
        self.alert_history.append(alert)

        for handler in self.handlers:
            try:
                handler.send(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

    def check_and_alert(self, validation_results: List[Any], 
                       invoice_data: Dict[str, Any],
                       existing_invoices: Optional[List[Dict]] = None):
        """Check validation results and send appropriate alerts."""
        invoice_id = invoice_data.get('id')
        invoice_num = invoice_data.get('invoice_number')
        vendor = invoice_data.get('vendor_name')
        amount = invoice_data.get('total_amount')

        # Check for duplicates
        if existing_invoices:
            for existing in existing_invoices:
                if (existing.get('invoice_number', '').lower() == str(invoice_num).lower() and
                    existing.get('vendor_name', '').lower() == str(vendor).lower()):
                    alert = Alert(
                        alert_type=AlertType.DUPLICATE,
                        severity="critical",
                        title="Duplicate Invoice Detected",
                        message=f"Invoice {invoice_num} from {vendor} appears to be a duplicate",
                        invoice_id=invoice_id,
                        invoice_number=invoice_num,
                        vendor_name=vendor,
                        amount=amount,
                        metadata={'existing_invoice_id': existing.get('id')}
                    )
                    self.send_alert(alert)
                    break

        # Check for high amount
        threshold = self.config.get('thresholds', {}).get('max_amount', 10000)
        if amount and amount > threshold:
            alert = Alert(
                alert_type=AlertType.HIGH_AMOUNT,
                severity="warning",
                title="High Value Invoice Alert",
                message=f"Invoice amount {amount} exceeds threshold {threshold}",
                invoice_id=invoice_id,
                invoice_number=invoice_num,
                vendor_name=vendor,
                amount=amount
            )
            self.send_alert(alert)

        # Check for validation errors
        for result in validation_results:
            if hasattr(result, 'severity'):
                if result.severity.value == 'error':
                    alert = Alert(
                        alert_type=AlertType.VALIDATION_ERROR,
                        severity="critical",
                        title="Invoice Validation Failed",
                        message=result.message,
                        invoice_id=invoice_id,
                        invoice_number=invoice_num,
                        vendor_name=vendor,
                        metadata={'field': result.field}
                    )
                    self.send_alert(alert)
                elif result.severity.value == 'warning':
                    alert = Alert(
                        alert_type=AlertType.VALIDATION_ERROR,
                        severity="warning",
                        title="Invoice Validation Warning",
                        message=result.message,
                        invoice_id=invoice_id,
                        invoice_number=invoice_num,
                        vendor_name=vendor,
                        metadata={'field': result.field}
                    )
                    self.send_alert(alert)

        # Check confidence scores
        confidence_scores = invoice_data.get('confidence_scores', {})
        avg_confidence = confidence_scores.get('average', 1.0)
        if avg_confidence < 0.7:
            alert = Alert(
                alert_type=AlertType.LOW_CONFIDENCE,
                severity="warning",
                title="Low OCR Confidence",
                message=f"Average confidence {avg_confidence:.2f} is below threshold",
                invoice_id=invoice_id,
                invoice_number=invoice_num,
                vendor_name=vendor,
                metadata={'confidence_scores': confidence_scores}
            )
            self.send_alert(alert)

    def get_recent_alerts(self, count: int = 10) -> List[Alert]:
        """Get recent alerts."""
        return sorted(self.alert_history, key=lambda x: x.timestamp, reverse=True)[:count]

    def clear_alerts(self):
        """Clear current alerts."""
        self.alerts = []


class ConsoleAlertHandler:
    """Handler for console alerts."""

    def send(self, alert: Alert):
        """Print alert to console."""
        emoji_map = {
            'critical': '🚨',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        emoji = emoji_map.get(alert.severity, 'ℹ️')

        print(f"\n{emoji} ALERT [{alert.alert_type.value.upper()}] {alert.severity.upper()}")
        print(f"   Title: {alert.title}")
        print(f"   Message: {alert.message}")
        if alert.invoice_number:
            print(f"   Invoice: {alert.invoice_number}")
        if alert.vendor_name:
            print(f"   Vendor: {alert.vendor_name}")
        if alert.amount:
            print(f"   Amount: ${alert.amount:,.2f}")
        print(f"   Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)


class EmailAlertHandler:
    """Handler for email alerts."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.smtp_server = config.get('smtp_server')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.recipients = config.get('recipients', [])

    def send(self, alert: Alert):
        """Send email alert."""
        if not all([self.smtp_server, self.username, self.password]):
            logger.warning("Email not configured, skipping email alert")
            return

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"[{alert.severity.upper()}] {alert.title}"

            body = f"""
            Alert Type: {alert.alert_type.value}
            Severity: {alert.severity}
            Title: {alert.title}
            Message: {alert.message}

            Invoice Details:
            - Number: {alert.invoice_number or 'N/A'}
            - Vendor: {alert.vendor_name or 'N/A'}
            - Amount: ${alert.amount:,.2f} if alert.amount else 'N/A'

            Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            """

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()

            logger.info(f"Email alert sent to {self.recipients}")

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")


class SlackAlertHandler:
    """Handler for Slack alerts."""

    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url')

    def send(self, alert: Alert):
        """Send Slack alert via webhook."""
        if not self.webhook_url:
            logger.warning("Slack webhook not configured")
            return

        try:
            import requests

            color_map = {
                'critical': '#FF0000',
                'warning': '#FFA500',
                'info': '#00FF00'
            }

            payload = {
                "attachments": [{
                    "color": color_map.get(alert.severity, '#808080'),
                    "title": f"{alert.severity.upper()}: {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Type", "value": alert.alert_type.value, "short": True},
                        {"title": "Invoice", "value": alert.invoice_number or 'N/A', "short": True},
                        {"title": "Vendor", "value": alert.vendor_name or 'N/A', "short": True},
                        {"title": "Amount", "value": f"${alert.amount:,.2f}" if alert.amount else 'N/A', "short": True}
                    ],
                    "footer": "Invoice Automation System",
                    "ts": int(alert.timestamp.timestamp())
                }]
            }

            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()

            logger.info("Slack alert sent successfully")

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
