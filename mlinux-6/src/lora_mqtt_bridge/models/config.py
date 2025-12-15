"""Configuration models for the LoRa MQTT Bridge.

This module defines configuration classes for the MQTT bridge,
including local broker settings, remote broker settings, and filtering options.

Compatible with Python 3.8+ without external dependencies (no pydantic).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TopicFormat(str, Enum):
    """Enum for supported topic formats."""

    LORA = "lora"
    SCADA = "scada"


def _normalize_eui(eui: str) -> str:
    """Normalize EUI values to lowercase with dashes.

    Args:
        eui: The EUI string to normalize.

    Returns:
        The normalized EUI string.
    """
    clean = eui.replace(":", "").replace("-", "").lower()
    if len(clean) == 16:
        return "-".join([clean[i : i + 2] for i in range(0, 16, 2)])
    return eui.lower()


def _normalize_eui_list(eui_list: list[str]) -> list[str]:
    """Normalize a list of EUI values.

    Args:
        eui_list: List of EUI strings to normalize.

    Returns:
        List of normalized EUI strings.
    """
    return [_normalize_eui(eui) for eui in eui_list]


def _parse_topic_format(value: Any) -> list[TopicFormat]:
    """Parse source_topic_format from various input types.

    Args:
        value: A single format or list of formats (strings or TopicFormat).

    Returns:
        List of TopicFormat values.
    """
    if value is None:
        return [TopicFormat.LORA]
    if isinstance(value, str):
        return [TopicFormat(value)]
    if isinstance(value, TopicFormat):
        return [value]
    if isinstance(value, list):
        result = []  # type: List[TopicFormat]
        for item in value:
            if isinstance(item, str):
                result.append(TopicFormat(item))
            elif isinstance(item, TopicFormat):
                result.append(item)
            else:
                result.append(item)
        return result
    return [TopicFormat.LORA]


@dataclass
class TopicConfig:
    """Configuration for MQTT topic formats.

    Attributes:
        format: The topic format to use (lora or scada).
        uplink_pattern: Pattern for uplink topics with wildcards.
        downlink_pattern: Pattern for downlink topics with %s for deveui.
    """

    format: TopicFormat = TopicFormat.LORA
    uplink_pattern: str = "lora/+/+/up"
    downlink_pattern: str = "lora/%s/down"

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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TopicConfig:
        """Create TopicConfig from a dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            A TopicConfig instance.
        """
        format_val = data.get("format", "lora")
        if isinstance(format_val, str):
            format_val = TopicFormat(format_val)
        return cls(
            format=format_val,
            uplink_pattern=data.get("uplink_pattern", "lora/+/+/up"),
            downlink_pattern=data.get("downlink_pattern", "lora/%s/down"),
        )


@dataclass
class LocalBrokerConfig:
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

    host: str = "127.0.0.1"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    client_id: str = "lora-mqtt-bridge-local"
    topics: TopicConfig = field(default_factory=TopicConfig)
    keepalive: int = 60

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LocalBrokerConfig:
        """Create LocalBrokerConfig from a dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            A LocalBrokerConfig instance.
        """
        topics_data = data.get("topics", {})
        topics = TopicConfig.from_dict(topics_data) if topics_data else TopicConfig()
        return cls(
            host=data.get("host", "127.0.0.1"),
            port=data.get("port", 1883),
            username=data.get("username"),
            password=data.get("password"),
            client_id=data.get("client_id", "lora-mqtt-bridge-local"),
            topics=topics,
            keepalive=data.get("keepalive", 60),
        )


@dataclass
class MessageFilterConfig:
    """Configuration for filtering messages by device identifiers.

    Attributes:
        deveui_whitelist: List of DevEUI values to allow (empty = allow all).
        deveui_blacklist: List of DevEUI values to block.
        joineui_whitelist: List of JoinEUI values to allow (empty = allow all).
        joineui_blacklist: List of JoinEUI values to block.
        appeui_whitelist: List of AppEUI values to allow (empty = allow all).
        appeui_blacklist: List of AppEUI values to block.
    """

    deveui_whitelist: list[str] = field(default_factory=list)
    deveui_blacklist: list[str] = field(default_factory=list)
    joineui_whitelist: list[str] = field(default_factory=list)
    joineui_blacklist: list[str] = field(default_factory=list)
    appeui_whitelist: list[str] = field(default_factory=list)
    appeui_blacklist: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MessageFilterConfig:
        """Create MessageFilterConfig from a dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            A MessageFilterConfig instance.
        """
        return cls(
            deveui_whitelist=_normalize_eui_list(data.get("deveui_whitelist", [])),
            deveui_blacklist=_normalize_eui_list(data.get("deveui_blacklist", [])),
            joineui_whitelist=_normalize_eui_list(data.get("joineui_whitelist", [])),
            joineui_blacklist=_normalize_eui_list(data.get("joineui_blacklist", [])),
            appeui_whitelist=_normalize_eui_list(data.get("appeui_whitelist", [])),
            appeui_blacklist=_normalize_eui_list(data.get("appeui_blacklist", [])),
        )


@dataclass
class FieldFilterConfig:
    """Configuration for filtering fields in uplink messages.

    Attributes:
        include_fields: List of field names to include (empty = include all).
        exclude_fields: List of field names to exclude.
        always_include: Fields that are always included regardless of filters.
    """

    include_fields: list[str] = field(default_factory=list)
    exclude_fields: list[str] = field(default_factory=list)
    always_include: list[str] = field(default_factory=lambda: ["deveui", "appeui", "time"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FieldFilterConfig:
        """Create FieldFilterConfig from a dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            A FieldFilterConfig instance.
        """
        return cls(
            include_fields=data.get("include_fields", []),
            exclude_fields=data.get("exclude_fields", []),
            always_include=data.get("always_include", ["deveui", "appeui", "time"]),
        )


@dataclass
class TLSConfig:
    """Configuration for TLS/SSL connections.

    Attributes:
        enabled: Whether TLS is enabled.
        ca_cert: Path to CA certificate file or certificate content.
        client_cert: Path to client certificate file or certificate content.
        client_key: Path to client key file or key content.
        verify_hostname: Whether to verify the server hostname.
        insecure: Allow insecure connections (skip certificate verification).
    """

    enabled: bool = False
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None
    verify_hostname: bool = True
    insecure: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TLSConfig:
        """Create TLSConfig from a dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            A TLSConfig instance.
        """
        return cls(
            enabled=data.get("enabled", False),
            ca_cert=data.get("ca_cert"),
            client_cert=data.get("client_cert"),
            client_key=data.get("client_key"),
            verify_hostname=data.get("verify_hostname", True),
            insecure=data.get("insecure", False),
        )


@dataclass
class RemoteBrokerConfig:
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

    name: str = ""
    enabled: bool = True
    host: str = ""
    port: int = 1883
    username: str | None = None
    password: str | None = None
    client_id: str | None = None
    tls: TLSConfig = field(default_factory=TLSConfig)
    source_topic_format: list[TopicFormat] = field(default_factory=lambda: [TopicFormat.LORA])
    topics: TopicConfig = field(default_factory=TopicConfig)
    message_filter: MessageFilterConfig = field(default_factory=MessageFilterConfig)
    field_filter: FieldFilterConfig = field(default_factory=FieldFilterConfig)
    keepalive: int = 60
    clean_session: bool = False
    qos: int = 1
    retain: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RemoteBrokerConfig:
        """Create RemoteBrokerConfig from a dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            A RemoteBrokerConfig instance.
        """
        tls_data = data.get("tls", {})
        topics_data = data.get("topics", {})
        message_filter_data = data.get("message_filter", {})
        field_filter_data = data.get("field_filter", {})

        return cls(
            name=data.get("name", ""),
            enabled=data.get("enabled", True),
            host=data.get("host", ""),
            port=data.get("port", 1883),
            username=data.get("username"),
            password=data.get("password"),
            client_id=data.get("client_id"),
            tls=TLSConfig.from_dict(tls_data) if tls_data else TLSConfig(),
            source_topic_format=_parse_topic_format(data.get("source_topic_format")),
            topics=TopicConfig.from_dict(topics_data) if topics_data else TopicConfig(),
            message_filter=(
                MessageFilterConfig.from_dict(message_filter_data)
                if message_filter_data
                else MessageFilterConfig()
            ),
            field_filter=(
                FieldFilterConfig.from_dict(field_filter_data)
                if field_filter_data
                else FieldFilterConfig()
            ),
            keepalive=data.get("keepalive", 60),
            clean_session=data.get("clean_session", False),
            qos=data.get("qos", 1),
            retain=data.get("retain", True),
        )


@dataclass
class LogConfig:
    """Configuration for logging.

    Attributes:
        level: The log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        format: The log format string.
        file: Optional file path for file logging.
    """

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogConfig:
        """Create LogConfig from a dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            A LogConfig instance.
        """
        return cls(
            level=data.get("level", "INFO"),
            format=data.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            file=data.get("file"),
        )


@dataclass
class BridgeConfig:
    """Main configuration for the MQTT Bridge application.

    Attributes:
        local_broker: Configuration for the local MQTT broker.
        remote_brokers: List of remote broker configurations.
        log: Logging configuration.
        reconnect_delay: Delay in seconds before reconnecting.
        max_reconnect_delay: Maximum reconnect delay in seconds.
    """

    local_broker: LocalBrokerConfig = field(default_factory=LocalBrokerConfig)
    remote_brokers: list[RemoteBrokerConfig] = field(default_factory=list)
    log: LogConfig = field(default_factory=LogConfig)
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 60.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BridgeConfig:
        """Create a BridgeConfig from a dictionary.

        Args:
            data: Dictionary containing configuration data.

        Returns:
            A BridgeConfig instance.
        """
        local_broker_data = data.get("local_broker", {})
        remote_brokers_data = data.get("remote_brokers", [])
        log_data = data.get("log", {})

        remote_brokers = [RemoteBrokerConfig.from_dict(rb) for rb in remote_brokers_data]  # type: List[RemoteBrokerConfig]

        return cls(
            local_broker=(
                LocalBrokerConfig.from_dict(local_broker_data)
                if local_broker_data
                else LocalBrokerConfig()
            ),
            remote_brokers=remote_brokers,
            log=LogConfig.from_dict(log_data) if log_data else LogConfig(),
            reconnect_delay=data.get("reconnect_delay", 1.0),
            max_reconnect_delay=data.get("max_reconnect_delay", 60.0),
        )
