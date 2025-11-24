"""Email template models."""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class EmailTemplate(models.Model):
    """Email templates for automated and manual sending."""

    TEMPLATE_TYPE_CHOICES = [
        ("welcome", _("Welcome")),
        ("follow_up", _("Follow Up")),
        ("reminder", _("Reminder")),
        ("custom", _("Custom")),
    ]

    name = models.CharField(_("name"), max_length=255)
    subject = models.CharField(_("subject"), max_length=255)
    body = models.TextField(_("body"))
    template_type = models.CharField(_("template type"), max_length=50, choices=TEMPLATE_TYPE_CHOICES)
    is_active = models.BooleanField(_("is active"), default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="email_templates",
        verbose_name=_("created by"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("email template")
        verbose_name_plural = _("email templates")
        ordering = ["name"]

    def __str__(self):
        return self.name

