"""WebSocket rate limiting to prevent message spam."""

import logging
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for WebSocket messages using sliding window."""

    def __init__(self, max_messages: int = 60, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_messages: Maximum messages allowed in the time window
            window_seconds: Time window in seconds
        """
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.limits: dict[str, deque[float]] = {}
        logger.info(
            f"Rate limiter initialized: {max_messages} messages per "
            f"{window_seconds} seconds"
        )

    def check_rate_limit(self, connection_id: str) -> bool:
        """
        Check if connection has exceeded rate limit.

        Args:
            connection_id: Unique identifier for the connection

        Returns:
            True if within limit, False if exceeded
        """
        current_time = time.time()

        # Initialize deque for new connections
        if connection_id not in self.limits:
            self.limits[connection_id] = deque()

        timestamps = self.limits[connection_id]

        # Remove timestamps outside the time window
        cutoff_time = current_time - self.window_seconds
        while timestamps and timestamps[0] < cutoff_time:
            timestamps.popleft()

        # Check if limit exceeded
        if len(timestamps) >= self.max_messages:
            logger.warning(
                f"Rate limit exceeded for connection {connection_id}: "
                f"{len(timestamps)} messages in {self.window_seconds}s"
            )
            return False

        # Add current timestamp
        timestamps.append(current_time)
        return True

    def cleanup_connection(self, connection_id: str) -> None:
        """
        Remove rate limit data for a connection.

        Args:
            connection_id: Unique identifier for the connection
        """
        if connection_id in self.limits:
            del self.limits[connection_id]
            logger.debug(
                f"Cleaned up rate limiter for connection {connection_id}"
            )

    def get_remaining_messages(self, connection_id: str) -> int:
        """
        Get number of messages remaining in current window.

        Args:
            connection_id: Unique identifier for the connection

        Returns:
            Number of messages that can still be sent
        """
        if connection_id not in self.limits:
            return self.max_messages

        current_time = time.time()
        timestamps = self.limits[connection_id]

        # Clean old timestamps
        cutoff_time = current_time - self.window_seconds
        while timestamps and timestamps[0] < cutoff_time:
            timestamps.popleft()

        return max(0, self.max_messages - len(timestamps))

    def get_stats(self) -> dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dict with active connections and total tracked
        """
        return {
            "tracked_connections": len(self.limits),
            "max_messages": self.max_messages,
            "window_seconds": self.window_seconds,
        }
