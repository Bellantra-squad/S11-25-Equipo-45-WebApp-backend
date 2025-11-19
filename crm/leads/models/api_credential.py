"""API credential models for external service integrations."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ApiCredential(models.Model):
    """API credentials for external services."""

    CREDENTIAL_TYPE_CHOICES = [
        ("whatsapp", _("WhatsApp")),
        ("email_smtp", _("Email SMTP")),
        ("email_brevo", _("Email Brevo")),
        ("other", _("Other")),
    ]

    service_name = models.CharField(_("service name"), max_length=255)
    credential_type = models.CharField(
        _("credential type"), max_length=50, choices=CREDENTIAL_TYPE_CHOICES
    )
    api_key = models.CharField(_("api key"), max_length=500, blank=True)
    api_secret = models.CharField(
        _("api secret"), max_length=500, blank=True
    )
    access_token = models.CharField(
        _("access token"), max_length=500, blank=True
    )
    refresh_token = models.CharField(
        _("refresh token"), max_length=500, blank=True
    )
    webhook_url = models.URLField(_("webhook url"), blank=True)
    phone_number_id = models.CharField(
        _("phone number id"), max_length=255, blank=True
    )
    business_account_id = models.CharField(
        _("business account id"), max_length=255, blank=True
    )
    additional_config = models.JSONField(
        _("additional config"), default=dict, blank=True
    )
    is_active = models.BooleanField(_("is active"), default=True)
    expires_at = models.DateTimeField(_("expires at"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("api credential")
        verbose_name_plural = _("api credentials")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.service_name} ({self.get_credential_type_display()})"
