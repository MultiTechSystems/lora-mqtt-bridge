"""Configuration loading utilities.

This module provides functions for loading configuration from
various sources including files, environment variables, and dictionaries.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

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

logger = logging.getLogger(__name__)


def load_config(config_path: str | Path) -> BridgeConfig:
    """Load configuration from a JSON file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        A BridgeConfig instance.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If the config file is invalid.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return BridgeConfig.from_dict(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to load config: {e}") from e


def load_config_from_env() -> BridgeConfig:
    """Load configuration from environment variables.

    Environment variables are prefixed with LORA_MQTT_BRIDGE_.

    Returns:
        A BridgeConfig instance.
    """
    prefix = "LORA_MQTT_BRIDGE_"

    def get_env(key: str, default: str | None = None) -> str | None:
        return os.environ.get(f"{prefix}{key}", default)

    def get_env_bool(key: str, default: bool = False) -> bool:
        value = get_env(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes")

    def get_env_int(key: str, default: int) -> int:
        value = get_env(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def get_env_list(key: str) -> list[str]:
        value = get_env(key)
        if value is None or value.strip() == "":
            return []
        return [v.strip() for v in value.split(",")]

    # Build local broker config
    topic_format = get_env("LOCAL_TOPIC_FORMAT", "lora")
    local_topics = TopicConfig(
        format=TopicFormat(topic_format) if topic_format else TopicFormat.LORA,
        uplink_pattern=get_env("LOCAL_UPLINK_PATTERN", "lora/+/+/up") or "lora/+/+/up",
        downlink_pattern=get_env("LOCAL_DOWNLINK_PATTERN", "lora/%s/down") or "lora/%s/down",
    )

    local_broker = LocalBrokerConfig(
        host=get_env("LOCAL_HOST", "127.0.0.1") or "127.0.0.1",
        port=get_env_int("LOCAL_PORT", 1883),
        username=get_env("LOCAL_USERNAME"),
        password=get_env("LOCAL_PASSWORD"),
        client_id=get_env("LOCAL_CLIENT_ID", "lora-mqtt-bridge-local") or "lora-mqtt-bridge-local",
        topics=local_topics,
        keepalive=get_env_int("LOCAL_KEEPALIVE", 60),
    )

    # Build remote broker configs from JSON env var
    remote_brokers: list[RemoteBrokerConfig] = []
    remote_config_json = get_env("REMOTE_BROKERS")

    if remote_config_json:
        try:
            remote_data = json.loads(remote_config_json)
            if isinstance(remote_data, list):
                for broker_data in remote_data:
                    remote_brokers.append(_parse_remote_broker(broker_data))
        except json.JSONDecodeError:
            logger.warning("Failed to parse REMOTE_BROKERS JSON")

    # Also support single remote broker via individual env vars
    single_remote_host = get_env("REMOTE_HOST")
    if single_remote_host:
        tls_config = TLSConfig(
            enabled=get_env_bool("REMOTE_TLS_ENABLED"),
            ca_cert=get_env("REMOTE_TLS_CA_CERT"),
            client_cert=get_env("REMOTE_TLS_CLIENT_CERT"),
            client_key=get_env("REMOTE_TLS_CLIENT_KEY"),
            verify_hostname=get_env_bool("REMOTE_TLS_VERIFY_HOSTNAME", True),
            insecure=get_env_bool("REMOTE_TLS_INSECURE"),
        )

        remote_topic_format = get_env("REMOTE_TOPIC_FORMAT", "lora")
        remote_topics = TopicConfig(
            format=TopicFormat(remote_topic_format) if remote_topic_format else TopicFormat.LORA,
            uplink_pattern=get_env("REMOTE_UPLINK_PATTERN", "lora/+/+/up") or "lora/+/+/up",
            downlink_pattern=get_env("REMOTE_DOWNLINK_PATTERN", "lora/%s/down") or "lora/%s/down",
        )

        message_filter = MessageFilterConfig(
            deveui_whitelist=get_env_list("REMOTE_DEVEUI_WHITELIST"),
            deveui_blacklist=get_env_list("REMOTE_DEVEUI_BLACKLIST"),
            joineui_whitelist=get_env_list("REMOTE_JOINEUI_WHITELIST"),
            joineui_blacklist=get_env_list("REMOTE_JOINEUI_BLACKLIST"),
            appeui_whitelist=get_env_list("REMOTE_APPEUI_WHITELIST"),
            appeui_blacklist=get_env_list("REMOTE_APPEUI_BLACKLIST"),
        )

        field_filter = FieldFilterConfig(
            include_fields=get_env_list("REMOTE_INCLUDE_FIELDS"),
            exclude_fields=get_env_list("REMOTE_EXCLUDE_FIELDS"),
        )

        remote_brokers.append(
            RemoteBrokerConfig(
                name=get_env("REMOTE_NAME", "remote") or "remote",
                enabled=get_env_bool("REMOTE_ENABLED", True),
                host=single_remote_host,
                port=get_env_int("REMOTE_PORT", 1883),
                username=get_env("REMOTE_USERNAME"),
                password=get_env("REMOTE_PASSWORD"),
                client_id=get_env("REMOTE_CLIENT_ID"),
                tls=tls_config,
                topics=remote_topics,
                message_filter=message_filter,
                field_filter=field_filter,
                keepalive=get_env_int("REMOTE_KEEPALIVE", 60),
                clean_session=get_env_bool("REMOTE_CLEAN_SESSION"),
                qos=get_env_int("REMOTE_QOS", 1),
                retain=get_env_bool("REMOTE_RETAIN", True),
            )
        )

    return BridgeConfig(
        local_broker=local_broker,
        remote_brokers=remote_brokers,
    )


def _parse_remote_broker(data: dict[str, Any]) -> RemoteBrokerConfig:
    """Parse a remote broker configuration from a dictionary.

    Args:
        data: Dictionary containing broker configuration.

    Returns:
        A RemoteBrokerConfig instance.
    """
    tls_data = data.get("tls", {})
    tls_config = TLSConfig(
        enabled=tls_data.get("enabled", False),
        ca_cert=tls_data.get("ca_cert"),
        client_cert=tls_data.get("client_cert"),
        client_key=tls_data.get("client_key"),
        verify_hostname=tls_data.get("verify_hostname", True),
        insecure=tls_data.get("insecure", False),
    )

    topics_data = data.get("topics", {})
    topic_format_str = topics_data.get("format", "lora")
    topics_config = TopicConfig(
        format=TopicFormat(topic_format_str),
        uplink_pattern=topics_data.get("uplink_pattern", "lora/+/+/up"),
        downlink_pattern=topics_data.get("downlink_pattern", "lora/%s/down"),
    )

    filter_data = data.get("message_filter", {})
    message_filter = MessageFilterConfig(
        deveui_whitelist=filter_data.get("deveui_whitelist", []),
        deveui_blacklist=filter_data.get("deveui_blacklist", []),
        joineui_whitelist=filter_data.get("joineui_whitelist", []),
        joineui_blacklist=filter_data.get("joineui_blacklist", []),
        appeui_whitelist=filter_data.get("appeui_whitelist", []),
        appeui_blacklist=filter_data.get("appeui_blacklist", []),
    )

    field_data = data.get("field_filter", {})
    field_filter = FieldFilterConfig(
        include_fields=field_data.get("include_fields", []),
        exclude_fields=field_data.get("exclude_fields", []),
        always_include=field_data.get("always_include", ["deveui", "appeui", "time"]),
    )

    return RemoteBrokerConfig(
        name=data.get("name", "remote"),
        enabled=data.get("enabled", True),
        host=data["host"],
        port=data.get("port", 1883),
        username=data.get("username"),
        password=data.get("password"),
        client_id=data.get("client_id"),
        tls=tls_config,
        topics=topics_config,
        message_filter=message_filter,
        field_filter=field_filter,
        keepalive=data.get("keepalive", 60),
        clean_session=data.get("clean_session", False),
        qos=data.get("qos", 1),
        retain=data.get("retain", True),
    )
