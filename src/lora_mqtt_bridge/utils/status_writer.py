"""Status writer for mPower app-manager integration.

This module provides functionality to write status.json files
that are read by the mPower app-manager to display application
status in the web UI and DeviceHQ.

Compatible with Python 3.10+ and mLinux 7.1.0
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


class StatusWriter:
    """Write application status to status.json for mPower integration.

    The status.json file is read by app-manager to display application
    status in the mPower web UI and DeviceHQ.

    Attributes:
        app_dir: The application directory (from APP_DIR environment variable).
        status_file: Path to the status.json file.
        update_interval: Interval in seconds between status updates.
    """

    def __init__(
        self,
        app_dir: str | None = None,
        update_interval: float = 10.0,
    ) -> None:
        """Initialize the status writer.

        Args:
            app_dir: Application directory path. If None, uses APP_DIR env var.
            update_interval: Interval in seconds between automatic status updates.
        """
        self.app_dir = app_dir or os.getenv("APP_DIR") or "."
        self.status_file = os.path.join(self.app_dir, "status.json")
        self.update_interval = update_interval

        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # Status information
        self._app_info = "Starting..."
        self._extra_info: dict[str, Any] = {}

        # Connection status tracking
        self._local_connected = False
        self._remote_connections: dict[str, bool] = {}
        self._message_count = 0
        self._last_message_time: str | None = None
        self._errors: list[str] = []

    def start(self) -> None:
        """Start the background status update thread."""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()
        logger.info("Status writer started, writing to %s", self.status_file)

    def stop(self) -> None:
        """Stop the background status update thread."""
        self._running = False
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

        # Write final status
        self._write_status("Stopped")
        logger.info("Status writer stopped")

    def set_app_info(self, info: str) -> None:
        """Set the application info message.

        Args:
            info: Status message (max 160 characters for UI display).
        """
        with self._lock:
            # Truncate to 160 characters for mPower UI
            self._app_info = info[:160] if len(info) > 160 else info

    def set_local_connected(self, connected: bool) -> None:
        """Set the local broker connection status.

        Args:
            connected: Whether the local broker is connected.
        """
        with self._lock:
            self._local_connected = connected

    def set_remote_connected(self, name: str, connected: bool) -> None:
        """Set a remote broker connection status.

        Args:
            name: The remote broker name.
            connected: Whether the broker is connected.
        """
        with self._lock:
            self._remote_connections[name] = connected

    def increment_message_count(self) -> None:
        """Increment the forwarded message count."""
        with self._lock:
            self._message_count += 1
            self._last_message_time = time.strftime("%Y-%m-%d %H:%M:%S")

    def add_error(self, error: str) -> None:
        """Add an error to the error list.

        Args:
            error: Error message to add.
        """
        with self._lock:
            # Keep only last 5 errors
            self._errors.append(error)
            if len(self._errors) > 5:
                self._errors.pop(0)

    def clear_errors(self) -> None:
        """Clear all errors."""
        with self._lock:
            self._errors.clear()

    def _build_status_message(self) -> str:
        """Build the status message string.

        Returns:
            A status message string for display.
        """
        with self._lock:
            # Build connection status
            local_status = "Local:OK" if self._local_connected else "Local:DISC"

            remote_count = len(self._remote_connections)
            remote_connected = sum(1 for c in self._remote_connections.values() if c)

            if remote_count > 0:
                remote_status = f"Remote:{remote_connected}/{remote_count}"
            else:
                remote_status = "Remote:none"

            # Build message
            parts = [local_status, remote_status]

            if self._message_count > 0:
                parts.append(f"Msgs:{self._message_count}")

            if self._errors:
                parts.append(f"Errs:{len(self._errors)}")

            status = " | ".join(parts)

            # Add timestamp
            timestamp = time.strftime("%H:%M:%S")
            status = f"{status} @ {timestamp}"

            return status[:160]  # Truncate to 160 chars

    def _write_status(self, app_info: str | None = None) -> None:
        """Write the status.json file.

        Args:
            app_info: Optional override for app info message.
        """
        try:
            pid = os.getpid()
            info = app_info if app_info is not None else self._build_status_message()

            status_data = {
                "pid": str(pid),
                "AppInfo": info,
            }

            # Write atomically by writing to temp file first
            temp_file = self.status_file + ".tmp"
            with open(temp_file, "w") as f:
                json.dump(status_data, f)

            # Rename to final location
            os.replace(temp_file, self.status_file)

            logger.debug("Status updated: %s", info)

        except Exception as e:
            logger.warning("Failed to write status.json: %s", e)

    def _update_loop(self) -> None:
        """Background thread loop to update status periodically."""
        while self._running:
            self._write_status()
            self._stop_event.wait(timeout=self.update_interval)

    def write_immediate(self, message: str) -> None:
        """Write a status message immediately.

        Args:
            message: The status message to write.
        """
        self._write_status(message)


# Global status writer instance
_status_writer: StatusWriter | None = None


def get_status_writer() -> StatusWriter:
    """Get the global status writer instance.

    Returns:
        The global StatusWriter instance.
    """
    global _status_writer
    if _status_writer is None:
        _status_writer = StatusWriter()
    return _status_writer


def init_status_writer(
    app_dir: str | None = None,
    update_interval: float = 10.0,
) -> StatusWriter:
    """Initialize and return the global status writer.

    Args:
        app_dir: Application directory path.
        update_interval: Status update interval in seconds.

    Returns:
        The initialized StatusWriter instance.
    """
    global _status_writer
    _status_writer = StatusWriter(app_dir=app_dir, update_interval=update_interval)
    return _status_writer
