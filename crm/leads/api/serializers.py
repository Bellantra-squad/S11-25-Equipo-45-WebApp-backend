"""Serializers for CRM leads app."""

from rest_framework import serializers

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
from crm.users.models import User


class UserBasicSerializer(serializers.ModelSerializer[User]):
    """Basic user serializer for nested relationships."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role"]
        read_only_fields = ["id"]


class CategorySerializer(serializers.ModelSerializer[Category]):
    """Category serializer."""

    class Meta:
        model = Category
        fields = ["id", "name", "description", "color", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeadStatusSerializer(serializers.ModelSerializer[LeadStatus]):
    """Lead status serializer."""

    class Meta:
        model = LeadStatus
        fields = [
            "id",
            "name",
            "description",
            "color",
            "order_position",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TagSerializer(serializers.ModelSerializer[Tag]):
    """Tag serializer."""

    class Meta:
        model = Tag
        fields = ["id", "name", "description", "color", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ContactBasicSerializer(serializers.ModelSerializer[Contact]):
    """Basic contact serializer for nested relationships."""

    class Meta:
        model = Contact
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "whatsapp_number",
            "position",
            "is_primary",
            "is_decision_maker",
        ]
        read_only_fields = ["id"]


class ContactSerializer(serializers.ModelSerializer[Contact]):
    """Full contact serializer with relationships."""

    lead = serializers.PrimaryKeyRelatedField(queryset=Lead.objects.all())
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), source="tags", write_only=True, required=False
    )

    class Meta:
        model = Contact
        fields = [
            "id",
            "lead",
            "first_name",
            "last_name",
            "email",
            "phone",
            "whatsapp_number",
            "position",
            "department",
            "is_primary",
            "is_decision_maker",
            "notes",
            "tags",
            "tag_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        """Create contact with tags."""
        tags = validated_data.pop("tags", [])
        contact = Contact.objects.create(**validated_data)
        if tags:
            contact.tags.set(tags)
        return contact

    def update(self, instance, validated_data):
        """Update contact with tags."""
        tags = validated_data.pop("tags", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        return instance


class LeadListSerializer(serializers.ModelSerializer[Lead]):
    """Lead serializer for list views (optimized)."""

    category = CategorySerializer(read_only=True)
    status = LeadStatusSerializer(read_only=True)
    assigned_to = UserBasicSerializer(read_only=True)
    contacts_count = serializers.IntegerField(source="contacts.count", read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id",
            "company_name",
            "industry",
            "website",
            "category",
            "status",
            "assigned_to",
            "is_client",
            "lead_source",
            "lead_score",
            "estimated_value",
            "contacts_count",
            "tags",
            "last_contact_date",
            "next_follow_up",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeadSerializer(serializers.ModelSerializer[Lead]):
    """Full lead serializer with nested relationships."""

    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source="category", write_only=True, required=False
    )
    status = LeadStatusSerializer(read_only=True)
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=LeadStatus.objects.all(), source="status", write_only=True, required=False
    )
    assigned_to = UserBasicSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="assigned_to", write_only=True, required=False
    )
    contacts = ContactBasicSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), source="tags", write_only=True, required=False
    )

    class Meta:
        model = Lead
        fields = [
            "id",
            "company_name",
            "industry",
            "website",
            "category",
            "category_id",
            "status",
            "status_id",
            "assigned_to",
            "assigned_to_id",
            "is_client",
            "lead_source",
            "lead_score",
            "estimated_value",
            "notes",
            "contacts",
            "tags",
            "tag_ids",
            "last_contact_date",
            "next_follow_up",
            "converted_to_client_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "converted_to_client_at"]

    def create(self, validated_data):
        """Create lead with tags."""
        tags = validated_data.pop("tags", [])
        lead = Lead.objects.create(**validated_data)
        if tags:
            lead.tags.set(tags)
        return lead

    def update(self, instance, validated_data):
        """Update lead with tags."""
        tags = validated_data.pop("tags", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        return instance


class ActivitySerializer(serializers.ModelSerializer[Activity]):
    """Activity serializer."""

    lead = serializers.PrimaryKeyRelatedField(queryset=Lead.objects.all(), required=False, allow_null=True)
    contact = serializers.PrimaryKeyRelatedField(queryset=Contact.objects.all(), required=False, allow_null=True)
    user = UserBasicSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="user", write_only=True, required=False
    )

    class Meta:
        model = Activity
        fields = [
            "id",
            "lead",
            "contact",
            "user",
            "user_id",
            "activity_type",
            "description",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TaskSerializer(serializers.ModelSerializer[Task]):
    """Task serializer."""

    lead = serializers.PrimaryKeyRelatedField(queryset=Lead.objects.all(), required=False, allow_null=True)
    contact = serializers.PrimaryKeyRelatedField(queryset=Contact.objects.all(), required=False, allow_null=True)
    assigned_to = UserBasicSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="assigned_to", write_only=True, required=False
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "lead",
            "contact",
            "assigned_to",
            "assigned_to_id",
            "task_type",
            "priority",
            "status",
            "due_date",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MessageBasicSerializer(serializers.ModelSerializer[Message]):
    """Basic message serializer for nested relationships."""

    class Meta:
        model = Message
        fields = [
            "id",
            "sender_type",
            "sender_id",
            "content",
            "message_type",
            "is_read",
            "sent_at",
            "delivered_at",
            "read_at",
        ]
        read_only_fields = ["id", "sent_at"]


class MessageSerializer(serializers.ModelSerializer[Message]):
    """Full message serializer."""

    conversation = serializers.PrimaryKeyRelatedField(queryset=Conversation.objects.all())

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender_type",
            "sender_id",
            "content",
            "message_type",
            "external_message_id",
            "is_read",
            "sent_at",
            "delivered_at",
            "read_at",
        ]
        read_only_fields = ["id", "sent_at"]


class ConversationSerializer(serializers.ModelSerializer[Conversation]):
    """Conversation serializer with messages."""

    lead = serializers.PrimaryKeyRelatedField(queryset=Lead.objects.all(), required=False, allow_null=True)
    contact = serializers.PrimaryKeyRelatedField(queryset=Contact.objects.all(), required=False, allow_null=True)
    assigned_to = UserBasicSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="assigned_to", write_only=True, required=False
    )
    messages = MessageBasicSerializer(many=True, read_only=True)
    messages_count = serializers.IntegerField(source="messages.count", read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "lead",
            "contact",
            "channel",
            "subject",
            "status",
            "assigned_to",
            "assigned_to_id",
            "messages",
            "messages_count",
            "unread_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_unread_count(self, obj):
        """Get count of unread messages."""
        return obj.messages.filter(is_read=False).count()


class EmailTemplateSerializer(serializers.ModelSerializer[EmailTemplate]):
    """Email template serializer."""

    created_by = UserBasicSerializer(read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source="created_by", write_only=True, required=False
    )

    class Meta:
        model = EmailTemplate
        fields = [
            "id",
            "name",
            "subject",
            "body",
            "template_type",
            "is_active",
            "created_by",
            "created_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SavedFilterSerializer(serializers.ModelSerializer[SavedFilter]):
    """Saved filter serializer."""

    user = UserBasicSerializer(read_only=True)

    class Meta:
        model = SavedFilter
        fields = [
            "id",
            "user",
            "name",
            "filter_config",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class ApiCredentialSerializer(serializers.ModelSerializer[ApiCredential]):
    """API credential serializer."""

    class Meta:
        model = ApiCredential
        fields = [
            "id",
            "service_name",
            "credential_type",
            "api_key",
            "api_secret",
            "access_token",
            "refresh_token",
            "webhook_url",
            "phone_number_id",
            "business_account_id",
            "additional_config",
            "is_active",
            "expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "api_key": {"write_only": True},
            "api_secret": {"write_only": True},
            "access_token": {"write_only": True},
            "refresh_token": {"write_only": True},
        }

