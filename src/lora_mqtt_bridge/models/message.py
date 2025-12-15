"""Message models for the LoRa MQTT Bridge.

This module defines data models for LoRaWAN messages including
uplinks, downlinks, and join events.

Compatible with Python 3.10+ and mLinux 7.1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    """Enum for LoRaWAN message types."""

    UPLINK = "up"
    DOWNLINK = "down"
    JOINED = "joined"
    MOVED = "moved"
    CLEAR = "clear"


def _normalize_eui(eui: str | int | None) -> str | None:
    """Normalize EUI values to lowercase with dashes.

    Args:
        eui: The EUI string (or int) to normalize.

    Returns:
        The normalized EUI string or None.
    """
    if eui is None:
        return None
    # Convert to string if not already
    if not isinstance(eui, str):
        eui = str(eui)
    # Remove colons and convert to lowercase with dashes
    clean = eui.replace(":", "").replace("-", "").lower()
    if len(clean) == 16:
        return "-".join([clean[i : i + 2] for i in range(0, 16, 2)])
    return eui.lower()


@dataclass
class LoRaMessage:
    """Model representing a LoRaWAN message.

    Attributes:
        deveui: The device EUI.
        appeui: The application EUI (JoinEUI).
        joineui: Alias for appeui (JoinEUI).
        gweui: The gateway EUI.
        time: The timestamp of the message.
        port: The LoRaWAN port number.
        data: The payload data (base64 encoded).
        raw_data: The raw message data dictionary.
        message_type: The type of message.
        topic: The original MQTT topic.
    """

    deveui: str = ""
    appeui: str | None = None
    joineui: str | None = None
    gweui: str | None = None
    time: datetime | str | None = None
    port: int | None = None
    data: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    message_type: MessageType = MessageType.UPLINK
    topic: str | None = None

    def __post_init__(self) -> None:
        """Normalize EUI values after initialization."""
        self.deveui = _normalize_eui(self.deveui) or ""
        self.appeui = _normalize_eui(self.appeui)
        self.joineui = _normalize_eui(self.joineui)
        self.gweui = _normalize_eui(self.gweui)

    @classmethod
    def from_mqtt_payload(
        cls,
        payload: dict[str, Any],
        topic: str | None = None,
        message_type: MessageType = MessageType.UPLINK,
    ) -> LoRaMessage:
        """Create a LoRaMessage from an MQTT payload.

        Args:
            payload: The parsed JSON payload from MQTT.
            topic: The MQTT topic the message was received on.
            message_type: The type of message.

        Returns:
            A LoRaMessage instance.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        if "deveui" not in payload:
            raise ValueError("Message payload must contain 'deveui' field")

        deveui = payload.get("deveui")
        # Reject null, empty, or whitespace-only deveui
        if deveui is None:
            raise ValueError("deveui cannot be null")
        if isinstance(deveui, str) and not deveui.strip():
            raise ValueError("deveui cannot be empty")

        return cls(
            deveui=payload.get("deveui", ""),
            appeui=payload.get("appeui"),
            joineui=payload.get("joineui") or payload.get("appeui"),
            gweui=payload.get("gweui"),
            time=payload.get("time"),
            port=payload.get("port"),
            data=payload.get("data"),
            raw_data=payload,
            message_type=message_type,
            topic=topic,
        )

    def get_effective_joineui(self) -> str | None:
        """Get the effective JoinEUI (joineui or appeui).

        Returns:
            The JoinEUI value or None.
        """
        return self.joineui or self.appeui

    def to_filtered_dict(
        self,
        include_fields: list[str] | None = None,
        exclude_fields: list[str] | None = None,
        always_include: list[str] | None = None,
    ) -> dict[str, Any]:
        """Convert message to a filtered dictionary.

        Args:
            include_fields: Fields to include (empty/None = all).
            exclude_fields: Fields to exclude.
            always_include: Fields to always include regardless of filters.

        Returns:
            A filtered dictionary representation of the message.
        """
        always_include = always_include or ["deveui", "appeui", "time"]
        exclude_fields = exclude_fields or []

        result: dict[str, Any] = {}
        source = self.raw_data if self.raw_data else self._to_dict()

        for key, value in source.items():
            # Skip internal fields
            if key in ("raw_data", "message_type", "topic"):
                continue

            # Always include required fields
            if key in always_include:
                result[key] = value
                continue

            # Check exclude list
            if key in exclude_fields:
                continue

            # Check include list (if specified)
            if include_fields and key not in include_fields:
                continue

            result[key] = value

        return result

    def _to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values.

        Returns:
            Dictionary representation.
        """
        result: dict[str, Any] = {}
        if self.deveui:
            result["deveui"] = self.deveui
        if self.appeui:
            result["appeui"] = self.appeui
        if self.joineui:
            result["joineui"] = self.joineui
        if self.gweui:
            result["gweui"] = self.gweui
        if self.time:
            result["time"] = self.time
        if self.port is not None:
            result["port"] = self.port
        if self.data:
            result["data"] = self.data
        return result


@dataclass
class DownlinkMessage:
    """Model representing a LoRaWAN downlink message.

    Attributes:
        deveui: The device EUI.
        port: The LoRaWAN port number.
        data: The payload data (base64 encoded).
        confirmed: Whether the downlink should be confirmed.
        priority: The priority of the downlink.
    """

    deveui: str = ""
    port: int = 1
    data: str = ""
    confirmed: bool = False
    priority: int = 0

    def __post_init__(self) -> None:
        """Normalize DevEUI after initialization."""
        self.deveui = _normalize_eui(self.deveui) or ""
