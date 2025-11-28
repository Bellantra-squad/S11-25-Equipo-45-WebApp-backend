"""API viewsets for CRM leads app."""

from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
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
from crm.leads.services.email_service import EmailService


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

    @extend_schema(
        summary="Convertir lead a cliente",
        description=(
            "Convierte un lead en cliente. Marca el lead como cliente y establece "
            "la fecha de conversión. Una vez convertido, el lead no puede revertirse."
        ),
        tags=["leads"],
        request=None,
        responses={
            200: LeadSerializer,
            404: {"description": "Lead no encontrado"},
        },
    )
    @action(detail=True, methods=["post"])
    def convert_to_client(self, request, pk=None):
        """Convert a lead to a client."""
        lead = self.get_object()
        lead.is_client = True
        lead.converted_to_client_at = timezone.now()
        lead.save()
        serializer = self.get_serializer(lead)
        return Response(serializer.data)

    @extend_schema(
        summary="Asignar lead a usuario",
        description=(
            "Asigna un lead a un usuario específico del sistema. El usuario asignado "
            "será responsable del seguimiento y gestión del lead."
        ),
        tags=["leads"],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "ID del usuario al que se asignará el lead",
                    }
                },
                "required": ["user_id"],
            }
        },
        responses={
            200: LeadSerializer,
            400: {"description": "user_id es requerido"},
            404: {"description": "Lead o usuario no encontrado"},
        },
    )
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

    @extend_schema(
        summary="Obtener contactos del lead",
        description=(
            "Retorna todos los contactos asociados a un lead específico. "
            "Incluye información completa de cada contacto como nombre, email, teléfono, "
            "posición y si es contacto principal o tomador de decisiones."
        ),
        tags=["leads"],
        parameters=[
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Número de página para paginación",
                required=False,
            ),
            OpenApiParameter(
                name="page_size",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Tamaño de página para paginación",
                required=False,
            ),
        ],
        responses={
            200: ContactSerializer(many=True),
            404: {"description": "Lead no encontrado"},
        },
    )
    @action(detail=True, methods=["get"])
    def contacts(self, request, pk=None):
        """Get all contacts for a lead."""
        lead = self.get_object()
        contacts = lead.contacts.all()
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Obtener actividades del lead",
        description=(
            "Retorna todas las actividades registradas para un lead específico. "
            "Incluye llamadas, reuniones, emails y otras interacciones con el lead."
        ),
        tags=["leads"],
        parameters=[
            OpenApiParameter(
                name="activity_type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filtrar por tipo de actividad",
                required=False,
            ),
            OpenApiParameter(
                name="user",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filtrar por ID de usuario",
                required=False,
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Campo para ordenar (created_at, -created_at)",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Número de página para paginación",
                required=False,
            ),
        ],
        responses={
            200: ActivitySerializer(many=True),
            404: {"description": "Lead no encontrado"},
        },
    )
    @action(detail=True, methods=["get"])
    def activities(self, request, pk=None):
        """Get all activities for a lead."""
        lead = self.get_object()
        activities = lead.activities.all()
        serializer = ActivitySerializer(activities, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Obtener tareas del lead",
        description=(
            "Retorna todas las tareas asociadas a un lead específico. "
            "Incluye tareas pendientes, en progreso y completadas con sus fechas de vencimiento."
        ),
        tags=["leads"],
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filtrar por estado (pending, in_progress, completed, cancelled)",
                required=False,
            ),
            OpenApiParameter(
                name="priority",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filtrar por prioridad (low, medium, high, urgent)",
                required=False,
            ),
            OpenApiParameter(
                name="task_type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filtrar por tipo de tarea",
                required=False,
            ),
            OpenApiParameter(
                name="assigned_to",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filtrar por ID de usuario asignado",
                required=False,
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Campo para ordenar (due_date, priority, created_at, status)",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Número de página para paginación",
                required=False,
            ),
        ],
        responses={
            200: TaskSerializer(many=True),
            404: {"description": "Lead no encontrado"},
        },
    )
    @action(detail=True, methods=["get"])
    def tasks(self, request, pk=None):
        """Get all tasks for a lead."""
        lead = self.get_object()
        tasks = lead.tasks.all()
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Obtener conversaciones del lead",
        description=(
            "Retorna todas las conversaciones asociadas a un lead específico. "
            "Incluye conversaciones de WhatsApp, Email y otros canales de comunicación, "
            "junto con sus mensajes y estado."
        ),
        tags=["leads"],
        parameters=[
            OpenApiParameter(
                name="channel",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filtrar por canal (whatsapp, email, etc.)",
                required=False,
            ),
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filtrar por estado de conversación",
                required=False,
            ),
            OpenApiParameter(
                name="assigned_to",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filtrar por ID de usuario asignado",
                required=False,
            ),
            OpenApiParameter(
                name="search",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Búsqueda por asunto",
                required=False,
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Campo para ordenar (created_at, updated_at, -created_at, -updated_at)",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Número de página para paginación",
                required=False,
            ),
        ],
        responses={
            200: ConversationSerializer(many=True),
            404: {"description": "Lead no encontrado"},
        },
    )
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

    @extend_schema(
        summary="Gestionar etiquetas del contacto",
        description=(
            "Gestiona las etiquetas de un contacto. "
            "POST: Asigna múltiples etiquetas al contacto (reemplaza las existentes). "
            "DELETE: Elimina una etiqueta específica del contacto."
        ),
        tags=["contacts"],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "tag_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Lista de IDs de etiquetas (requerido para POST)",
                    },
                    "tag_id": {
                        "type": "integer",
                        "description": "ID de la etiqueta a eliminar (requerido para DELETE)",
                    },
                },
            }
        },
        responses={
            200: ContactSerializer,
            400: {"description": "Datos inválidos o faltantes (tag_ids requerido para POST, tag_id requerido para DELETE)"},
            404: {"description": "Contacto o etiqueta no encontrado"},
        },
    )
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

    @extend_schema(
        summary="Marcar tarea como completada",
        description=(
            "Marca una tarea como completada. Actualiza el estado a 'completed' "
            "y establece la fecha de completado con la fecha y hora actual."
        ),
        tags=["tasks"],
        request=None,
        responses={
            200: TaskSerializer,
            404: {"description": "Tarea no encontrada"},
        },
    )
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

    @extend_schema(
        summary="Obtener o crear mensajes de conversación",
        description=(
            "GET: Retorna todos los mensajes de una conversación específica, "
            "ordenados por fecha de envío. "
            "POST: Crea un nuevo mensaje en la conversación. El campo 'conversation' "
            "no debe incluirse en el request ya que se obtiene de la URL."
        ),
        tags=["conversations"],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "sender_type": {
                        "type": "string",
                        "description": "Tipo de remitente (user, contact)",
                    },
                    "sender_id": {
                        "type": "integer",
                        "description": "ID del remitente",
                    },
                    "content": {
                        "type": "string",
                        "description": "Contenido del mensaje",
                    },
                    "message_type": {
                        "type": "string",
                        "description": "Tipo de mensaje",
                    },
                    "external_message_id": {
                        "type": "string",
                        "description": "ID externo del mensaje (opcional)",
                    },
                    "is_read": {
                        "type": "boolean",
                        "description": "Si el mensaje ha sido leído",
                    },
                },
                "required": ["sender_type", "sender_id", "content"],
            }
        },
        parameters=[
            OpenApiParameter(
                name="sender_type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filtrar por tipo de remitente (user, contact) - solo GET",
                required=False,
            ),
            OpenApiParameter(
                name="message_type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filtrar por tipo de mensaje - solo GET",
                required=False,
            ),
            OpenApiParameter(
                name="is_read",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="Filtrar por estado de lectura - solo GET",
                required=False,
            ),
            OpenApiParameter(
                name="ordering",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Campo para ordenar (sent_at, -sent_at) - solo GET",
                required=False,
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Número de página para paginación - solo GET",
                required=False,
            ),
        ],
        responses={
            200: MessageSerializer(many=True),
            201: MessageSerializer,
            400: {"description": "Datos inválidos"},
            404: {"description": "Conversación no encontrada"},
        },
    )
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

    @extend_schema(
        summary="Marcar mensaje como leído",
        description=(
            "Marca un mensaje como leído. Actualiza el campo is_read a True "
            "y establece la fecha de lectura con la fecha y hora actual."
        ),
        tags=["messages"],
        responses={
            200: MessageSerializer,
            404: {"description": "Mensaje no encontrado"},
        },
    )
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

    @extend_schema(
        summary="Enviar email usando plantilla",
        description=(
            "Envía un email usando una plantilla específica. "
            "Esta funcionalidad será implementada en el servicio de email. "
            "Actualmente retorna un error 501 (No implementado)."
        ),
        tags=["templates"],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "format": "email",
                        "description": "Dirección de email del destinatario",
                    },
                    "lead_id": {
                        "type": "integer",
                        "description": "ID del lead asociado (opcional)",
                    },
                    "contact_id": {
                        "type": "integer",
                        "description": "ID del contacto asociado (opcional)",
                    },
                },
            }
        },
        responses={
            200: {"description": "Email enviado exitosamente"},
            501: {"description": "Funcionalidad no implementada aún"},
            404: {"description": "Plantilla no encontrada"},
        },
    )
    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Send email using template."""
        self.get_object()  # Validate template exists
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

    @action(detail=False, methods=["post"], url_path="test-brevo")
    def test_brevo(self, request):
        """
        Test Brevo email sending.

        Sends a test email via Brevo API to verify configuration.
        """
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email address is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Try to get active Brevo credential or use settings
        credential = ApiCredential.objects.filter(
            credential_type="email_brevo", is_active=True
        ).first()

        # Initialize email service with Brevo
        email_service = EmailService(api_credential=credential, use_brevo=True)

        # Prepare test email content
        html_body = """
        <html>
            <body>
                <h1>Email de Prueba - Brevo</h1>
                <p>Este es un email de prueba enviado desde el sistema CRM.</p>
                <p>Si recibes este correo, la configuración de Brevo está funcionando correctamente.</p>
                <hr>
                <p><small>Enviado desde: CRM System</small></p>
            </body>
        </html>
        """
        plain_body = (
            "Este es un email de prueba enviado desde el sistema CRM. "
            "Si recibes este correo, la configuración de Brevo está funcionando correctamente."
        )

        # Send test email
        result = email_service.send_email(
            to=[email],
            subject="[TEST] Email de Prueba - Brevo CRM",
            body=plain_body,
            html_body=html_body,
        )

        if result.get("success"):
            return Response(
                {
                    "message": "Email de prueba enviado exitosamente",
                    "email": email,
                    "message_id": result.get("message_id"),
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "error": "Error al enviar email de prueba",
                    "details": result.get("error"),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

