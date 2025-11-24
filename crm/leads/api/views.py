"""API viewsets for CRM leads app."""

from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from crm.core.utils.pagination import DefaultPageNumberPagination
from crm.leads.api.serializers import (
    ActivitySerializer,
    ApiCredentialSerializer,
    CategorySerializer,
    ContactSerializer,
    ConversationSerializer,
    EmailTemplateSerializer,
    LeadListSerializer,
    LeadSerializer,
    LeadStatusSerializer,
    MessageSerializer,
    SavedFilterSerializer,
    TagSerializer,
    TaskSerializer,
)
from crm.leads.models import (
    Activity,
    ApiCredential,
    Category,
    Contact,
    Conversation,
    EmailTemplate,
    Lead,
    LeadStatus,
    Message,
    SavedFilter,
    Tag,
    Task,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Category model."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    pagination_class = DefaultPageNumberPagination

class LeadStatusViewSet(viewsets.ModelViewSet):
    """ViewSet for LeadStatus model."""

    queryset = LeadStatus.objects.all()
    serializer_class = LeadStatusSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["order_position", "name", "created_at"]
    ordering = ["order_position", "name"]
    pagination_class = DefaultPageNumberPagination


class TagViewSet(viewsets.ModelViewSet):
    """ViewSet for Tag model."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    pagination_class = DefaultPageNumberPagination

class LeadViewSet(viewsets.ModelViewSet):
    """ViewSet for Lead model."""

    queryset = Lead.objects.select_related("category", "status", "assigned_to").prefetch_related(
        "tags", "contacts"
    )
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category", "status", "assigned_to", "is_client", "lead_source"]
    search_fields = ["company_name", "industry", "website", "notes"]
    ordering_fields = ["created_at", "updated_at", "lead_score", "estimated_value", "company_name"]
    ordering = ["-created_at"]
    pagination_class = DefaultPageNumberPagination

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == "list":
            return LeadListSerializer
        return LeadSerializer

    @action(detail=True, methods=["post"])
    def convert_to_client(self, request, pk=None):
        """Convert a lead to a client."""
        lead = self.get_object()
        lead.is_client = True
        lead.converted_to_client_at = timezone.now()
        lead.save()
        serializer = self.get_serializer(lead)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Assign lead to a user."""
        lead = self.get_object()
        user_id = request.data.get("user_id")
        if user_id:
            from crm.users.models import User

            try:
                user = User.objects.get(pk=user_id)
                lead.assigned_to = user
                lead.save()
                serializer = self.get_serializer(lead)
                return Response(serializer.data)
            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def contacts(self, request, pk=None):
        """Get all contacts for a lead."""
        lead = self.get_object()
        contacts = lead.contacts.all()
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def activities(self, request, pk=None):
        """Get all activities for a lead."""
        lead = self.get_object()
        activities = lead.activities.all()
        serializer = ActivitySerializer(activities, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def tasks(self, request, pk=None):
        """Get all tasks for a lead."""
        lead = self.get_object()
        tasks = lead.tasks.all()
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def conversations(self, request, pk=None):
        """Get all conversations for a lead."""
        lead = self.get_object()
        conversations = lead.conversations.all()
        serializer = ConversationSerializer(conversations, many=True)
        return Response(serializer.data)


class ContactViewSet(viewsets.ModelViewSet):
    """ViewSet for Contact model."""

    queryset = Contact.objects.select_related("lead").prefetch_related("tags")
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["lead", "is_primary", "is_decision_maker"]
    search_fields = ["first_name", "last_name", "email", "phone", "whatsapp_number", "position"]
    ordering_fields = ["first_name", "last_name", "created_at"]
    ordering = ["-is_primary", "first_name"]
    pagination_class = DefaultPageNumberPagination

    @action(detail=True, methods=["post", "delete"])
    def tags(self, request, pk=None):
        """Manage contact tags."""
        contact = self.get_object()
        if request.method == "POST":
            tag_ids = request.data.get("tag_ids", [])
            tags = Tag.objects.filter(pk__in=tag_ids)
            contact.tags.set(tags)
            serializer = self.get_serializer(contact)
            return Response(serializer.data)
        elif request.method == "DELETE":
            tag_id = request.data.get("tag_id")
            if tag_id:
                try:
                    tag = Tag.objects.get(pk=tag_id)
                    contact.tags.remove(tag)
                    serializer = self.get_serializer(contact)
                    return Response(serializer.data)
                except Tag.DoesNotExist:
                    return Response({"error": "Tag not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"error": "tag_id is required"}, status=status.HTTP_400_BAD_REQUEST)


class ActivityViewSet(viewsets.ModelViewSet):
    """ViewSet for Activity model."""

    queryset = Activity.objects.select_related("lead", "contact", "user")
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["lead", "contact", "user", "activity_type"]
    search_fields = ["description"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    pagination_class = DefaultPageNumberPagination

    def perform_create(self, serializer):
        """Set user to current user if not provided."""
        if not serializer.validated_data.get("user"):
            serializer.save(user=self.request.user)
        else:
            serializer.save()


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet for Task model."""

    queryset = Task.objects.select_related("lead", "contact", "assigned_to")
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["lead", "contact", "assigned_to", "task_type", "priority", "status"]
    search_fields = ["title", "description"]
    ordering_fields = ["due_date", "priority", "created_at", "status"]
    ordering = ["-due_date", "-created_at"]
    pagination_class = DefaultPageNumberPagination

    def get_queryset(self):
        """Filter tasks by current user if needed."""
        queryset = super().get_queryset()
        if self.request.query_params.get("my_tasks") == "true":
            queryset = queryset.filter(assigned_to=self.request.user)
        return queryset

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark task as completed."""
        task = self.get_object()
        task.status = "completed"
        task.completed_at = timezone.now()
        task.save()
        serializer = self.get_serializer(task)
        return Response(serializer.data)


class ConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for Conversation model."""

    queryset = Conversation.objects.select_related("lead", "contact", "assigned_to").prefetch_related(
        "messages"
    )
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["lead", "contact", "channel", "status", "assigned_to"]
    search_fields = ["subject"]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-updated_at", "-created_at"]
    pagination_class = DefaultPageNumberPagination

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        """Get or create messages for a conversation."""
        conversation = self.get_object()
        if request.method == "GET":
            messages = conversation.messages.all()
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)
        elif request.method == "POST":
            serializer = MessageSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(conversation=conversation)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for Message model."""

    queryset = Message.objects.select_related("conversation")
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["conversation", "sender_type", "message_type", "is_read"]
    search_fields = ["content"]
    ordering_fields = ["sent_at"]
    ordering = ["sent_at"]
    pagination_class = DefaultPageNumberPagination

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """Mark message as read."""
        message = self.get_object()
        message.is_read = True
        message.read_at = timezone.now()
        message.save()
        serializer = self.get_serializer(message)
        return Response(serializer.data)


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for EmailTemplate model."""

    queryset = EmailTemplate.objects.select_related("created_by")
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["template_type", "is_active", "created_by"]
    search_fields = ["name", "subject", "body"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    pagination_class = DefaultPageNumberPagination

    def perform_create(self, serializer):
        """Set created_by to current user if not provided."""
        if not serializer.validated_data.get("created_by"):
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Send email using template."""
        template = self.get_object()
        # This will be implemented in the email service
        return Response(
            {"message": "Email sending will be implemented in email service"},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class SavedFilterViewSet(viewsets.ModelViewSet):
    """ViewSet for SavedFilter model."""

    serializer_class = SavedFilterSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    pagination_class = DefaultPageNumberPagination

    def get_queryset(self):
        """Return filters for current user or public filters."""
        return SavedFilter.objects.filter(
            Q(user=self.request.user) | Q(is_public=True)
        ).select_related("user")

    def perform_create(self, serializer):
        """Set user to current user."""
        serializer.save(user=self.request.user)


class ApiCredentialViewSet(viewsets.ModelViewSet):
    """ViewSet for ApiCredential model."""

    queryset = ApiCredential.objects.all()
    serializer_class = ApiCredentialSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["credential_type", "is_active", "service_name"]
    search_fields = ["service_name"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    pagination_class = DefaultPageNumberPagination

