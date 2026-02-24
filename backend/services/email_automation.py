"""
Email Automation Service

Uses SMTP when configured, otherwise runs in safe demo mode.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Dict, Any

logger = logging.getLogger("valora.email_automation")


class EmailAutomationService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "").strip()
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "").strip()
        self.smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "1").strip() != "0"
        self.from_email = os.getenv("SMTP_FROM_EMAIL", self.smtp_user or "noreply@valora.ai").strip()
        self.enabled = bool(self.smtp_host and self.smtp_user and self.smtp_password)

        if self.enabled:
            logger.info("[EmailAutomation] SMTP enabled: %s:%s", self.smtp_host, self.smtp_port)
        else:
            logger.warning("[EmailAutomation] SMTP not configured. Running in demo/no-send mode.")

    def send_text_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        to_email = (to_email or "").strip()
        if not to_email:
            raise ValueError("to_email is required")
        if not subject:
            raise ValueError("subject is required")

        if not self.enabled:
            logger.info(
                "[EmailAutomation][DEMO] To=%s Subject=%s BodyPreview=%s",
                to_email,
                subject,
                body[:200].replace("\n", " "),
            )
            return {"success": True, "sent": False, "demo_mode": True}

        msg = EmailMessage()
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as client:
            if self.smtp_use_tls:
                client.starttls()
            client.login(self.smtp_user, self.smtp_password)
            client.send_message(msg)

        logger.info("[EmailAutomation] Email sent to %s", to_email)
        return {"success": True, "sent": True, "demo_mode": False}


_email_automation_service: EmailAutomationService | None = None


def get_email_automation_service() -> EmailAutomationService:
    global _email_automation_service
    if _email_automation_service is None:
        _email_automation_service = EmailAutomationService()
    return _email_automation_service

