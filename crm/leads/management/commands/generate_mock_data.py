"""Management command to generate mock data using factories."""

import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

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
from crm.leads.tests.factories import (
    ActivityFactory,
    ApiCredentialFactory,
    CategoryFactory,
    ContactFactory,
    ContactTagFactory,
    ConversationFactory,
    EmailTemplateFactory,
    LeadFactory,
    LeadStatusFactory,
    LeadTagFactory,
    MessageFactory,
    SavedFilterFactory,
    TagFactory,
    TaskFactory,
)
from crm.users.tests.factories import UserFactory

User = get_user_model()


class Command(BaseCommand):
    """Generate mock data for CRM using factories."""

    help = "Generate mock data for CRM using factories"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--categories",
            type=int,
            default=5,
            help="Number of categories to generate (default: 5)",
        )
        parser.add_argument(
            "--tags",
            type=int,
            default=10,
            help="Number of tags to generate (default: 10)",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=5,
            help="Number of users to generate (default: 5)",
        )
        parser.add_argument(
            "--leads",
            type=int,
            default=20,
            help="Number of leads to generate (default: 20)",
        )
        parser.add_argument(
            "--contacts-per-lead",
            type=int,
            default=2,
            help="Number of contacts per lead (default: 2)",
        )
        parser.add_argument(
            "--activities",
            type=int,
            default=50,
            help="Number of activities to generate (default: 50)",
        )
        parser.add_argument(
            "--tasks",
            type=int,
            default=30,
            help="Number of tasks to generate (default: 30)",
        )
        parser.add_argument(
            "--conversations",
            type=int,
            default=25,
            help="Number of conversations to generate (default: 25)",
        )
        parser.add_argument(
            "--messages-per-conversation",
            type=int,
            default=5,
            help="Number of messages per conversation (default: 5)",
        )
        parser.add_argument(
            "--email-templates",
            type=int,
            default=5,
            help="Number of email templates to generate (default: 5)",
        )
        parser.add_argument(
            "--saved-filters",
            type=int,
            default=10,
            help="Number of saved filters to generate (default: 10)",
        )
        parser.add_argument(
            "--api-credentials",
            type=int,
            default=2,
            help="Number of API credentials to generate (default: 2)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before generating",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            self._clear_data()

        # Generate base data
        self.stdout.write(self.style.SUCCESS("Generating base data..."))
        categories = self._generate_categories(options["categories"])
        lead_statuses = self._generate_lead_statuses()
        tags = self._generate_tags(options["tags"])
        users = self._generate_users(options["users"])

        # Generate leads and related data
        self.stdout.write(self.style.SUCCESS("Generating leads and contacts..."))
        leads = self._generate_leads(options["leads"], categories, lead_statuses, users)
        self._generate_contacts(
            leads, options["contacts_per_lead"], options["tags"], tags, users
        )

        # Generate activities and tasks
        self.stdout.write(self.style.SUCCESS("Generating activities and tasks..."))
        self._generate_activities(options["activities"], leads, users)
        self._generate_tasks(options["tasks"], leads, users)

        # Generate conversations and messages
        self.stdout.write(self.style.SUCCESS("Generating conversations and messages..."))
        conversations = self._generate_conversations(
            options["conversations"], leads, users
        )
        self._generate_messages(
            conversations, options["messages_per_conversation"]
        )

        # Generate email templates and filters
        self.stdout.write(self.style.SUCCESS("Generating email templates and filters..."))
        self._generate_email_templates(options["email_templates"], users)
        self._generate_saved_filters(options["saved_filters"], users)

        # Summary
        self.stdout.write(self.style.SUCCESS("\n=== Mock Data Generation Complete ==="))
        self._print_summary()

    def _clear_data(self):
        """Clear existing data."""
        Message.objects.all().delete()
        Conversation.objects.all().delete()
        Task.objects.all().delete()
        Activity.objects.all().delete()
        ContactTag.objects.all().delete()
        Contact.objects.all().delete()
        LeadTag.objects.all().delete()
        Lead.objects.all().delete()
        SavedFilter.objects.all().delete()
        EmailTemplate.objects.all().delete()
        ApiCredential.objects.all().delete()
        Tag.objects.all().delete()
        LeadStatus.objects.all().delete()
        Category.objects.all().delete()

    def _generate_categories(self, count):
        """Generate categories."""
        categories = []
        for _ in range(count):
            categories.append(CategoryFactory())
        self.stdout.write(f"  ✓ Generated {count} categories")
        return categories

    def _generate_lead_statuses(self):
        """Generate lead statuses."""
        # Don't override existing statuses from fixtures
        statuses = list(LeadStatus.objects.all())
        if not statuses:
            # Generate some default statuses if none exist
            status_names = [
                "Nuevo",
                "Contactado",
                "En seguimiento",
                "Calificado",
                "Negociación",
                "Ganado (Cliente)",
                "Perdido",
            ]
            for i, name in enumerate(status_names, 1):
                statuses.append(
                    LeadStatusFactory(
                        name=name,
                        order_position=i,
                        is_active=True,
                    )
                )
            self.stdout.write(f"  ✓ Generated {len(statuses)} lead statuses")
        else:
            self.stdout.write(f"  ✓ Using {len(statuses)} existing lead statuses")
        return statuses

    def _generate_tags(self, count):
        """Generate tags."""
        tags = []
        tag_names = [
            "VIP",
            "Hot Lead",
            "Cold Lead",
            "Follow-up Required",
            "Prospect",
            "Qualified",
            "Unqualified",
            "High Priority",
            "Low Priority",
            "Urgent",
            "Interested",
            "Not Interested",
            "Budget Approved",
            "Decision Maker",
            "Technical Contact",
        ]
        for i in range(count):
            if i < len(tag_names):
                tag = TagFactory(name=tag_names[i])
            else:
                tag = TagFactory()
            tags.append(tag)
        self.stdout.write(f"  ✓ Generated {count} tags")
        return tags

    def _generate_users(self, count):
        """Generate users."""
        existing_count = User.objects.count()
        users = list(User.objects.all())

        # Generate additional users if needed
        if len(users) < count:
            for _ in range(count - len(users)):
                users.append(UserFactory())
            self.stdout.write(
                f"  ✓ Generated {count - existing_count} users "
                f"({existing_count} existing, {count} total)"
            )
        else:
            self.stdout.write(f"  ✓ Using {len(users)} existing users")
        return users

    def _generate_leads(self, count, categories, lead_statuses, users):
        """Generate leads."""
        leads = []
        for _ in range(count):
            lead = LeadFactory(
                category=random.choice(categories) if categories else None,
                status=random.choice(lead_statuses) if lead_statuses else None,
                assigned_to=random.choice(users) if users else None,
            )
            leads.append(lead)
        self.stdout.write(f"  ✓ Generated {count} leads")
        return leads

    def _generate_contacts(self, leads, contacts_per_lead, tag_count, tags, users):
        """Generate contacts for leads."""
        total_contacts = 0
        for lead in leads:
            num_contacts = random.randint(1, contacts_per_lead + 1)
            for i in range(num_contacts):
                is_primary = i == 0  # First contact is primary
                contact = ContactFactory(lead=lead, is_primary=is_primary)
                total_contacts += 1

                # Assign some tags to contacts
                if tags and random.random() > 0.5:
                    num_contact_tags = random.randint(1, min(3, len(tags)))
                    contact_tags = random.sample(tags, num_contact_tags)
                    for tag in contact_tags:
                        ContactTagFactory(contact=contact, tag=tag)

        self.stdout.write(f"  ✓ Generated {total_contacts} contacts")

        # Assign some tags to leads
        for lead in leads:
            if tags and random.random() > 0.6:
                num_lead_tags = random.randint(1, min(4, len(tags)))
                lead_tags = random.sample(tags, num_lead_tags)
                for tag in lead_tags:
                    LeadTagFactory(lead=lead, tag=tag)

    def _generate_activities(self, count, leads, users):
        """Generate activities."""
        activities = []
        for _ in range(count):
            lead = random.choice(leads) if leads else None
            contact = (
                random.choice(list(lead.contacts.all())) if lead and lead.contacts.exists() else None
            )
            activity = ActivityFactory(
                lead=lead,
                contact=contact,
                user=random.choice(users) if users else None,
            )
            activities.append(activity)
        self.stdout.write(f"  ✓ Generated {count} activities")
        return activities

    def _generate_tasks(self, count, leads, users):
        """Generate tasks."""
        tasks = []
        for _ in range(count):
            lead = random.choice(leads) if leads else None
            contact = (
                random.choice(list(lead.contacts.all())) if lead and lead.contacts.exists() else None
            )
            task = TaskFactory(
                lead=lead,
                contact=contact,
                assigned_to=random.choice(users) if users else None,
            )
            tasks.append(task)
        self.stdout.write(f"  ✓ Generated {count} tasks")
        return tasks

    def _generate_conversations(self, count, leads, users):
        """Generate conversations."""
        conversations = []
        for _ in range(count):
            lead = random.choice(leads) if leads else None
            contact = (
                random.choice(list(lead.contacts.all())) if lead and lead.contacts.exists() else None
            )
            conversation = ConversationFactory(
                lead=lead,
                contact=contact,
                assigned_to=random.choice(users) if users else None,
            )
            conversations.append(conversation)
        self.stdout.write(f"  ✓ Generated {count} conversations")
        return conversations

    def _generate_messages(self, conversations, messages_per_conversation):
        """Generate messages for conversations."""
        total_messages = 0
        for conversation in conversations:
            num_messages = random.randint(2, messages_per_conversation + 2)
            for i in range(num_messages):
                # Alternate between contact and user messages
                sender_type = "contact" if i % 2 == 0 else "user"
                sender_id = (
                    str(conversation.contact.id)
                    if sender_type == "contact" and conversation.contact
                    else str(conversation.assigned_to.id)
                    if conversation.assigned_to
                    else "1"
                )
                MessageFactory(
                    conversation=conversation,
                    sender_type=sender_type,
                    sender_id=sender_id,
                )
                total_messages += 1
        self.stdout.write(f"  ✓ Generated {total_messages} messages")

    def _generate_email_templates(self, count, users):
        """Generate email templates."""
        templates = []
        template_types = ["welcome", "follow_up", "reminder", "custom"]
        for i in range(count):
            template = EmailTemplateFactory(
                template_type=template_types[i % len(template_types)],
                created_by=random.choice(users) if users else None,
            )
            templates.append(template)
        self.stdout.write(f"  ✓ Generated {count} email templates")
        return templates

    def _generate_saved_filters(self, count, users):
        """Generate saved filters."""
        filters = []
        for _ in range(count):
            filter_obj = SavedFilterFactory(
                user=random.choice(users) if users else None,
            )
            filters.append(filter_obj)
        self.stdout.write(f"  ✓ Generated {count} saved filters")
        return filters

    def _print_summary(self):
        """Print summary of generated data."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Summary:"))
        self.stdout.write(f"  Categories: {Category.objects.count()}")
        self.stdout.write(f"  Lead Statuses: {LeadStatus.objects.count()}")
        self.stdout.write(f"  Tags: {Tag.objects.count()}")
        self.stdout.write(f"  Users: {User.objects.count()}")
        self.stdout.write(f"  Leads: {Lead.objects.count()}")
        self.stdout.write(f"  Contacts: {Contact.objects.count()}")
        self.stdout.write(f"  Lead Tags: {LeadTag.objects.count()}")
        self.stdout.write(f"  Contact Tags: {ContactTag.objects.count()}")
        self.stdout.write(f"  Activities: {Activity.objects.count()}")
        self.stdout.write(f"  Tasks: {Task.objects.count()}")
        self.stdout.write(f"  Conversations: {Conversation.objects.count()}")
        self.stdout.write(f"  Messages: {Message.objects.count()}")
        self.stdout.write(f"  Email Templates: {EmailTemplate.objects.count()}")
        self.stdout.write(f"  Saved Filters: {SavedFilter.objects.count()}")
        self.stdout.write(f"  API Credentials: {ApiCredential.objects.count()}")
        self.stdout.write("=" * 50)

