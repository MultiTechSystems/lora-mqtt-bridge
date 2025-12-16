"""Message filtering based on device identifiers.

This module provides filtering functionality for LoRaWAN messages
based on DevEUI, JoinEUI (AppEUI), and other device identifiers.

Supports three types of filtering:
- Exact match lists (whitelist/blacklist)
- Range filters with [min, max] pairs
- Mask patterns using 'x' as wildcards
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lora_mqtt_bridge.models.config import EUIMask, EUIRange, MessageFilterConfig
    from lora_mqtt_bridge.models.message import LoRaMessage


logger = logging.getLogger(__name__)


class MessageFilter:
    """Filter messages based on device identifiers.

    This class provides whitelist, blacklist, range, and mask filtering for LoRaWAN
    messages based on DevEUI, JoinEUI, and AppEUI values.

    Filter precedence:
    1. Blacklist (always blocks if matched)
    2. Whitelist exact match (allows if matched)
    3. Range filters (allows if within any range)
    4. Mask patterns (allows if matches any mask)
    5. If no whitelist/range/mask defined, allow all (subject to blacklist)

    Attributes:
        config: The filter configuration.
    """

    def __init__(self, config: MessageFilterConfig) -> None:
        """Initialize the message filter.

        Args:
            config: The filter configuration containing whitelist/blacklist settings.
        """
        self.config = config
        self._deveui_whitelist = set(config.deveui_whitelist)
        self._deveui_blacklist = set(config.deveui_blacklist)
        self._deveui_ranges: list[EUIRange] = list(config.deveui_ranges)
        self._deveui_masks: list[EUIMask] = list(config.deveui_masks)
        self._joineui_whitelist = set(config.joineui_whitelist)
        self._joineui_blacklist = set(config.joineui_blacklist)
        self._joineui_ranges: list[EUIRange] = list(config.joineui_ranges)
        self._joineui_masks: list[EUIMask] = list(config.joineui_masks)
        self._appeui_whitelist = set(config.appeui_whitelist)
        self._appeui_blacklist = set(config.appeui_blacklist)
        self._appeui_ranges: list[EUIRange] = list(config.appeui_ranges)
        self._appeui_masks: list[EUIMask] = list(config.appeui_masks)

    def _normalize_eui(self, eui: str | None) -> str | None:
        """Normalize an EUI value for comparison.

        Args:
            eui: The EUI string to normalize.

        Returns:
            The normalized EUI string or None.
        """
        if eui is None:
            return None
        clean = eui.replace(":", "").replace("-", "").lower()
        if len(clean) == 16:
            return "-".join([clean[i : i + 2] for i in range(0, 16, 2)])
        return eui.lower()

    def _check_ranges(self, value: str, ranges: list[EUIRange]) -> bool:
        """Check if a value falls within any of the specified ranges.

        Args:
            value: The EUI value to check (already normalized).
            ranges: List of EUIRange objects to check against.

        Returns:
            True if the value is within any range, False otherwise.
        """
        for eui_range in ranges:
            if eui_range.contains(value):
                return True
        return False

    def _check_masks(self, value: str, masks: list[EUIMask]) -> bool:
        """Check if a value matches any of the specified masks.

        Args:
            value: The EUI value to check (already normalized).
            masks: List of EUIMask objects to check against.

        Returns:
            True if the value matches any mask, False otherwise.
        """
        for eui_mask in masks:
            if eui_mask.matches(value):
                return True
        return False

    def _check_whitelist(
        self,
        value: str | None,
        whitelist: set[str],
        blacklist: set[str],
        ranges: list[EUIRange],
        masks: list[EUIMask],
        field_name: str,
    ) -> bool:
        """Check if a value passes whitelist/blacklist/range/mask filtering.

        Args:
            value: The value to check.
            whitelist: The set of allowed values (empty = allow all).
            blacklist: The set of blocked values.
            ranges: List of allowed EUI ranges.
            masks: List of allowed EUI mask patterns.
            field_name: Name of the field for logging.

        Returns:
            True if the value passes filtering, False otherwise.
        """
        # Determine if any allow filters are active
        has_allow_filters = bool(whitelist or ranges or masks)

        if value is None:
            # If no value provided and allow filters exist, fail
            if has_allow_filters:
                logger.debug("No %s provided and allow filters are active", field_name)
                return False
            return True

        normalized = self._normalize_eui(value)
        if normalized is None:
            return False

        # Check blacklist first (always blocks)
        if normalized in blacklist:
            logger.debug("%s %s is blacklisted", field_name, normalized)
            return False

        # If no allow filters defined, allow all (subject to blacklist)
        if not has_allow_filters:
            return True

        # Check whitelist exact match
        if whitelist and normalized in whitelist:
            logger.debug("%s %s matched whitelist", field_name, normalized)
            return True

        # Check range filters
        if ranges and self._check_ranges(normalized, ranges):
            logger.debug("%s %s matched range filter", field_name, normalized)
            return True

        # Check mask patterns
        if masks and self._check_masks(normalized, masks):
            logger.debug("%s %s matched mask pattern", field_name, normalized)
            return True

        # Value didn't match any allow filter
        logger.debug("%s %s not in any allow filter", field_name, normalized)
        return False

    def should_forward(self, message: LoRaMessage) -> bool:
        """Determine if a message should be forwarded based on filters.

        Args:
            message: The LoRa message to check.

        Returns:
            True if the message should be forwarded, False otherwise.
        """
        # Check DevEUI
        if not self._check_whitelist(
            message.deveui,
            self._deveui_whitelist,
            self._deveui_blacklist,
            self._deveui_ranges,
            self._deveui_masks,
            "DevEUI",
        ):
            return False

        # Check JoinEUI
        joineui = message.get_effective_joineui()
        if not self._check_whitelist(
            joineui,
            self._joineui_whitelist,
            self._joineui_blacklist,
            self._joineui_ranges,
            self._joineui_masks,
            "JoinEUI",
        ):
            return False

        # Check AppEUI
        if not self._check_whitelist(
            message.appeui,
            self._appeui_whitelist,
            self._appeui_blacklist,
            self._appeui_ranges,
            self._appeui_masks,
            "AppEUI",
        ):
            return False

        logger.debug("Message from DevEUI %s passed all filters", message.deveui)
        return True

    def add_to_deveui_whitelist(self, deveui: str) -> None:
        """Add a DevEUI to the whitelist.

        Args:
            deveui: The DevEUI to add.
        """
        normalized = self._normalize_eui(deveui)
        if normalized:
            self._deveui_whitelist.add(normalized)
            logger.info("Added DevEUI %s to whitelist", normalized)

    def remove_from_deveui_whitelist(self, deveui: str) -> None:
        """Remove a DevEUI from the whitelist.

        Args:
            deveui: The DevEUI to remove.
        """
        normalized = self._normalize_eui(deveui)
        if normalized:
            self._deveui_whitelist.discard(normalized)
            logger.info("Removed DevEUI %s from whitelist", normalized)

    def add_to_deveui_blacklist(self, deveui: str) -> None:
        """Add a DevEUI to the blacklist.

        Args:
            deveui: The DevEUI to add.
        """
        normalized = self._normalize_eui(deveui)
        if normalized:
            self._deveui_blacklist.add(normalized)
            logger.info("Added DevEUI %s to blacklist", normalized)

    def remove_from_deveui_blacklist(self, deveui: str) -> None:
        """Remove a DevEUI from the blacklist.

        Args:
            deveui: The DevEUI to remove.
        """
        normalized = self._normalize_eui(deveui)
        if normalized:
            self._deveui_blacklist.discard(normalized)
            logger.info("Removed DevEUI %s from blacklist", normalized)

    def add_deveui_range(self, min_eui: str, max_eui: str) -> None:
        """Add a DevEUI range filter.

        Args:
            min_eui: The minimum EUI in the range (inclusive).
            max_eui: The maximum EUI in the range (inclusive).
        """
        from lora_mqtt_bridge.models.config import EUIRange

        eui_range = EUIRange(min_eui=min_eui, max_eui=max_eui)
        self._deveui_ranges.append(eui_range)
        logger.info("Added DevEUI range %s to %s", min_eui, max_eui)

    def remove_deveui_range(self, min_eui: str, max_eui: str) -> bool:
        """Remove a DevEUI range filter.

        Args:
            min_eui: The minimum EUI of the range to remove.
            max_eui: The maximum EUI of the range to remove.

        Returns:
            True if the range was removed, False if not found.
        """
        from lora_mqtt_bridge.models.config import _normalize_eui

        norm_min = _normalize_eui(min_eui)
        norm_max = _normalize_eui(max_eui)
        for i, eui_range in enumerate(self._deveui_ranges):
            if eui_range.min_eui == norm_min and eui_range.max_eui == norm_max:
                self._deveui_ranges.pop(i)
                logger.info("Removed DevEUI range %s to %s", min_eui, max_eui)
                return True
        return False

    def add_deveui_mask(self, mask_pattern: str) -> None:
        """Add a DevEUI mask pattern filter.

        Args:
            mask_pattern: The mask pattern (e.g., "00-11-xx-xx-xx-xx-xx-xx").
        """
        from lora_mqtt_bridge.models.config import EUIMask

        eui_mask = EUIMask.from_string(mask_pattern)
        self._deveui_masks.append(eui_mask)
        logger.info("Added DevEUI mask pattern %s", mask_pattern)

    def remove_deveui_mask(self, mask_pattern: str) -> bool:
        """Remove a DevEUI mask pattern filter.

        Args:
            mask_pattern: The mask pattern to remove.

        Returns:
            True if the mask was removed, False if not found.
        """
        for i, eui_mask in enumerate(self._deveui_masks):
            if eui_mask.pattern.lower() == mask_pattern.lower():
                self._deveui_masks.pop(i)
                logger.info("Removed DevEUI mask pattern %s", mask_pattern)
                return True
        return False
