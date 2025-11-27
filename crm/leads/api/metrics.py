"""Metrics dashboard API endpoints."""

from datetime import datetime, timedelta
from typing import Any, Dict

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from crm.leads.models import Contact, Conversation, Lead, LeadStatus, Message, Task


class MetricsViewSet(ViewSet):
    """Metrics dashboard API."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Obtener métricas del dashboard principal",
        description=(
            "Retorna un resumen completo de métricas para el dashboard principal. "
            "Incluye contactos activos, mensajes enviados/recibidos, tasa de respuesta, "
            "leads por estado, tasa de conversión, actividades recientes y tareas pendientes. "
            "Los datos se calculan para los últimos 30 días por defecto."
        ),
        tags=["metrics"],
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
                    "period_days": {"type": "integer"},
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def dashboard(self, request) -> Response:
        """Get main dashboard metrics."""
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # Active contacts (contacts with recent activity)
        active_contacts = Contact.objects.filter(
            Q(activities__created_at__gte=thirty_days_ago)
            | Q(conversations__updated_at__gte=thirty_days_ago)
        ).distinct().count()

        # Messages sent in last 30 days
        messages_sent = Message.objects.filter(
            sender_type="user", sent_at__gte=thirty_days_ago
        ).count()

        # Total messages (for response rate calculation)
        total_messages = Message.objects.filter(sent_at__gte=thirty_days_ago).count()
        messages_received = total_messages - messages_sent
        response_rate = (
            (messages_received / messages_sent * 100) if messages_sent > 0 else 0
        )

        # Leads by status
        leads_by_status = (
            Lead.objects.values("status__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Conversion rate
        total_leads = Lead.objects.count()
        converted_leads = Lead.objects.filter(is_client=True).count()
        conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0

        # Recent activity count
        recent_activities = Contact.objects.filter(
            activities__created_at__gte=thirty_days_ago
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
            "period_days": 30,
        }

        return Response(data)

    @extend_schema(
        summary="Obtener conteo de contactos activos",
        description=(
            "Retorna el número de contactos activos en un período específico. "
            "Un contacto se considera activo si tiene actividades o conversaciones "
            "actualizadas en el período especificado."
        ),
        tags=["metrics"],
        parameters=[
            OpenApiParameter(
                name="days",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Número de días hacia atrás para calcular contactos activos (default: 30)",
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Número de contactos activos"},
                    "period_days": {"type": "integer", "description": "Período en días"},
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def contacts_active(self, request) -> Response:
        """Get active contacts count."""
        days = int(request.query_params.get("days", 30))
        cutoff_date = timezone.now() - timedelta(days=days)

        active_contacts = Contact.objects.filter(
            Q(activities__created_at__gte=cutoff_date)
            | Q(conversations__updated_at__gte=cutoff_date)
        ).distinct().count()

        return Response({"count": active_contacts, "period_days": days})

    @extend_schema(
        summary="Obtener conteo de mensajes enviados",
        description=(
            "Retorna el número de mensajes enviados por usuarios en un período específico. "
            "Incluye un desglose diario de mensajes enviados para análisis de tendencias."
        ),
        tags=["metrics"],
        parameters=[
            OpenApiParameter(
                name="days",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Número de días hacia atrás para calcular mensajes enviados (default: 30)",
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "count": {"type": "integer", "description": "Total de mensajes enviados"},
                    "period_days": {"type": "integer", "description": "Período en días"},
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
        days = int(request.query_params.get("days", 30))
        cutoff_date = timezone.now() - timedelta(days=days)

        messages_sent = Message.objects.filter(
            sender_type="user", sent_at__gte=cutoff_date
        ).count()

        # Group by day
        messages_by_day = (
            Message.objects.filter(sender_type="user", sent_at__gte=cutoff_date)
            .extra(select={"day": "date(sent_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        return Response(
            {
                "count": messages_sent,
                "period_days": days,
                "by_day": list(messages_by_day),
            }
        )

    @extend_schema(
        summary="Calcular tasa de respuesta",
        description=(
            "Calcula la tasa de respuesta de mensajes en un período específico. "
            "La tasa de respuesta se calcula como: (mensajes recibidos / mensajes enviados) * 100. "
            "Indica qué porcentaje de mensajes enviados recibieron respuesta."
        ),
        tags=["metrics"],
        parameters=[
            OpenApiParameter(
                name="days",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Número de días hacia atrás para calcular la tasa (default: 30)",
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "response_rate": {
                        "type": "number",
                        "description": "Tasa de respuesta en porcentaje",
                    },
                    "messages_sent": {"type": "integer", "description": "Total de mensajes enviados"},
                    "messages_received": {
                        "type": "integer",
                        "description": "Total de mensajes recibidos",
                    },
                    "period_days": {"type": "integer", "description": "Período en días"},
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def response_rate(self, request) -> Response:
        """Calculate response rate."""
        days = int(request.query_params.get("days", 30))
        cutoff_date = timezone.now() - timedelta(days=days)

        messages_sent = Message.objects.filter(
            sender_type="user", sent_at__gte=cutoff_date
        ).count()

        messages_received = Message.objects.filter(
            sender_type="contact", sent_at__gte=cutoff_date
        ).count()

        response_rate = (
            (messages_received / messages_sent * 100) if messages_sent > 0 else 0
        )

        return Response(
            {
                "response_rate": round(response_rate, 2),
                "messages_sent": messages_sent,
                "messages_received": messages_received,
                "period_days": days,
            }
        )

    @extend_schema(
        summary="Obtener leads agrupados por estado",
        description=(
            "Retorna un resumen de leads agrupados por estado. "
            "Incluye el conteo y porcentaje de leads en cada estado, "
            "junto con información del estado (nombre, color, ID)."
        ),
        tags=["metrics"],
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
                    "total": {"type": "integer", "description": "Total de leads"},
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def leads_by_status(self, request) -> Response:
        """Get leads grouped by status."""
        leads_by_status = (
            Lead.objects.values("status__name", "status__color", "status__id")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Add percentage
        total = Lead.objects.count()
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

        return Response({"leads_by_status": result, "total": total})

    @extend_schema(
        summary="Calcular tasa de conversión de leads",
        description=(
            "Calcula la tasa de conversión de leads a clientes. "
            "Incluye la tasa general y un desglose mensual de conversiones "
            "para análisis de tendencias a lo largo del tiempo."
        ),
        tags=["metrics"],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "conversion_rate": {
                        "type": "number",
                        "description": "Tasa de conversión en porcentaje",
                    },
                    "total_leads": {"type": "integer", "description": "Total de leads"},
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
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def conversion_rate(self, request) -> Response:
        """Calculate lead to client conversion rate."""
        total_leads = Lead.objects.count()
        converted_leads = Lead.objects.filter(is_client=True).count()

        # Conversion rate over time
        conversions_by_month = (
            Lead.objects.filter(is_client=True, converted_to_client_at__isnull=False)
            .extra(select={"month": "date_trunc('month', converted_to_client_at)"})
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0

        return Response(
            {
                "conversion_rate": round(conversion_rate, 2),
                "total_leads": total_leads,
                "converted_leads": converted_leads,
                "conversions_by_month": list(conversions_by_month),
            }
        )

