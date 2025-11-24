"""Automation service for automated responses and reminders."""

import logging
from datetime import timedelta
from typing import Dict, Optional

from django.utils import timezone

from crm.leads.models import Lead, Message, Task
from crm.leads.services.email_service import EmailService
from crm.leads.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


class AutomationService:
    """Service for automation rules and automated responses."""

    def __init__(self):
        """Initialize automation service."""
        self.whatsapp_service = WhatsAppService()
        self.email_service = EmailService()

    def process_incoming_message(
        self, lead: Lead, contact, message: Message, channel: str
    ) -> None:
        """
        Process incoming message and trigger automation rules.

        This is called after a message is received and can:
        - Send auto-replies based on lead status
        - Create follow-up tasks
        - Update lead score
        """
        try:
            # Example: Auto-reply for new leads
            if lead.status and "new" in lead.status.name.lower():
                self._send_auto_reply(lead, contact, channel)

            # Create follow-up task if needed
            if lead.next_follow_up is None:
                self._create_follow_up_task(lead, contact, days=1)

            # Update lead score based on engagement
            self._update_lead_score(lead, message)

        except Exception as e:
            logger.exception(f"Error in automation processing: {e}")

    def _send_auto_reply(self, lead: Lead, contact, channel: str) -> None:
        """Send automatic reply to new leads."""
        try:
            message_text = f"Hello {contact.first_name or 'there'}, thank you for contacting us! We'll get back to you soon."

            if channel == "whatsapp":
                if contact.whatsapp_number:
                    result = self.whatsapp_service.send_message(
                        to=contact.whatsapp_number.replace("+", ""), message=message_text
                    )
                    if result.get("success"):
                        logger.info(f"Auto-reply sent via WhatsApp to {contact.whatsapp_number}")
            elif channel == "email":
                if contact.email:
                    result = self.email_service.send_email(
                        to=[contact.email],
                        subject="Thank you for contacting us",
                        body=message_text,
                    )
                    if result.get("success"):
                        logger.info(f"Auto-reply sent via email to {contact.email}")

        except Exception as e:
            logger.error(f"Error sending auto-reply: {e}")

    def _create_follow_up_task(self, lead: Lead, contact, days: int = 1) -> None:
        """Create a follow-up task."""
        try:
            Task.objects.create(
                lead=lead,
                contact=contact,
                title=f"Follow up with {contact.first_name or 'contact'}",
                description=f"Follow up on recent {lead.lead_source or 'communication'}",
                task_type="follow_up",
                priority="medium",
                status="pending",
                due_date=timezone.now() + timedelta(days=days),
                assigned_to=lead.assigned_to,
            )

            lead.next_follow_up = timezone.now() + timedelta(days=days)
            lead.save(update_fields=["next_follow_up"])

        except Exception as e:
            logger.error(f"Error creating follow-up task: {e}")

    def _update_lead_score(self, lead: Lead, message: Message) -> None:
        """Update lead score based on message activity."""
        try:
            # Simple scoring: +1 for each message received
            lead.lead_score += 1
            lead.save(update_fields=["lead_score"])
        except Exception as e:
            logger.error(f"Error updating lead score: {e}")

    def check_reminders(self) -> Dict[str, any]:
        """
        Check for tasks due and send reminders.

        This should be called by a scheduled task (Celery or cron).
        """
        try:
            now = timezone.now()
            tomorrow = now + timedelta(days=1)

            # Find tasks due in next 24 hours that are not completed
            tasks_due = Task.objects.filter(
                due_date__lte=tomorrow,
                due_date__gte=now,
                status__in=["pending", "in_progress"],
                completed_at__isnull=True,
            ).select_related("lead", "contact", "assigned_to")

            reminders_sent = 0
            for task in tasks_due:
                if task.assigned_to and task.assigned_to.email:
                    try:
                        self.email_service.send_email(
                            to=[task.assigned_to.email],
                            subject=f"Reminder: {task.title}",
                            body=f"You have a task due soon: {task.title}\n\nDue: {task.due_date}\nDescription: {task.description}",
                        )
                        reminders_sent += 1
                    except Exception as e:
                        logger.error(f"Error sending reminder for task {task.id}: {e}")

            logger.info(f"Sent {reminders_sent} task reminders")
            return {
                "success": True,
                "reminders_sent": reminders_sent,
                "tasks_checked": tasks_due.count(),
            }

        except Exception as e:
            logger.exception(f"Error checking reminders: {e}")
            return {"success": False, "error": str(e)}

    def check_follow_ups(self) -> Dict[str, any]:
        """
        Check for leads that need follow-up and create tasks.

        This should be called by a scheduled task.
        """
        try:
            now = timezone.now()
            # Find leads with next_follow_up in past but no recent activity
            leads_to_follow_up = Lead.objects.filter(
                next_follow_up__lte=now,
                is_client=False,
            ).select_related("assigned_to").prefetch_related("contacts")

            tasks_created = 0
            for lead in leads_to_follow_up:
                # Check if there's already a pending follow-up task
                has_pending_task = Task.objects.filter(
                    lead=lead,
                    task_type="follow_up",
                    status__in=["pending", "in_progress"],
                ).exists()

                if not has_pending_task:
                    primary_contact = lead.contacts.filter(is_primary=True).first()
                    if primary_contact:
                        self._create_follow_up_task(lead, primary_contact, days=0)
                        tasks_created += 1

            logger.info(f"Created {tasks_created} follow-up tasks")
            return {
                "success": True,
                "tasks_created": tasks_created,
                "leads_checked": leads_to_follow_up.count(),
            }

        except Exception as e:
            logger.exception(f"Error checking follow-ups: {e}")
            return {"success": False, "error": str(e)}

