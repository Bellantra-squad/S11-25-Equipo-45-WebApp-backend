"""Lead and related models (Category, LeadStatus, Tag, LeadTag)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Category(models.Model):
    """Lead categories."""

    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    color = models.CharField(_("color"), max_length=7, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        ordering = ["name"]

    def __str__(self):
        return self.name


class LeadStatus(models.Model):
    """Lead status/funnel stages."""

    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    color = models.CharField(_("color"), max_length=7, blank=True)
    order_position = models.IntegerField(_("order position"), default=0)
    is_active = models.BooleanField(_("is active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("lead status")
        verbose_name_plural = _("lead statuses")
        ordering = ["order_position", "name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Tags for leads and contacts."""

    name = models.CharField(_("name"), max_length=255, unique=True)
    description = models.TextField(_("description"), blank=True)
    color = models.CharField(_("color"), max_length=7, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("tag")
        verbose_name_plural = _("tags")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Lead(models.Model):
    """Core lead entity."""

    company_name = models.CharField(_("company name"), max_length=255)
    industry = models.CharField(_("industry"), max_length=255, blank=True)
    website = models.URLField(_("website"), blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
        verbose_name=_("category"),
    )
    status = models.ForeignKey(
        LeadStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
        verbose_name=_("status"),
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads",
        verbose_name=_("assigned to"),
    )
    is_client = models.BooleanField(_("is client"), default=False)
    lead_source = models.CharField(_("lead source"), max_length=255, blank=True)
    lead_score = models.IntegerField(_("lead score"), default=0)
    estimated_value = models.DecimalField(
        _("estimated value"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    notes = models.TextField(_("notes"), blank=True)
    last_contact_date = models.DateTimeField(_("last contact date"), null=True, blank=True)
    next_follow_up = models.DateTimeField(_("next follow up"), null=True, blank=True)
    converted_to_client_at = models.DateTimeField(_("converted to client at"), null=True, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    tags = models.ManyToManyField(Tag, through="LeadTag", related_name="leads")

    class Meta:
        verbose_name = _("lead")
        verbose_name_plural = _("leads")
        ordering = ["-created_at"]

    def __str__(self):
        return self.company_name

    def clean(self):
        """Validate lead data."""
        if self.website:
            validator = URLValidator()
            try:
                validator(self.website)
            except ValidationError:
                raise ValidationError({"website": _("Invalid URL format.")})


class LeadTag(models.Model):
    """Junction table for Lead-Tag many-to-many relationship."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="lead_tags")
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="lead_tags")
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("lead tag")
        verbose_name_plural = _("lead tags")
        unique_together = [["lead", "tag"]]

    def __str__(self):
        return f"{self.lead} - {self.tag}"

