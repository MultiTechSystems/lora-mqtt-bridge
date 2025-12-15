"""Tests for MQTT client classes.

This module contains tests for the MQTT client implementations.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from lora_mqtt_bridge.clients.local import LocalMQTTClient
from lora_mqtt_bridge.clients.remote import RemoteMQTTClient
from lora_mqtt_bridge.models.config import (
    FieldFilterConfig,
    LocalBrokerConfig,
    MessageFilterConfig,
    RemoteBrokerConfig,
)
from lora_mqtt_bridge.models.message import LoRaMessage

if TYPE_CHECKING:
    pass


class TestLocalMQTTClient:
    """Tests for LocalMQTTClient class."""

    def test_initialization(self, local_broker_config: LocalBrokerConfig) -> None:
        """Test client initialization.

        Args:
            local_broker_config: Local broker config fixture.
        """
        client = LocalMQTTClient(local_broker_config)
        assert client.name == "local"
        assert client.host == "127.0.0.1"
        assert client.port == 1883
        assert client.is_connected is False

    def test_get_subscribed_topics_empty_before_connect(
        self, local_broker_config: LocalBrokerConfig
    ) -> None:
        """Test subscribed topics list is empty before connection.

        Args:
            local_broker_config: Local broker config fixture.
        """
        client = LocalMQTTClient(local_broker_config)
        assert client.get_subscribed_topics() == []

    @patch("lora_mqtt_bridge.clients.base.mqtt.Client")
    def test_publish_downlink(
        self,
        mock_mqtt_class: MagicMock,
        local_broker_config: LocalBrokerConfig,
    ) -> None:
        """Test publishing downlink message.

        Args:
            mock_mqtt_class: Mocked MQTT client class.
            local_broker_config: Local broker config fixture.
        """
        client = LocalMQTTClient(local_broker_config)

        # Mock the client
        mock_client = MagicMock()
        client._client = mock_client
        client._connected = True

        # Publish downlink
        deveui = "00-11-22-33-44-55-66-77"
        payload = json.dumps({"port": 1, "data": "dGVzdA=="})
        client.publish_downlink(deveui, payload)

        # Verify publish was called with correct topic
        mock_client.publish.assert_called_once()
        args = mock_client.publish.call_args
        assert "lora/00-11-22-33-44-55-66-77/down" in args[0]

    @patch("lora_mqtt_bridge.clients.base.mqtt.Client")
    def test_publish_clear(
        self,
        mock_mqtt_class: MagicMock,
        local_broker_config: LocalBrokerConfig,
    ) -> None:
        """Test publishing queue clear message.

        Args:
            mock_mqtt_class: Mocked MQTT client class.
            local_broker_config: Local broker config fixture.
        """
        client = LocalMQTTClient(local_broker_config)

        # Mock the client
        mock_client = MagicMock()
        client._client = mock_client
        client._connected = True

        # Publish clear
        deveui = "00-11-22-33-44-55-66-77"
        client.publish_clear(deveui)

        # Verify publish was called
        mock_client.publish.assert_called_once()
        args = mock_client.publish.call_args
        assert "clear" in args[0][0]


class TestRemoteMQTTClient:
    """Tests for RemoteMQTTClient class."""

    def test_initialization(self, remote_broker_config: RemoteBrokerConfig) -> None:
        """Test client initialization.

        Args:
            remote_broker_config: Remote broker config fixture.
        """
        client = RemoteMQTTClient(remote_broker_config)
        assert client.name == "test-remote"
        assert client.host == "remote.example.com"
        assert client.port == 8883
        assert client.is_connected is False

    def test_message_filter_initialized(self, remote_broker_config: RemoteBrokerConfig) -> None:
        """Test that message filter is initialized.

        Args:
            remote_broker_config: Remote broker config fixture.
        """
        client = RemoteMQTTClient(remote_broker_config)
        assert client.message_filter is not None

    def test_field_filter_initialized(self, remote_broker_config: RemoteBrokerConfig) -> None:
        """Test that field filter is initialized.

        Args:
            remote_broker_config: Remote broker config fixture.
        """
        client = RemoteMQTTClient(remote_broker_config)
        assert client.field_filter is not None

    def test_forward_message_filtered_out(self, remote_broker_config: RemoteBrokerConfig) -> None:
        """Test that filtered messages are not forwarded.

        Args:
            remote_broker_config: Remote broker config fixture.
        """
        # Configure with whitelist that doesn't include our message
        remote_broker_config.message_filter = MessageFilterConfig(
            deveui_whitelist=["ff-ff-ff-ff-ff-ff-ff-ff"],
        )
        client = RemoteMQTTClient(remote_broker_config)

        message = LoRaMessage(
            deveui="00-11-22-33-44-55-66-77",
            appeui="aa-bb-cc-dd-ee-ff-00-11",
            raw_data={"deveui": "00-11-22-33-44-55-66-77"},
        )

        # Should return False (filtered out)
        result = client.forward_message(message)
        assert result is False

    def test_forward_message_queued_when_disconnected(
        self,
        remote_broker_config: RemoteBrokerConfig,
        sample_lora_message: LoRaMessage,
    ) -> None:
        """Test that messages are queued when disconnected.

        Args:
            remote_broker_config: Remote broker config fixture.
            sample_lora_message: Sample message fixture.
        """
        # Clear the whitelist so message passes filter
        remote_broker_config.message_filter = MessageFilterConfig()
        client = RemoteMQTTClient(remote_broker_config)

        # Not connected
        assert client.is_connected is False

        # Forward message - should be queued
        client.forward_message(sample_lora_message)

        # Check queue size
        assert client.get_queue_size() > 0

    def test_queue_size_limit(self, remote_broker_config: RemoteBrokerConfig) -> None:
        """Test that message queue has size limit.

        Args:
            remote_broker_config: Remote broker config fixture.
        """
        remote_broker_config.message_filter = MessageFilterConfig()
        client = RemoteMQTTClient(remote_broker_config)
        client._max_queue_size = 5  # Set small limit for testing

        # Queue more messages than limit
        for i in range(10):
            message = LoRaMessage(
                deveui=f"00-11-22-33-44-55-66-{i:02d}",
                raw_data={"deveui": f"00-11-22-33-44-55-66-{i:02d}"},
            )
            client.forward_message(message)

        # Queue should be at limit
        assert client.get_queue_size() == 5

    def test_build_uplink_topic_format_string(
        self, remote_broker_config: RemoteBrokerConfig
    ) -> None:
        """Test building uplink topic with format string.

        Args:
            remote_broker_config: Remote broker config fixture.
        """
        client = RemoteMQTTClient(remote_broker_config)

        message = LoRaMessage(
            deveui="00-11-22-33-44-55-66-77",
            appeui="aa-bb-cc-dd-ee-ff-00-11",
        )

        topic = client._build_uplink_topic(message)

        # Should use format string pattern
        assert "aa-bb-cc-dd-ee-ff-00-11" in topic
        assert "00-11-22-33-44-55-66-77" in topic
        assert topic.endswith("/up")

    def test_handle_downlink_valid(self, remote_broker_config: RemoteBrokerConfig) -> None:
        """Test handling valid downlink message.

        Args:
            remote_broker_config: Remote broker config fixture.
        """
        client = RemoteMQTTClient(remote_broker_config)

        payload = json.dumps(
            {
                "deveui": "00-11-22-33-44-55-66-77",
                "port": 1,
                "data": "dGVzdA==",
            }
        ).encode("utf-8")

        result = client.handle_downlink("test/down", payload)

        assert result is not None
        assert result["deveui"] == "00-11-22-33-44-55-66-77"
        assert result["port"] == 1

    def test_handle_downlink_missing_deveui(self, remote_broker_config: RemoteBrokerConfig) -> None:
        """Test handling downlink without deveui.

        Args:
            remote_broker_config: Remote broker config fixture.
        """
        client = RemoteMQTTClient(remote_broker_config)

        payload = json.dumps({"port": 1, "data": "dGVzdA=="}).encode("utf-8")

        result = client.handle_downlink("test/down", payload)

        assert result is None

    def test_handle_downlink_invalid_json(self, remote_broker_config: RemoteBrokerConfig) -> None:
        """Test handling downlink with invalid JSON.

        Args:
            remote_broker_config: Remote broker config fixture.
        """
        client = RemoteMQTTClient(remote_broker_config)

        payload = b"not valid json"

        result = client.handle_downlink("test/down", payload)

        assert result is None


class TestRemoteMQTTClientFieldFiltering:
    """Tests for field filtering in RemoteMQTTClient."""

    def test_field_filter_applied_on_forward(
        self,
        sample_lora_message: LoRaMessage,
    ) -> None:
        """Test that field filter is applied when forwarding.

        Args:
            sample_lora_message: Sample message fixture.
        """
        config = RemoteBrokerConfig(
            name="test",
            host="example.com",
            message_filter=MessageFilterConfig(),
            field_filter=FieldFilterConfig(
                exclude_fields=["rssi", "snr"],
                always_include=["deveui", "time"],
            ),
        )
        client = RemoteMQTTClient(config)

        # Mock publish to capture payload
        published_payloads: list[tuple[str, str]] = []

        def capture_publish(topic: str, payload: str) -> None:
            published_payloads.append((topic, payload))

        client._queue_message = capture_publish  # type: ignore[assignment]

        # Forward message (will be queued since not connected)
        client.forward_message(sample_lora_message)

        # Check that rssi and snr were filtered out
        assert len(published_payloads) == 1
        _, payload_str = published_payloads[0]
        payload = json.loads(payload_str)

        assert "deveui" in payload
        assert "rssi" not in payload
        assert "snr" not in payload
