"""Saved filter models related to User."""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class SavedFilter(models.Model):
    """User-defined saved filters."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="saved_filters",
        verbose_name=_("user"),
    )
    name = models.CharField(_("name"), max_length=255)
    filter_config = models.JSONField(_("filter config"), default=dict)
    is_public = models.BooleanField(_("is public"), default=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("saved filter")
        verbose_name_plural = _("saved filters")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.user.email})"

