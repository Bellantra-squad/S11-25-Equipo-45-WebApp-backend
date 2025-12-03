"""Campaign models for mass messaging."""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from crm.leads.models.contact import Contact

User = get_user_model()


class Campaign(models.Model):
    """Campaign for mass messaging via WhatsApp or Email."""

    CHANNEL_CHOICES = [
        ("whatsapp", _("WhatsApp")),
        ("email", _("Email")),
    ]

    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("scheduled", _("Scheduled")),
        ("in_progress", _("In Progress")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
        ("paused", _("Paused")),
    ]

    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    channel = models.CharField(_("channel"), max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="draft"
    )

    # Message content
    message_content = models.TextField(_("message content"), blank=True)

    # WhatsApp specific fields
    whatsapp_template_name = models.CharField(
        _("WhatsApp template name"), max_length=255, blank=True
    )
    whatsapp_template_params = models.JSONField(
        _("WhatsApp template params"), default=dict, blank=True
    )
    whatsapp_template_language = models.CharField(
        _("WhatsApp template language"), max_length=10, default="es", blank=True
    )

    # Email specific fields
    email_subject = models.CharField(_("email subject"), max_length=255, blank=True)

    # Scheduling
    scheduled_at = models.DateTimeField(_("scheduled at"), null=True, blank=True)
    started_at = models.DateTimeField(_("started at"), null=True, blank=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)

    # Filter configuration for selecting contacts
    filter_config = models.JSONField(
        _("filter config"),
        default=dict,
        blank=True,
        help_text=_(
            "JSON config for filtering contacts. Supports: lead_status, tags, "
            "category, is_client, assigned_to, lead_source"
        ),
    )

    # Ownership
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="campaigns",
        verbose_name=_("created by"),
    )

    # Timestamps
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("campaign")
        verbose_name_plural = _("campaigns")
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def total_recipients(self) -> int:
        """Get total number of recipients."""
        return self.recipients.count()

    @property
    def sent_count(self) -> int:
        """Get number of sent messages."""
        return self.recipients.exclude(status="pending").count()

    @property
    def delivered_count(self) -> int:
        """Get number of delivered messages."""
        return self.recipients.filter(status__in=["delivered", "read"]).count()

    @property
    def read_count(self) -> int:
        """Get number of read messages."""
        return self.recipients.filter(status="read").count()

    @property
    def failed_count(self) -> int:
        """Get number of failed messages."""
        return self.recipients.filter(status="failed").count()

    @property
    def pending_count(self) -> int:
        """Get number of pending messages."""
        return self.recipients.filter(status="pending").count()

    @property
    def delivery_rate(self) -> float:
        """Calculate delivery rate percentage."""
        sent = self.sent_count
        if sent == 0:
            return 0.0
        return round((self.delivered_count / sent) * 100, 2)

    @property
    def read_rate(self) -> float:
        """Calculate read rate percentage."""
        delivered = self.delivered_count
        if delivered == 0:
            return 0.0
        return round((self.read_count / delivered) * 100, 2)


class CampaignRecipient(models.Model):
    """Individual recipient tracking for a campaign."""

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("sent", _("Sent")),
        ("delivered", _("Delivered")),
        ("read", _("Read")),
        ("failed", _("Failed")),
    ]

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="recipients",
        verbose_name=_("campaign"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="campaign_recipients",
        verbose_name=_("contact"),
    )
    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    external_message_id = models.CharField(
        _("external message id"), max_length=255, blank=True
    )
    error_message = models.TextField(_("error message"), blank=True)

    # Tracking timestamps
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    delivered_at = models.DateTimeField(_("delivered at"), null=True, blank=True)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("campaign recipient")
        verbose_name_plural = _("campaign recipients")
        ordering = ["-created_at"]
        unique_together = [["campaign", "contact"]]

    def __str__(self):
        return f"{self.campaign.name} - {self.contact}"

