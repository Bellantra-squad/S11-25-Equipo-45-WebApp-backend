"""Activity models related to Lead and Contact."""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from crm.leads.models.contact import Contact
from crm.leads.models.lead import Lead

User = get_user_model()


class Activity(models.Model):
    """Activity log/audit trail."""

    ACTIVITY_TYPES = [
        ("call", _("Call")),
        ("email", _("Email")),
        ("meeting", _("Meeting")),
        ("note", _("Note")),
        ("task", _("Task")),
        ("message", _("Message")),
        ("status_change", _("Status Change")),
        ("other", _("Other")),
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="activities",
        null=True,
        blank=True,
        verbose_name=_("lead"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="activities",
        null=True,
        blank=True,
        verbose_name=_("contact"),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="activities",
        verbose_name=_("user"),
    )
    activity_type = models.CharField(_("activity type"), max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField(_("description"))
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("activity")
        verbose_name_plural = _("activities")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.created_at}"

