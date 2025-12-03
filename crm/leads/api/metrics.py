"""Metrics dashboard API endpoints."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from crm.leads.models import Contact, Lead, Message, Task


def parse_date_range(
    start_date: Optional[str], end_date: Optional[str]
) -> Tuple[datetime, datetime]:
    """
    Parse date range from query parameters.

    Args:
        start_date: Start date string (YYYY-MM-DD format) or None
        end_date: End date string (YYYY-MM-DD format) or None

    Returns:
        Tuple of (start_datetime, end_datetime) as timezone-aware datetimes

    Behavior:
        - If both are None: returns last 3 months range
        - If both are the same date: returns that day (00:00 to 23:59)
        - Otherwise: returns the specified range
    """
    now = timezone.now()

    if not start_date and not end_date:
        # Default: last 3 months
        end_dt = now
        start_dt = now - timedelta(days=90)
        return start_dt, end_dt

    # Parse dates
    try:
        if start_date:
            start_dt = timezone.make_aware(
                datetime.strptime(start_date, "%Y-%m-%d")
            )
        else:
            start_dt = now - timedelta(days=90)

        if end_date:
            end_dt = timezone.make_aware(
                datetime.strptime(end_date, "%Y-%m-%d")
            )
        else:
            end_dt = now
    except ValueError:
        # Invalid date format, use defaults
        start_dt = now - timedelta(days=90)
        end_dt = now
        return start_dt, end_dt

    # If same date, set end to end of day
    if start_date == end_date:
        end_dt = end_dt.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

    # Ensure end_date includes the full day
    if end_date and start_date != end_date:
        end_dt = end_dt.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

    return start_dt, end_dt


# Common OpenAPI parameters for date range
DATE_RANGE_PARAMETERS = [
    OpenApiParameter(
        name="start_date",
        type=str,
        location=OpenApiParameter.QUERY,
        description=(
            "Fecha de inicio del rango (formato: YYYY-MM-DD). "
            "Por defecto: hace 3 meses"
        ),
        required=False,
    ),
    OpenApiParameter(
        name="end_date",
        type=str,
        location=OpenApiParameter.QUERY,
        description=(
            "Fecha de fin del rango (formato: YYYY-MM-DD). Por defecto: hoy. "
            "Si es igual a start_date, filtra solo ese día"
        ),
        required=False,
    ),
]


class MetricsViewSet(ViewSet):
    """Metrics dashboard API."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Obtener métricas del dashboard principal",
        description=(
            "Retorna un resumen completo de métricas para el dashboard. "
            "Incluye contactos activos, mensajes, tasa de respuesta, "
            "leads por estado, conversión, actividades y tareas pendientes. "
            "Por defecto: últimos 3 meses. "
            "Si start_date=end_date, filtra ese día."
        ),
        tags=["metrics"],
        parameters=DATE_RANGE_PARAMETERS,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "active_contacts": {"type": "integer"},
                    "messages_sent": {"type": "integer"},
                    "messages_received": {"type": "integer"},
                    "response_rate": {"type": "number"},
                    "leads_by_status": {"type": "array"},
                    "conversion_rate": {"type": "number"},
                    "total_leads": {"type": "integer"},
                    "converted_leads": {"type": "integer"},
                    "recent_activities": {"type": "integer"},
                    "pending_tasks": {"type": "integer"},
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def dashboard(self, request) -> Response:
        """Get main dashboard metrics."""
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        start_dt, end_dt = parse_date_range(start_date, end_date)

        # Active contacts (contacts with recent activity)
        active_contacts = Contact.objects.filter(
            Q(
                activities__created_at__gte=start_dt,
                activities__created_at__lte=end_dt,
            )
            | Q(
                conversations__updated_at__gte=start_dt,
                conversations__updated_at__lte=end_dt,
            )
        ).distinct().count()

        # Messages sent in period
        messages_sent = Message.objects.filter(
            sender_type="user", sent_at__gte=start_dt, sent_at__lte=end_dt
        ).count()

        # Total messages (for response rate calculation)
        total_messages = Message.objects.filter(
            sent_at__gte=start_dt, sent_at__lte=end_dt
        ).count()
        messages_received = total_messages - messages_sent
        if messages_sent > 0:
            response_rate = messages_received / messages_sent * 100
        else:
            response_rate = 0

        # Leads by status (filtered by created_at in period)
        leads_by_status = (
            Lead.objects.filter(
                created_at__gte=start_dt, created_at__lte=end_dt
            )
            .values("status__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Conversion rate (for leads created in period)
        total_leads = Lead.objects.filter(
            created_at__gte=start_dt, created_at__lte=end_dt
        ).count()
        converted_leads = Lead.objects.filter(
            is_client=True, created_at__gte=start_dt, created_at__lte=end_dt
        ).count()
        if total_leads > 0:
            conversion_rate = converted_leads / total_leads * 100
        else:
            conversion_rate = 0

        # Recent activity count
        recent_activities = Contact.objects.filter(
            activities__created_at__gte=start_dt,
            activities__created_at__lte=end_dt,
        ).count()

        # Pending tasks
        pending_tasks = Task.objects.filter(
            status__in=["pending", "in_progress"], assigned_to=request.user
        ).count()

        data: Dict[str, Any] = {
            "active_contacts": active_contacts,
            "messages_sent": messages_sent,
            "messages_received": messages_received,
            "response_rate": round(response_rate, 2),
            "leads_by_status": list(leads_by_status),
            "conversion_rate": round(conversion_rate, 2),
            "total_leads": total_leads,
            "converted_leads": converted_leads,
            "recent_activities": recent_activities,
            "pending_tasks": pending_tasks,
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d"),
        }

        return Response(data)

    @extend_schema(
        summary="Obtener conteo de contactos activos",
        description=(
            "Retorna el número de contactos activos en un período. "
            "Un contacto es activo si tiene actividades o conversaciones "
            "actualizadas en el período. Por defecto: últimos 3 meses. "
            "Si start_date=end_date, filtra solo ese día."
        ),
        tags=["metrics"],
        parameters=DATE_RANGE_PARAMETERS,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Número de contactos activos",
                    },
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def contacts_active(self, request) -> Response:
        """Get active contacts count."""
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        start_dt, end_dt = parse_date_range(start_date, end_date)

        active_contacts = Contact.objects.filter(
            Q(
                activities__created_at__gte=start_dt,
                activities__created_at__lte=end_dt,
            )
            | Q(
                conversations__updated_at__gte=start_dt,
                conversations__updated_at__lte=end_dt,
            )
        ).distinct().count()

        return Response({
            "count": active_contacts,
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d"),
        })

    @extend_schema(
        summary="Obtener conteo de mensajes enviados",
        description=(
            "Retorna el número de mensajes enviados por usuarios en un "
            "período. Incluye un desglose diario de mensajes enviados para "
            "análisis de tendencias. Por defecto: últimos 3 meses. "
            "Si start_date=end_date, filtra solo ese día."
        ),
        tags=["metrics"],
        parameters=DATE_RANGE_PARAMETERS,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Total de mensajes enviados",
                    },
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                    "by_day": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "day": {"type": "string", "format": "date"},
                                "count": {"type": "integer"},
                            },
                        },
                        "description": "Mensajes agrupados por día",
                    },
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def messages_sent(self, request) -> Response:
        """Get messages sent count with date range."""
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        start_dt, end_dt = parse_date_range(start_date, end_date)

        messages_sent = Message.objects.filter(
            sender_type="user",
            sent_at__gte=start_dt,
            sent_at__lte=end_dt,
        ).count()

        # Group by day
        messages_by_day = (
            Message.objects.filter(
                sender_type="user",
                sent_at__gte=start_dt,
                sent_at__lte=end_dt,
            )
            .extra(select={"day": "date(sent_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        return Response(
            {
                "count": messages_sent,
                "start_date": start_dt.strftime("%Y-%m-%d"),
                "end_date": end_dt.strftime("%Y-%m-%d"),
                "by_day": list(messages_by_day),
            }
        )

    @extend_schema(
        summary="Calcular tasa de respuesta",
        description=(
            "Calcula la tasa de respuesta de mensajes en un período. "
            "Tasa = (recibidos / enviados) * 100. "
            "Indica qué porcentaje de mensajes recibieron respuesta. "
            "Por defecto: últimos 3 meses. "
            "Si start_date=end_date, filtra ese día."
        ),
        tags=["metrics"],
        parameters=DATE_RANGE_PARAMETERS,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "response_rate": {
                        "type": "number",
                        "description": "Tasa de respuesta en porcentaje",
                    },
                    "messages_sent": {
                        "type": "integer",
                        "description": "Total de mensajes enviados",
                    },
                    "messages_received": {
                        "type": "integer",
                        "description": "Total de mensajes recibidos",
                    },
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def response_rate(self, request) -> Response:
        """Calculate response rate."""
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        start_dt, end_dt = parse_date_range(start_date, end_date)

        messages_sent = Message.objects.filter(
            sender_type="user",
            sent_at__gte=start_dt,
            sent_at__lte=end_dt,
        ).count()

        messages_received = Message.objects.filter(
            sender_type="contact",
            sent_at__gte=start_dt,
            sent_at__lte=end_dt,
        ).count()

        if messages_sent > 0:
            response_rate = messages_received / messages_sent * 100
        else:
            response_rate = 0

        return Response(
            {
                "response_rate": round(response_rate, 2),
                "messages_sent": messages_sent,
                "messages_received": messages_received,
                "start_date": start_dt.strftime("%Y-%m-%d"),
                "end_date": end_dt.strftime("%Y-%m-%d"),
            }
        )

    @extend_schema(
        summary="Obtener leads agrupados por estado",
        description=(
            "Retorna un resumen de leads agrupados por estado. "
            "Incluye el conteo y porcentaje de leads en cada estado, "
            "junto con información del estado (nombre, color, ID). "
            "Por defecto: últimos 3 meses. "
            "Si start_date=end_date, filtra ese día."
        ),
        tags=["metrics"],
        parameters=DATE_RANGE_PARAMETERS,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "leads_by_status": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "status_name": {"type": "string"},
                                "status_id": {"type": "integer"},
                                "color": {"type": "string"},
                                "count": {"type": "integer"},
                                "percentage": {"type": "number"},
                            },
                        },
                    },
                    "total": {
                        "type": "integer",
                        "description": "Total de leads",
                    },
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def leads_by_status(self, request) -> Response:
        """Get leads grouped by status."""
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        start_dt, end_dt = parse_date_range(start_date, end_date)

        leads_by_status = (
            Lead.objects.filter(
                created_at__gte=start_dt, created_at__lte=end_dt
            )
            .values("status__name", "status__color", "status__id")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Add percentage
        total = Lead.objects.filter(
            created_at__gte=start_dt, created_at__lte=end_dt
        ).count()
        result = []
        for item in leads_by_status:
            percentage = (item["count"] / total * 100) if total > 0 else 0
            result.append(
                {
                    "status_name": item["status__name"],
                    "status_id": item["status__id"],
                    "color": item["status__color"],
                    "count": item["count"],
                    "percentage": round(percentage, 2),
                }
            )

        return Response({
            "leads_by_status": result,
            "total": total,
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d"),
        })

    @extend_schema(
        summary="Calcular tasa de conversión de leads",
        description=(
            "Calcula la tasa de conversión de leads a clientes. "
            "Incluye la tasa general y un desglose mensual de conversiones "
            "para análisis de tendencias a lo largo del tiempo. "
            "Por defecto: últimos 3 meses. "
            "Si start_date=end_date, filtra ese día."
        ),
        tags=["metrics"],
        parameters=DATE_RANGE_PARAMETERS,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "conversion_rate": {
                        "type": "number",
                        "description": "Tasa de conversión en porcentaje",
                    },
                    "total_leads": {
                        "type": "integer",
                        "description": "Total de leads",
                    },
                    "converted_leads": {
                        "type": "integer",
                        "description": "Total de leads convertidos a clientes",
                    },
                    "conversions_by_month": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "month": {"type": "string"},
                                "count": {"type": "integer"},
                            },
                        },
                        "description": "Conversiones agrupadas por mes",
                    },
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def conversion_rate(self, request) -> Response:
        """Calculate lead to client conversion rate."""
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        start_dt, end_dt = parse_date_range(start_date, end_date)

        total_leads = Lead.objects.filter(
            created_at__gte=start_dt, created_at__lte=end_dt
        ).count()
        converted_leads = Lead.objects.filter(
            is_client=True,
            created_at__gte=start_dt,
            created_at__lte=end_dt,
        ).count()

        # Conversion rate over time (within the date range)
        conversions_by_month = (
            Lead.objects.filter(
                is_client=True,
                converted_to_client_at__isnull=False,
                converted_to_client_at__gte=start_dt,
                converted_to_client_at__lte=end_dt,
            )
            .extra(select={
                "month": "date_trunc('month', converted_to_client_at)"
            })
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        if total_leads > 0:
            conversion_rate = converted_leads / total_leads * 100
        else:
            conversion_rate = 0

        return Response(
            {
                "conversion_rate": round(conversion_rate, 2),
                "total_leads": total_leads,
                "converted_leads": converted_leads,
                "conversions_by_month": list(conversions_by_month),
                "start_date": start_dt.strftime("%Y-%m-%d"),
                "end_date": end_dt.strftime("%Y-%m-%d"),
            }
        )
