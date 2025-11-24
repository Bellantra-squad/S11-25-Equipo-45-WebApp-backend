"""Metrics dashboard API endpoints."""

from datetime import datetime, timedelta
from typing import Any, Dict

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from crm.leads.models import Contact, Conversation, Lead, LeadStatus, Message, Task


class MetricsViewSet(ViewSet):
    """Metrics dashboard API."""

    permission_classes = [IsAuthenticated]

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

