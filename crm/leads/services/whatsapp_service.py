"""WhatsApp Cloud API service."""

import logging
from typing import Dict, Optional

import requests

from crm.leads.models import ApiCredential

logger = logging.getLogger(__name__)


class WhatsAppService:
    """Service for interacting with WhatsApp Cloud API."""

    def __init__(self, api_credential: Optional[ApiCredential] = None):
        """Initialize WhatsApp service with API credential."""
        self.api_credential = api_credential
        if not api_credential:
            # Try to get active WhatsApp credential
            self.api_credential = ApiCredential.objects.filter(
                credential_type="whatsapp", is_active=True
            ).first()

        if not self.api_credential:
            raise ValueError("No active WhatsApp API credential found")

    @property
    def access_token(self) -> str:
        """Get access token."""
        return self.api_credential.access_token or ""

    @property
    def phone_number_id(self) -> str:
        """Get phone number ID."""
        return self.api_credential.phone_number_id or ""

    @property
    def base_url(self) -> str:
        """Get base URL with version from credentials."""
        version = self.api_credential.additional_config.get("version", "v18.0")
        return f"https://graph.facebook.com/{version}"

    def send_message(
        self, to: str, message: str, message_type: str = "text"
    ) -> Dict[str, any]:
        """
        Send a WhatsApp message.

        Args:
            to: Recipient phone number (with country code, no +)
            message: Message content
            message_type: Type of message (text, image, etc.)

        Returns:
            Response dictionary with message_id and status
        """
        url = f"{self.base_url}/{self.phone_number_id}/messages"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        if message_type == "text":
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": message},
            }
        else:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": message_type,
                message_type: {"text": message},
            }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            message_id = data.get("messages", [{}])[0].get("id", "")
            logger.info(f"WhatsApp message sent to {to}: {message_id}")

            return {
                "success": True,
                "message_id": message_id,
                "data": data,
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_message_status(self, message_id: str) -> Dict[str, any]:
        """Get status of a sent message."""
        # This would require webhook or polling implementation
        # For now, return placeholder
        return {
            "success": True,
            "status": "delivered",  # delivered, read, failed
        }

    def verify_webhook(self, verify_token: str, challenge: str) -> Optional[str]:
        """
        Verify webhook subscription.

        Returns:
            Challenge string if verified, None otherwise
        """
        expected_token = self.api_credential.additional_config.get("verify_token", "")
        if verify_token == expected_token:
            return challenge
        return None

    def parse_webhook_message(self, webhook_data: Dict) -> Optional[Dict[str, any]]:
        """
        Parse incoming webhook message.

        Returns:
            Parsed message data or None
        """
        try:
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})

            # Check if it's a message
            messages = value.get("messages", [])
            if not messages:
                return None

            message = messages[0]
            contact = value.get("contacts", [{}])[0]

            message_type = message.get("type", "text")
            content = ""
            if message_type == "text":
                content = message.get("text", {}).get("body", "")
            else:
                content = str(message.get(message_type, {}))

            return {
                "message_id": message.get("id"),
                "from": message.get("from"),
                "message_type": message_type,
                "content": content,
                "timestamp": message.get("timestamp"),
                "contact_name": contact.get("profile", {}).get("name", ""),
            }
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Error parsing WhatsApp webhook: {e}")
            return None

