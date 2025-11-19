"""Django admin configuration for leads app."""

from django.contrib import admin

from crm.leads.models import (
    Activity,
    ApiCredential,
    Category,
    Contact,
    ContactTag,
    Conversation,
    EmailTemplate,
    Lead,
    LeadStatus,
    LeadTag,
    Message,
    SavedFilter,
    Tag,
    Task,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for Category model."""

    list_display = ["name", "description", "color", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "description"]
    ordering = ["name"]


@admin.register(LeadStatus)
class LeadStatusAdmin(admin.ModelAdmin):
    """Admin for LeadStatus model."""

    list_display = ["name", "order_position", "color", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["order_position", "name"]
    list_editable = ["order_position", "is_active"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin for Tag model."""

    list_display = ["name", "description", "color", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "description"]
    ordering = ["name"]


class ContactInline(admin.TabularInline):
    """Inline admin for Contact model."""

    model = Contact
    extra = 1
    fields = ["first_name", "last_name", "email", "phone", "whatsapp_number", "is_primary", "is_decision_maker"]


class TaskInline(admin.TabularInline):
    """Inline admin for Task model."""

    model = Task
    extra = 0
    fields = ["title", "assigned_to", "priority", "status", "due_date"]
    readonly_fields = ["created_at"]


class ActivityInline(admin.TabularInline):
    """Inline admin for Activity model."""

    model = Activity
    extra = 0
    fields = ["user", "activity_type", "description", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    """Admin for Lead model."""

    list_display = [
        "company_name",
        "status",
        "category",
        "assigned_to",
        "is_client",
        "lead_score",
        "lead_source",
        "created_at",
    ]
    list_filter = ["is_client", "category", "status", "lead_source", "assigned_to", "created_at"]
    search_fields = ["company_name", "industry", "website", "notes"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at", "converted_to_client_at"]
    inlines = [ContactInline, TaskInline, ActivityInline]
    fieldsets = (
        ("Basic Information", {"fields": ("company_name", "industry", "website", "category", "status")}),
        ("Assignment", {"fields": ("assigned_to", "is_client", "lead_source")}),
        ("Metrics", {"fields": ("lead_score", "estimated_value")}),
        ("Dates", {"fields": ("last_contact_date", "next_follow_up", "converted_to_client_at")}),
        ("Additional", {"fields": ("notes", "created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("category", "status", "assigned_to")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Admin for Contact model."""

    list_display = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "lead",
        "is_primary",
        "is_decision_maker",
        "created_at",
    ]
    list_filter = ["is_primary", "is_decision_maker", "lead", "created_at"]
    search_fields = ["first_name", "last_name", "email", "phone", "whatsapp_number", "position"]
    ordering = ["-is_primary", "first_name", "last_name"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("lead")


@admin.register(LeadTag)
class LeadTagAdmin(admin.ModelAdmin):
    """Admin for LeadTag junction model."""

    list_display = ["lead", "tag", "created_at"]
    list_filter = ["created_at", "tag"]
    search_fields = ["lead__company_name", "tag__name"]
    ordering = ["-created_at"]


@admin.register(ContactTag)
class ContactTagAdmin(admin.ModelAdmin):
    """Admin for ContactTag junction model."""

    list_display = ["contact", "tag", "created_at"]
    list_filter = ["created_at", "tag"]
    search_fields = ["contact__first_name", "contact__last_name", "tag__name"]
    ordering = ["-created_at"]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    """Admin for Activity model."""

    list_display = ["activity_type", "lead", "contact", "user", "created_at"]
    list_filter = ["activity_type", "created_at", "user"]
    search_fields = ["description"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at"]

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("lead", "contact", "user")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin for Task model."""

    list_display = [
        "title",
        "lead",
        "contact",
        "assigned_to",
        "priority",
        "status",
        "due_date",
        "completed_at",
    ]
    list_filter = ["priority", "status", "task_type", "assigned_to", "due_date", "created_at"]
    search_fields = ["title", "description"]
    ordering = ["-due_date", "-created_at"]
    readonly_fields = ["created_at", "updated_at", "completed_at"]
    list_editable = ["status", "priority"]

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("lead", "contact", "assigned_to")


class MessageInline(admin.TabularInline):
    """Inline admin for Message model."""

    model = Message
    extra = 0
    fields = ["sender_type", "sender_id", "content", "is_read", "sent_at"]
    readonly_fields = ["sent_at"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Admin for Conversation model."""

    list_display = ["channel", "subject", "lead", "contact", "status", "assigned_to", "updated_at"]
    list_filter = ["channel", "status", "assigned_to", "created_at", "updated_at"]
    search_fields = ["subject"]
    ordering = ["-updated_at", "-created_at"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [MessageInline]

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("lead", "contact", "assigned_to")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin for Message model."""

    list_display = ["conversation", "sender_type", "content_preview", "is_read", "sent_at"]
    list_filter = ["sender_type", "message_type", "is_read", "sent_at"]
    search_fields = ["content", "external_message_id"]
    ordering = ["sent_at"]
    readonly_fields = ["sent_at", "delivered_at", "read_at"]

    def content_preview(self, obj):
        """Show content preview."""
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = "Content"

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("conversation")


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """Admin for EmailTemplate model."""

    list_display = ["name", "template_type", "subject", "is_active", "created_by", "created_at"]
    list_filter = ["template_type", "is_active", "created_by", "created_at"]
    search_fields = ["name", "subject", "body"]
    ordering = ["name"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("created_by")


@admin.register(SavedFilter)
class SavedFilterAdmin(admin.ModelAdmin):
    """Admin for SavedFilter model."""

    list_display = ["name", "user", "is_public", "created_at"]
    list_filter = ["is_public", "created_at"]
    search_fields = ["name"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related("user")


@admin.register(ApiCredential)
class ApiCredentialAdmin(admin.ModelAdmin):
    """Admin for ApiCredential model."""

    list_display = ["service_name", "credential_type", "is_active", "expires_at", "created_at"]
    list_filter = ["credential_type", "is_active", "created_at"]
    search_fields = ["service_name"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["is_active"]

    fieldsets = (
        ("Basic Information", {"fields": ("service_name", "credential_type", "is_active")}),
        (
            "Credentials",
            {
                "fields": (
                    "api_key",
                    "api_secret",
                    "access_token",
                    "refresh_token",
                ),
            },
        ),
        (
            "WhatsApp Configuration",
            {
                "fields": (
                    "phone_number_id",
                    "business_account_id",
                    "webhook_url",
                ),
            },
        ),
        (
            "Additional",
            {
                "fields": (
                    "additional_config",
                    "expires_at",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )
