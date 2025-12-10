"""Lead orchestrator - main business logic for message flow."""

import logging
from typing import Dict, Optional

from django.db import transaction
from django.utils import timezone

from crm.leads.models import Activity, Contact, Conversation, Lead, Message
from crm.leads.models.text_constants import LEAD_ORCHESTRATOR_MESSAGES
from crm.leads.services.automation_service import AutomationService
from crm.leads.services.campaign_service import CampaignService
from crm.leads.services.email_service import EmailService
from crm.leads.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


class LeadOrchestrator:
    """Orchestrates the flow of incoming messages and lead/contact creation."""

    def __init__(self):
        """Initialize orchestrator."""
        self.whatsapp_service = WhatsAppService()
        self.email_service = EmailService()
        self.automation_service = AutomationService()
        self.campaign_service = CampaignService()

    def process_whatsapp_webhook(self, webhook_data: Dict) -> Dict[str, any]:
        """
        Process incoming WhatsApp webhook.

        Flow:
        1. Parse webhook message
        2. Extract sender info
        3. Find or create Contact and Lead
        4. Find or create Conversation
        5. Create Message record
        6. Create Activity log
        7. Trigger automation rules
        """
        try:
            # Parse webhook
            message_data = self.whatsapp_service.parse_webhook_message(webhook_data)
            if not message_data:
                return {
                    "success": False,
                    "error": LEAD_ORCHESTRATOR_MESSAGES["whatsapp_parse_error"],
                }

            sender_phone = message_data.get("from", "")
            content = message_data.get("content", "")
            message_id = message_data.get("message_id", "")

            if not sender_phone:
                return {
                    "success": False,
                    "error": LEAD_ORCHESTRATOR_MESSAGES["whatsapp_no_sender"],
                }

            with transaction.atomic():
                # Find or create Contact and Lead
                contact, lead = self._get_or_create_contact_and_lead(
                    phone=sender_phone,
                    whatsapp_number=sender_phone,
                    name=message_data.get("contact_name", ""),
                    channel="whatsapp",
                )

                # Find or create Conversation
                conversation = self._get_or_create_conversation(
                    lead=lead,
                    contact=contact,
                    channel="whatsapp",
                )

                # Create Message
                message = Message.objects.create(
                    conversation=conversation,
                    sender_type="contact",
                    sender_id=str(contact.id),
                    content=content,
                    message_type="text",
                    external_message_id=message_id,
                    is_read=False,
                    sent_at=timezone.now(),
                )

                Activity.objects.create(
                    lead=lead,
                    contact=contact,
                    activity_type="message",
                    description=LEAD_ORCHESTRATOR_MESSAGES[
                        "whatsapp_activity_desc"
                    ].format(content=content[:100]),
                    metadata={
                        "message_id": message_id,
                        "channel": "whatsapp",
                        "message_type": "text",
                    },
                )

                # Update lead last contact date
                lead.last_contact_date = timezone.now()
                lead.save(update_fields=["last_contact_date"])

                # Trigger automation
                self.automation_service.process_incoming_message(
                    lead=lead,
                    contact=contact,
                    message=message,
                    channel="whatsapp",
                )

            logger.info(
                LEAD_ORCHESTRATOR_MESSAGES["whatsapp_processed"].format(
                    sender=sender_phone
                )
            )
            return {"success": True, "contact_id": contact.id, "lead_id": lead.id}

        except Exception as e:
            logger.exception(
                LEAD_ORCHESTRATOR_MESSAGES["whatsapp_process_error"].format(
                    error=e
                )
            )
            return {"success": False, "error": str(e)}

    def process_whatsapp_status_webhook(
        self, webhook_data: Dict
    ) -> Dict[str, any]:
        """
        Process WhatsApp message status updates (delivered, read, failed).

        Updates both Message records and CampaignRecipient records.
        """
        try:
            statuses = self._parse_whatsapp_statuses(webhook_data)
            if not statuses:
                return {
                    "success": False,
                    "error": LEAD_ORCHESTRATOR_MESSAGES["whatsapp_status_empty"],
                }

            updated_count = 0
            for status_update in statuses:
                message_id = status_update.get("id", "")
                status = status_update.get("status", "")

                if not message_id or not status:
                    continue

                # Update Message record
                message = Message.objects.filter(
                    external_message_id=message_id
                ).first()

                if message:
                    now = timezone.now()
                    if status == "delivered" and not message.delivered_at:
                        message.delivered_at = now
                        message.save(update_fields=["delivered_at"])
                    elif status == "read" and not message.read_at:
                        message.read_at = now
                        message.is_read = True
                        if not message.delivered_at:
                            message.delivered_at = now
                        message.save(
                            update_fields=["read_at", "is_read", "delivered_at"]
                        )

                # Update CampaignRecipient record
                self.campaign_service.update_recipient_status(
                    external_message_id=message_id,
                    new_status=status,
                )
                updated_count += 1

            logger.info(
                LEAD_ORCHESTRATOR_MESSAGES["whatsapp_status_processed"].format(
                    count=updated_count
                )
            )
            return {"success": True, "updated_count": updated_count}

        except Exception as e:
            logger.exception(
                LEAD_ORCHESTRATOR_MESSAGES["whatsapp_status_error"].format(
                    error=e
                )
            )
            return {"success": False, "error": str(e)}

    def _parse_whatsapp_statuses(self, webhook_data: Dict) -> list:
        """Parse WhatsApp status updates from webhook data."""
        try:
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            statuses = value.get("statuses", [])
            return statuses
        except (KeyError, IndexError, TypeError):
            return []

    def process_brevo_status_webhook(
        self, webhook_data: Dict
    ) -> Dict[str, any]:
        """
        Process Brevo email status updates (delivered, opened, clicked, etc.).

        Updates CampaignRecipient records.
        """
        try:
            event = webhook_data.get("event", "")
            message_id = webhook_data.get("message-id", "")

            if not message_id:
                return {
                    "success": False,
                    "error": LEAD_ORCHESTRATOR_MESSAGES["brevo_no_message_id"],
                }

            # Map Brevo events to internal status
            status_map = {
                "delivered": "delivered",
                "opened": "read",
                "click": "read",
                "soft_bounce": "failed",
                "hard_bounce": "failed",
                "invalid_email": "failed",
                "blocked": "failed",
                "spam": "failed",
                "unsubscribed": "delivered",
            }

            internal_status = status_map.get(event)
            if not internal_status:
                return {
                    "success": False,
                    "error": LEAD_ORCHESTRATOR_MESSAGES[
                        "brevo_unknown_event"
                    ].format(event=event),
                }

            # Update CampaignRecipient record
            updated = self.campaign_service.update_recipient_status(
                external_message_id=message_id,
                new_status=internal_status,
            )

            if updated:
                logger.info(
                    LEAD_ORCHESTRATOR_MESSAGES["brevo_updated"].format(
                        message_id=message_id, status=internal_status
                    )
                )
                return {"success": True, "status": internal_status}
            else:
                return {
                    "success": False,
                    "error": LEAD_ORCHESTRATOR_MESSAGES["brevo_not_found"],
                }

        except Exception as e:
            logger.exception(
                LEAD_ORCHESTRATOR_MESSAGES["brevo_error"].format(error=e)
            )
            return {"success": False, "error": str(e)}

    def process_email_webhook(self, webhook_data: Dict) -> Dict[str, any]:
        """
        Process incoming email webhook.

        Similar flow to WhatsApp but for email.
        """
        try:
            # Parse webhook
            email_data = self.email_service.parse_webhook(webhook_data)
            if not email_data:
                return {
                    "success": False,
                    "error": LEAD_ORCHESTRATOR_MESSAGES["email_parse_error"],
                }

            sender_email = email_data.get("from_email", "")
            content = email_data.get("body", "")
            subject = email_data.get("subject", "")

            if not sender_email:
                return {
                    "success": False,
                    "error": LEAD_ORCHESTRATOR_MESSAGES["email_no_sender"],
                }

            with transaction.atomic():
                # Find or create Contact and Lead
                # Try to extract name from email or from_name
                name_parts = email_data.get("from_name", "").split(" ", 1)
                first_name = name_parts[0] if name_parts else ""
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                contact, lead = self._get_or_create_contact_and_lead(
                    email=sender_email,
                    first_name=first_name,
                    last_name=last_name,
                    channel="email",
                )

                # Find or create Conversation
                conversation = self._get_or_create_conversation(
                    lead=lead,
                    contact=contact,
                    channel="email",
                    subject=subject,
                )

                # Create Message
                message = Message.objects.create(
                    conversation=conversation,
                    sender_type="contact",
                    sender_id=str(contact.id),
                    content=content,
                    message_type="text",
                    external_message_id=email_data.get("message_id", ""),
                    is_read=False,
                    sent_at=timezone.now(),
                )

                # Create Activity
                Activity.objects.create(
                    lead=lead,
                    contact=contact,
                    activity_type="email",
                    description=LEAD_ORCHESTRATOR_MESSAGES[
                        "email_activity_desc"
                    ].format(subject=subject),
                    metadata={
                        "message_id": email_data.get("message_id", ""),
                        "channel": "email",
                        "subject": subject,
                    },
                )

                # Update lead last contact date
                lead.last_contact_date = timezone.now()
                lead.save(update_fields=["last_contact_date"])

                # Trigger automation
                self.automation_service.process_incoming_message(
                    lead=lead,
                    contact=contact,
                    message=message,
                    channel="email",
                )

            logger.info(
                LEAD_ORCHESTRATOR_MESSAGES["email_processed"].format(
                    sender=sender_email
                )
            )
            return {"success": True, "contact_id": contact.id, "lead_id": lead.id}

        except Exception as e:
            logger.exception(
                LEAD_ORCHESTRATOR_MESSAGES["email_process_error"].format(
                    error=e
                )
            )
            return {"success": False, "error": str(e)}

    def _get_or_create_contact_and_lead(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        whatsapp_number: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        name: Optional[str] = None,
        channel: str = "whatsapp",
    ):
        """
        Get or create Contact and Lead.

        Logic:
        - If Contact exists by email/phone/whatsapp -> get Lead
        - If Contact doesn't exist -> create Lead + Contact
        """
        contact = None
        lead = None

        # Try to find existing contact
        if email:
            contact = Contact.objects.filter(email=email).first()
        elif whatsapp_number:
            contact = Contact.objects.filter(whatsapp_number=whatsapp_number).first()
        elif phone:
            contact = Contact.objects.filter(phone=phone).first()

        # If contact found, get lead
        if contact:
            lead = contact.lead
            # Update contact with new info if provided
            if email and not contact.email:
                contact.email = email
            if phone and not contact.phone:
                contact.phone = phone
            if whatsapp_number and not contact.whatsapp_number:
                contact.whatsapp_number = whatsapp_number
            if first_name and not contact.first_name:
                contact.first_name = first_name
            if last_name and not contact.last_name:
                contact.last_name = last_name
            contact.save()
        else:
            # Create new Lead and Contact
            # Extract name if provided as single string
            if name and not first_name:
                name_parts = name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

            first_name = first_name or LEAD_ORCHESTRATOR_MESSAGES[
                "default_first_name"
            ]
            last_name = last_name or ""

            # Create Lead with default status
            from crm.leads.models.lead import LeadStatus

            default_status = LeadStatus.objects.filter(is_active=True).order_by("order_position").first()

            # Generate company name from email or use default
            if email and "@" in email:
                domain_parts = email.split("@")[1].split(".")
                company_name = (
                    domain_parts[0].title()
                    if domain_parts
                    else LEAD_ORCHESTRATOR_MESSAGES["default_company_name"]
                )
            else:
                company_name = LEAD_ORCHESTRATOR_MESSAGES["default_company_name"]

            lead = Lead.objects.create(
                company_name=company_name,
                lead_source=channel,
                status=default_status,
            )

            # Create Contact
            contact = Contact.objects.create(
                lead=lead,
                first_name=first_name,
                last_name=last_name,
                email=email or "",
                phone=phone or "",
                whatsapp_number=whatsapp_number or "",
                is_primary=True,  # First contact is primary by default
            )

        return contact, lead

    def _get_or_create_conversation(
        self,
        lead: Lead,
        contact: Contact,
        channel: str,
        subject: Optional[str] = None,
    ) -> Conversation:
        """Get or create conversation for lead/contact/channel."""
        conversation = Conversation.objects.filter(
            lead=lead,
            contact=contact,
            channel=channel,
            status__in=["open", "pending"],
        ).first()

        if not conversation:
            conversation = Conversation.objects.create(
                lead=lead,
                contact=contact,
                channel=channel,
                subject=subject
                or LEAD_ORCHESTRATOR_MESSAGES["conversation_subject"].format(
                    channel=channel.title()
                ),
                status="open",
            )

        return conversation

