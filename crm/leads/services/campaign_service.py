"""Campaign service for mass messaging orchestration."""

import logging
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from crm.leads.models import Campaign, CampaignRecipient, Contact
from crm.leads.services.email_service import EmailService
from crm.leads.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


class CampaignService:
    """Service for orchestrating campaign execution."""

    def __init__(self):
        """Initialize campaign service."""
        self._whatsapp_service: Optional[WhatsAppService] = None
        self._email_service: Optional[EmailService] = None

    @property
    def whatsapp_service(self) -> WhatsAppService:
        """Lazy load WhatsApp service."""
        if self._whatsapp_service is None:
            self._whatsapp_service = WhatsAppService()
        return self._whatsapp_service

    @property
    def email_service(self) -> EmailService:
        """Lazy load email service."""
        if self._email_service is None:
            self._email_service = EmailService()
        return self._email_service

    def get_filtered_contacts(self, filter_config: Dict[str, Any]) -> List[Contact]:
        """
        Get contacts based on filter configuration.

        Supported filters:
        - lead_status: List of status IDs
        - tags: List of tag IDs
        - category: List of category IDs
        - is_client: Boolean
        - assigned_to: List of user IDs
        - lead_source: List of lead sources
        - has_whatsapp: Boolean (for WhatsApp campaigns)
        - has_email: Boolean (for email campaigns)

        Args:
            filter_config: Dictionary with filter criteria

        Returns:
            List of Contact objects matching the filters
        """
        queryset = Contact.objects.select_related("lead").all()

        # Filter by lead status
        lead_status = filter_config.get("lead_status")
        if lead_status:
            queryset = queryset.filter(lead__status_id__in=lead_status)

        # Filter by tags
        tags = filter_config.get("tags")
        if tags:
            queryset = queryset.filter(
                Q(tags__id__in=tags) | Q(lead__tags__id__in=tags)
            ).distinct()

        # Filter by category
        category = filter_config.get("category")
        if category:
            queryset = queryset.filter(lead__category_id__in=category)

        # Filter by is_client
        is_client = filter_config.get("is_client")
        if is_client is not None:
            queryset = queryset.filter(lead__is_client=is_client)

        # Filter by assigned_to
        assigned_to = filter_config.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(lead__assigned_to_id__in=assigned_to)

        # Filter by lead_source
        lead_source = filter_config.get("lead_source")
        if lead_source:
            queryset = queryset.filter(lead__lead_source__in=lead_source)

        # Filter by WhatsApp availability
        has_whatsapp = filter_config.get("has_whatsapp")
        if has_whatsapp:
            queryset = queryset.exclude(
                Q(whatsapp_number__isnull=True) | Q(whatsapp_number="")
            )

        # Filter by email availability
        has_email = filter_config.get("has_email")
        if has_email:
            queryset = queryset.exclude(Q(email__isnull=True) | Q(email=""))

        return list(queryset.distinct())

    def create_recipients(self, campaign: Campaign) -> int:
        """
        Create campaign recipients based on filter configuration.

        Args:
            campaign: Campaign instance

        Returns:
            Number of recipients created
        """
        # Get filter config with channel-specific defaults
        filter_config = campaign.filter_config.copy()

        # Auto-add channel filter based on campaign channel
        if campaign.channel == "whatsapp":
            filter_config["has_whatsapp"] = True
        elif campaign.channel == "email":
            filter_config["has_email"] = True

        contacts = self.get_filtered_contacts(filter_config)

        # Create recipients (skip duplicates)
        recipients_created = 0
        for contact in contacts:
            _, created = CampaignRecipient.objects.get_or_create(
                campaign=campaign,
                contact=contact,
                defaults={"status": "pending"},
            )
            if created:
                recipients_created += 1

        return recipients_created

    def preview_recipients(
        self, filter_config: Dict[str, Any], channel: str
    ) -> List[Dict[str, Any]]:
        """
        Preview contacts that would receive a campaign.

        Args:
            filter_config: Filter configuration
            channel: Campaign channel (whatsapp or email)

        Returns:
            List of contact previews
        """
        # Add channel filter
        config = filter_config.copy()
        if channel == "whatsapp":
            config["has_whatsapp"] = True
        elif channel == "email":
            config["has_email"] = True

        contacts = self.get_filtered_contacts(config)

        return [
            {
                "id": contact.id,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "email": contact.email,
                "whatsapp_number": contact.whatsapp_number,
                "lead_id": contact.lead_id,
                "lead_name": contact.lead.company_name if contact.lead else None,
            }
            for contact in contacts[:100]  # Limit preview to 100
        ]

    def execute_campaign(self, campaign: Campaign) -> Dict[str, Any]:
        """
        Execute a campaign by sending messages to all pending recipients.

        Args:
            campaign: Campaign instance

        Returns:
            Execution result summary
        """
        if campaign.status not in ["draft", "scheduled", "paused"]:
            return {
                "success": False,
                "error": f"Cannot execute campaign with status '{campaign.status}'",
            }

        # Update campaign status
        campaign.status = "in_progress"
        campaign.started_at = timezone.now()
        campaign.save(update_fields=["status", "started_at", "updated_at"])

        # Create recipients if not exist
        if campaign.recipients.count() == 0:
            self.create_recipients(campaign)

        # Get pending recipients
        pending_recipients = campaign.recipients.filter(status="pending")

        sent_count = 0
        failed_count = 0

        for recipient in pending_recipients:
            # Check if campaign was paused or cancelled
            campaign.refresh_from_db()
            if campaign.status in ["paused", "cancelled"]:
                break

            try:
                if campaign.channel == "whatsapp":
                    result = self._send_whatsapp_message(campaign, recipient)
                elif campaign.channel == "email":
                    result = self._send_email_message(campaign, recipient)
                else:
                    result = {"success": False, "error": "Unknown channel"}

                if result.get("success"):
                    recipient.status = "sent"
                    recipient.external_message_id = result.get("message_id", "")
                    recipient.sent_at = timezone.now()
                    sent_count += 1
                else:
                    recipient.status = "failed"
                    recipient.error_message = result.get("error", "Unknown error")
                    failed_count += 1

                recipient.save()

            except Exception as e:
                logger.exception(f"Error sending to recipient {recipient.id}: {e}")
                recipient.status = "failed"
                recipient.error_message = str(e)
                recipient.save()
                failed_count += 1

        # Check if campaign completed
        campaign.refresh_from_db()
        if campaign.status == "in_progress":
            remaining = campaign.recipients.filter(status="pending").count()
            if remaining == 0:
                campaign.status = "completed"
                campaign.completed_at = timezone.now()
                campaign.save(update_fields=["status", "completed_at", "updated_at"])

        return {
            "success": True,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "status": campaign.status,
        }

    def _send_whatsapp_message(
        self, campaign: Campaign, recipient: CampaignRecipient
    ) -> Dict[str, Any]:
        """
        Send WhatsApp message to a recipient.

        Args:
            campaign: Campaign instance
            recipient: CampaignRecipient instance

        Returns:
            Send result dictionary
        """
        phone = recipient.contact.whatsapp_number
        if not phone:
            return {"success": False, "error": "No WhatsApp number"}

        # Remove + if present
        phone = phone.replace("+", "")

        try:
            # Check if using template or free text
            if campaign.whatsapp_template_name:
                result = self.whatsapp_service.send_template_message(
                    to=phone,
                    template_name=campaign.whatsapp_template_name,
                    language_code=campaign.whatsapp_template_language or "es",
                    parameters=campaign.whatsapp_template_params or {},
                )
            else:
                # Use free text message
                message = self._personalize_message(
                    campaign.message_content, recipient.contact
                )
                result = self.whatsapp_service.send_message(
                    to=phone,
                    message=message,
                    message_type="text",
                )

            return result

        except ValueError as e:
            return {"success": False, "error": str(e)}

    def _send_email_message(
        self, campaign: Campaign, recipient: CampaignRecipient
    ) -> Dict[str, Any]:
        """
        Send email message to a recipient.

        Args:
            campaign: Campaign instance
            recipient: CampaignRecipient instance

        Returns:
            Send result dictionary
        """
        email = recipient.contact.email
        if not email:
            return {"success": False, "error": "No email address"}

        try:
            subject = self._personalize_message(
                campaign.email_subject, recipient.contact
            )
            body = self._personalize_message(
                campaign.message_content, recipient.contact
            )

            result = self.email_service.send_email(
                to=[email],
                subject=subject,
                body=body,
                html_body=body if "<html" in body.lower() else None,
            )

            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _personalize_message(self, template: str, contact: Contact) -> str:
        """
        Personalize message template with contact data.

        Supported placeholders:
        - {{first_name}}
        - {{last_name}}
        - {{full_name}}
        - {{email}}
        - {{phone}}
        - {{company}}

        Args:
            template: Message template
            contact: Contact instance

        Returns:
            Personalized message
        """
        replacements = {
            "{{first_name}}": contact.first_name or "",
            "{{last_name}}": contact.last_name or "",
            "{{full_name}}": f"{contact.first_name} {contact.last_name}".strip(),
            "{{email}}": contact.email or "",
            "{{phone}}": contact.phone or contact.whatsapp_number or "",
            "{{company}}": contact.lead.company_name if contact.lead else "",
        }

        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)

        return result

    def pause_campaign(self, campaign: Campaign) -> Dict[str, Any]:
        """
        Pause a running campaign.

        Args:
            campaign: Campaign instance

        Returns:
            Result dictionary
        """
        if campaign.status != "in_progress":
            return {
                "success": False,
                "error": f"Cannot pause campaign with status '{campaign.status}'",
            }

        campaign.status = "paused"
        campaign.save(update_fields=["status", "updated_at"])

        return {"success": True, "status": "paused"}

    def resume_campaign(self, campaign: Campaign) -> Dict[str, Any]:
        """
        Resume a paused campaign.

        Args:
            campaign: Campaign instance

        Returns:
            Result dictionary
        """
        if campaign.status != "paused":
            return {
                "success": False,
                "error": f"Cannot resume campaign with status '{campaign.status}'",
            }

        # Execute will handle the rest
        return self.execute_campaign(campaign)

    def cancel_campaign(self, campaign: Campaign) -> Dict[str, Any]:
        """
        Cancel a campaign.

        Args:
            campaign: Campaign instance

        Returns:
            Result dictionary
        """
        if campaign.status in ["completed", "cancelled"]:
            return {
                "success": False,
                "error": f"Cannot cancel campaign with status '{campaign.status}'",
            }

        campaign.status = "cancelled"
        campaign.save(update_fields=["status", "updated_at"])

        return {"success": True, "status": "cancelled"}

    def update_recipient_status(
        self,
        external_message_id: str,
        new_status: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Update recipient status from webhook.

        Args:
            external_message_id: External message ID from WhatsApp/Brevo
            new_status: New status (delivered, read, failed)
            timestamp: Optional timestamp string

        Returns:
            True if updated, False otherwise
        """
        try:
            recipient = CampaignRecipient.objects.get(
                external_message_id=external_message_id
            )

            # Map external status to internal status
            status_map = {
                "delivered": "delivered",
                "read": "read",
                "failed": "failed",
                "sent": "sent",
            }

            internal_status = status_map.get(new_status.lower())
            if not internal_status:
                return False

            recipient.status = internal_status

            # Update timestamps
            now = timezone.now()
            if internal_status == "delivered" and not recipient.delivered_at:
                recipient.delivered_at = now
            elif internal_status == "read" and not recipient.read_at:
                recipient.read_at = now
                if not recipient.delivered_at:
                    recipient.delivered_at = now

            recipient.save()

            logger.info(
                f"Updated recipient {recipient.id} status to {internal_status}"
            )
            return True

        except CampaignRecipient.DoesNotExist:
            return False
        except Exception as e:
            logger.exception(f"Error updating recipient status: {e}")
            return False

    def get_campaign_metrics(self, campaign: Campaign) -> Dict[str, Any]:
        """
        Get detailed metrics for a campaign.

        Args:
            campaign: Campaign instance

        Returns:
            Dictionary with campaign metrics
        """
        from django.db.models import Count
        from django.db.models.functions import TruncHour

        # Status counts
        status_counts = dict(
            campaign.recipients.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

        total = campaign.total_recipients
        sent = total - status_counts.get("pending", 0)
        delivered = status_counts.get("delivered", 0) + status_counts.get("read", 0)
        read = status_counts.get("read", 0)
        failed = status_counts.get("failed", 0)

        # Calculate rates
        delivery_rate = round((delivered / sent) * 100, 2) if sent > 0 else 0
        read_rate = round((read / delivered) * 100, 2) if delivered > 0 else 0
        failure_rate = round((failed / total) * 100, 2) if total > 0 else 0

        # Hourly distribution of sent messages
        hourly_sent = list(
            campaign.recipients.exclude(sent_at__isnull=True)
            .annotate(hour=TruncHour("sent_at"))
            .values("hour")
            .annotate(count=Count("id"))
            .order_by("hour")
        )

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "channel": campaign.channel,
            "status": campaign.status,
            "total_recipients": total,
            "pending": status_counts.get("pending", 0),
            "sent": sent,
            "delivered": delivered,
            "read": read,
            "failed": failed,
            "delivery_rate": delivery_rate,
            "read_rate": read_rate,
            "failure_rate": failure_rate,
            "started_at": campaign.started_at,
            "completed_at": campaign.completed_at,
            "hourly_distribution": hourly_sent,
        }

