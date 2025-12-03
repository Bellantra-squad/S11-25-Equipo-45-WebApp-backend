from django.apps import AppConfig


class LeadsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "crm.leads"
    verbose_name = "Leads"

    def ready(self):
        """Import signals when app is ready."""
        import crm.leads.signals  # noqa: F401
