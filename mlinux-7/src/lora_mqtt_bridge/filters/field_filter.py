"""Field filtering for uplink messages.

This module provides functionality to filter which fields are included
in forwarded uplink messages.

Compatible with Python 3.10+ and mLinux 7.1.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lora_mqtt_bridge.models.config import FieldFilterConfig


logger = logging.getLogger(__name__)


class FieldFilter:
    """Filter fields in message payloads.

    This class provides functionality to include or exclude specific
    fields from message payloads before forwarding.

    Attributes:
        config: The field filter configuration.
    """

    def __init__(self, config: FieldFilterConfig) -> None:
        """Initialize the field filter.

        Args:
            config: The filter configuration containing include/exclude settings.
        """
        self.config = config
        self._include_fields: set[str] = set(config.include_fields)
        self._exclude_fields: set[str] = set(config.exclude_fields)
        self._always_include: set[str] = set(config.always_include)

    def filter_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Filter a message payload based on configured rules.

        Args:
            payload: The original message payload dictionary.

        Returns:
            A filtered payload dictionary.
        """
        result: dict[str, Any] = {}

        for key, value in payload.items():
            # Always include required fields
            if key in self._always_include:
                result[key] = value
                continue

            # Check exclude list first
            if key in self._exclude_fields:
                logger.debug("Excluding field: %s", key)
                continue

            # Check include list (empty = include all not excluded)
            if self._include_fields and key not in self._include_fields:
                logger.debug("Field not in include list: %s", key)
                continue

            result[key] = value

        logger.debug(
            "Filtered payload from %d to %d fields",
            len(payload),
            len(result),
        )
        return result

    def add_include_field(self, field: str) -> None:
        """Add a field to the include list.

        Args:
            field: The field name to add.
        """
        self._include_fields.add(field)
        logger.info("Added field '%s' to include list", field)

    def remove_include_field(self, field: str) -> None:
        """Remove a field from the include list.

        Args:
            field: The field name to remove.
        """
        self._include_fields.discard(field)
        logger.info("Removed field '%s' from include list", field)

    def add_exclude_field(self, field: str) -> None:
        """Add a field to the exclude list.

        Args:
            field: The field name to add.
        """
        self._exclude_fields.add(field)
        logger.info("Added field '%s' to exclude list", field)

    def remove_exclude_field(self, field: str) -> None:
        """Remove a field from the exclude list.

        Args:
            field: The field name to remove.
        """
        self._exclude_fields.discard(field)
        logger.info("Removed field '%s' from exclude list", field)

    def set_always_include(self, fields: list[str]) -> None:
        """Set the list of fields to always include.

        Args:
            fields: List of field names to always include.
        """
        self._always_include = set(fields)
        logger.info("Set always-include fields: %s", fields)
