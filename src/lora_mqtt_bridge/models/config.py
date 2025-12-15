"""Configuration models for the LoRa MQTT Bridge.

This module defines Pydantic models for configuration of the MQTT bridge,
including local broker settings, remote broker settings, and filtering options.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TopicFormat(str, Enum):
    """Enum for supported topic formats."""

    LORA = "lora"
    SCADA = "scada"


class TopicConfig(BaseModel):
    """Configuration for MQTT topic formats.

    Attributes:
        format: The topic format to use (lora or scada).
        uplink_pattern: Pattern for uplink topics with wildcards.
        downlink_pattern: Pattern for downlink topics with %s for deveui.
    """

    format: TopicFormat = Field(default=TopicFormat.LORA)
    uplink_pattern: str = Field(default="lora/+/+/up")
    downlink_pattern: str = Field(default="lora/%s/down")

    @field_validator("uplink_pattern", "downlink_pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate that pattern is not empty.

        Args:
            v: The pattern string to validate.

        Returns:
            The validated pattern string.

        Raises:
            ValueError: If the pattern is empty.
        """
        if not v or not v.strip():
            raise ValueError("Pattern cannot be empty")
        return v

    def get_uplink_pattern(self) -> str:
        """Get the uplink topic pattern based on format.

        Returns:
            The uplink topic pattern string.
        """
        if self.format == TopicFormat.SCADA:
            return "scada/+/up"
        return self.uplink_pattern

    def get_downlink_pattern(self) -> str:
        """Get the downlink topic pattern based on format.

        Returns:
            The downlink topic pattern string.
        """
        if self.format == TopicFormat.SCADA:
            return "scada/%s/down"
        return self.downlink_pattern


class LocalBrokerConfig(BaseModel):
    """Configuration for the local MQTT broker connection.

    Attributes:
        host: The hostname or IP address of the local broker.
        port: The port number of the local broker.
        username: Optional username for authentication.
        password: Optional password for authentication.
        client_id: The client ID to use for the connection.
        topics: Topic configuration for subscriptions and publishes.
        keepalive: The keepalive interval in seconds.
    """

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=1883, ge=1, le=65535)
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)
    client_id: str = Field(default="lora-mqtt-bridge-local")
    topics: TopicConfig = Field(default_factory=TopicConfig)
    keepalive: int = Field(default=60, ge=10, le=3600)


class MessageFilterConfig(BaseModel):
    """Configuration for filtering messages by device identifiers.

    Attributes:
        deveui_whitelist: List of DevEUI values to allow (empty = allow all).
        deveui_blacklist: List of DevEUI values to block.
        joineui_whitelist: List of JoinEUI values to allow (empty = allow all).
        joineui_blacklist: List of JoinEUI values to block.
        appeui_whitelist: List of AppEUI values to allow (empty = allow all).
        appeui_blacklist: List of AppEUI values to block.
    """

    deveui_whitelist: list[str] = Field(default_factory=list)
    deveui_blacklist: list[str] = Field(default_factory=list)
    joineui_whitelist: list[str] = Field(default_factory=list)
    joineui_blacklist: list[str] = Field(default_factory=list)
    appeui_whitelist: list[str] = Field(default_factory=list)
    appeui_blacklist: list[str] = Field(default_factory=list)

    @field_validator(
        "deveui_whitelist",
        "deveui_blacklist",
        "joineui_whitelist",
        "joineui_blacklist",
        "appeui_whitelist",
        "appeui_blacklist",
    )
    @classmethod
    def normalize_eui_list(cls, v: list[str]) -> list[str]:
        """Normalize EUI values to lowercase with dashes.

        Args:
            v: List of EUI strings to normalize.

        Returns:
            List of normalized EUI strings.
        """
        normalized = []
        for eui in v:
            # Remove colons and convert to lowercase with dashes
            clean = eui.replace(":", "").replace("-", "").lower()
            if len(clean) == 16:
                # Format as xx-xx-xx-xx-xx-xx-xx-xx
                normalized.append("-".join([clean[i : i + 2] for i in range(0, 16, 2)]))
            else:
                normalized.append(eui.lower())
        return normalized


class FieldFilterConfig(BaseModel):
    """Configuration for filtering fields in uplink messages.

    Attributes:
        include_fields: List of field names to include (empty = include all).
        exclude_fields: List of field names to exclude.
        always_include: Fields that are always included regardless of filters.
    """

    include_fields: list[str] = Field(default_factory=list)
    exclude_fields: list[str] = Field(default_factory=list)
    always_include: list[str] = Field(default_factory=lambda: ["deveui", "appeui", "time"])


class TLSConfig(BaseModel):
    """Configuration for TLS/SSL connections.

    Attributes:
        enabled: Whether TLS is enabled.
        ca_cert: Path to CA certificate file or certificate content.
        client_cert: Path to client certificate file or certificate content.
        client_key: Path to client key file or key content.
        verify_hostname: Whether to verify the server hostname.
        insecure: Allow insecure connections (skip certificate verification).
    """

    enabled: bool = Field(default=False)
    ca_cert: str | None = Field(default=None)
    client_cert: str | None = Field(default=None)
    client_key: str | None = Field(default=None)
    verify_hostname: bool = Field(default=True)
    insecure: bool = Field(default=False)


class RemoteBrokerConfig(BaseModel):
    """Configuration for a remote MQTT broker connection.

    Attributes:
        name: A unique name identifier for this remote broker.
        enabled: Whether this broker connection is enabled.
        host: The hostname or IP address of the remote broker.
        port: The port number of the remote broker.
        username: Optional username for authentication.
        password: Optional password for authentication.
        client_id: The client ID to use for the connection.
        tls: TLS/SSL configuration.
        source_topic_format: Which local topic format to listen for (lora, scada, or both).
        topics: Topic configuration for this broker (for publishing).
        message_filter: Filter for messages based on device identifiers.
        field_filter: Filter for fields in uplink messages.
        keepalive: The keepalive interval in seconds.
        clean_session: Whether to use a clean session.
        qos: Default QoS level for publishes.
        retain: Whether to retain published messages.
    """

    name: str = Field(...)
    enabled: bool = Field(default=True)
    host: str = Field(...)
    port: int = Field(default=1883, ge=1, le=65535)
    username: str | None = Field(default=None)
    password: str | None = Field(default=None)
    client_id: str | None = Field(default=None)
    tls: TLSConfig = Field(default_factory=TLSConfig)
    source_topic_format: list[TopicFormat] = Field(
        default_factory=lambda: [TopicFormat.LORA],
        description="Which local topic formats to forward (lora, scada, or both)",
    )
    topics: TopicConfig = Field(default_factory=TopicConfig)
    message_filter: MessageFilterConfig = Field(default_factory=MessageFilterConfig)
    field_filter: FieldFilterConfig = Field(default_factory=FieldFilterConfig)
    keepalive: int = Field(default=60, ge=10, le=3600)
    clean_session: bool = Field(default=False)
    qos: int = Field(default=1, ge=0, le=2)
    retain: bool = Field(default=True)

    @field_validator("source_topic_format", mode="before")
    @classmethod
    def normalize_source_topic_format(
        cls, v: str | list[str] | TopicFormat | list[TopicFormat]
    ) -> list[TopicFormat]:
        """Normalize source_topic_format to a list of TopicFormat.

        Args:
            v: A single format or list of formats (strings or TopicFormat).

        Returns:
            List of TopicFormat values.
        """
        if isinstance(v, str):
            return [TopicFormat(v)]
        if isinstance(v, TopicFormat):
            return [v]
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, str):
                    result.append(TopicFormat(item))
                elif isinstance(item, TopicFormat):
                    result.append(item)
                else:
                    result.append(item)
            return result
        return v


class LogConfig(BaseModel):
    """Configuration for logging.

    Attributes:
        level: The log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format: The log format string.
        file: Optional file path for file logging.
    """

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file: str | None = Field(default=None)


class BridgeConfig(BaseModel):
    """Main configuration for the MQTT Bridge application.

    Attributes:
        local_broker: Configuration for the local MQTT broker.
        remote_brokers: List of remote broker configurations.
        log: Logging configuration.
        reconnect_delay: Delay in seconds before reconnecting.
        max_reconnect_delay: Maximum reconnect delay in seconds.
    """

    local_broker: LocalBrokerConfig = Field(default_factory=LocalBrokerConfig)
    remote_brokers: list[RemoteBrokerConfig] = Field(default_factory=list)
    log: LogConfig = Field(default_factory=LogConfig)
    reconnect_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    max_reconnect_delay: float = Field(default=60.0, ge=1.0, le=3600.0)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BridgeConfig:
        """Create a BridgeConfig from a dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            A BridgeConfig instance.
        """
        return cls(**data)
