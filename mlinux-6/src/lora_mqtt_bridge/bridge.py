"""MQTT Bridge - Main bridge manager class.

This module provides the MQTTBridge class that orchestrates
the bridging of messages between local and remote MQTT brokers.
"""

from __future__ import annotations

import json
import logging
import signal
import threading
from typing import TYPE_CHECKING, Any

from lora_mqtt_bridge.clients.local import LocalMQTTClient
from lora_mqtt_bridge.clients.remote import RemoteMQTTClient
from lora_mqtt_bridge.models.config import TopicFormat
from lora_mqtt_bridge.models.message import LoRaMessage, MessageType
from lora_mqtt_bridge.utils.status_writer import get_status_writer

if TYPE_CHECKING:
    from lora_mqtt_bridge.models.config import BridgeConfig


logger = logging.getLogger(__name__)


class MQTTBridge:
    """Main MQTT bridge manager.

    This class manages the lifecycle of MQTT connections and coordinates
    message forwarding between the local broker and multiple remote brokers.

    Attributes:
        config: The bridge configuration.
        local_client: The local MQTT broker client.
        remote_clients: Dictionary of remote broker clients by name.
    """

    def __init__(self, config: BridgeConfig) -> None:
        """Initialize the MQTT bridge.

        Args:
            config: The bridge configuration.
        """
        self.config = config
        self._running = False
        self._shutdown_event = threading.Event()

        # Create local client
        self.local_client = LocalMQTTClient(config.local_broker)
        self.local_client.add_message_callback(self._handle_local_message)

        # Create remote clients
        self.remote_clients: dict[str, RemoteMQTTClient] = {}
        for remote_config in config.remote_brokers:
            if remote_config.enabled:
                client = RemoteMQTTClient(remote_config)
                client.add_message_callback(self._handle_remote_message)
                self.remote_clients[remote_config.name] = client
                logger.info("Configured remote broker: %s", remote_config.name)

    def start(self) -> None:
        """Start the MQTT bridge.

        Connects to all configured brokers and begins message forwarding.
        """
        logger.info("Starting MQTT bridge")
        self._running = True

        # Get status writer
        status_writer = get_status_writer()

        # Connect to local broker
        try:
            self.local_client.connect()
            logger.info("Connected to local broker")
            status_writer.set_local_connected(True)
        except Exception:
            logger.exception("Failed to connect to local broker")
            status_writer.set_local_connected(False)
            raise

        # Connect to remote brokers
        for name, client in self.remote_clients.items():
            try:
                client.connect()
                logger.info("Connected to remote broker: %s", name)
                status_writer.set_remote_connected(name, True)
            except Exception:
                logger.exception("Failed to connect to remote broker: %s", name)
                status_writer.set_remote_connected(name, False)
                # Continue with other brokers

        logger.info("MQTT bridge started with %d remote brokers", len(self.remote_clients))

    def stop(self) -> None:
        """Stop the MQTT bridge.

        Disconnects from all brokers and releases resources.
        """
        logger.info("Stopping MQTT bridge")
        self._running = False
        self._shutdown_event.set()

        # Disconnect from remote brokers
        for name, client in self.remote_clients.items():
            try:
                client.disconnect()
                logger.info("Disconnected from remote broker: %s", name)
            except Exception:
                logger.exception("Error disconnecting from remote broker: %s", name)

        # Disconnect from local broker
        try:
            self.local_client.disconnect()
            logger.info("Disconnected from local broker")
        except Exception:
            logger.exception("Error disconnecting from local broker")

        logger.info("MQTT bridge stopped")

    def run(self) -> None:
        """Run the bridge in the foreground until interrupted.

        This method blocks until a SIGINT or SIGTERM signal is received.
        """
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.start()

        logger.info("MQTT bridge running. Press Ctrl+C to stop.")

        try:
            while self._running:
                # Periodic health check
                self._health_check()
                self._shutdown_event.wait(timeout=5.0)
        finally:
            self.stop()

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals.

        Args:
            signum: The signal number.
            frame: The current stack frame.
        """
        logger.info("Received signal %d, shutting down", signum)
        self._running = False
        self._shutdown_event.set()

    def _health_check(self) -> None:
        """Perform periodic health check on connections."""
        if not self.local_client.is_connected:
            logger.warning("Local broker disconnected, attempting reconnect")
            try:
                self.local_client.connect()
            except Exception:
                logger.exception("Reconnection to local broker failed")

        for name, client in self.remote_clients.items():
            if not client.is_connected:
                logger.warning("Remote broker %s disconnected, attempting reconnect", name)
                try:
                    client.connect()
                except Exception:
                    logger.exception("Reconnection to %s failed", name)

    def _handle_local_message(self, topic: str, payload: bytes) -> None:
        """Handle messages received from the local broker.

        Args:
            topic: The MQTT topic.
            payload: The message payload.
        """
        logger.debug("Received local message on topic: %s", topic)

        # Parse message type from topic
        message_type = self._parse_message_type(topic)
        if message_type is None:
            logger.debug("Unknown message type for topic: %s", topic)
            return

        # Determine the source topic format (lora or scada)
        source_format = self._get_source_topic_format(topic)
        if source_format is None:
            logger.debug("Unknown topic format for topic: %s", topic)
            return

        # Parse payload
        try:
            data = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.error("Failed to parse message payload")
            return

        # Validate required fields
        if "deveui" not in data:
            logger.error("Message missing required 'deveui' field")
            return

        # Create message object
        try:
            message = LoRaMessage.from_mqtt_payload(data, topic, message_type)
        except ValueError as e:
            logger.error("Failed to create LoRaMessage: %s", e)
            return

        # Forward to remote brokers that are configured to receive this topic format
        forwarded_count = 0
        status_writer = get_status_writer()
        for name, client in self.remote_clients.items():
            # Check if this remote broker wants this source topic format
            if source_format not in client.config.source_topic_format:
                logger.debug(
                    "Skipping %s for broker %s (format %s not in %s)",
                    message.deveui,
                    name,
                    source_format.value,
                    [f.value for f in client.config.source_topic_format],
                )
                continue

            if client.forward_message(message):
                forwarded_count += 1
                status_writer.increment_message_count()

        logger.debug(
            "Message from %s (%s) forwarded to %d/%d remote brokers",
            message.deveui,
            source_format.value,
            forwarded_count,
            len(self.remote_clients),
        )

    def _handle_remote_message(self, topic: str, payload: bytes) -> None:
        """Handle messages received from remote brokers (downlinks).

        Args:
            topic: The MQTT topic.
            payload: The message payload.
        """
        logger.debug("Received remote message on topic: %s", topic)

        # Parse payload
        try:
            data = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.error("Failed to parse downlink payload")
            return

        # Validate required fields
        if "deveui" not in data:
            logger.error("Downlink missing required 'deveui' field")
            return

        deveui = data["deveui"]

        # Check if this is a clear command or downlink
        if "clear" in topic.lower():
            logger.info("Processing queue clear for %s", deveui)
            self.local_client.publish_clear(deveui)
        else:
            logger.info("Processing downlink for %s", deveui)
            self.local_client.publish_downlink(deveui, json.dumps(data))

    def _parse_message_type(self, topic: str) -> MessageType | None:
        """Parse the message type from an MQTT topic.

        Args:
            topic: The MQTT topic string.

        Returns:
            The MessageType or None if unknown.
        """
        parts = topic.split("/")

        # Find the event type in the topic
        for part in parts:
            part_lower = part.lower()
            if part_lower == "up":
                return MessageType.UPLINK
            elif part_lower == "down":
                return MessageType.DOWNLINK
            elif part_lower == "joined":
                return MessageType.JOINED
            elif part_lower == "moved":
                return MessageType.MOVED
            elif part_lower == "clear":
                return MessageType.CLEAR

        return None

    def _get_source_topic_format(self, topic: str) -> TopicFormat | None:
        """Determine the source topic format from the topic string.

        Args:
            topic: The MQTT topic string.

        Returns:
            TopicFormat.LORA, TopicFormat.SCADA, or None if unknown.
        """
        parts = topic.split("/")
        if not parts:
            return None

        prefix = parts[0].lower()
        if prefix == "lora":
            return TopicFormat.LORA
        elif prefix == "scada":
            return TopicFormat.SCADA

        return None

    def get_status(self) -> dict[str, Any]:
        """Get the current status of the bridge.

        Returns:
            Dictionary containing status information.
        """
        remote_status = {}
        for name, client in self.remote_clients.items():
            remote_status[name] = {
                "connected": client.is_connected,
                "queue_size": client.get_queue_size(),
            }

        return {
            "running": self._running,
            "local_broker": {
                "connected": self.local_client.is_connected,
                "host": self.local_client.host,
                "port": self.local_client.port,
            },
            "remote_brokers": remote_status,
        }

    def add_remote_broker(self, config: Any) -> None:
        """Add a new remote broker dynamically.

        Args:
            config: The RemoteBrokerConfig for the new broker.
        """
        if config.name in self.remote_clients:
            logger.warning("Remote broker %s already exists", config.name)
            return

        client = RemoteMQTTClient(config)
        client.add_message_callback(self._handle_remote_message)

        if self._running:
            try:
                client.connect()
            except Exception:
                logger.exception("Failed to connect new remote broker: %s", config.name)
                return

        self.remote_clients[config.name] = client
        logger.info("Added remote broker: %s", config.name)

    def remove_remote_broker(self, name: str) -> bool:
        """Remove a remote broker.

        Args:
            name: The name of the broker to remove.

        Returns:
            True if removed, False if not found.
        """
        if name not in self.remote_clients:
            logger.warning("Remote broker %s not found", name)
            return False

        client = self.remote_clients.pop(name)
        try:
            client.disconnect()
        except Exception:
            logger.exception("Error disconnecting removed broker: %s", name)

        logger.info("Removed remote broker: %s", name)
        return True
