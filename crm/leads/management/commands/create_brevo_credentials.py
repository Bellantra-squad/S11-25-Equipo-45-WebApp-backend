"""Django management command to create Brevo API credentials."""

from django.core.management.base import BaseCommand, CommandError
from crm.leads.models import ApiCredential


class Command(BaseCommand):
    """Create or update Brevo API credentials."""

    help = "Create or update Brevo API credentials in the database"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--api-key",
            type=str,
            required=True,
            help="Brevo API key",
        )
        parser.add_argument(
            "--service-name",
            type=str,
            default="Brevo",
            help="Service name (default: Brevo)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing credential if found",
        )
        parser.add_argument(
            "--deactivate-others",
            action="store_true",
            help="Deactivate other Brevo credentials",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        api_key = options["api_key"]
        service_name = options["service_name"]
        update = options["update"]
        deactivate_others = options["deactivate_others"]

        try:
            # Check if credential already exists
            existing_credential = ApiCredential.objects.filter(
                credential_type="email_brevo",
                service_name=service_name,
            ).first()

            if existing_credential:
                if update:
                    # Update existing credential
                    existing_credential.api_key = api_key
                    existing_credential.is_active = True
                    existing_credential.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Successfully updated Brevo credentials for '{service_name}'"
                        )
                    )
                else:
                    raise CommandError(
                        f"Credential for '{service_name}' already exists. "
                        "Use --update flag to update it."
                    )
            else:
                # Create new credential
                credential = ApiCredential.objects.create(
                    service_name=service_name,
                    credential_type="email_brevo",
                    api_key=api_key,
                    is_active=True,
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Successfully created Brevo credentials for '{service_name}'"
                    )
                )

            # Deactivate other Brevo credentials if requested
            if deactivate_others:
                deactivated = ApiCredential.objects.filter(
                    credential_type="email_brevo",
                    is_active=True,
                ).exclude(
                    service_name=service_name
                ).update(is_active=False)

                if deactivated > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ Deactivated {deactivated} other Brevo credential(s)"
                        )
                    )

            # Display credential info
            credential = ApiCredential.objects.get(
                credential_type="email_brevo",
                service_name=service_name,
            )

            self.stdout.write("\nCredential details:")
            self.stdout.write(f"  ID: {credential.id}")
            self.stdout.write(f"  Service: {credential.service_name}")
            self.stdout.write(f"  Type: {credential.get_credential_type_display()}")
            self.stdout.write(f"  API Key: {credential.api_key[:20]}...")
            self.stdout.write(f"  Active: {credential.is_active}")
            self.stdout.write(f"  Created: {credential.created_at}")

        except Exception as e:
            raise CommandError(f"Error creating Brevo credentials: {str(e)}")

