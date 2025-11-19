"""Conversation and Message models related to Lead and Contact."""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from crm.leads.models.contact import Contact
from crm.leads.models.lead import Lead

User = get_user_model()


class Conversation(models.Model):
    """Conversations across different channels."""

    CHANNEL_CHOICES = [
        ("whatsapp", _("WhatsApp")),
        ("email", _("Email")),
        ("sms", _("SMS")),
        ("other", _("Other")),
    ]

    STATUS_CHOICES = [
        ("open", _("Open")),
        ("closed", _("Closed")),
        ("pending", _("Pending")),
        ("resolved", _("Resolved")),
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True,
        verbose_name=_("lead"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True,
        verbose_name=_("contact"),
    )
    channel = models.CharField(_("channel"), max_length=50, choices=CHANNEL_CHOICES)
    subject = models.CharField(_("subject"), max_length=255, blank=True)
    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="open")
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_conversations",
        verbose_name=_("assigned to"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("conversation")
        verbose_name_plural = _("conversations")
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return f"{self.get_channel_display()} - {self.subject or 'No Subject'}"


class Message(models.Model):
    """Individual messages within conversations."""

    SENDER_TYPE_CHOICES = [
        ("user", _("User")),
        ("contact", _("Contact")),
        ("system", _("System")),
    ]

    MESSAGE_TYPE_CHOICES = [
        ("text", _("Text")),
        ("image", _("Image")),
        ("file", _("File")),
        ("audio", _("Audio")),
        ("video", _("Video")),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("conversation"),
    )
    sender_type = models.CharField(_("sender type"), max_length=20, choices=SENDER_TYPE_CHOICES)
    sender_id = models.CharField(_("sender id"), max_length=255)
    content = models.TextField(_("content"))
    message_type = models.CharField(_("message type"), max_length=20, choices=MESSAGE_TYPE_CHOICES, default="text")
    external_message_id = models.CharField(_("external message id"), max_length=255, blank=True)
    is_read = models.BooleanField(_("is read"), default=False)
    sent_at = models.DateTimeField(_("sent at"), auto_now_add=True)
    delivered_at = models.DateTimeField(_("delivered at"), null=True, blank=True)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)

    class Meta:
        verbose_name = _("message")
        verbose_name_plural = _("messages")
        ordering = ["sent_at"]

    def __str__(self):
        return f"{self.sender_type} - {self.content[:50]}..."

