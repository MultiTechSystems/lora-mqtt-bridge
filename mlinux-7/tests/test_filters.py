"""Tests for filter classes.

This module contains tests for message and field filtering functionality.
Compatible with Python 3.8+ (mLinux 6.3.5)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lora_mqtt_bridge.filters.field_filter import FieldFilter
from lora_mqtt_bridge.filters.message_filter import MessageFilter
from lora_mqtt_bridge.models.config import FieldFilterConfig, MessageFilterConfig
from lora_mqtt_bridge.models.message import LoRaMessage

if TYPE_CHECKING:
    pass


class TestMessageFilter:
    """Tests for MessageFilter class."""

    def test_no_filters_allows_all(self, sample_lora_message: LoRaMessage) -> None:
        """Test that empty filters allow all messages.

        Args:
            sample_lora_message: Sample message fixture.
        """
        config = MessageFilterConfig()
        filter_obj = MessageFilter(config)
        assert filter_obj.should_forward(sample_lora_message) is True

    def test_deveui_whitelist(self, sample_lora_message: LoRaMessage) -> None:
        """Test DevEUI whitelist filtering.

        Args:
            sample_lora_message: Sample message fixture.
        """
        # Message deveui is in whitelist
        config = MessageFilterConfig(
            deveui_whitelist=["00-11-22-33-44-55-66-77"],
        )
        filter_obj = MessageFilter(config)
        assert filter_obj.should_forward(sample_lora_message) is True

        # Message deveui not in whitelist
        config = MessageFilterConfig(
            deveui_whitelist=["ff-ff-ff-ff-ff-ff-ff-ff"],
        )
        filter_obj = MessageFilter(config)
        assert filter_obj.should_forward(sample_lora_message) is False

    def test_deveui_blacklist(self, sample_lora_message: LoRaMessage) -> None:
        """Test DevEUI blacklist filtering.

        Args:
            sample_lora_message: Sample message fixture.
        """
        # Message deveui in blacklist
        config = MessageFilterConfig(
            deveui_blacklist=["00-11-22-33-44-55-66-77"],
        )
        filter_obj = MessageFilter(config)
        assert filter_obj.should_forward(sample_lora_message) is False

        # Message deveui not in blacklist
        config = MessageFilterConfig(
            deveui_blacklist=["ff-ff-ff-ff-ff-ff-ff-ff"],
        )
        filter_obj = MessageFilter(config)
        assert filter_obj.should_forward(sample_lora_message) is True

    def test_appeui_whitelist(self, sample_lora_message: LoRaMessage) -> None:
        """Test AppEUI whitelist filtering.

        Args:
            sample_lora_message: Sample message fixture.
        """
        # Message appeui is in whitelist
        config = MessageFilterConfig(
            appeui_whitelist=["aa-bb-cc-dd-ee-ff-00-11"],
        )
        filter_obj = MessageFilter(config)
        assert filter_obj.should_forward(sample_lora_message) is True

        # Message appeui not in whitelist
        config = MessageFilterConfig(
            appeui_whitelist=["ff-ff-ff-ff-ff-ff-ff-ff"],
        )
        filter_obj = MessageFilter(config)
        assert filter_obj.should_forward(sample_lora_message) is False

    def test_joineui_whitelist(self) -> None:
        """Test JoinEUI whitelist filtering."""
        message = LoRaMessage(
            deveui="00-11-22-33-44-55-66-77",
            joineui="aa-bb-cc-dd-ee-ff-00-11",
        )

        # JoinEUI in whitelist
        config = MessageFilterConfig(
            joineui_whitelist=["aa-bb-cc-dd-ee-ff-00-11"],
        )
        filter_obj = MessageFilter(config)
        assert filter_obj.should_forward(message) is True

        # JoinEUI not in whitelist
        config = MessageFilterConfig(
            joineui_whitelist=["ff-ff-ff-ff-ff-ff-ff-ff"],
        )
        filter_obj = MessageFilter(config)
        assert filter_obj.should_forward(message) is False

    def test_blacklist_takes_precedence(self, sample_lora_message: LoRaMessage) -> None:
        """Test that blacklist is checked before whitelist.

        Args:
            sample_lora_message: Sample message fixture.
        """
        # Device in both whitelist and blacklist - should be blocked
        config = MessageFilterConfig(
            deveui_whitelist=["00-11-22-33-44-55-66-77"],
            deveui_blacklist=["00-11-22-33-44-55-66-77"],
        )
        filter_obj = MessageFilter(config)
        assert filter_obj.should_forward(sample_lora_message) is False

    def test_add_to_whitelist(self) -> None:
        """Test dynamically adding to whitelist."""
        config = MessageFilterConfig(
            deveui_whitelist=["aa-bb-cc-dd-ee-ff-00-11"],
        )
        filter_obj = MessageFilter(config)

        message = LoRaMessage(deveui="00-11-22-33-44-55-66-77")

        # Initially blocked
        assert filter_obj.should_forward(message) is False

        # Add to whitelist
        filter_obj.add_to_deveui_whitelist("00-11-22-33-44-55-66-77")

        # Now allowed
        assert filter_obj.should_forward(message) is True

    def test_add_to_blacklist(self, sample_lora_message: LoRaMessage) -> None:
        """Test dynamically adding to blacklist.

        Args:
            sample_lora_message: Sample message fixture.
        """
        config = MessageFilterConfig()
        filter_obj = MessageFilter(config)

        # Initially allowed
        assert filter_obj.should_forward(sample_lora_message) is True

        # Add to blacklist
        filter_obj.add_to_deveui_blacklist("00-11-22-33-44-55-66-77")

        # Now blocked
        assert filter_obj.should_forward(sample_lora_message) is False

    def test_eui_normalization_in_filter(self) -> None:
        """Test EUI normalization during filtering."""
        config = MessageFilterConfig(
            deveui_whitelist=["0011223344556677"],  # Without dashes
        )
        filter_obj = MessageFilter(config)

        message = LoRaMessage(deveui="00-11-22-33-44-55-66-77")  # With dashes
        assert filter_obj.should_forward(message) is True


class TestFieldFilter:
    """Tests for FieldFilter class."""

    def test_no_filters_returns_all(self, sample_uplink_payload: dict[str, Any]) -> None:
        """Test that empty filters return all fields.

        Args:
            sample_uplink_payload: Sample payload fixture.
        """
        config = FieldFilterConfig(
            include_fields=[],
            exclude_fields=[],
            always_include=[],
        )
        filter_obj = FieldFilter(config)
        result = filter_obj.filter_payload(sample_uplink_payload)

        assert result == sample_uplink_payload

    def test_exclude_fields(self, sample_uplink_payload: dict[str, Any]) -> None:
        """Test excluding specific fields.

        Args:
            sample_uplink_payload: Sample payload fixture.
        """
        config = FieldFilterConfig(
            exclude_fields=["rssi", "snr", "freq"],
            always_include=[],
        )
        filter_obj = FieldFilter(config)
        result = filter_obj.filter_payload(sample_uplink_payload)

        assert "rssi" not in result
        assert "snr" not in result
        assert "freq" not in result
        assert "deveui" in result
        assert "port" in result

    def test_include_fields(self, sample_uplink_payload: dict[str, Any]) -> None:
        """Test including only specific fields.

        Args:
            sample_uplink_payload: Sample payload fixture.
        """
        config = FieldFilterConfig(
            include_fields=["deveui", "port", "data"],
            always_include=[],
        )
        filter_obj = FieldFilter(config)
        result = filter_obj.filter_payload(sample_uplink_payload)

        assert set(result.keys()) == {"deveui", "port", "data"}

    def test_always_include(self, sample_uplink_payload: dict[str, Any]) -> None:
        """Test always-include fields.

        Args:
            sample_uplink_payload: Sample payload fixture.
        """
        config = FieldFilterConfig(
            include_fields=["port"],
            always_include=["deveui", "time"],
        )
        filter_obj = FieldFilter(config)
        result = filter_obj.filter_payload(sample_uplink_payload)

        # Always-include fields should be present even if not in include_fields
        assert "deveui" in result
        assert "time" in result
        assert "port" in result
        # Other fields should be excluded
        assert "rssi" not in result

    def test_exclude_with_always_include(
        self, sample_uplink_payload: dict[str, Any]
    ) -> None:
        """Test that always-include overrides exclude.

        Args:
            sample_uplink_payload: Sample payload fixture.
        """
        config = FieldFilterConfig(
            exclude_fields=["deveui", "rssi"],
            always_include=["deveui"],
        )
        filter_obj = FieldFilter(config)
        result = filter_obj.filter_payload(sample_uplink_payload)

        # deveui should be present despite being in exclude
        assert "deveui" in result
        # rssi should be excluded
        assert "rssi" not in result

    def test_add_exclude_field(self, sample_uplink_payload: dict[str, Any]) -> None:
        """Test dynamically adding exclude field.

        Args:
            sample_uplink_payload: Sample payload fixture.
        """
        config = FieldFilterConfig(always_include=[])
        filter_obj = FieldFilter(config)

        # Initially all fields present
        result = filter_obj.filter_payload(sample_uplink_payload)
        assert "rssi" in result

        # Add to exclude list
        filter_obj.add_exclude_field("rssi")

        # Now excluded
        result = filter_obj.filter_payload(sample_uplink_payload)
        assert "rssi" not in result

    def test_empty_payload(self) -> None:
        """Test filtering empty payload."""
        config = FieldFilterConfig()
        filter_obj = FieldFilter(config)
        result = filter_obj.filter_payload({})

        assert result == {}
