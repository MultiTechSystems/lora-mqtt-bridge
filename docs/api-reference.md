# API Reference

This document provides detailed API documentation for the LoRa MQTT Bridge classes.

## MQTTBridge

The main bridge manager class that orchestrates message forwarding.

### Class: `MQTTBridge`

```python
from lora_mqtt_bridge import MQTTBridge
from lora_mqtt_bridge.models.config import BridgeConfig

config = BridgeConfig.from_dict(config_dict)
bridge = MQTTBridge(config)
```

#### Methods

##### `start() -> None`

Start the bridge and connect to all configured brokers.

```python
bridge.start()
```

##### `stop() -> None`

Stop the bridge and disconnect from all brokers.

```python
bridge.stop()
```

##### `run() -> None`

Run the bridge in the foreground until interrupted.

```python
bridge.run()  # Blocks until SIGINT/SIGTERM
```

##### `get_status() -> dict`

Get the current status of the bridge.

```python
status = bridge.get_status()
# Returns:
# {
#     "running": True,
#     "local_broker": {"connected": True, "host": "127.0.0.1", "port": 1883},
#     "remote_brokers": {
#         "cloud": {"connected": True, "queue_size": 0}
#     }
# }
```

##### `add_remote_broker(config: RemoteBrokerConfig) -> None`

Add a new remote broker dynamically.

```python
from lora_mqtt_bridge.models.config import RemoteBrokerConfig

new_broker = RemoteBrokerConfig(name="new", host="new.example.com")
bridge.add_remote_broker(new_broker)
```

##### `remove_remote_broker(name: str) -> bool`

Remove a remote broker.

```python
removed = bridge.remove_remote_broker("cloud")
```

## Configuration Models

### BridgeConfig

Main configuration container.

```python
from lora_mqtt_bridge.models.config import BridgeConfig

config = BridgeConfig(
    local_broker=LocalBrokerConfig(...),
    remote_brokers=[RemoteBrokerConfig(...)],
    log=LogConfig(...),
    reconnect_delay=1.0,
    max_reconnect_delay=60.0
)
```

### LocalBrokerConfig

Local MQTT broker configuration.

```python
from lora_mqtt_bridge.models.config import LocalBrokerConfig, TopicConfig

config = LocalBrokerConfig(
    host="127.0.0.1",
    port=1883,
    username=None,
    password=None,
    client_id="lora-mqtt-bridge-local",
    topics=TopicConfig(),
    keepalive=60
)
```

### RemoteBrokerConfig

Remote MQTT broker configuration.

```python
from lora_mqtt_bridge.models.config import (
    RemoteBrokerConfig,
    TLSConfig,
    TopicConfig,
    MessageFilterConfig,
    FieldFilterConfig
)

config = RemoteBrokerConfig(
    name="cloud",
    enabled=True,
    host="mqtt.example.com",
    port=8883,
    username="user",
    password="pass",
    client_id="gateway-001",
    tls=TLSConfig(enabled=True),
    topics=TopicConfig(),
    message_filter=MessageFilterConfig(),
    field_filter=FieldFilterConfig(),
    keepalive=60,
    clean_session=False,
    qos=1,
    retain=True
)
```

### MessageFilterConfig

Message filtering configuration.

```python
from lora_mqtt_bridge.models.config import MessageFilterConfig

config = MessageFilterConfig(
    deveui_whitelist=["00-11-22-33-44-55-66-77"],
    deveui_blacklist=[],
    joineui_whitelist=[],
    joineui_blacklist=[],
    appeui_whitelist=[],
    appeui_blacklist=[]
)
```

### FieldFilterConfig

Field filtering configuration.

```python
from lora_mqtt_bridge.models.config import FieldFilterConfig

config = FieldFilterConfig(
    include_fields=["deveui", "port", "data"],
    exclude_fields=[],
    always_include=["deveui", "time"]
)
```

## Filter Classes

### MessageFilter

Filter messages based on device identifiers.

```python
from lora_mqtt_bridge.filters import MessageFilter
from lora_mqtt_bridge.models.config import MessageFilterConfig
from lora_mqtt_bridge.models.message import LoRaMessage

config = MessageFilterConfig(deveui_whitelist=["00-11-22-33-44-55-66-77"])
filter = MessageFilter(config)

message = LoRaMessage(deveui="00-11-22-33-44-55-66-77")
should_forward = filter.should_forward(message)  # True
```

#### Methods

- `should_forward(message: LoRaMessage) -> bool`
- `add_to_deveui_whitelist(deveui: str) -> None`
- `remove_from_deveui_whitelist(deveui: str) -> None`
- `add_to_deveui_blacklist(deveui: str) -> None`
- `remove_from_deveui_blacklist(deveui: str) -> None`

### FieldFilter

Filter fields in message payloads.

```python
from lora_mqtt_bridge.filters import FieldFilter
from lora_mqtt_bridge.models.config import FieldFilterConfig

config = FieldFilterConfig(exclude_fields=["rssi", "snr"])
filter = FieldFilter(config)

payload = {"deveui": "...", "rssi": -85, "snr": 7.5, "data": "..."}
filtered = filter.filter_payload(payload)
# {"deveui": "...", "data": "..."}
```

#### Methods

- `filter_payload(payload: dict) -> dict`
- `add_include_field(field: str) -> None`
- `remove_include_field(field: str) -> None`
- `add_exclude_field(field: str) -> None`
- `remove_exclude_field(field: str) -> None`
- `set_always_include(fields: list[str]) -> None`

## Message Models

### LoRaMessage

Represents a LoRaWAN message.

```python
from lora_mqtt_bridge.models.message import LoRaMessage, MessageType

# From MQTT payload
message = LoRaMessage.from_mqtt_payload(
    payload={"deveui": "00-11-22-33-44-55-66-77", "port": 1, "data": "..."},
    topic="lora/app/dev/up",
    message_type=MessageType.UPLINK
)

# Access properties
print(message.deveui)  # "00-11-22-33-44-55-66-77"
print(message.get_effective_joineui())  # Returns joineui or appeui

# Convert to filtered dict
filtered_dict = message.to_filtered_dict(
    exclude_fields=["rssi", "snr"]
)
```

## Utility Functions

### Configuration Loading

```python
from lora_mqtt_bridge.utils import load_config, load_config_from_env

# From file
config = load_config("/path/to/config.json")

# From environment variables
config = load_config_from_env()
```

### Logging Setup

```python
from lora_mqtt_bridge.utils import setup_logging
from lora_mqtt_bridge.models.config import LogConfig

log_config = LogConfig(level="DEBUG", file="/var/log/bridge.log")
logger = setup_logging(log_config)
```
