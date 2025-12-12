"""Factory classes for CRM leads models."""

import random
from decimal import Decimal

from django.utils import timezone
from faker import Faker as FakerLibrary
from factory import Faker, LazyAttribute, SubFactory, fuzzy
from factory.django import DjangoModelFactory

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

# Configurar Faker con locale español
fake = FakerLibrary("es_ES")


class CategoryFactory(DjangoModelFactory[Category]):
    """Factory for Category model."""

    name = Faker(
        "word",
        ext_word_list=[
            "Tecnología",
            "Salud",
            "Finanzas",
            "Educación",
            "Retail",
        ],
    )
    description = Faker("text", max_nb_chars=200, locale="es_ES")
    color = Faker("hex_color")

    class Meta:
        model = Category
        django_get_or_create = ["name"]


class LeadStatusFactory(DjangoModelFactory[LeadStatus]):
    """Factory for LeadStatus model."""

    name = Faker(
        "word",
        ext_word_list=["Nuevo", "Contactado", "Calificado", "Ganado", "Perdido"],
    )
    description = Faker("text", max_nb_chars=200, locale="es_ES")
    color = Faker("hex_color")
    order_position = fuzzy.FuzzyInteger(0, 100)
    is_active = True

    class Meta:
        model = LeadStatus
        django_get_or_create = ["name"]


class TagFactory(DjangoModelFactory[Tag]):
    """Factory for Tag model."""

    name = Faker(
        "word",
        ext_word_list=["VIP", "Caliente", "Frío", "Seguimiento", "Prospecto"],
    )
    description = Faker("text", max_nb_chars=200, locale="es_ES")
    color = Faker("hex_color")

    class Meta:
        model = Tag
        django_get_or_create = ["name"]


class LeadFactory(DjangoModelFactory[Lead]):
    """Factory for Lead model."""

    company_name = Faker("company", locale="es_ES")
    industry = Faker(
        "word",
        ext_word_list=[
            "Tecnología",
            "Salud",
            "Finanzas",
            "Educación",
            "Retail",
        ],
    )
    website = Faker("url")
    category = SubFactory(CategoryFactory)
    status = SubFactory(LeadStatusFactory)
    assigned_to = SubFactory("crm.users.tests.factories.UserFactory")
    is_client = False
    lead_source = Faker(
        "word",
        ext_word_list=[
            "sitio_web",
            "referido",
            "llamada_fría",
            "redes_sociales",
            "whatsapp",
            "email",
        ],
    )
    lead_score = fuzzy.FuzzyInteger(0, 100)
    estimated_value = LazyAttribute(
        lambda obj: Decimal(
            str(round(random.uniform(1000.00, 100000.00), 2))
        )
    )
    notes = Faker("text", max_nb_chars=500, locale="es_ES")
    last_contact_date = Faker(
        "date_time_this_year", tzinfo=timezone.get_current_timezone()
    )
    next_follow_up = Faker(
        "date_time_this_year", tzinfo=timezone.get_current_timezone()
    )

    class Meta:
        model = Lead


class LeadTagFactory(DjangoModelFactory[LeadTag]):
    """Factory for LeadTag junction model."""

    lead = SubFactory(LeadFactory)
    tag = SubFactory(TagFactory)

    class Meta:
        model = LeadTag
        django_get_or_create = ["lead", "tag"]


class ContactFactory(DjangoModelFactory[Contact]):
    """Factory for Contact model."""

    lead = SubFactory(LeadFactory)
    first_name = Faker("first_name", locale="es_ES")
    last_name = Faker("last_name", locale="es_ES")
    email = Faker("email", locale="es_ES")
    phone = LazyAttribute(lambda obj: f"+{fake.msisdn()}")
    whatsapp_number = LazyAttribute(lambda obj: f"+{fake.msisdn()}")
    position = Faker("job", locale="es_ES")
    department = Faker(
        "word",
        ext_word_list=["Ventas", "Marketing", "TI", "RRHH", "Finanzas"],
    )
    is_primary = False
    is_decision_maker = fuzzy.FuzzyChoice([True, False])
    notes = Faker("text", max_nb_chars=300, locale="es_ES")

    class Meta:
        model = Contact


class ContactTagFactory(DjangoModelFactory[ContactTag]):
    """Factory for ContactTag junction model."""

    contact = SubFactory(ContactFactory)
    tag = SubFactory(TagFactory)

    class Meta:
        model = ContactTag
        django_get_or_create = ["contact", "tag"]


class ActivityFactory(DjangoModelFactory[Activity]):
    """Factory for Activity model."""

    lead = SubFactory(LeadFactory)
    contact = SubFactory(ContactFactory)
    user = SubFactory("crm.users.tests.factories.UserFactory")
    activity_type = fuzzy.FuzzyChoice(
        [
            "call",
            "email",
            "meeting",
            "note",
            "task",
            "message",
            "status_change",
            "other",
        ]
    )
    description = Faker("text", max_nb_chars=500, locale="es_ES")
    metadata = LazyAttribute(
        lambda obj: {
            "source": fake.word(),
            "duration": random.randint(5, 60),
        }
    )

    class Meta:
        model = Activity


class TaskFactory(DjangoModelFactory[Task]):
    """Factory for Task model."""

    title = Faker("sentence", nb_words=4, locale="es_ES")
    description = Faker("text", max_nb_chars=500, locale="es_ES")
    lead = SubFactory(LeadFactory)
    contact = SubFactory(ContactFactory)
    assigned_to = SubFactory("crm.users.tests.factories.UserFactory")
    task_type = fuzzy.FuzzyChoice(
        ["call", "email", "meeting", "follow_up", "other"]
    )
    priority = fuzzy.FuzzyChoice(["low", "medium", "high", "urgent"])
    status = fuzzy.FuzzyChoice(
        ["pending", "in_progress", "completed", "cancelled"]
    )
    due_date = Faker(
        "date_time_this_year", tzinfo=timezone.get_current_timezone()
    )
    completed_at = LazyAttribute(
        lambda obj: fake.date_time_this_year(
            tzinfo=timezone.get_current_timezone()
        )
        if obj.status == "completed"
        else None
    )

    class Meta:
        model = Task


class ConversationFactory(DjangoModelFactory[Conversation]):
    """Factory for Conversation model."""

    lead = SubFactory(LeadFactory)
    contact = SubFactory(ContactFactory)
    channel = fuzzy.FuzzyChoice(["whatsapp", "email", "sms", "other"])
    subject = Faker("sentence", nb_words=5, locale="es_ES")
    status = fuzzy.FuzzyChoice(["open", "closed", "pending", "resolved"])
    assigned_to = SubFactory("crm.users.tests.factories.UserFactory")

    class Meta:
        model = Conversation


class MessageFactory(DjangoModelFactory[Message]):
    """Factory for Message model."""

    conversation = SubFactory(ConversationFactory)
    sender_type = fuzzy.FuzzyChoice(["user", "contact", "system"])
    sender_id = LazyAttribute(
        lambda obj: str(random.randint(1, 1000))
    )
    content = Faker("text", max_nb_chars=500, locale="es_ES")
    message_type = fuzzy.FuzzyChoice(
        ["text", "image", "file", "audio", "video"]
    )
    external_message_id = Faker("uuid4")
    is_read = fuzzy.FuzzyChoice([True, False])
    sent_at = Faker(
        "date_time_this_year", tzinfo=timezone.get_current_timezone()
    )
    delivered_at = LazyAttribute(
        lambda obj: fake.date_time_this_year(
            tzinfo=timezone.get_current_timezone()
        )
        if obj.is_read
        else None
    )
    read_at = LazyAttribute(
        lambda obj: fake.date_time_this_year(
            tzinfo=timezone.get_current_timezone()
        )
        if obj.is_read
        else None
    )

    class Meta:
        model = Message


class EmailTemplateFactory(DjangoModelFactory[EmailTemplate]):
    """Factory for EmailTemplate model."""

    name = Faker(
        "word",
        ext_word_list=["Bienvenida", "Seguimiento", "Recordatorio", "Personalizado"],
    )
    subject = Faker("sentence", nb_words=5, locale="es_ES")
    body = Faker("text", max_nb_chars=1000, locale="es_ES")
    template_type = fuzzy.FuzzyChoice(
        ["welcome", "follow_up", "reminder", "custom"]
    )
    is_active = True
    created_by = SubFactory("crm.users.tests.factories.UserFactory")

    class Meta:
        model = EmailTemplate


class SavedFilterFactory(DjangoModelFactory[SavedFilter]):
    """Factory for SavedFilter model."""

    user = SubFactory("crm.users.tests.factories.UserFactory")
    name = Faker(
        "word",
        ext_word_list=[
            "Mis Leads",
            "Prospectos Calientes",
            "Esta Semana",
            "VIP",
            "Contactados",
        ],
    )
    filter_config = LazyAttribute(
        lambda obj: {
            "status": fake.word(),
            "category": fake.word(),
            "is_client": False,
        }
    )
    is_public = False

    class Meta:
        model = SavedFilter


class ApiCredentialFactory(DjangoModelFactory[ApiCredential]):
    """Factory for ApiCredential model."""

    service_name = Faker("company", locale="es_ES")
    credential_type = fuzzy.FuzzyChoice(
        ["whatsapp", "email_smtp", "email_brevo", "other"]
    )
    api_key = Faker("password", length=32, special_chars=False)
    api_secret = Faker("password", length=32, special_chars=False)
    access_token = Faker("password", length=64, special_chars=False)
    refresh_token = Faker("password", length=64, special_chars=False)
    webhook_url = Faker("url")
    phone_number_id = Faker(
        "random_int", min=100000000000000, max=999999999999999
    )
    business_account_id = Faker("uuid4")
    additional_config = LazyAttribute(
        lambda obj: {
            "region": fake.word(),
            "environment": "production" if obj.is_active else "staging",
        }
    )
    is_active = True
    expires_at = Faker(
        "future_datetime",
        end_date="+365d",
        tzinfo=timezone.get_current_timezone(),
    )

    class Meta:
        model = ApiCredential
