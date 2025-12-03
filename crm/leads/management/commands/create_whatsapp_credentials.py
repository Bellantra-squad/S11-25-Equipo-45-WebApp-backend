"""Django management command to create WhatsApp API credentials."""

from django.core.management.base import BaseCommand, CommandError
from crm.leads.models import ApiCredential


class Command(BaseCommand):
    """Create or update WhatsApp API credentials."""

    help = "Create or update WhatsApp API credentials in the database"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--api-version",
            type=str,
            required=True,
            help="WhatsApp Graph API version (e.g., v18.0, v19.0)",
        )
        parser.add_argument(
            "--phone-number-id",
            type=str,
            required=True,
            help="WhatsApp Business Phone Number ID",
        )
        parser.add_argument(
            "--access-token",
            type=str,
            required=True,
            help="Facebook User Access Token",
        )
        parser.add_argument(
            "--service-name",
            type=str,
            default="WhatsApp",
            help="Service name (default: WhatsApp)",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing credential if found",
        )
        parser.add_argument(
            "--deactivate-others",
            action="store_true",
            help="Deactivate other WhatsApp credentials",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        version = options["api_version"]
        phone_number_id = options["phone_number_id"]
        access_token = options["access_token"]
        service_name = options["service_name"]
        update = options["update"]
        deactivate_others = options["deactivate_others"]

        try:
            # Check if credential already exists
            existing_credential = ApiCredential.objects.filter(
                credential_type="whatsapp",
                service_name=service_name,
            ).first()

            if existing_credential:
                if update:
                    # Update existing credential
                    existing_credential.access_token = access_token
                    existing_credential.phone_number_id = phone_number_id
                    existing_credential.additional_config = {"version": version}
                    existing_credential.is_active = True
                    existing_credential.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Successfully updated WhatsApp credentials for '{service_name}'"
                        )
                    )
                else:
                    raise CommandError(
                        f"Credential for '{service_name}' already exists. "
                        "Use --update flag to update it."
                    )
            else:
                # Create new credential
                ApiCredential.objects.create(
                    service_name=service_name,
                    credential_type="whatsapp",
                    access_token=access_token,
                    phone_number_id=phone_number_id,
                    additional_config={"version": version},
                    is_active=True,
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Successfully created WhatsApp credentials for '{service_name}'"
                    )
                )

            # Deactivate other WhatsApp credentials if requested
            if deactivate_others:
                deactivated = ApiCredential.objects.filter(
                    credential_type="whatsapp",
                    is_active=True,
                ).exclude(
                    service_name=service_name
                ).update(is_active=False)

                if deactivated > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ Deactivated {deactivated} other WhatsApp credential(s)"
                        )
                    )

            # Display credential info
            credential = ApiCredential.objects.get(
                credential_type="whatsapp",
                service_name=service_name,
            )

            self.stdout.write("\nCredential details:")
            self.stdout.write(f"  ID: {credential.id}")
            self.stdout.write(f"  Service: {credential.service_name}")
            self.stdout.write(f"  Type: {credential.get_credential_type_display()}")
            self.stdout.write(f"  Phone Number ID: {credential.phone_number_id}")
            self.stdout.write(f"  Access Token: {credential.access_token[:20]}...")
            self.stdout.write(f"  API Version: {credential.additional_config.get('version')}")
            self.stdout.write(f"  Active: {credential.is_active}")
            self.stdout.write(f"  Created: {credential.created_at}")

        except Exception as e:
            raise CommandError(f"Error creating WhatsApp credentials: {str(e)}")

