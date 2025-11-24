"""Management command to check and create follow-up tasks."""

from django.core.management.base import BaseCommand

from crm.leads.services.automation_service import AutomationService


class Command(BaseCommand):
    """Check for leads needing follow-up and create tasks."""

    help = "Check for leads that need follow-up and create tasks"

    def handle(self, *args, **options):
        """Execute the command."""
        automation_service = AutomationService()
        result = automation_service.check_follow_ups()

        if result.get("success"):
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created {result.get('tasks_created', 0)} follow-up tasks "
                    f"out of {result.get('leads_checked', 0)} leads checked"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"Error checking follow-ups: {result.get('error', 'Unknown error')}")
            )

