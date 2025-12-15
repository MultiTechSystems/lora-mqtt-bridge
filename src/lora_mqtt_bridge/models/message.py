"""Message models for the LoRa MQTT Bridge.

This module defines data models for LoRaWAN messages including
uplinks, downlinks, and join events.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MessageType(str, Enum):
    """Enum for LoRaWAN message types."""

    UPLINK = "up"
    DOWNLINK = "down"
    JOINED = "joined"
    MOVED = "moved"
    CLEAR = "clear"


class LoRaMessage(BaseModel):
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

    deveui: str = Field(...)
    appeui: str | None = Field(default=None)
    joineui: str | None = Field(default=None)
    gweui: str | None = Field(default=None)
    time: datetime | str | None = Field(default=None)
    port: int | None = Field(default=None, ge=0, le=255)
    data: str | None = Field(default=None)
    raw_data: dict[str, Any] = Field(default_factory=dict)
    message_type: MessageType = Field(default=MessageType.UPLINK)
    topic: str | None = Field(default=None)

    @field_validator("deveui", "appeui", "joineui", "gweui", mode="before")
    @classmethod
    def normalize_eui(cls, v: str | None) -> str | None:
        """Normalize EUI values to lowercase with dashes.

        Args:
            v: The EUI string to normalize.

        Returns:
            The normalized EUI string or None.
        """
        if v is None:
            return None
        # Remove colons and convert to lowercase with dashes
        clean = v.replace(":", "").replace("-", "").lower()
        if len(clean) == 16:
            return "-".join([clean[i : i + 2] for i in range(0, 16, 2)])
        return v.lower()

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
            ValueError: If required fields are missing.
        """
        if "deveui" not in payload:
            raise ValueError("Message payload must contain 'deveui' field")

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

        result = {}
        source = self.raw_data if self.raw_data else self.model_dump(exclude_none=True)

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


class DownlinkMessage(BaseModel):
    """Model representing a LoRaWAN downlink message.

    Attributes:
        deveui: The device EUI.
        port: The LoRaWAN port number.
        data: The payload data (base64 encoded).
        confirmed: Whether the downlink should be confirmed.
        priority: The priority of the downlink.
    """

    deveui: str = Field(...)
    port: int = Field(default=1, ge=0, le=255)
    data: str = Field(...)
    confirmed: bool = Field(default=False)
    priority: int = Field(default=0, ge=0, le=255)

    @field_validator("deveui", mode="before")
    @classmethod
    def normalize_deveui(cls, v: str) -> str:
        """Normalize DevEUI to lowercase with dashes.

        Args:
            v: The DevEUI string to normalize.

        Returns:
            The normalized DevEUI string.
        """
        clean = v.replace(":", "").replace("-", "").lower()
        if len(clean) == 16:
            return "-".join([clean[i : i + 2] for i in range(0, 16, 2)])
        return v.lower()
