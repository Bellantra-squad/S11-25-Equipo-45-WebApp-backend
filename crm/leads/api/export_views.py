"""Export functionality for leads and contacts."""

import csv
from io import BytesIO

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from crm.leads.models import Contact, Lead


class ExportViewSet(viewsets.ViewSet):
    """Export functionality for leads and contacts."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def leads_csv(self, request) -> HttpResponse:
        """Export leads to CSV."""
        queryset = Lead.objects.select_related("category", "status", "assigned_to")

        # Apply filters
        category = request.query_params.get("category")
        status = request.query_params.get("status")
        is_client = request.query_params.get("is_client")

        if category:
            queryset = queryset.filter(category_id=category)
        if status:
            queryset = queryset.filter(status_id=status)
        if is_client is not None:
            queryset = queryset.filter(is_client=is_client.lower() == "true")

        # Create CSV
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="leads_export.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "ID",
                "Company Name",
                "Industry",
                "Website",
                "Category",
                "Status",
                "Assigned To",
                "Is Client",
                "Lead Source",
                "Lead Score",
                "Estimated Value",
                "Created At",
            ]
        )

        for lead in queryset:
            writer.writerow(
                [
                    lead.id,
                    lead.company_name,
                    lead.industry,
                    lead.website,
                    lead.category.name if lead.category else "",
                    lead.status.name if lead.status else "",
                    lead.assigned_to.email if lead.assigned_to else "",
                    lead.is_client,
                    lead.lead_source,
                    lead.lead_score,
                    lead.estimated_value,
                    lead.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )

        return response

    @action(detail=False, methods=["get"])
    def leads_pdf(self, request) -> HttpResponse:
        """Export leads to PDF."""
        queryset = Lead.objects.select_related("category", "status", "assigned_to")

        # Apply filters
        category = request.query_params.get("category")
        status = request.query_params.get("status")
        is_client = request.query_params.get("is_client")

        if category:
            queryset = queryset.filter(category_id=category)
        if status:
            queryset = queryset.filter(status_id=status)
        if is_client is not None:
            queryset = queryset.filter(is_client=is_client.lower() == "true")

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        normal_style = styles["Normal"]

        # Title
        elements.append(Paragraph("Leads Export", title_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Table data
        data = [
            [
                "ID",
                "Company",
                "Category",
                "Status",
                "Assigned To",
                "Lead Score",
                "Created At",
            ]
        ]

        for lead in queryset[:100]:  # Limit to 100 rows for PDF
            data.append(
                [
                    str(lead.id),
                    lead.company_name[:30],
                    lead.category.name[:20] if lead.category else "",
                    lead.status.name[:20] if lead.status else "",
                    lead.assigned_to.email[:20] if lead.assigned_to else "",
                    str(lead.lead_score),
                    lead.created_at.strftime("%Y-%m-%d"),
                ]
            )

        # Create table
        table = Table(data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                ]
            )
        )

        elements.append(table)
        doc.build(elements)

        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="leads_export.pdf"'
        return response

    @action(detail=False, methods=["get"])
    def contacts_csv(self, request) -> HttpResponse:
        """Export contacts to CSV."""
        queryset = Contact.objects.select_related("lead")

        # Apply filters
        lead_id = request.query_params.get("lead")
        is_primary = request.query_params.get("is_primary")
        is_decision_maker = request.query_params.get("is_decision_maker")

        if lead_id:
            queryset = queryset.filter(lead_id=lead_id)
        if is_primary is not None:
            queryset = queryset.filter(is_primary=is_primary.lower() == "true")
        if is_decision_maker is not None:
            queryset = queryset.filter(is_decision_maker=is_decision_maker.lower() == "true")

        # Create CSV
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="contacts_export.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "ID",
                "Lead ID",
                "Company Name",
                "First Name",
                "Last Name",
                "Email",
                "Phone",
                "WhatsApp Number",
                "Position",
                "Department",
                "Is Primary",
                "Is Decision Maker",
                "Created At",
            ]
        )

        for contact in queryset:
            writer.writerow(
                [
                    contact.id,
                    contact.lead.id,
                    contact.lead.company_name,
                    contact.first_name,
                    contact.last_name,
                    contact.email,
                    contact.phone,
                    contact.whatsapp_number,
                    contact.position,
                    contact.department,
                    contact.is_primary,
                    contact.is_decision_maker,
                    contact.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )

        return response

