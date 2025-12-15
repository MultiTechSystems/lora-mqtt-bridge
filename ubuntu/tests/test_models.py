"""Tests for data models.

This module contains tests for the configuration and message models.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from lora_mqtt_bridge.models.config import (
    BridgeConfig,
    FieldFilterConfig,
    LocalBrokerConfig,
    MessageFilterConfig,
    RemoteBrokerConfig,
    TopicConfig,
    TopicFormat,
)
from lora_mqtt_bridge.models.message import LoRaMessage, MessageType

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


class TestTopicConfig:
    """Tests for TopicConfig model."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = TopicConfig()
        assert config.format == TopicFormat.LORA
        assert config.uplink_pattern == "lora/+/+/up"
        assert config.downlink_pattern == "lora/%s/down"

    def test_lora_format_patterns(self) -> None:
        """Test get pattern methods for LORA format."""
        config = TopicConfig(format=TopicFormat.LORA)
        assert config.get_uplink_pattern() == "lora/+/+/up"
        assert config.get_downlink_pattern() == "lora/%s/down"

    def test_scada_format_patterns(self) -> None:
        """Test get pattern methods for SCADA format."""
        config = TopicConfig(format=TopicFormat.SCADA)
        assert config.get_uplink_pattern() == "scada/+/up"
        assert config.get_downlink_pattern() == "scada/%s/down"

    def test_custom_patterns(self) -> None:
        """Test custom pattern values."""
        config = TopicConfig(
            format=TopicFormat.LORA,
            uplink_pattern="custom/+/+/uplink",
            downlink_pattern="custom/%s/downlink",
        )
        assert config.uplink_pattern == "custom/+/+/uplink"
        assert config.downlink_pattern == "custom/%s/downlink"

    def test_empty_pattern_validation(self) -> None:
        """Test that empty patterns raise validation error."""
        with pytest.raises(ValueError):
            TopicConfig(uplink_pattern="")

        with pytest.raises(ValueError):
            TopicConfig(downlink_pattern="   ")


class TestMessageFilterConfig:
    """Tests for MessageFilterConfig model."""

    def test_default_empty_lists(self) -> None:
        """Test that default lists are empty."""
        config = MessageFilterConfig()
        assert config.deveui_whitelist == []
        assert config.deveui_blacklist == []
        assert config.joineui_whitelist == []
        assert config.joineui_blacklist == []
        assert config.appeui_whitelist == []
        assert config.appeui_blacklist == []

    def test_eui_normalization(self) -> None:
        """Test that EUI values are normalized."""
        config = MessageFilterConfig(
            deveui_whitelist=["0011223344556677", "AA:BB:CC:DD:EE:FF:00:11"],
        )
        assert "00-11-22-33-44-55-66-77" in config.deveui_whitelist
        assert "aa-bb-cc-dd-ee-ff-00-11" in config.deveui_whitelist

    def test_eui_with_dashes(self) -> None:
        """Test EUI values that already have dashes."""
        config = MessageFilterConfig(
            deveui_whitelist=["00-11-22-33-44-55-66-77"],
        )
        assert "00-11-22-33-44-55-66-77" in config.deveui_whitelist


class TestFieldFilterConfig:
    """Tests for FieldFilterConfig model."""

    def test_default_always_include(self) -> None:
        """Test default always-include fields."""
        config = FieldFilterConfig()
        assert "deveui" in config.always_include
        assert "appeui" in config.always_include
        assert "time" in config.always_include

    def test_custom_include_fields(self) -> None:
        """Test custom include fields."""
        config = FieldFilterConfig(
            include_fields=["deveui", "port", "data"],
        )
        assert config.include_fields == ["deveui", "port", "data"]


class TestLocalBrokerConfig:
    """Tests for LocalBrokerConfig model."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = LocalBrokerConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 1883
        assert config.username is None
        assert config.password is None
        assert config.keepalive == 60

    def test_port_validation(self) -> None:
        """Test port number validation."""
        with pytest.raises(ValueError):
            LocalBrokerConfig(port=0)

        with pytest.raises(ValueError):
            LocalBrokerConfig(port=70000)

        # Valid ports should work
        config = LocalBrokerConfig(port=8883)
        assert config.port == 8883


class TestRemoteBrokerConfig:
    """Tests for RemoteBrokerConfig model."""

    def test_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValueError):
            RemoteBrokerConfig()  # type: ignore[call-arg]

        # Should work with required fields
        config = RemoteBrokerConfig(name="test", host="example.com")
        assert config.name == "test"
        assert config.host == "example.com"

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = RemoteBrokerConfig(name="test", host="example.com")
        assert config.enabled is True
        assert config.port == 1883
        assert config.qos == 1
        assert config.retain is True
        assert config.clean_session is False


class TestLoRaMessage:
    """Tests for LoRaMessage model."""

    def test_from_mqtt_payload(self, sample_uplink_payload: dict[str, Any]) -> None:
        """Test creating message from MQTT payload.

        Args:
            sample_uplink_payload: Sample payload fixture.
        """
        message = LoRaMessage.from_mqtt_payload(
            sample_uplink_payload,
            topic="lora/test/up",
            message_type=MessageType.UPLINK,
        )
        assert message.deveui == "00-11-22-33-44-55-66-77"
        assert message.appeui == "aa-bb-cc-dd-ee-ff-00-11"
        assert message.port == 1
        assert message.message_type == MessageType.UPLINK

    def test_missing_deveui_raises_error(self) -> None:
        """Test that missing deveui raises ValueError."""
        with pytest.raises(ValueError, match="deveui"):
            LoRaMessage.from_mqtt_payload({"port": 1, "data": "test"})

    def test_eui_normalization(self) -> None:
        """Test that EUI values are normalized."""
        message = LoRaMessage(
            deveui="0011223344556677",
            appeui="AABBCCDDEEFF0011",
        )
        assert message.deveui == "00-11-22-33-44-55-66-77"
        assert message.appeui == "aa-bb-cc-dd-ee-ff-00-11"

    def test_get_effective_joineui(self) -> None:
        """Test get_effective_joineui method."""
        # With joineui set
        message = LoRaMessage(
            deveui="00-11-22-33-44-55-66-77",
            joineui="aa-bb-cc-dd-ee-ff-00-11",
            appeui="ff-ff-ff-ff-ff-ff-ff-ff",
        )
        assert message.get_effective_joineui() == "aa-bb-cc-dd-ee-ff-00-11"

        # Without joineui, falls back to appeui
        message = LoRaMessage(
            deveui="00-11-22-33-44-55-66-77",
            appeui="ff-ff-ff-ff-ff-ff-ff-ff",
        )
        assert message.get_effective_joineui() == "ff-ff-ff-ff-ff-ff-ff-ff"

    def test_to_filtered_dict(self, sample_uplink_payload: dict[str, Any]) -> None:
        """Test filtering message fields.

        Args:
            sample_uplink_payload: Sample payload fixture.
        """
        message = LoRaMessage.from_mqtt_payload(sample_uplink_payload)

        # Test with exclude fields
        filtered = message.to_filtered_dict(exclude_fields=["rssi", "snr"])
        assert "rssi" not in filtered
        assert "snr" not in filtered
        assert "deveui" in filtered  # Always included

        # Test with include fields
        filtered = message.to_filtered_dict(include_fields=["deveui", "port"])
        assert "port" in filtered
        assert "deveui" in filtered
        assert "freq" not in filtered


class TestBridgeConfig:
    """Tests for BridgeConfig model."""

    def test_from_dict(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "local_broker": {
                "host": "localhost",
                "port": 1883,
            },
            "remote_brokers": [
                {
                    "name": "test",
                    "host": "remote.example.com",
                    "port": 8883,
                }
            ],
        }
        config = BridgeConfig.from_dict(data)
        assert config.local_broker.host == "localhost"
        assert len(config.remote_brokers) == 1
        assert config.remote_brokers[0].name == "test"

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = BridgeConfig()
        assert config.local_broker is not None
        assert config.remote_brokers == []
        assert config.reconnect_delay == 1.0
        assert config.max_reconnect_delay == 60.0
