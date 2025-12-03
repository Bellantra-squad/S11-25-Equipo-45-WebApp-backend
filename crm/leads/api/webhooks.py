"""Webhook endpoints for external integrations."""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from crm.leads.services.lead_orchestrator import LeadOrchestrator

logger = logging.getLogger(__name__)


def verify_whatsapp_signature(request: HttpRequest, app_secret: str) -> bool:
    """
    Verify WhatsApp webhook signature.

    WhatsApp Cloud API sends a signature in the X-Hub-Signature-256 header.
    """
    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    signature = signature_header.replace("sha256=", "")
    body = request.body

    # Compute expected signature
    expected_signature = hmac.new(
        app_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):
    """Webhook endpoint for WhatsApp Cloud API."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handle incoming WhatsApp webhooks."""
        try:
            # Get webhook verification token from request or settings
            mode = request.GET.get("hub.mode")
            token = request.GET.get("hub.verify_token")
            challenge = request.GET.get("hub.challenge")

            # Webhook verification
            if mode == "subscribe":
                verify_token = getattr(settings, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
                if token == verify_token:
                    logger.info("WhatsApp webhook verified")
                    return HttpResponse(challenge, content_type="text/plain")
                return HttpResponse("Verification failed", status=403)

            # Handle incoming messages
            body = json.loads(request.body.decode("utf-8"))
            logger.info(f"Received WhatsApp webhook: {json.dumps(body, indent=2)}")

            # Verify signature if app secret is configured
            app_secret = getattr(settings, "WHATSAPP_APP_SECRET", "")
            if app_secret and not verify_whatsapp_signature(request, app_secret):
                logger.warning("Invalid WhatsApp webhook signature")
                return JsonResponse({"error": "Invalid signature"}, status=403)

            # Process webhook
            orchestrator = LeadOrchestrator()

            # Check if this is a status update or a new message
            is_status_update = self._is_status_update(body)

            if is_status_update:
                result = orchestrator.process_whatsapp_status_webhook(body)
            else:
                result = orchestrator.process_whatsapp_webhook(body)

            if result.get("success"):
                return JsonResponse({"status": "ok"}, status=200)
            return JsonResponse(
                {"error": result.get("error", "Unknown error")}, status=400
            )

        except json.JSONDecodeError:
            logger.error("Invalid JSON in WhatsApp webhook")
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.exception(f"Error processing WhatsApp webhook: {e}")
            return JsonResponse({"error": str(e)}, status=500)

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handle webhook verification."""
        return self.post(request)

    def _is_status_update(self, webhook_data: dict) -> bool:
        """Check if the webhook is a status update vs a new message."""
        try:
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            # Status updates have 'statuses' key, messages have 'messages' key
            return bool(value.get("statuses")) and not value.get("messages")
        except (KeyError, IndexError, TypeError):
            return False


@method_decorator(csrf_exempt, name="dispatch")
class EmailWebhookView(View):
    """Webhook endpoint for email services (Brevo, etc.)."""

    def post(self, request: HttpRequest) -> HttpResponse:
        """Handle incoming email webhooks."""
        try:
            body = json.loads(request.body.decode("utf-8"))
            logger.info(f"Received email webhook: {json.dumps(body, indent=2)}")

            # Verify signature if configured
            signature_header = request.headers.get("X-Brevo-Signature", "")
            webhook_secret = getattr(settings, "BREVO_WEBHOOK_SECRET", "")
            if webhook_secret and signature_header:
                expected_signature = hmac.new(
                    webhook_secret.encode("utf-8"), request.body, hashlib.sha256
                ).hexdigest()
                if not hmac.compare_digest(signature_header, expected_signature):
                    logger.warning("Invalid email webhook signature")
                    return JsonResponse({"error": "Invalid signature"}, status=403)

            # Process webhook
            orchestrator = LeadOrchestrator()

            # Check if this is a status update or inbound message
            # (supports Brevo Transactional and Brevo Conversations)
            event_type = body.get("event", "")

            # Status events from Brevo Transactional
            is_status_event = event_type in [
                "delivered",
                "opened",
                "click",
                "soft_bounce",
                "hard_bounce",
                "invalid_email",
                "blocked",
                "spam",
                "unsubscribed",
            ]

            if is_status_event:
                result = orchestrator.process_brevo_status_webhook(body)
            else:
                # Process as inbound message (Conversations or transactional)
                result = orchestrator.process_email_webhook(body)

            if result.get("success"):
                return JsonResponse({"status": "ok"}, status=200)
            return JsonResponse(
                {"error": result.get("error", "Unknown error")}, status=400
            )

        except json.JSONDecodeError:
            logger.error("Invalid JSON in email webhook")
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.exception(f"Error processing email webhook: {e}")
            return JsonResponse({"error": str(e)}, status=500)

