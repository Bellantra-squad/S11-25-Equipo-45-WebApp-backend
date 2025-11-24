"""Task models related to Lead and Contact."""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from crm.leads.models.contact import Contact
from crm.leads.models.lead import Lead

User = get_user_model()


class Task(models.Model):
    """Tasks assigned to users."""

    PRIORITY_CHOICES = [
        ("low", _("Low")),
        ("medium", _("Medium")),
        ("high", _("High")),
        ("urgent", _("Urgent")),
    ]

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("in_progress", _("In Progress")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
    ]

    TASK_TYPES = [
        ("call", _("Call")),
        ("email", _("Email")),
        ("meeting", _("Meeting")),
        ("follow_up", _("Follow Up")),
        ("other", _("Other")),
    ]

    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
        verbose_name=_("lead"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="tasks",
        null=True,
        blank=True,
        verbose_name=_("contact"),
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        verbose_name=_("assigned to"),
    )
    task_type = models.CharField(_("task type"), max_length=50, choices=TASK_TYPES, default="other")
    priority = models.CharField(_("priority"), max_length=20, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="pending")
    due_date = models.DateTimeField(_("due date"), null=True, blank=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("task")
        verbose_name_plural = _("tasks")
        ordering = ["-due_date", "-created_at"]

    def __str__(self):
        return self.title

