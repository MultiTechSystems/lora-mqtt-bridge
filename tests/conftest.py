"""Pytest configuration and shared fixtures.

This module provides shared fixtures for testing the LoRa MQTT Bridge.
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
    TLSConfig,
    TopicConfig,
    TopicFormat,
)
from lora_mqtt_bridge.models.message import LoRaMessage, MessageType

if TYPE_CHECKING:
    pass


@pytest.fixture
def sample_uplink_payload() -> dict[str, Any]:
    """Create a sample uplink message payload.

    Returns:
        Dictionary containing sample uplink data.
    """
    return {
        "deveui": "00-11-22-33-44-55-66-77",
        "appeui": "aa-bb-cc-dd-ee-ff-00-11",
        "gweui": "ff-ee-dd-cc-bb-aa-99-88",
        "time": "2024-01-15T10:30:00Z",
        "port": 1,
        "data": "SGVsbG8gV29ybGQh",
        "fcnt": 42,
        "rssi": -85,
        "snr": 7.5,
        "freq": 868.1,
        "dr": "SF7BW125",
    }


@pytest.fixture
def sample_lora_message(sample_uplink_payload: dict[str, Any]) -> LoRaMessage:
    """Create a sample LoRaMessage instance.

    Args:
        sample_uplink_payload: The sample payload fixture.

    Returns:
        A LoRaMessage instance.
    """
    return LoRaMessage.from_mqtt_payload(
        sample_uplink_payload,
        topic="lora/aa-bb-cc-dd-ee-ff-00-11/00-11-22-33-44-55-66-77/up",
        message_type=MessageType.UPLINK,
    )


@pytest.fixture
def local_broker_config() -> LocalBrokerConfig:
    """Create a local broker configuration for testing.

    Returns:
        A LocalBrokerConfig instance.
    """
    return LocalBrokerConfig(
        host="127.0.0.1",
        port=1883,
        username=None,
        password=None,
        client_id="test-local-client",
        topics=TopicConfig(
            format=TopicFormat.LORA,
            uplink_pattern="lora/+/+/up",
            downlink_pattern="lora/%s/down",
        ),
        keepalive=60,
    )


@pytest.fixture
def remote_broker_config() -> RemoteBrokerConfig:
    """Create a remote broker configuration for testing.

    Returns:
        A RemoteBrokerConfig instance.
    """
    return RemoteBrokerConfig(
        name="test-remote",
        enabled=True,
        host="remote.example.com",
        port=8883,
        username="testuser",
        password="testpass",
        client_id="test-remote-client",
        tls=TLSConfig(
            enabled=True,
            verify_hostname=False,
            insecure=True,
        ),
        topics=TopicConfig(
            format=TopicFormat.LORA,
            uplink_pattern="lorawan/%(appeui)s/%(deveui)s/up",
            downlink_pattern="lorawan/%(deveui)s/down",
        ),
        message_filter=MessageFilterConfig(
            deveui_whitelist=[],
            deveui_blacklist=[],
        ),
        field_filter=FieldFilterConfig(
            include_fields=[],
            exclude_fields=["rssi", "snr"],
        ),
        keepalive=60,
        clean_session=False,
        qos=1,
        retain=True,
    )


@pytest.fixture
def bridge_config(
    local_broker_config: LocalBrokerConfig,
    remote_broker_config: RemoteBrokerConfig,
) -> BridgeConfig:
    """Create a complete bridge configuration for testing.

    Args:
        local_broker_config: The local broker config fixture.
        remote_broker_config: The remote broker config fixture.

    Returns:
        A BridgeConfig instance.
    """
    return BridgeConfig(
        local_broker=local_broker_config,
        remote_brokers=[remote_broker_config],
    )


@pytest.fixture
def message_filter_config_with_whitelist() -> MessageFilterConfig:
    """Create a message filter configuration with whitelists.

    Returns:
        A MessageFilterConfig instance with whitelist entries.
    """
    return MessageFilterConfig(
        deveui_whitelist=["00-11-22-33-44-55-66-77", "aa-bb-cc-dd-ee-ff-00-11"],
        deveui_blacklist=[],
        joineui_whitelist=[],
        joineui_blacklist=[],
        appeui_whitelist=["aa-bb-cc-dd-ee-ff-00-11"],
        appeui_blacklist=[],
    )


@pytest.fixture
def message_filter_config_with_blacklist() -> MessageFilterConfig:
    """Create a message filter configuration with blacklists.

    Returns:
        A MessageFilterConfig instance with blacklist entries.
    """
    return MessageFilterConfig(
        deveui_whitelist=[],
        deveui_blacklist=["ff-ff-ff-ff-ff-ff-ff-ff"],
        joineui_whitelist=[],
        joineui_blacklist=[],
        appeui_whitelist=[],
        appeui_blacklist=["00-00-00-00-00-00-00-00"],
    )


@pytest.fixture
def field_filter_config() -> FieldFilterConfig:
    """Create a field filter configuration.

    Returns:
        A FieldFilterConfig instance.
    """
    return FieldFilterConfig(
        include_fields=["deveui", "appeui", "time", "port", "data"],
        exclude_fields=[],
        always_include=["deveui", "time"],
    )
