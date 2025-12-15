"""Base MQTT client class.

This module provides the abstract base class for MQTT client implementations
used in the LoRa MQTT Bridge.

Compatible with Python 3.10+ and paho-mqtt 1.6.x (mLinux 7.1.0)
"""

from __future__ import annotations

import logging
import ssl
import tempfile
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


# Type alias for message callback
MessageCallback = Callable[[str, bytes], None]


class BaseMQTTClient(ABC):
    """Abstract base class for MQTT clients.

    This class provides common functionality for MQTT client implementations
    including connection management, TLS configuration, and message handling.

    Attributes:
        name: A descriptive name for this client.
        host: The broker hostname.
        port: The broker port.
        client_id: The MQTT client ID.
        username: Optional authentication username.
        password: Optional authentication password.
        keepalive: The keepalive interval in seconds.
    """

    def __init__(
        self,
        name: str,
        host: str,
        port: int = 1883,
        client_id: str | None = None,
        username: str | None = None,
        password: str | None = None,
        keepalive: int = 60,
        clean_session: bool = False,
    ) -> None:
        """Initialize the MQTT client.

        Args:
            name: A descriptive name for this client.
            host: The broker hostname.
            port: The broker port.
            client_id: The MQTT client ID.
            username: Optional authentication username.
            password: Optional authentication password.
            keepalive: The keepalive interval in seconds.
            clean_session: Whether to use a clean session.
        """
        self.name = name
        self.host = host
        self.port = port
        self.client_id = client_id or f"lora-mqtt-bridge-{name}"
        self.username = username
        self.password = password
        self.keepalive = keepalive
        self.clean_session = clean_session

        self._client: mqtt.Client | None = None
        self._connected = False
        self._lock = threading.Lock()
        self._message_callbacks: list[MessageCallback] = []
        self._temp_files: list[Path] = []

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected.

        Returns:
            True if connected, False otherwise.
        """
        return self._connected

    def _create_client(self) -> mqtt.Client:
        """Create and configure the MQTT client.

        Returns:
            A configured paho MQTT client instance.
        """
        # paho-mqtt 1.6.x API
        client = mqtt.Client(
            client_id=self.client_id,
            clean_session=self.clean_session,
            userdata={"name": self.name},
        )

        # Set up authentication
        if self.username or self.password:
            client.username_pw_set(self.username, self.password)

        # Set up callbacks (paho-mqtt 1.6.x callback signatures)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.on_subscribe = self._on_subscribe

        return client

    def configure_tls(
        self,
        ca_cert: str | None = None,
        client_cert: str | None = None,
        client_key: str | None = None,
        verify_hostname: bool = True,
        insecure: bool = False,
    ) -> None:
        """Configure TLS for the client connection.

        Args:
            ca_cert: Path to CA certificate or certificate content.
            client_cert: Path to client certificate or certificate content.
            client_key: Path to client key or key content.
            verify_hostname: Whether to verify the server hostname.
            insecure: Allow insecure connections.
        """
        if self._client is None:
            raise RuntimeError("Client not created. Call connect() first.")

        # Determine if we have paths or content
        ca_file = self._prepare_cert_file(ca_cert, "ca")
        cert_file = self._prepare_cert_file(client_cert, "client_cert")
        key_file = self._prepare_cert_file(client_key, "client_key")

        # Default CA if none provided
        if ca_file is None:
            ca_file = "/var/config/ca-cert-links/ca-certificates.crt"
            if not Path(ca_file).exists():
                ca_file = "/etc/ssl/certs/ca-certificates.crt"

        cert_reqs = ssl.CERT_REQUIRED if ca_cert else ssl.CERT_NONE

        try:
            self._client.tls_set(
                ca_certs=ca_file,
                certfile=cert_file,
                keyfile=key_file,
                cert_reqs=cert_reqs,
                tls_version=ssl.PROTOCOL_TLSv1_2,
            )
            self._client.tls_insecure_set(insecure or not verify_hostname)
            logger.info("TLS configured for client %s", self.name)
        except Exception as e:
            logger.exception("Failed to configure TLS for client %s", self.name)
            raise RuntimeError(f"TLS configuration failed: {e}") from e

    def _prepare_cert_file(self, cert_data: str | None, prefix: str) -> str | None:
        """Prepare a certificate file from path or content.

        Args:
            cert_data: File path or certificate content.
            prefix: Prefix for temporary file name.

        Returns:
            Path to the certificate file or None.
        """
        if cert_data is None or cert_data.strip() == "":
            return None

        # Check if it's a file path
        if Path(cert_data).exists():
            return cert_data

        # It's certificate content, write to temp file
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            prefix=f"{prefix}_{self.name}_",
            suffix=".pem",
            delete=False,
        )
        temp_file.write(cert_data)
        temp_file.flush()
        temp_file.close()
        self._temp_files.append(Path(temp_file.name))
        return temp_file.name

    def connect(self) -> None:
        """Connect to the MQTT broker.

        Raises:
            RuntimeError: If connection fails.
        """
        try:
            self._client = self._create_client()
            logger.info(
                "Connecting to %s at %s:%d",
                self.name,
                self.host,
                self.port,
            )
            self._client.connect(self.host, self.port, self.keepalive)
            self._client.loop_start()
        except Exception as e:
            logger.exception("Failed to connect to %s", self.name)
            raise RuntimeError(f"Connection to {self.name} failed: {e}") from e

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self._client is not None:
            logger.info("Disconnecting from %s", self.name)
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
            self._connected = False

        # Clean up temporary certificate files
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass
        self._temp_files.clear()

    def subscribe(self, topic: str, qos: int = 1) -> None:
        """Subscribe to an MQTT topic.

        Args:
            topic: The topic pattern to subscribe to.
            qos: The QoS level for the subscription.
        """
        if self._client is None:
            raise RuntimeError("Client not connected")

        logger.info("Subscribing to topic: %s (qos=%d)", topic, qos)
        self._client.subscribe(topic, qos)

    def publish(
        self,
        topic: str,
        payload: str | bytes | None,
        qos: int = 1,
        retain: bool = False,
    ) -> None:
        """Publish a message to an MQTT topic.

        Args:
            topic: The topic to publish to.
            payload: The message payload.
            qos: The QoS level for the publish.
            retain: Whether to retain the message.
        """
        if self._client is None:
            raise RuntimeError("Client not connected")

        with self._lock:
            self._client.publish(topic, payload, qos, retain)
            log_payload = str(payload)[:100] if payload else None
            logger.debug("Published to %s: %s", topic, log_payload)

    def add_message_callback(self, callback: MessageCallback) -> None:
        """Add a callback for received messages.

        Args:
            callback: A callable that takes (topic, payload) arguments.
        """
        self._message_callbacks.append(callback)

    def remove_message_callback(self, callback: MessageCallback) -> None:
        """Remove a message callback.

        Args:
            callback: The callback to remove.
        """
        if callback in self._message_callbacks:
            self._message_callbacks.remove(callback)

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: dict[str, Any],
        flags: dict[str, Any],
        rc: int,
    ) -> None:
        """Handle connection events (paho-mqtt 1.6.x callback signature).

        Args:
            client: The MQTT client instance.
            userdata: User data attached to the client.
            flags: Connection flags.
            rc: The connection result code.
        """
        if rc == 0:
            self._connected = True
            logger.info("Connected to %s successfully", self.name)
            self._on_connected()
        else:
            logger.error("Connection to %s failed with code: %d", self.name, rc)

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: dict[str, Any],
        rc: int,
    ) -> None:
        """Handle disconnection events (paho-mqtt 1.6.x callback signature).

        Args:
            client: The MQTT client instance.
            userdata: User data attached to the client.
            rc: The disconnect reason code.
        """
        self._connected = False
        logger.warning("Disconnected from %s with code: %d", self.name, rc)

    def _on_subscribe(
        self,
        client: mqtt.Client,
        userdata: dict[str, Any],
        mid: int,
        granted_qos: Any,
    ) -> None:
        """Handle subscription acknowledgments (paho-mqtt 1.6.x callback signature).

        Args:
            client: The MQTT client instance.
            userdata: User data attached to the client.
            mid: The message ID.
            granted_qos: The granted QoS levels.
        """
        logger.debug("Subscription acknowledged for %s: mid=%d", self.name, mid)

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: dict[str, Any],
        msg: mqtt.MQTTMessage,
    ) -> None:
        """Handle received messages (paho-mqtt 1.6.x callback signature).

        Args:
            client: The MQTT client instance.
            userdata: User data attached to the client.
            msg: The received message.
        """
        logger.debug("Message received on %s: topic=%s", self.name, msg.topic)
        for callback in self._message_callbacks:
            try:
                callback(msg.topic, msg.payload)
            except Exception:
                logger.exception("Error in message callback")

    @abstractmethod
    def _on_connected(self) -> None:
        """Handle successful connection - to be implemented by subclasses."""
        pass
