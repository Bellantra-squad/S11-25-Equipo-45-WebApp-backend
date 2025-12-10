"""WebSocket application with routing and channel subscriptions."""

import json
import logging
import time

from django.conf import settings

from config.ws.auth import authenticate_websocket
from config.ws.manager import manager
from config.ws.rate_limiter import RateLimiter
from crm.leads.models.text_constants import WEBSOCKET_TEXTS

logger = logging.getLogger(__name__)

# Initialize rate limiter with settings
rate_limiter = RateLimiter(
    max_messages=getattr(settings, "WEBSOCKET_RATE_LIMIT_MESSAGES", 60),
    window_seconds=getattr(settings, "WEBSOCKET_RATE_LIMIT_WINDOW", 60),
)


async def handle_health_check(scope, receive, send):
    """
    Handle WebSocket health check requests.

    Provides information about:
    - Total active connections
    - Connections per channel
    - Rate limiter stats
    - System status
    """
    try:
        # Wait for connection
        event = await receive()
        if event["type"] == "websocket.connect":
            await send({"type": "websocket.accept"})

            # Gather health metrics
            health_data = {
                "type": "health_check",
                "status": WEBSOCKET_TEXTS["health_status"],
                "timestamp": time.time(),
                "data": {
                    "total_connections": manager.get_total_connections(),
                    "channels": manager.get_all_channels_info(),
                    "rate_limiter": rate_limiter.get_stats(),
                },
            }

            # Send health data
            await send({
                "type": "websocket.send",
                "text": json.dumps(health_data),
            })

            # Close connection gracefully
            await send({"type": "websocket.close", "code": 1000})
            logger.info(WEBSOCKET_TEXTS["health_success_log"])

    except Exception as e:
        logger.exception(
            WEBSOCKET_TEXTS["health_error_log"].format(error=e)
        )
        try:
            error_msg = {
                "type": "health_check",
                "status": WEBSOCKET_TEXTS["health_error"],
                "message": WEBSOCKET_TEXTS["health_error_message"],
            }
            await send({
                "type": "websocket.send",
                "text": json.dumps(error_msg),
            })
            await send({"type": "websocket.close", "code": 1011})
        except Exception:
            pass


async def websocket_application(scope, receive, send):
    """
    WebSocket application with support for different channels.

    Supported routes:
    - /ws/activities/ - Subscribe to activity creation events
    - /ws/tasks/ - Subscribe to task events (future)
    - /ws/ - General websocket connection

    Message format:
    - Client can send: {"action": "ping"} to test connection
    - Server responds: {"type": "pong", "message": "Connection alive"}
    - Activity events: {"type": "activity_created", "data": {...}}
    """
    # Parse the path to determine the channel
    path = scope.get("path", "")
    channel = None

    # Health check endpoint
    if path.startswith("/ws/health"):
        await handle_health_check(scope, receive, send)
        return

    # Determine channel
    if path.startswith("/ws/activities"):
        channel = "activities"
    elif path.startswith("/ws/tasks"):
        channel = "tasks"
    elif path.startswith("/ws/"):
        channel = "general"
    else:
        # Invalid websocket path
        await send({"type": "websocket.close"})
        return

    # Authenticate user
    require_auth = getattr(settings, "WEBSOCKET_REQUIRE_AUTH", True)
    user = await authenticate_websocket(scope)

    if require_auth and not user:
        # Authentication required but failed
        logger.warning(
            WEBSOCKET_TEXTS["unauthenticated_log"].format(path=path)
        )
        await send({"type": "websocket.close", "code": 4001})
        return

    connection_info = {
        "send": send,
        "scope": scope,
        "user": user,
        "user_id": user.id if user else None,
        "user_email": user.email if user else None,
    }
    connection_id = str(id(connection_info))
    connected = False

    try:
        while True:
            event = await receive()

            if event["type"] == "websocket.connect":
                await send({"type": "websocket.accept"})
                connected = True

                # Add connection to the channel
                if channel:
                    await manager.connect(channel, connection_info)
                    logger.info(
                        WEBSOCKET_TEXTS["connected_log"].format(
                            channel=channel,
                            user=user.email if user else "anónimo",
                        )
                    )

                    # Send welcome message
                    welcome_msg = {
                        "type": "connection_established",
                        "channel": channel,
                        "message": (
                            WEBSOCKET_TEXTS["welcome_message"].format(
                                channel=channel
                            )
                        ),
                        "user": {
                            "id": user.id,
                            "email": user.email,
                        } if user else None,
                        "authenticated": user is not None,
                    }
                    await send({
                        "type": "websocket.send",
                        "text": json.dumps(welcome_msg),
                    })

            elif event["type"] == "websocket.disconnect":
                break

            elif event["type"] == "websocket.receive":
                # Check rate limit
                if not rate_limiter.check_rate_limit(connection_id):
                    remaining = rate_limiter.get_remaining_messages(
                        connection_id
                    )
                    error_msg = {
                        "type": "rate_limit_exceeded",
                        "message": WEBSOCKET_TEXTS["rate_limit"],
                        "retry_after": rate_limiter.window_seconds,
                        "remaining": remaining,
                    }
                    await send({
                        "type": "websocket.send",
                        "text": json.dumps(error_msg),
                    })
                    continue

                # Handle incoming messages from client
                try:
                    if "text" in event:
                        data = (
                            json.loads(event["text"])
                            if event["text"] != "ping"
                            else {"action": "ping"}
                        )

                        # Handle ping
                        if data.get("action") == "ping":
                            pong_msg = {
                                "type": "pong",
                                "message": "Connection alive",
                            }
                            await send({
                                "type": "websocket.send",
                                "text": json.dumps(pong_msg),
                            })

                        # Handle subscription info request
                        elif data.get("action") == "info":
                            info_msg = {
                                "type": "info",
                                "channel": channel,
                                "connections": manager.get_channel_count(
                                    channel
                                ),
                            }
                            await send({
                                "type": "websocket.send",
                                "text": json.dumps(info_msg),
                            })

                        else:
                            # Unknown action
                            error_msg = {
                                "type": "error",
                                "message": WEBSOCKET_TEXTS[
                                    "unknown_action"
                                ].format(
                                    action=data.get("action", "none")
                                ),
                            }
                            await send({
                                "type": "websocket.send",
                                "text": json.dumps(error_msg),
                            })

                except json.JSONDecodeError:
                    error_msg = {
                        "type": "error",
                        "message": WEBSOCKET_TEXTS["invalid_json"],
                    }
                    await send({
                        "type": "websocket.send",
                        "text": json.dumps(error_msg),
                    })
                except Exception as e:
                    logger.exception(
                        WEBSOCKET_TEXTS["websocket_error_log"].format(
                            error=e
                        )
                    )
                    error_msg = {
                        "type": "error",
                        "message": WEBSOCKET_TEXTS["internal_error"],
                    }
                    await send({
                        "type": "websocket.send",
                        "text": json.dumps(error_msg),
                    })

    except Exception as e:
        logger.exception(
            WEBSOCKET_TEXTS["websocket_error_log"].format(error=e)
        )
    finally:
        # Always disconnect from the channel
        if connected and channel:
            await manager.disconnect(channel, connection_info)
            logger.info(
                WEBSOCKET_TEXTS["disconnected_log"].format(
                    channel=channel,
                    user=user.email if user else "anónimo",
                )
            )

        # Cleanup rate limiter
        rate_limiter.cleanup_connection(connection_id)
