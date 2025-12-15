"""Tests for the MQTT bridge manager.

This module contains tests for the MQTTBridge class.
Compatible with Python 3.8+ (mLinux 6.3.5)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

from lora_mqtt_bridge.bridge import MQTTBridge
from lora_mqtt_bridge.models.config import (
    BridgeConfig,
    LocalBrokerConfig,
    RemoteBrokerConfig,
)
from lora_mqtt_bridge.models.message import MessageType

if TYPE_CHECKING:
    pass


class TestMQTTBridge:
    """Tests for MQTTBridge class."""

    def test_initialization(self, bridge_config: BridgeConfig) -> None:
        """Test bridge initialization.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        assert bridge.local_client is not None
        assert len(bridge.remote_clients) == 1
        assert "test-remote" in bridge.remote_clients

    def test_disabled_remote_broker_not_created(
        self,
        local_broker_config: LocalBrokerConfig,
    ) -> None:
        """Test that disabled brokers are not created.

        Args:
            local_broker_config: Local broker config fixture.
        """
        config = BridgeConfig(
            local_broker=local_broker_config,
            remote_brokers=[
                RemoteBrokerConfig(
                    name="enabled",
                    host="enabled.example.com",
                    enabled=True,
                ),
                RemoteBrokerConfig(
                    name="disabled",
                    host="disabled.example.com",
                    enabled=False,
                ),
            ],
        )

        bridge = MQTTBridge(config)

        assert len(bridge.remote_clients) == 1
        assert "enabled" in bridge.remote_clients
        assert "disabled" not in bridge.remote_clients

    def test_get_status(self, bridge_config: BridgeConfig) -> None:
        """Test getting bridge status.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)
        status = bridge.get_status()

        assert "running" in status
        assert "local_broker" in status
        assert "remote_brokers" in status
        assert status["running"] is False
        assert status["local_broker"]["connected"] is False

    @patch("lora_mqtt_bridge.clients.local.LocalMQTTClient.connect")
    @patch("lora_mqtt_bridge.clients.remote.RemoteMQTTClient.connect")
    def test_start_connects_all_clients(
        self,
        mock_remote_connect: MagicMock,
        mock_local_connect: MagicMock,
        bridge_config: BridgeConfig,
    ) -> None:
        """Test that start() connects all clients.

        Args:
            mock_remote_connect: Mocked remote connect method.
            mock_local_connect: Mocked local connect method.
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)
        bridge.start()

        mock_local_connect.assert_called_once()
        mock_remote_connect.assert_called_once()
        assert bridge._running is True

    @patch("lora_mqtt_bridge.clients.local.LocalMQTTClient.disconnect")
    @patch("lora_mqtt_bridge.clients.remote.RemoteMQTTClient.disconnect")
    def test_stop_disconnects_all_clients(
        self,
        mock_remote_disconnect: MagicMock,
        mock_local_disconnect: MagicMock,
        bridge_config: BridgeConfig,
    ) -> None:
        """Test that stop() disconnects all clients.

        Args:
            mock_remote_disconnect: Mocked remote disconnect method.
            mock_local_disconnect: Mocked local disconnect method.
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)
        bridge._running = True
        bridge.stop()

        mock_local_disconnect.assert_called_once()
        mock_remote_disconnect.assert_called_once()
        assert bridge._running is False

    def test_parse_message_type_uplink(self, bridge_config: BridgeConfig) -> None:
        """Test parsing uplink message type from topic.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        assert bridge._parse_message_type("lora/test/up") == MessageType.UPLINK
        assert bridge._parse_message_type("lora/eui/device/up") == MessageType.UPLINK

    def test_parse_message_type_downlink(self, bridge_config: BridgeConfig) -> None:
        """Test parsing downlink message type from topic.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        assert bridge._parse_message_type("lora/test/down") == MessageType.DOWNLINK

    def test_parse_message_type_joined(self, bridge_config: BridgeConfig) -> None:
        """Test parsing joined message type from topic.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        assert bridge._parse_message_type("lora/device/joined") == MessageType.JOINED

    def test_parse_message_type_unknown(self, bridge_config: BridgeConfig) -> None:
        """Test parsing unknown message type from topic.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        assert bridge._parse_message_type("lora/device/unknown") is None

    def test_handle_local_message_invalid_json(
        self, bridge_config: BridgeConfig
    ) -> None:
        """Test handling message with invalid JSON.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        # Should not raise, just log error
        bridge._handle_local_message("lora/test/up", b"not valid json")

    def test_handle_local_message_missing_deveui(
        self, bridge_config: BridgeConfig
    ) -> None:
        """Test handling message without deveui.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        payload = json.dumps({"port": 1, "data": "test"}).encode("utf-8")

        # Should not raise, just log error
        bridge._handle_local_message("lora/test/up", payload)

    @patch("lora_mqtt_bridge.clients.remote.RemoteMQTTClient.forward_message")
    def test_handle_local_message_forwards_to_remotes(
        self,
        mock_forward: MagicMock,
        bridge_config: BridgeConfig,
        sample_uplink_payload: dict[str, Any],
    ) -> None:
        """Test that local messages are forwarded to remote brokers.

        Args:
            mock_forward: Mocked forward_message method.
            bridge_config: Bridge configuration fixture.
            sample_uplink_payload: Sample payload fixture.
        """
        mock_forward.return_value = True

        bridge = MQTTBridge(bridge_config)

        payload = json.dumps(sample_uplink_payload).encode("utf-8")
        bridge._handle_local_message("lora/test/test/up", payload)

        mock_forward.assert_called_once()

    @patch("lora_mqtt_bridge.clients.local.LocalMQTTClient.publish_downlink")
    def test_handle_remote_message_downlink(
        self,
        mock_publish: MagicMock,
        bridge_config: BridgeConfig,
    ) -> None:
        """Test handling downlink from remote broker.

        Args:
            mock_publish: Mocked publish_downlink method.
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        payload = json.dumps({
            "deveui": "00-11-22-33-44-55-66-77",
            "port": 1,
            "data": "dGVzdA==",
        }).encode("utf-8")

        bridge._handle_remote_message("lorawan/test/down", payload)

        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "00-11-22-33-44-55-66-77"

    @patch("lora_mqtt_bridge.clients.local.LocalMQTTClient.publish_clear")
    def test_handle_remote_message_clear(
        self,
        mock_clear: MagicMock,
        bridge_config: BridgeConfig,
    ) -> None:
        """Test handling clear command from remote broker.

        Args:
            mock_clear: Mocked publish_clear method.
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        payload = json.dumps({
            "deveui": "00-11-22-33-44-55-66-77",
        }).encode("utf-8")

        bridge._handle_remote_message("lorawan/test/clear", payload)

        mock_clear.assert_called_once()
        assert mock_clear.call_args[0][0] == "00-11-22-33-44-55-66-77"


class TestMQTTBridgeDynamicBrokers:
    """Tests for dynamic broker management."""

    def test_add_remote_broker(self, bridge_config: BridgeConfig) -> None:
        """Test adding a remote broker dynamically.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        new_config = RemoteBrokerConfig(
            name="new-broker",
            host="new.example.com",
        )

        bridge.add_remote_broker(new_config)

        assert "new-broker" in bridge.remote_clients

    def test_add_duplicate_broker_ignored(
        self, bridge_config: BridgeConfig
    ) -> None:
        """Test that duplicate broker names are ignored.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        original_count = len(bridge.remote_clients)

        new_config = RemoteBrokerConfig(
            name="test-remote",  # Same name as existing
            host="new.example.com",
        )

        bridge.add_remote_broker(new_config)

        assert len(bridge.remote_clients) == original_count

    def test_remove_remote_broker(self, bridge_config: BridgeConfig) -> None:
        """Test removing a remote broker.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        assert "test-remote" in bridge.remote_clients

        result = bridge.remove_remote_broker("test-remote")

        assert result is True
        assert "test-remote" not in bridge.remote_clients

    def test_remove_nonexistent_broker(self, bridge_config: BridgeConfig) -> None:
        """Test removing a broker that doesn't exist.

        Args:
            bridge_config: Bridge configuration fixture.
        """
        bridge = MQTTBridge(bridge_config)

        result = bridge.remove_remote_broker("nonexistent")

        assert result is False
