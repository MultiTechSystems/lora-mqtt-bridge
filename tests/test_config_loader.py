"""Tests for configuration loading utilities.

This module contains tests for loading configuration from files
and environment variables.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import TYPE_CHECKING

import pytest

from lora_mqtt_bridge.utils.config_loader import (
    load_config,
    load_config_from_env,
)

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config_file(self) -> None:
        """Test loading a valid configuration file."""
        config_data = {
            "local_broker": {
                "host": "localhost",
                "port": 1883,
            },
            "remote_brokers": [
                {
                    "name": "test",
                    "host": "remote.example.com",
                }
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = load_config(temp_path)
            assert config.local_broker.host == "localhost"
            assert len(config.remote_brokers) == 1
            assert config.remote_brokers[0].name == "test"
        finally:
            os.unlink(temp_path)

    def test_load_nonexistent_file(self) -> None:
        """Test loading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.json")

    def test_load_invalid_json(self) -> None:
        """Test loading a file with invalid JSON."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("not valid json")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                load_config(temp_path)
        finally:
            os.unlink(temp_path)

    def test_load_config_with_all_options(self) -> None:
        """Test loading a comprehensive configuration file."""
        config_data = {
            "local_broker": {
                "host": "192.168.1.100",
                "port": 1883,
                "username": "localuser",
                "password": "localpass",
                "client_id": "custom-client",
                "topics": {
                    "format": "scada",
                    "uplink_pattern": "scada/+/up",
                    "downlink_pattern": "scada/%s/down",
                },
                "keepalive": 120,
            },
            "remote_brokers": [
                {
                    "name": "cloud",
                    "enabled": True,
                    "host": "cloud.example.com",
                    "port": 8883,
                    "username": "clouduser",
                    "password": "cloudpass",
                    "tls": {
                        "enabled": True,
                        "verify_hostname": True,
                    },
                    "message_filter": {
                        "deveui_whitelist": ["00-11-22-33-44-55-66-77"],
                    },
                    "field_filter": {
                        "exclude_fields": ["rssi", "snr"],
                    },
                }
            ],
            "log": {
                "level": "DEBUG",
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = load_config(temp_path)

            assert config.local_broker.host == "192.168.1.100"
            assert config.local_broker.username == "localuser"
            assert config.local_broker.topics.format.value == "scada"

            assert len(config.remote_brokers) == 1
            remote = config.remote_brokers[0]
            assert remote.name == "cloud"
            assert remote.tls.enabled is True
            assert "00-11-22-33-44-55-66-77" in remote.message_filter.deveui_whitelist
            assert "rssi" in remote.field_filter.exclude_fields

            assert config.log.level == "DEBUG"
        finally:
            os.unlink(temp_path)


class TestLoadConfigFromEnv:
    """Tests for load_config_from_env function."""

    def test_default_values(self, monkeypatch: MonkeyPatch) -> None:
        """Test that default values are used when env vars not set.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
        """
        # Clear any existing env vars
        for key in list(os.environ.keys()):
            if key.startswith("LORA_MQTT_BRIDGE_"):
                monkeypatch.delenv(key, raising=False)

        config = load_config_from_env()

        assert config.local_broker.host == "127.0.0.1"
        assert config.local_broker.port == 1883

    def test_local_broker_from_env(self, monkeypatch: MonkeyPatch) -> None:
        """Test loading local broker config from environment.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
        """
        monkeypatch.setenv("LORA_MQTT_BRIDGE_LOCAL_HOST", "192.168.1.50")
        monkeypatch.setenv("LORA_MQTT_BRIDGE_LOCAL_PORT", "1884")
        monkeypatch.setenv("LORA_MQTT_BRIDGE_LOCAL_USERNAME", "testuser")
        monkeypatch.setenv("LORA_MQTT_BRIDGE_LOCAL_PASSWORD", "testpass")

        config = load_config_from_env()

        assert config.local_broker.host == "192.168.1.50"
        assert config.local_broker.port == 1884
        assert config.local_broker.username == "testuser"
        assert config.local_broker.password == "testpass"

    def test_single_remote_broker_from_env(self, monkeypatch: MonkeyPatch) -> None:
        """Test loading single remote broker from environment.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
        """
        monkeypatch.setenv("LORA_MQTT_BRIDGE_REMOTE_HOST", "remote.example.com")
        monkeypatch.setenv("LORA_MQTT_BRIDGE_REMOTE_PORT", "8883")
        monkeypatch.setenv("LORA_MQTT_BRIDGE_REMOTE_NAME", "cloud")
        monkeypatch.setenv("LORA_MQTT_BRIDGE_REMOTE_TLS_ENABLED", "true")

        config = load_config_from_env()

        assert len(config.remote_brokers) == 1
        remote = config.remote_brokers[0]
        assert remote.host == "remote.example.com"
        assert remote.port == 8883
        assert remote.name == "cloud"
        assert remote.tls.enabled is True

    def test_remote_brokers_json_from_env(self, monkeypatch: MonkeyPatch) -> None:
        """Test loading multiple remote brokers from JSON env var.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
        """
        brokers_json = json.dumps([
            {"name": "broker1", "host": "broker1.example.com"},
            {"name": "broker2", "host": "broker2.example.com", "port": 8884},
        ])
        monkeypatch.setenv("LORA_MQTT_BRIDGE_REMOTE_BROKERS", brokers_json)

        config = load_config_from_env()

        assert len(config.remote_brokers) == 2
        assert config.remote_brokers[0].name == "broker1"
        assert config.remote_brokers[1].name == "broker2"
        assert config.remote_brokers[1].port == 8884

    def test_topic_format_from_env(self, monkeypatch: MonkeyPatch) -> None:
        """Test loading topic format from environment.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
        """
        monkeypatch.setenv("LORA_MQTT_BRIDGE_LOCAL_TOPIC_FORMAT", "scada")
        monkeypatch.setenv("LORA_MQTT_BRIDGE_LOCAL_UPLINK_PATTERN", "scada/+/up")
        monkeypatch.setenv("LORA_MQTT_BRIDGE_LOCAL_DOWNLINK_PATTERN", "scada/%s/down")

        config = load_config_from_env()

        assert config.local_broker.topics.format.value == "scada"

    def test_filter_lists_from_env(self, monkeypatch: MonkeyPatch) -> None:
        """Test loading filter lists from environment.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
        """
        monkeypatch.setenv("LORA_MQTT_BRIDGE_REMOTE_HOST", "remote.example.com")
        monkeypatch.setenv(
            "LORA_MQTT_BRIDGE_REMOTE_DEVEUI_WHITELIST",
            "00-11-22-33-44-55-66-77,aa-bb-cc-dd-ee-ff-00-11",
        )
        monkeypatch.setenv(
            "LORA_MQTT_BRIDGE_REMOTE_EXCLUDE_FIELDS",
            "rssi,snr,freq",
        )

        config = load_config_from_env()

        assert len(config.remote_brokers) == 1
        remote = config.remote_brokers[0]
        assert len(remote.message_filter.deveui_whitelist) == 2
        assert len(remote.field_filter.exclude_fields) == 3

    def test_invalid_json_remote_brokers(self, monkeypatch: MonkeyPatch) -> None:
        """Test handling invalid JSON in REMOTE_BROKERS env var.

        Args:
            monkeypatch: Pytest monkeypatch fixture.
        """
        monkeypatch.setenv("LORA_MQTT_BRIDGE_REMOTE_BROKERS", "not valid json")

        # Should not raise, just return empty list
        config = load_config_from_env()
        assert config.remote_brokers == []
