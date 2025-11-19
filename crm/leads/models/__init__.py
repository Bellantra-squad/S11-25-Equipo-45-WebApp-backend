"""CRM leads models organized by relationship structure."""

from crm.leads.models.activity import Activity
from crm.leads.models.api_credential import ApiCredential
from crm.leads.models.contact import Contact, ContactTag
from crm.leads.models.conversation import Conversation, Message
from crm.leads.models.filter import SavedFilter
from crm.leads.models.lead import Category, Lead, LeadStatus, LeadTag, Tag
from crm.leads.models.task import Task
from crm.leads.models.template import EmailTemplate

__all__ = [
    # Lead-related models
    "Category",
    "LeadStatus",
    "Tag",
    "Lead",
    "LeadTag",
    # Contact models
    "Contact",
    "ContactTag",
    # Activity models
    "Activity",
    # Task models
    "Task",
    # Conversation models
    "Conversation",
    "Message",
    # Template models
    "EmailTemplate",
    # Filter models
    "SavedFilter",
    # API models
    "ApiCredential",
]
