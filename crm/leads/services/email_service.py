"""Email service for SMTP and Brevo integration."""

import logging
from typing import Dict, List, Optional

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.core.mail.backends.smtp import EmailBackend

from crm.leads.models import ApiCredential, EmailTemplate

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP or Brevo."""

    def __init__(self, api_credential: Optional[ApiCredential] = None, use_brevo: bool = False):
        """Initialize email service."""
        self.api_credential = api_credential
        self.use_brevo = use_brevo

        if not api_credential and not use_brevo:
            # Try to get active email credential
            self.api_credential = ApiCredential.objects.filter(
                credential_type__in=["email_smtp", "email_brevo"], is_active=True
            ).first()

            if self.api_credential:
                self.use_brevo = self.api_credential.credential_type == "email_brevo"

    def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html_body: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Send an email.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Plain text body
            from_email: Sender email (optional)
            cc: CC recipients (optional)
            bcc: BCC recipients (optional)
            html_body: HTML body (optional)

        Returns:
            Response dictionary with success status
        """
        if self.use_brevo:
            return self._send_via_brevo(to, subject, body, from_email, cc, bcc, html_body)
        else:
            return self._send_via_smtp(to, subject, body, from_email, cc, bcc, html_body)

    def _send_via_smtp(
        self,
        to: List[str],
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html_body: Optional[str] = None,
    ) -> Dict[str, any]:
        """Send email via SMTP."""
        try:
            if not from_email:
                from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")

            # Use custom SMTP settings if API credential is provided
            if self.api_credential and self.api_credential.credential_type == "email_smtp":
                connection = get_connection(
                    host=self.api_credential.additional_config.get("smtp_host", ""),
                    port=self.api_credential.additional_config.get("smtp_port", 587),
                    username=self.api_credential.api_key or "",
                    password=self.api_credential.api_secret or "",
                    use_tls=self.api_credential.additional_config.get("use_tls", True),
                )
            else:
                connection = None

            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=to,
                cc=cc or [],
                bcc=bcc or [],
                connection=connection,
            )

            if html_body:
                email.content_subtype = "html"
                email.body = html_body

            email.send()

            logger.info(f"Email sent via SMTP to {to}: {subject}")
            return {
                "success": True,
                "message": "Email sent successfully",
            }
        except Exception as e:
            logger.error(f"Error sending email via SMTP: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _send_via_brevo(
        self,
        to: List[str],
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        html_body: Optional[str] = None,
    ) -> Dict[str, any]:
        """Send email via Brevo API."""
        try:
            import requests

            api_key = (
                self.api_credential.api_key
                if self.api_credential
                else getattr(settings, "BREVO_API_KEY", "")
            )

            if not api_key:
                raise ValueError("Brevo API key not found")

            url = "https://api.brevo.com/v3/smtp/email"

            headers = {
                "Accept": "application/json",
                "api-key": api_key,
                "Content-Type": "application/json",
            }

            payload = {
                "sender": {"email": from_email or getattr(settings, "DEFAULT_FROM_EMAIL", "")},
                "to": [{"email": email} for email in to],
                "subject": subject,
                "htmlContent": html_body or body,
                "textContent": body if not html_body else None,
            }

            if cc:
                payload["cc"] = [{"email": email} for email in cc]
            if bcc:
                payload["bcc"] = [{"email": email} for email in bcc]

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            logger.info(f"Email sent via Brevo to {to}: {subject}")
            return {
                "success": True,
                "message_id": response.json().get("messageId"),
                "message": "Email sent successfully",
            }
        except Exception as e:
            logger.error(f"Error sending email via Brevo: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def send_template_email(
        self, template: EmailTemplate, to: List[str], context: Optional[Dict] = None
    ) -> Dict[str, any]:
        """Send email using a template."""
        context = context or {}

        # Simple template variable substitution
        subject = template.subject
        body = template.body

        for key, value in context.items():
            subject = subject.replace(f"{{{{{key}}}}}}}", str(value))
            body = body.replace(f"{{{{{key}}}}}}}", str(value))

        return self.send_email(
            to=to,
            subject=subject,
            body=body,
            html_body=body if "<html" in body.lower() else None,
        )

    def parse_webhook(self, webhook_data: Dict) -> Optional[Dict[str, any]]:
        """
        Parse incoming email webhook (Brevo).

        Returns:
            Parsed email data or None
        """
        try:
            # Brevo webhook format
            event_type = webhook_data.get("event")
            if event_type not in ["inbound_email_processed"]:
                return None

            data = webhook_data.get("data", {})
            return {
                "from_email": data.get("sender", {}).get("email", ""),
                "from_name": data.get("sender", {}).get("name", ""),
                "to_email": data.get("recipient", ""),
                "subject": data.get("subject", ""),
                "body": data.get("htmlBody") or data.get("textBody", ""),
                "message_id": data.get("messageId", ""),
                "timestamp": data.get("date", ""),
            }
        except (KeyError, TypeError) as e:
            logger.error(f"Error parsing email webhook: {e}")
            return None

