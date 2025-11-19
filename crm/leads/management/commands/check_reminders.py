"""Management command to check and send task reminders."""

from django.core.management.base import BaseCommand

from crm.leads.services.automation_service import AutomationService


class Command(BaseCommand):
    """Check for tasks due and send reminders."""

    help = "Check for tasks due and send reminders via email"

    def handle(self, *args, **options):
        """Execute the command."""
        automation_service = AutomationService()
        result = automation_service.check_reminders()

        if result.get("success"):
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully sent {result.get('reminders_sent', 0)} reminders "
                    f"out of {result.get('tasks_checked', 0)} tasks checked"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"Error checking reminders: {result.get('error', 'Unknown error')}")
            )

