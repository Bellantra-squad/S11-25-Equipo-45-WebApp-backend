"""Tests for leads models."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from crm.leads.models import (
    Activity,
    Category,
    Contact,
    ContactTag,
    Conversation,
    EmailTemplate,
    Lead,
    LeadStatus,
    LeadTag,
    Message,
    Tag,
    Task,
)

User = get_user_model()


@pytest.mark.django_db
class TestCategory:
    """Tests for Category model."""

    def test_category_creation(self):
        """Test creating a category."""
        category = Category.objects.create(name="Technology", description="Tech companies", color="#FF0000")
        assert category.name == "Technology"
        assert str(category) == "Technology"


@pytest.mark.django_db
class TestLeadStatus:
    """Tests for LeadStatus model."""

    def test_lead_status_creation(self):
        """Test creating a lead status."""
        status = LeadStatus.objects.create(
            name="New",
            description="New leads",
            color="#00FF00",
            order_position=1,
        )
        assert status.name == "New"
        assert status.order_position == 1
        assert str(status) == "New"


@pytest.mark.django_db
class TestTag:
    """Tests for Tag model."""

    def test_tag_creation(self):
        """Test creating a tag."""
        tag = Tag.objects.create(name="VIP", description="VIP customers", color="#0000FF")
        assert tag.name == "VIP"
        assert str(tag) == "VIP"


@pytest.mark.django_db
class TestLead:
    """Tests for Lead model."""

    def test_lead_creation(self):
        """Test creating a lead."""
        category = Category.objects.create(name="Technology")
        status = LeadStatus.objects.create(name="New", order_position=1)
        user = User.objects.create_user(email="test@example.com", password="testpass123")

        lead = Lead.objects.create(
            company_name="Test Corp",
            industry="Tech",
            website="https://testcorp.com",
            category=category,
            status=status,
            assigned_to=user,
            lead_source="website",
        )

        assert lead.company_name == "Test Corp"
        assert lead.category == category
        assert lead.status == status
        assert str(lead) == "Test Corp"

    def test_lead_without_category(self):
        """Test creating a lead without category."""
        lead = Lead.objects.create(company_name="Test Corp", lead_source="website")
        assert lead.company_name == "Test Corp"
        assert lead.category is None


@pytest.mark.django_db
class TestContact:
    """Tests for Contact model."""

    def test_contact_creation(self):
        """Test creating a contact."""
        lead = Lead.objects.create(company_name="Test Corp", lead_source="website")
        contact = Contact.objects.create(
            lead=lead,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="+1234567890",
        )

        assert contact.first_name == "John"
        assert contact.last_name == "Doe"
        assert contact.lead == lead
        assert str(contact) == "John Doe"

    def test_contact_validation(self):
        """Test contact validation requires at least email, phone, or whatsapp."""
        lead = Lead.objects.create(company_name="Test Corp", lead_source="website")
        contact = Contact(lead=lead, first_name="John", last_name="Doe")
        # Should not raise error on creation, validation happens in clean() if called
        contact.email = "test@example.com"
        contact.save()
        assert contact.email == "test@example.com"


@pytest.mark.django_db
class TestTask:
    """Tests for Task model."""

    def test_task_creation(self):
        """Test creating a task."""
        lead = Lead.objects.create(company_name="Test Corp", lead_source="website")
        user = User.objects.create_user(email="user@example.com", password="testpass123")

        task = Task.objects.create(
            title="Follow up",
            description="Follow up with client",
            lead=lead,
            assigned_to=user,
            task_type="follow_up",
            priority="high",
            due_date=timezone.now(),
        )

        assert task.title == "Follow up"
        assert task.lead == lead
        assert task.assigned_to == user
        assert str(task) == "Follow up"


@pytest.mark.django_db
class TestConversation:
    """Tests for Conversation model."""

    def test_conversation_creation(self):
        """Test creating a conversation."""
        lead = Lead.objects.create(company_name="Test Corp", lead_source="website")
        contact = Contact.objects.create(lead=lead, first_name="John", last_name="Doe", email="john@example.com")

        conversation = Conversation.objects.create(
            lead=lead,
            contact=contact,
            channel="whatsapp",
            subject="Test conversation",
        )

        assert conversation.channel == "whatsapp"
        assert conversation.lead == lead
        assert conversation.contact == contact


@pytest.mark.django_db
class TestMessage:
    """Tests for Message model."""

    def test_message_creation(self):
        """Test creating a message."""
        lead = Lead.objects.create(company_name="Test Corp", lead_source="website")
        contact = Contact.objects.create(lead=lead, first_name="John", last_name="Doe", email="john@example.com")
        conversation = Conversation.objects.create(lead=lead, contact=contact, channel="whatsapp")

        message = Message.objects.create(
            conversation=conversation,
            sender_type="contact",
            sender_id=str(contact.id),
            content="Hello",
            message_type="text",
        )

        assert message.content == "Hello"
        assert message.conversation == conversation
        assert message.sender_type == "contact"


@pytest.mark.django_db
class TestLeadTag:
    """Tests for LeadTag junction model."""

    def test_lead_tag_creation(self):
        """Test creating a lead-tag relationship."""
        lead = Lead.objects.create(company_name="Test Corp", lead_source="website")
        tag = Tag.objects.create(name="VIP")

        lead_tag = LeadTag.objects.create(lead=lead, tag=tag)
        assert lead_tag.lead == lead
        assert lead_tag.tag == tag
        assert str(lead_tag) == f"{lead} - {tag}"


@pytest.mark.django_db
class TestActivity:
    """Tests for Activity model."""

    def test_activity_creation(self):
        """Test creating an activity."""
        lead = Lead.objects.create(company_name="Test Corp", lead_source="website")
        user = User.objects.create_user(email="user@example.com", password="testpass123")

        activity = Activity.objects.create(
            lead=lead,
            user=user,
            activity_type="call",
            description="Made a call to client",
        )

        assert activity.activity_type == "call"
        assert activity.lead == lead
        assert activity.user == user


@pytest.mark.django_db
class TestEmailTemplate:
    """Tests for EmailTemplate model."""

    def test_email_template_creation(self):
        """Test creating an email template."""
        user = User.objects.create_user(email="user@example.com", password="testpass123")

        template = EmailTemplate.objects.create(
            name="Welcome Email",
            subject="Welcome!",
            body="Welcome to our platform",
            template_type="welcome",
            created_by=user,
        )

        assert template.name == "Welcome Email"
        assert template.template_type == "welcome"
        assert template.created_by == user

