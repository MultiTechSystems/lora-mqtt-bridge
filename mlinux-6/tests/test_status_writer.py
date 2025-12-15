"""Tests for the StatusWriter class."""

import json
import os
import tempfile
import time

from lora_mqtt_bridge.utils.status_writer import StatusWriter


class TestStatusWriter:
    """Tests for StatusWriter."""

    def test_initialization(self):
        """Test StatusWriter initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir, update_interval=1.0)
            assert writer.app_dir == tmpdir
            assert writer.status_file == os.path.join(tmpdir, "status.json")
            assert writer.update_interval == 1.0

    def test_write_immediate(self):
        """Test writing status immediately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir)
            writer.write_immediate("Test message")

            with open(writer.status_file) as f:
                data = json.load(f)

            assert "pid" in data
            assert data["pid"] == str(os.getpid())
            assert data["AppInfo"] == "Test message"

    def test_set_local_connected(self):
        """Test setting local connection status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir)
            writer.set_local_connected(True)
            assert writer._local_connected is True

            writer.set_local_connected(False)
            assert writer._local_connected is False

    def test_set_remote_connected(self):
        """Test setting remote connection status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir)
            writer.set_remote_connected("broker1", True)
            writer.set_remote_connected("broker2", False)

            assert writer._remote_connections["broker1"] is True
            assert writer._remote_connections["broker2"] is False

    def test_increment_message_count(self):
        """Test incrementing message count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir)
            assert writer._message_count == 0

            writer.increment_message_count()
            assert writer._message_count == 1

            writer.increment_message_count()
            writer.increment_message_count()
            assert writer._message_count == 3

    def test_add_error(self):
        """Test adding errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir)
            assert len(writer._errors) == 0

            writer.add_error("Error 1")
            assert len(writer._errors) == 1

            # Add more than 5 errors to test limit
            for i in range(10):
                writer.add_error(f"Error {i}")

            assert len(writer._errors) == 5  # Should keep only last 5

    def test_clear_errors(self):
        """Test clearing errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir)
            writer.add_error("Error 1")
            writer.add_error("Error 2")
            assert len(writer._errors) == 2

            writer.clear_errors()
            assert len(writer._errors) == 0

    def test_build_status_message(self):
        """Test building status message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir)
            writer.set_local_connected(True)
            writer.set_remote_connected("cloud", True)
            writer.increment_message_count()

            message = writer._build_status_message()

            assert "Local:OK" in message
            assert "Remote:1/1" in message
            assert "Msgs:1" in message

    def test_build_status_message_disconnected(self):
        """Test status message when disconnected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir)
            writer.set_local_connected(False)
            writer.set_remote_connected("cloud", False)

            message = writer._build_status_message()

            assert "Local:DISC" in message
            assert "Remote:0/1" in message

    def test_build_status_message_with_errors(self):
        """Test status message with errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir)
            writer.set_local_connected(True)
            writer.add_error("Test error")

            message = writer._build_status_message()

            assert "Errs:1" in message

    def test_message_truncation(self):
        """Test that messages are truncated to 160 characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir)
            long_message = "x" * 200
            writer.set_app_info(long_message)
            assert len(writer._app_info) == 160

    def test_start_stop(self):
        """Test starting and stopping the status writer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = StatusWriter(app_dir=tmpdir, update_interval=0.1)
            writer.set_local_connected(True)

            writer.start()
            assert writer._running is True
            assert writer._thread is not None

            # Wait for at least one status update
            time.sleep(0.2)

            writer.stop()
            assert writer._running is False

            # Check that final status was written
            with open(writer.status_file) as f:
                data = json.load(f)
            assert data["AppInfo"] == "Stopped"
