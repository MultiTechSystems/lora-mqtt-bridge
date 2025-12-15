"""Remote MQTT broker client.

This module provides the MQTT client implementation for connecting
to remote MQTT brokers with filtering capabilities.

Compatible with Python 3.10+ and paho-mqtt 1.6.x (mLinux 7.1.0)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from lora_mqtt_bridge.clients.base import BaseMQTTClient
from lora_mqtt_bridge.filters.field_filter import FieldFilter
from lora_mqtt_bridge.filters.message_filter import MessageFilter
from lora_mqtt_bridge.models.message import LoRaMessage
from lora_mqtt_bridge.utils.system_info import get_gateway_uuid

if TYPE_CHECKING:
    from lora_mqtt_bridge.models.config import RemoteBrokerConfig


logger = logging.getLogger(__name__)


class RemoteMQTTClient(BaseMQTTClient):
    """MQTT client for remote brokers with filtering support.

    This client connects to a remote MQTT broker and publishes
    filtered LoRaWAN messages received from the local broker.

    Attributes:
        config: The remote broker configuration.
        message_filter: Filter for messages based on device identifiers.
        field_filter: Filter for fields in message payloads.
    """

    def __init__(self, config: RemoteBrokerConfig) -> None:
        """Initialize the remote MQTT client.

        Args:
            config: The remote broker configuration.
        """
        client_id = config.client_id or f"lora-mqtt-bridge-{config.name}"
        super().__init__(
            name=config.name,
            host=config.host,
            port=config.port,
            client_id=client_id,
            username=config.username,
            password=config.password,
            keepalive=config.keepalive,
            clean_session=config.clean_session,
        )
        self.config = config
        self.message_filter = MessageFilter(config.message_filter)
        self.field_filter = FieldFilter(config.field_filter)

        # Queue for messages while disconnected
        self._message_queue: list[tuple[str, str]] = []
        self._max_queue_size = 10000

    def connect(self) -> None:
        """Connect to the remote MQTT broker with TLS if configured."""
        super().connect()

        # Configure TLS if enabled
        if self.config.tls.enabled and self._client is not None:
            self.configure_tls(
                ca_cert=self.config.tls.ca_cert,
                client_cert=self.config.tls.client_cert,
                client_key=self.config.tls.client_key,
                verify_hostname=self.config.tls.verify_hostname,
                insecure=self.config.tls.insecure,
            )

    def _on_connected(self) -> None:
        """Handle successful connection by processing queued messages."""
        logger.info("Remote client %s connected", self.name)

        # Publish any queued messages
        while self._message_queue:
            topic, payload = self._message_queue.pop(0)
            try:
                self.publish(topic, payload, self.config.qos, self.config.retain)
            except Exception:
                logger.exception("Failed to publish queued message")

    def forward_message(self, message: LoRaMessage) -> bool:
        """Forward a LoRa message to this remote broker if it passes filters.

        Args:
            message: The LoRa message to forward.

        Returns:
            True if the message was forwarded, False if filtered out.
        """
        # Check if message passes filters
        if not self.message_filter.should_forward(message):
            logger.debug(
                "Message from %s filtered out for broker %s",
                message.deveui,
                self.name,
            )
            return False

        # Build the topic for this broker
        topic = self._build_uplink_topic(message)

        # Filter and prepare payload
        filtered_payload = self.field_filter.filter_payload(message.raw_data)
        payload_str = json.dumps(filtered_payload)

        # Publish or queue the message
        if self.is_connected:
            try:
                self.publish(topic, payload_str, self.config.qos, self.config.retain)
                logger.debug(
                    "Forwarded message from %s to %s",
                    message.deveui,
                    self.name,
                )
                return True
            except Exception:
                logger.exception("Failed to publish to %s", self.name)
                self._queue_message(topic, payload_str)
                return False
        else:
            self._queue_message(topic, payload_str)
            return False

    def _build_uplink_topic(self, message: LoRaMessage) -> str:
        """Build the uplink topic for a message.

        Args:
            message: The LoRa message.

        Returns:
            The topic string to publish to.
        """
        # Get the base pattern
        pattern = self.config.topics.get_uplink_pattern()

        # Replace wildcards with actual values
        # Pattern could be like "lorawan/%(gwuuid)s/%(appeui)s/%(deveui)s/up"
        # or "lora/+/+/up" style

        if "%" in pattern:
            # Use format-style replacement
            format_dict: dict[str, Any] = {
                "deveui": message.deveui or "",
                "appeui": message.appeui or "",
                "joineui": message.get_effective_joineui() or "",
                "gweui": message.gweui or "",
                "gwuuid": get_gateway_uuid(),
            }
            return pattern % format_dict
        else:
            # Replace + wildcards with actual values
            parts = pattern.split("/")
            result_parts = []
            for part in parts:
                if part == "+":
                    # Try to substitute with deveui, then appeui
                    if message.deveui and not result_parts:
                        result_parts.append(message.deveui)
                    elif message.appeui:
                        result_parts.append(message.appeui or "")
                    elif message.deveui:
                        result_parts.append(message.deveui)
                    else:
                        result_parts.append("unknown")
                else:
                    result_parts.append(part)
            return "/".join(result_parts)

    def _queue_message(self, topic: str, payload: str) -> None:
        """Queue a message for later sending.

        Args:
            topic: The topic to publish to.
            payload: The message payload.
        """
        if len(self._message_queue) >= self._max_queue_size:
            # Remove oldest message
            self._message_queue.pop(0)
            logger.warning(
                "Message queue full for %s, dropping oldest message",
                self.name,
            )

        self._message_queue.append((topic, payload))
        logger.debug(
            "Queued message for %s, queue size: %d",
            self.name,
            len(self._message_queue),
        )

    def handle_downlink(self, topic: str, payload: bytes) -> dict[str, Any] | None:
        """Handle a downlink message from this remote broker.

        Args:
            topic: The topic the message was received on.
            payload: The message payload.

        Returns:
            Parsed downlink message dict or None if invalid.
        """
        try:
            data = json.loads(payload.decode("utf-8"))
            if "deveui" not in data:
                logger.error("Downlink missing deveui field")
                return None

            logger.info(
                "Received downlink for %s from %s",
                data.get("deveui"),
                self.name,
            )
            return data
        except json.JSONDecodeError:
            logger.error("Failed to parse downlink payload as JSON")
            return None

    def subscribe_to_downlinks(self, downlink_topic: str) -> None:
        """Subscribe to downlink topics on this remote broker.

        Args:
            downlink_topic: The topic pattern to subscribe to.
        """
        if self._client is not None:
            self.subscribe(downlink_topic, qos=1)
            logger.info(
                "Subscribed to downlinks on %s: %s",
                self.name,
                downlink_topic,
            )

    def get_queue_size(self) -> int:
        """Get the current message queue size.

        Returns:
            Number of messages in the queue.
        """
        return len(self._message_queue)
