"""Local MQTT broker client.

This module provides the MQTT client implementation for connecting
to the local LoRaWAN gateway broker.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from lora_mqtt_bridge.clients.base import BaseMQTTClient

if TYPE_CHECKING:
    from lora_mqtt_bridge.models.config import LocalBrokerConfig


logger = logging.getLogger(__name__)


class LocalMQTTClient(BaseMQTTClient):
    """MQTT client for the local LoRaWAN gateway broker.

    This client connects to the local MQTT broker on the gateway
    and subscribes to LoRaWAN uplink topics.

    Attributes:
        config: The local broker configuration.
    """

    def __init__(self, config: LocalBrokerConfig) -> None:
        """Initialize the local MQTT client.

        Args:
            config: The local broker configuration.
        """
        super().__init__(
            name="local",
            host=config.host,
            port=config.port,
            client_id=config.client_id,
            username=config.username,
            password=config.password,
            keepalive=config.keepalive,
            clean_session=False,
        )
        self.config = config
        self._subscribed_topics: list[str] = []

    def _on_connected(self) -> None:
        """Handle successful connection by subscribing to all local topics.

        Subscribes to both lora and scada topics so that remote brokers can
        independently choose which format(s) to forward.
        """
        # Subscribe to LoRa topics
        self.subscribe("lora/+/+/up")
        self._subscribed_topics.append("lora/+/+/up")

        self.subscribe("lora/+/joined")
        self._subscribed_topics.append("lora/+/joined")

        self.subscribe("lora/+/+/moved")
        self._subscribed_topics.append("lora/+/+/moved")

        # Subscribe to SCADA topics (scada/lorawan/$deveui/up)
        self.subscribe("scada/+/+/up")
        self._subscribed_topics.append("scada/+/+/up")

        logger.info(
            "Local client subscribed to %d topics (lora and scada)",
            len(self._subscribed_topics),
        )

    def publish_downlink(self, deveui: str, payload: str | bytes) -> None:
        """Publish a downlink message to the local broker.

        Args:
            deveui: The device EUI to send the downlink to.
            payload: The downlink payload (JSON string).
        """
        topic = self.config.topics.get_downlink_pattern() % deveui
        logger.info("Publishing downlink to %s", topic)
        self.publish(topic, payload, qos=1, retain=False)

    def publish_clear(self, deveui: str) -> None:
        """Publish a queue clear message to the local broker.

        Args:
            deveui: The device EUI to clear the queue for.
        """
        # Clear topic pattern - same as downlink but with /clear suffix
        if self.config.topics.format.value == "lora":
            topic = f"lora/{deveui}/clear"
        else:
            topic = f"scada/{deveui}/clear"

        logger.info("Publishing queue clear to %s", topic)
        self.publish(topic, None, qos=1, retain=False)

    def get_subscribed_topics(self) -> list[str]:
        """Get the list of subscribed topics.

        Returns:
            List of subscribed topic patterns.
        """
        return self._subscribed_topics.copy()
