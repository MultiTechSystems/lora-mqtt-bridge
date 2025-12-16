"""Tests for filter classes.

This module contains tests for message and field filtering functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from lora_mqtt_bridge.filters.field_filter import FieldFilter
from lora_mqtt_bridge.filters.message_filter import MessageFilter
from lora_mqtt_bridge.models.config import (
    EUIMask,
    EUIRange,
    FieldFilterConfig,
    MessageFilterConfig,
)
from lora_mqtt_bridge.models.message import LoRaMessage

if TYPE_CHECKING:
    pass


class TestEUIRange:
    """Tests for EUIRange class."""

    def test_range_creation(self) -> None:
        """Test EUIRange creation and normalization."""
        eui_range = EUIRange(
            min_eui="00-11-22-33-44-55-66-00",
            max_eui="00-11-22-33-44-55-66-ff",
        )
        assert eui_range.min_eui == "00-11-22-33-44-55-66-00"
        assert eui_range.max_eui == "00-11-22-33-44-55-66-ff"

    def test_range_contains(self) -> None:
        """Test EUIRange.contains method."""
        eui_range = EUIRange(
            min_eui="00-11-22-33-44-55-66-00",
            max_eui="00-11-22-33-44-55-66-ff",
        )
        # In range
        assert eui_range.contains("00-11-22-33-44-55-66-50") is True
        assert eui_range.contains("00-11-22-33-44-55-66-00") is True  # Min boundary
        assert eui_range.contains("00-11-22-33-44-55-66-ff") is True  # Max boundary

        # Out of range
        assert eui_range.contains("00-11-22-33-44-55-65-ff") is False  # Below min
        assert eui_range.contains("00-11-22-33-44-55-67-00") is False  # Above max

    def test_range_from_list(self) -> None:
        """Test EUIRange.from_list class method."""
        eui_range = EUIRange.from_list(["0011223344556600", "0011223344556699"])
        assert eui_range.min_eui == "00-11-22-33-44-55-66-00"
        assert eui_range.max_eui == "00-11-22-33-44-55-66-99"

    def test_range_from_list_invalid(self) -> None:
        """Test EUIRange.from_list with invalid input."""
        with pytest.raises(ValueError, match="exactly 2 elements"):
            EUIRange.from_list(["00-11-22-33-44-55-66-00"])

        with pytest.raises(ValueError, match="exactly 2 elements"):
            EUIRange.from_list(["a", "b", "c"])


class TestEUIMask:
    """Tests for EUIMask class."""

    def test_mask_creation(self) -> None:
        """Test EUIMask creation."""
        eui_mask = EUIMask(pattern="00-11-22-xx-xx-xx-xx-xx")
        assert eui_mask.pattern == "00-11-22-xx-xx-xx-xx-xx"

    def test_mask_matches_prefix(self) -> None:
        """Test EUIMask.matches with prefix pattern."""
        eui_mask = EUIMask(pattern="00-11-22-xx-xx-xx-xx-xx")

        # Should match
        assert eui_mask.matches("00-11-22-33-44-55-66-77") is True
        assert eui_mask.matches("00-11-22-00-00-00-00-00") is True
        assert eui_mask.matches("00-11-22-ff-ff-ff-ff-ff") is True

        # Should not match
        assert eui_mask.matches("00-11-23-33-44-55-66-77") is False
        assert eui_mask.matches("ff-11-22-33-44-55-66-77") is False

    def test_mask_matches_suffix(self) -> None:
        """Test EUIMask.matches with suffix pattern."""
        eui_mask = EUIMask(pattern="xx-xx-xx-xx-xx-55-66-77")

        # Should match
        assert eui_mask.matches("00-11-22-33-44-55-66-77") is True
        assert eui_mask.matches("ff-ff-ff-ff-ff-55-66-77") is True

        # Should not match
        assert eui_mask.matches("00-11-22-33-44-55-66-78") is False

    def test_mask_matches_mixed(self) -> None:
        """Test EUIMask.matches with mixed pattern."""
        eui_mask = EUIMask(pattern="00-xx-22-xx-44-xx-66-xx")

        # Should match
        assert eui_mask.matches("00-11-22-33-44-55-66-77") is True
        assert eui_mask.matches("00-ff-22-ff-44-ff-66-ff") is True

        # Should not match
        assert eui_mask.matches("01-11-22-33-44-55-66-77") is False
        assert eui_mask.matches("00-11-23-33-44-55-66-77") is False

    def test_mask_from_string(self) -> None:
        """Test EUIMask.from_string class method."""
        eui_mask = EUIMask.from_string("0011XX334455XXXX")
        assert eui_mask.matches("00-11-00-33-44-55-00-00") is True
        assert eui_mask.matches("00-11-ff-33-44-55-ff-ff") is True

    def test_mask_case_insensitive(self) -> None:
        """Test that mask matching is case insensitive."""
        eui_mask = EUIMask(pattern="AA-BB-XX-XX-XX-XX-XX-XX")

        # Should match regardless of case
        assert eui_mask.matches("aa-bb-cc-dd-ee-ff-00-11") is True
        assert eui_mask.matches("AA-BB-CC-DD-EE-FF-00-11") is True


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

    def test_remove_from_whitelist(self, sample_lora_message: LoRaMessage) -> None:
        """Test dynamically removing from whitelist.

        Args:
            sample_lora_message: Sample message fixture.
        """
        config = MessageFilterConfig(
            deveui_whitelist=["00-11-22-33-44-55-66-77"],
        )
        filter_obj = MessageFilter(config)

        # Initially allowed
        assert filter_obj.should_forward(sample_lora_message) is True

        # Remove from whitelist
        filter_obj.remove_from_deveui_whitelist("00-11-22-33-44-55-66-77")

        # Now blocked (empty whitelist means different device not allowed)
        # Actually, empty whitelist allows all, so this needs adjustment
        # After removal, whitelist is empty, which means all are allowed
        assert filter_obj.should_forward(sample_lora_message) is True

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
        # Use from_dict for EUI normalization (as done when loading config)
        config = MessageFilterConfig.from_dict(
            {
                "deveui_whitelist": ["0011223344556677"],  # Without dashes
            }
        )
        filter_obj = MessageFilter(config)

        message = LoRaMessage(deveui="00-11-22-33-44-55-66-77")  # With dashes
        assert filter_obj.should_forward(message) is True


class TestMessageFilterRanges:
    """Tests for MessageFilter range filtering."""

    def test_deveui_range_allows_in_range(self) -> None:
        """Test that DevEUI within range is allowed."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_ranges": [["00-11-22-33-44-55-66-00", "00-11-22-33-44-55-66-ff"]],
            }
        )
        filter_obj = MessageFilter(config)

        # In range
        message = LoRaMessage(deveui="00-11-22-33-44-55-66-50")
        assert filter_obj.should_forward(message) is True

    def test_deveui_range_blocks_out_of_range(self) -> None:
        """Test that DevEUI outside range is blocked."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_ranges": [["00-11-22-33-44-55-66-00", "00-11-22-33-44-55-66-ff"]],
            }
        )
        filter_obj = MessageFilter(config)

        # Out of range
        message = LoRaMessage(deveui="00-11-22-33-44-55-67-00")
        assert filter_obj.should_forward(message) is False

    def test_multiple_deveui_ranges(self) -> None:
        """Test multiple DevEUI ranges."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_ranges": [
                    ["00-11-22-33-44-55-66-00", "00-11-22-33-44-55-66-0f"],
                    ["00-11-22-33-44-55-66-f0", "00-11-22-33-44-55-66-ff"],
                ],
            }
        )
        filter_obj = MessageFilter(config)

        # In first range
        message1 = LoRaMessage(deveui="00-11-22-33-44-55-66-05")
        assert filter_obj.should_forward(message1) is True

        # In second range
        message2 = LoRaMessage(deveui="00-11-22-33-44-55-66-f5")
        assert filter_obj.should_forward(message2) is True

        # In neither range
        message3 = LoRaMessage(deveui="00-11-22-33-44-55-66-50")
        assert filter_obj.should_forward(message3) is False

    def test_range_with_whitelist(self) -> None:
        """Test that whitelist and range work together."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_whitelist": ["aa-bb-cc-dd-ee-ff-00-11"],
                "deveui_ranges": [["00-11-22-33-44-55-66-00", "00-11-22-33-44-55-66-ff"]],
            }
        )
        filter_obj = MessageFilter(config)

        # In whitelist
        message1 = LoRaMessage(deveui="aa-bb-cc-dd-ee-ff-00-11")
        assert filter_obj.should_forward(message1) is True

        # In range
        message2 = LoRaMessage(deveui="00-11-22-33-44-55-66-50")
        assert filter_obj.should_forward(message2) is True

        # Neither
        message3 = LoRaMessage(deveui="ff-ff-ff-ff-ff-ff-ff-ff")
        assert filter_obj.should_forward(message3) is False

    def test_blacklist_overrides_range(self) -> None:
        """Test that blacklist blocks even if in range."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_ranges": [["00-11-22-33-44-55-66-00", "00-11-22-33-44-55-66-ff"]],
                "deveui_blacklist": ["00-11-22-33-44-55-66-50"],
            }
        )
        filter_obj = MessageFilter(config)

        # In range but blacklisted
        message = LoRaMessage(deveui="00-11-22-33-44-55-66-50")
        assert filter_obj.should_forward(message) is False

        # In range and not blacklisted
        message2 = LoRaMessage(deveui="00-11-22-33-44-55-66-60")
        assert filter_obj.should_forward(message2) is True

    def test_add_deveui_range_dynamically(self) -> None:
        """Test dynamically adding a DevEUI range."""
        config = MessageFilterConfig()
        filter_obj = MessageFilter(config)

        message = LoRaMessage(deveui="00-11-22-33-44-55-66-50")

        # Initially no ranges, so allowed
        assert filter_obj.should_forward(message) is True

        # Add a range that doesn't include the device
        filter_obj.add_deveui_range("aa-00-00-00-00-00-00-00", "aa-ff-ff-ff-ff-ff-ff-ff")

        # Now blocked (range is active but device not in it)
        assert filter_obj.should_forward(message) is False

        # Add a range that includes the device
        filter_obj.add_deveui_range("00-11-22-33-44-55-66-00", "00-11-22-33-44-55-66-ff")

        # Now allowed
        assert filter_obj.should_forward(message) is True

    def test_remove_deveui_range_dynamically(self) -> None:
        """Test dynamically removing a DevEUI range."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_ranges": [["00-11-22-33-44-55-66-00", "00-11-22-33-44-55-66-ff"]],
            }
        )
        filter_obj = MessageFilter(config)

        message = LoRaMessage(deveui="00-11-22-33-44-55-66-50")

        # Initially allowed
        assert filter_obj.should_forward(message) is True

        # Remove the range
        result = filter_obj.remove_deveui_range(
            "00-11-22-33-44-55-66-00", "00-11-22-33-44-55-66-ff"
        )
        assert result is True

        # Now allowed (no filters active)
        assert filter_obj.should_forward(message) is True


class TestMessageFilterMasks:
    """Tests for MessageFilter mask filtering."""

    def test_deveui_mask_allows_matching(self) -> None:
        """Test that DevEUI matching mask is allowed."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_masks": ["00-11-22-xx-xx-xx-xx-xx"],
            }
        )
        filter_obj = MessageFilter(config)

        # Matches mask
        message = LoRaMessage(deveui="00-11-22-33-44-55-66-77")
        assert filter_obj.should_forward(message) is True

    def test_deveui_mask_blocks_non_matching(self) -> None:
        """Test that DevEUI not matching mask is blocked."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_masks": ["00-11-22-xx-xx-xx-xx-xx"],
            }
        )
        filter_obj = MessageFilter(config)

        # Doesn't match mask
        message = LoRaMessage(deveui="00-11-23-33-44-55-66-77")
        assert filter_obj.should_forward(message) is False

    def test_multiple_deveui_masks(self) -> None:
        """Test multiple DevEUI masks."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_masks": [
                    "00-11-xx-xx-xx-xx-xx-xx",
                    "aa-bb-xx-xx-xx-xx-xx-xx",
                ],
            }
        )
        filter_obj = MessageFilter(config)

        # Matches first mask
        message1 = LoRaMessage(deveui="00-11-22-33-44-55-66-77")
        assert filter_obj.should_forward(message1) is True

        # Matches second mask
        message2 = LoRaMessage(deveui="aa-bb-cc-dd-ee-ff-00-11")
        assert filter_obj.should_forward(message2) is True

        # Matches neither
        message3 = LoRaMessage(deveui="ff-ff-ff-ff-ff-ff-ff-ff")
        assert filter_obj.should_forward(message3) is False

    def test_mask_with_whitelist_and_range(self) -> None:
        """Test that whitelist, range, and mask work together."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_whitelist": ["ff-ff-ff-ff-ff-ff-ff-ff"],
                "deveui_ranges": [["aa-00-00-00-00-00-00-00", "aa-ff-ff-ff-ff-ff-ff-ff"]],
                "deveui_masks": ["00-11-xx-xx-xx-xx-xx-xx"],
            }
        )
        filter_obj = MessageFilter(config)

        # In whitelist
        message1 = LoRaMessage(deveui="ff-ff-ff-ff-ff-ff-ff-ff")
        assert filter_obj.should_forward(message1) is True

        # In range
        message2 = LoRaMessage(deveui="aa-50-00-00-00-00-00-00")
        assert filter_obj.should_forward(message2) is True

        # Matches mask
        message3 = LoRaMessage(deveui="00-11-22-33-44-55-66-77")
        assert filter_obj.should_forward(message3) is True

        # None of the above
        message4 = LoRaMessage(deveui="bb-cc-dd-ee-00-00-00-00")
        assert filter_obj.should_forward(message4) is False

    def test_blacklist_overrides_mask(self) -> None:
        """Test that blacklist blocks even if matches mask."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_masks": ["00-11-xx-xx-xx-xx-xx-xx"],
                "deveui_blacklist": ["00-11-22-33-44-55-66-77"],
            }
        )
        filter_obj = MessageFilter(config)

        # Matches mask but blacklisted
        message = LoRaMessage(deveui="00-11-22-33-44-55-66-77")
        assert filter_obj.should_forward(message) is False

        # Matches mask and not blacklisted
        message2 = LoRaMessage(deveui="00-11-22-33-44-55-66-88")
        assert filter_obj.should_forward(message2) is True

    def test_add_deveui_mask_dynamically(self) -> None:
        """Test dynamically adding a DevEUI mask."""
        config = MessageFilterConfig()
        filter_obj = MessageFilter(config)

        message = LoRaMessage(deveui="00-11-22-33-44-55-66-77")

        # Initially no masks, so allowed
        assert filter_obj.should_forward(message) is True

        # Add a mask that doesn't match the device
        filter_obj.add_deveui_mask("aa-bb-xx-xx-xx-xx-xx-xx")

        # Now blocked (mask is active but device doesn't match)
        assert filter_obj.should_forward(message) is False

        # Add a mask that matches the device
        filter_obj.add_deveui_mask("00-11-xx-xx-xx-xx-xx-xx")

        # Now allowed
        assert filter_obj.should_forward(message) is True

    def test_remove_deveui_mask_dynamically(self) -> None:
        """Test dynamically removing a DevEUI mask."""
        config = MessageFilterConfig.from_dict(
            {
                "deveui_masks": ["00-11-xx-xx-xx-xx-xx-xx"],
            }
        )
        filter_obj = MessageFilter(config)

        message = LoRaMessage(deveui="00-11-22-33-44-55-66-77")

        # Initially allowed
        assert filter_obj.should_forward(message) is True

        # Remove the mask
        result = filter_obj.remove_deveui_mask("00-11-xx-xx-xx-xx-xx-xx")
        assert result is True

        # Now allowed (no filters active)
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

    def test_exclude_with_always_include(self, sample_uplink_payload: dict[str, Any]) -> None:
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

    def test_remove_exclude_field(self, sample_uplink_payload: dict[str, Any]) -> None:
        """Test dynamically removing exclude field.

        Args:
            sample_uplink_payload: Sample payload fixture.
        """
        config = FieldFilterConfig(
            exclude_fields=["rssi"],
            always_include=[],
        )
        filter_obj = FieldFilter(config)

        # Initially excluded
        result = filter_obj.filter_payload(sample_uplink_payload)
        assert "rssi" not in result

        # Remove from exclude list
        filter_obj.remove_exclude_field("rssi")

        # Now included
        result = filter_obj.filter_payload(sample_uplink_payload)
        assert "rssi" in result

    def test_set_always_include(self, sample_uplink_payload: dict[str, Any]) -> None:
        """Test setting always-include fields.

        Args:
            sample_uplink_payload: Sample payload fixture.
        """
        config = FieldFilterConfig(
            include_fields=["port"],
            always_include=[],
        )
        filter_obj = FieldFilter(config)

        # Only port should be present
        result = filter_obj.filter_payload(sample_uplink_payload)
        assert "deveui" not in result

        # Set always-include
        filter_obj.set_always_include(["deveui", "time"])

        # Now deveui and time should also be present
        result = filter_obj.filter_payload(sample_uplink_payload)
        assert "deveui" in result
        assert "time" in result

    def test_empty_payload(self) -> None:
        """Test filtering empty payload."""
        config = FieldFilterConfig()
        filter_obj = FieldFilter(config)
        result = filter_obj.filter_payload({})

        assert result == {}
