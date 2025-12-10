"""Signals for broadcasting real-time events."""

import asyncio
import logging

from asgiref.sync import async_to_sync
from django.db.models.signals import post_save
from django.dispatch import receiver

from crm.leads.models import Activity
from crm.leads.models.text_constants import SIGNAL_LOGS

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Activity)
def activity_created(sender, instance, created, **kwargs):
    """Broadcast when a new Activity is created."""
    if not created:
        return

    try:
        # Import here to avoid circular imports
        from config.ws.manager import manager

        # Prepare the activity data
        activity_data = {
            "type": "activity_created",
            "data": {
                "id": instance.id,
                "activity_type": instance.activity_type,
                "description": instance.description,
                "metadata": instance.metadata,
                "created_at": instance.created_at.isoformat(),
                "lead_id": instance.lead_id,
                "contact_id": instance.contact_id,
                "user_id": instance.user_id,
                "user": {
                    "id": instance.user.id,
                    "email": instance.user.email,
                    "name": (
                        instance.user.name
                        if hasattr(instance.user, "name")
                        else instance.user.email
                    ),
                }
                if instance.user
                else None,
            },
        }

        # Broadcast to the activities channel
        # We need to run this in an async context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a task
                asyncio.create_task(manager.broadcast("activities", activity_data))
            else:
                # Otherwise, run it synchronously
                async_to_sync(manager.broadcast)("activities", activity_data)
        except RuntimeError:
            # No event loop, create one
            async_to_sync(manager.broadcast)("activities", activity_data)

        logger.info(
            SIGNAL_LOGS["activity_broadcasted"].format(
                activity_id=instance.id
            )
        )

    except Exception as e:
        logger.exception(
            SIGNAL_LOGS["activity_error"].format(error=e)
        )

