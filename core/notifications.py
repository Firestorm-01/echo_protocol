"""
Notification dispatch system.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from dataclasses import dataclass

import requests

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    success: bool
    channel: str
    recipient: str
    error: Optional[str] = None


class NotificationEngine:
    """Handles sending notifications through multiple channels."""

    def __init__(self):
        self._twilio = None  # renamed to avoid property/attr collision

    @property
    def twilio_client(self):
        if self._twilio is None and settings.TWILIO_SID:
            from twilio.rest import Client
            self._twilio = Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)
        return self._twilio

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> NotificationResult:
        """Send email notification."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_USER
            msg["To"] = to

            msg.attach(MIMEText(body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, to, msg.as_string())

            logger.info(f"Email sent to {to}")
            return NotificationResult(success=True, channel="email", recipient=to)

        except Exception as e:
            logger.error(f"Email failed to {to}: {e}")
            return NotificationResult(success=False, channel="email", recipient=to, error=str(e))

    def send_sms(self, to: str, message: str) -> NotificationResult:
        """Send SMS notification via Twilio."""
        if not self.twilio_client:
            return NotificationResult(
                success=False, channel="sms", recipient=to,
                error="Twilio not configured",
            )

        try:
            # Use keyword argument to avoid 'from' reserved-word clash
            self.twilio_client.messages.create(
                body=message,
                from_=settings.TWILIO_FROM,
                to=to,
            )
            logger.info(f"SMS sent to {to}")
            return NotificationResult(success=True, channel="sms", recipient=to)

        except Exception as e:
            logger.error(f"SMS failed to {to}: {e}")
            return NotificationResult(success=False, channel="sms", recipient=to, error=str(e))

    def send_webhook(
        self,
        url: str,
        payload: dict,
        headers: Optional[dict] = None,
    ) -> NotificationResult:
        """Send webhook notification."""
        try:
            default_headers = {"Content-Type": "application/json"}
            if headers:
                default_headers.update(headers)

            response = requests.post(url, json=payload, headers=default_headers, timeout=30)
            response.raise_for_status()

            logger.info(f"Webhook sent to {url}")
            return NotificationResult(success=True, channel="webhook", recipient=url)

        except Exception as e:
            logger.error(f"Webhook failed to {url}: {e}")
            return NotificationResult(success=False, channel="webhook", recipient=url, error=str(e))

    def notify_contacts(
        self,
        contacts: List,
        subject: str,
        message: str,
        payload_data: Optional[dict] = None,
    ) -> List[NotificationResult]:
        """Send notifications to all provided contacts."""
        results = []

        for contact in contacts:
            if contact.email:
                results.append(self.send_email(contact.email, subject, message))

            if contact.phone:
                sms_msg = f"ECHO PROTOCOL ALERT: {subject[:100]}"
                results.append(self.send_sms(contact.phone, sms_msg))

            if contact.webhook_url:
                webhook_payload = {
                    "alert_type": "dead_mans_switch",
                    "subject": subject,
                    "message": message,
                    "payload": payload_data or {},
                }
                results.append(self.send_webhook(contact.webhook_url, webhook_payload))

        return results
