"""Contact models related to Lead."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from crm.leads.models.lead import Lead, Tag


class Contact(models.Model):
    """Contacts linked to leads."""

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="contacts",
        verbose_name=_("lead"),
    )
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    email = models.EmailField(_("email"), blank=True)
    phone = models.CharField(_("phone"), max_length=20, blank=True)
    whatsapp_number = models.CharField(_("whatsapp number"), max_length=20, blank=True)
    position = models.CharField(_("position"), max_length=255, blank=True)
    department = models.CharField(_("department"), max_length=255, blank=True)
    is_primary = models.BooleanField(_("is primary"), default=False)
    is_decision_maker = models.BooleanField(_("is decision maker"), default=False)
    notes = models.TextField(_("notes"), blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    tags = models.ManyToManyField(Tag, through="ContactTag", related_name="contacts")

    class Meta:
        verbose_name = _("contact")
        verbose_name_plural = _("contacts")
        ordering = ["-is_primary", "first_name", "last_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        """Validate contact data."""
        if not self.email and not self.phone and not self.whatsapp_number:
            raise ValidationError(_("Contact must have at least email, phone, or WhatsApp number."))


class ContactTag(models.Model):
    """Junction table for Contact-Tag many-to-many relationship."""

    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="contact_tags")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="contact_tags")
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("contact tag")
        verbose_name_plural = _("contact tags")
        unique_together = [["contact", "tag"]]

    def __str__(self):
        return f"{self.contact} - {self.tag}"

