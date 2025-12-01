"""WebSocket connection manager for broadcasting real-time events."""

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasting."""

    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: dict[str, list[dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, channel: str, connection_info: dict[str, Any]) -> None:
        """
        Add a new connection to a channel.

        Args:
            channel: The channel name (e.g., 'activities', 'tasks')
            connection_info: Dict with 'send' callable and metadata
        """
        async with self._lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = []
            self.active_connections[channel].append(connection_info)
            logger.info(
                f"New connection to channel '{channel}'. "
                f"Total: {len(self.active_connections[channel])}"
            )

    async def disconnect(self, channel: str, connection_info: dict[str, Any]) -> None:
        """
        Remove a connection from a channel.

        Args:
            channel: The channel name
            connection_info: The connection info to remove
        """
        async with self._lock:
            if channel in self.active_connections:
                try:
                    self.active_connections[channel].remove(connection_info)
                    logger.info(
                        f"Connection removed from channel '{channel}'. "
                        f"Total: {len(self.active_connections[channel])}"
                    )
                    if not self.active_connections[channel]:
                        del self.active_connections[channel]
                except ValueError:
                    logger.warning(
                        f"Connection not found in channel '{channel}'"
                    )

    async def broadcast(self, channel: str, message: dict[str, Any]) -> None:
        """
        Broadcast a message to all connections in a channel.

        Args:
            channel: The channel name
            message: The message dict to broadcast
        """
        async with self._lock:
            if channel not in self.active_connections:
                logger.debug(
                    f"No connections in channel '{channel}' to broadcast to"
                )
                return

            connections = self.active_connections[channel].copy()

        # Broadcast outside the lock to avoid blocking
        message_json = json.dumps(message)
        disconnected = []

        for conn_info in connections:
            try:
                send = conn_info["send"]
                await send({"type": "websocket.send", "text": message_json})
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(conn_info)

        # Remove disconnected connections
        if disconnected:
            async with self._lock:
                for conn_info in disconnected:
                    if channel in self.active_connections:
                        try:
                            self.active_connections[channel].remove(conn_info)
                        except ValueError:
                            pass

        logger.info(
            f"Broadcasted to {len(connections) - len(disconnected)} "
            f"connections in channel '{channel}'"
        )

    def get_channel_count(self, channel: str) -> int:
        """Get the number of active connections in a channel."""
        return len(self.active_connections.get(channel, []))

    def get_total_connections(self) -> int:
        """
        Get total number of active connections across all channels.

        Returns:
            Total number of connections
        """
        return sum(len(conns) for conns in self.active_connections.values())

    def get_all_channels_info(self) -> dict[str, int]:
        """
        Get information about all active channels.

        Returns:
            Dict mapping channel names to connection counts
        """
        return {
            channel: len(conns)
            for channel, conns in self.active_connections.items()
        }


# Global connection manager instance
manager = ConnectionManager()
