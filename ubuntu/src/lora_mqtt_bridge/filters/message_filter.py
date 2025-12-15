"""Message filtering based on device identifiers.

This module provides filtering functionality for LoRaWAN messages
based on DevEUI, JoinEUI (AppEUI), and other device identifiers.

Compatible with Python 3.10+ and mLinux 7.1.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lora_mqtt_bridge.models.config import MessageFilterConfig
    from lora_mqtt_bridge.models.message import LoRaMessage


logger = logging.getLogger(__name__)


class MessageFilter:
    """Filter messages based on device identifiers.

    This class provides whitelist and blacklist filtering for LoRaWAN
    messages based on DevEUI, JoinEUI, and AppEUI values.

    Attributes:
        config: The filter configuration.
    """

    def __init__(self, config: MessageFilterConfig) -> None:
        """Initialize the message filter.

        Args:
            config: The filter configuration containing whitelist/blacklist settings.
        """
        self.config = config
        self._deveui_whitelist: set[str] = set(config.deveui_whitelist)
        self._deveui_blacklist: set[str] = set(config.deveui_blacklist)
        self._joineui_whitelist: set[str] = set(config.joineui_whitelist)
        self._joineui_blacklist: set[str] = set(config.joineui_blacklist)
        self._appeui_whitelist: set[str] = set(config.appeui_whitelist)
        self._appeui_blacklist: set[str] = set(config.appeui_blacklist)

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
            return "-".join([clean[i:i + 2] for i in range(0, 16, 2)])
        return eui.lower()

    def _check_whitelist(
        self,
        value: str | None,
        whitelist: set[str],
        blacklist: set[str],
        field_name: str,
    ) -> bool:
        """Check if a value passes whitelist/blacklist filtering.

        Args:
            value: The value to check.
            whitelist: The set of allowed values (empty = allow all).
            blacklist: The set of blocked values.
            field_name: Name of the field for logging.

        Returns:
            True if the value passes filtering, False otherwise.
        """
        if value is None:
            # If no value provided and whitelist exists, fail
            if whitelist:
                logger.debug("No %s provided and whitelist is active", field_name)
                return False
            return True

        normalized = self._normalize_eui(value)

        # Check blacklist first
        if normalized in blacklist:
            logger.debug("%s %s is blacklisted", field_name, normalized)
            return False

        # Check whitelist (empty whitelist = allow all)
        if whitelist and normalized not in whitelist:
            logger.debug("%s %s not in whitelist", field_name, normalized)
            return False

        return True

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
            "DevEUI",
        ):
            return False

        # Check JoinEUI
        joineui = message.get_effective_joineui()
        if not self._check_whitelist(
            joineui,
            self._joineui_whitelist,
            self._joineui_blacklist,
            "JoinEUI",
        ):
            return False

        # Check AppEUI
        if not self._check_whitelist(
            message.appeui,
            self._appeui_whitelist,
            self._appeui_blacklist,
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
