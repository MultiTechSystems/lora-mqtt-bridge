"""LoRa MQTT Bridge - Bridge MQTT messages from local to remote brokers.

This package provides functionality to bridge MQTT messages from a local
LoRaWAN gateway broker to multiple remote MQTT brokers with filtering
and field selection capabilities.
"""

from lora_mqtt_bridge.bridge import MQTTBridge

__version__ = "1.0.0"
__all__ = ["MQTTBridge", "__version__"]
