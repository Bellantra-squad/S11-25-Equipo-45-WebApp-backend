"""WebSocket authentication using Django REST Framework tokens."""

import logging
from typing import Optional

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()
logger = logging.getLogger(__name__)


@sync_to_async
def get_user_from_token(token_key: str) -> Optional[User]:
    """
    Get user from token key.

    Args:
        token_key: The token string

    Returns:
        User object if token is valid, None otherwise
    """
    try:
        token = Token.objects.select_related("user").get(key=token_key)
        if token.user.is_active:
            return token.user
        logger.warning(
            f"Inactive user attempted WebSocket connection: "
            f"{token.user.email}"
        )
        return None
    except Token.DoesNotExist:
        logger.warning(
            f"Invalid token attempted WebSocket connection: {token_key[:8]}..."
        )
        return None


async def authenticate_websocket(scope: dict) -> Optional[User]:
    """
    Authenticate WebSocket connection using query parameter.

    Expected query parameter: ?token=<token_key>

    Args:
        scope: ASGI scope dict containing connection info

    Returns:
        User object if authenticated, None otherwise
    """
    # Parse query string
    query_string = scope.get("query_string", b"").decode("utf-8")

    # Parse query parameters
    from urllib.parse import parse_qs
    params = parse_qs(query_string)

    # Get token from query parameter
    token_key = params.get("token", [None])[0]

    if not token_key:
        logger.info(
            "WebSocket connection attempt without token parameter"
        )
        return None

    # Validate token and get user
    user = await get_user_from_token(token_key)

    if user:
        logger.info(f"WebSocket authenticated: {user.email} (ID: {user.id})")
    else:
        logger.warning("WebSocket authentication failed")

    return user
