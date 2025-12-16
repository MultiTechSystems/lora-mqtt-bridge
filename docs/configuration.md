# Configuration Guide

The LoRa MQTT Bridge can be configured using a JSON configuration file or environment variables.

## Configuration File

### Complete Example

```json
{
  "local_broker": {
    "host": "127.0.0.1",
    "port": 1883,
    "username": null,
    "password": null,
    "client_id": "lora-mqtt-bridge-local",
    "topics": {
      "format": "lora",
      "uplink_pattern": "lora/+/+/up",
      "downlink_pattern": "lora/%s/down"
    },
    "keepalive": 60
  },
  "remote_brokers": [
    {
      "name": "cloud-primary",
      "enabled": true,
      "host": "mqtt.cloud.com",
      "port": 8883,
      "username": "user",
      "password": "pass",
      "client_id": "gateway-001",
      "tls": {
        "enabled": true,
        "ca_cert": "/path/to/ca.pem",
        "client_cert": "/path/to/client.pem",
        "client_key": "/path/to/client.key",
        "verify_hostname": true,
        "insecure": false
      },
      "source_topic_format": ["lora", "scada"],
      "topics": {
        "uplink_pattern": "lorawan/%(gwuuid)s/%(appeui)s/%(deveui)s/up",
        "downlink_pattern": "lorawan/%(deveui)s/down"
      },
      "message_filter": {
        "deveui_whitelist": [],
        "deveui_blacklist": [],
        "deveui_ranges": [],
        "deveui_masks": [],
        "joineui_whitelist": [],
        "joineui_blacklist": [],
        "joineui_ranges": [],
        "joineui_masks": [],
        "appeui_whitelist": [],
        "appeui_blacklist": [],
        "appeui_ranges": [],
        "appeui_masks": []
      },
      "field_filter": {
        "include_fields": [],
        "exclude_fields": ["rssi", "snr"],
        "always_include": ["deveui", "appeui", "time"]
      },
      "keepalive": 60,
      "clean_session": false,
      "qos": 1,
      "retain": true
    }
  ],
  "log": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "/var/log/lora-mqtt-bridge.log"
  },
  "reconnect_delay": 1.0,
  "max_reconnect_delay": 60.0
}
```

## Configuration Sections

### Local Broker

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| host | string | "127.0.0.1" | Local broker hostname |
| port | integer | 1883 | Local broker port |
| username | string | null | Authentication username |
| password | string | null | Authentication password |
| client_id | string | "lora-mqtt-bridge-local" | MQTT client ID |
| topics | object | - | Topic configuration |
| keepalive | integer | 60 | Keepalive interval in seconds |

### Remote Brokers

Each remote broker can have the following configuration:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| name | string | required | Unique broker identifier |
| enabled | boolean | true | Enable/disable this broker |
| host | string | required | Broker hostname |
| port | integer | 1883 | Broker port |
| username | string | null | Authentication username |
| password | string | null | Authentication password |
| client_id | string | auto-generated | MQTT client ID |
| tls | object | - | TLS configuration |
| source_topic_format | array | ["lora"] | Local topic formats to forward: "lora", "scada", or both |
| topics | object | - | Topic configuration |
| message_filter | object | - | Message filtering rules |
| field_filter | object | - | Field filtering rules |
| keepalive | integer | 60 | Keepalive interval |
| clean_session | boolean | false | MQTT clean session flag |
| qos | integer | 1 | Default QoS level (0-2) |
| retain | boolean | true | Retain published messages |

### TLS Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| enabled | boolean | false | Enable TLS |
| ca_cert | string | null | CA certificate path or content |
| client_cert | string | null | Client certificate path or content |
| client_key | string | null | Client key path or content |
| verify_hostname | boolean | true | Verify server hostname |
| insecure | boolean | false | Allow insecure connections |

### Topic Configuration

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| format | string | "lora" | Topic format: "lora" or "scada" |
| uplink_pattern | string | "lora/+/+/up" | Uplink topic pattern (supports `%(gwuuid)s`, `%(deveui)s`, `%(appeui)s`, `%(joineui)s`, `%(gweui)s`) |
| downlink_pattern | string | "lora/%s/down" | Downlink topic pattern |

**Note:** The `%(gwuuid)s` variable is automatically populated with the gateway's UUID at runtime.

### Message Filter Configuration

Each EUI type (deveui, joineui, appeui) supports four filter mechanisms:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| {eui}_whitelist | array | [] | Exact EUI values to allow |
| {eui}_blacklist | array | [] | Exact EUI values to block |
| {eui}_ranges | array | [] | Array of `[min, max]` EUI range pairs |
| {eui}_masks | array | [] | Array of mask patterns using `x` as wildcards |

**Filter Precedence:**
1. Blacklist always blocks (highest priority)
2. Whitelist, ranges, and masks are combined with OR (any match allows)
3. If no allow filters defined, all are allowed (subject to blacklist)

**Example with all filter types:**

```json
{
  "message_filter": {
    "deveui_whitelist": ["ff-ff-ff-ff-ff-ff-ff-ff"],
    "deveui_blacklist": ["00-00-00-00-00-00-00-00"],
    "deveui_ranges": [
      ["00-11-22-33-44-55-00-00", "00-11-22-33-44-55-ff-ff"]
    ],
    "deveui_masks": ["aa-bb-xx-xx-xx-xx-xx-xx"]
  }
}
```

See the [Filtering Guide](filtering.md) for detailed examples.

## Environment Variables

All configuration can be provided via environment variables with the prefix `LORA_MQTT_BRIDGE_`.

### Local Broker Variables

```bash
LORA_MQTT_BRIDGE_LOCAL_HOST=127.0.0.1
LORA_MQTT_BRIDGE_LOCAL_PORT=1883
LORA_MQTT_BRIDGE_LOCAL_USERNAME=user
LORA_MQTT_BRIDGE_LOCAL_PASSWORD=pass
LORA_MQTT_BRIDGE_LOCAL_CLIENT_ID=my-client
LORA_MQTT_BRIDGE_LOCAL_TOPIC_FORMAT=lora
LORA_MQTT_BRIDGE_LOCAL_UPLINK_PATTERN=lora/+/+/up
LORA_MQTT_BRIDGE_LOCAL_DOWNLINK_PATTERN=lora/%s/down
```

### Single Remote Broker Variables

```bash
LORA_MQTT_BRIDGE_REMOTE_NAME=cloud
LORA_MQTT_BRIDGE_REMOTE_HOST=mqtt.example.com
LORA_MQTT_BRIDGE_REMOTE_PORT=8883
LORA_MQTT_BRIDGE_REMOTE_USERNAME=user
LORA_MQTT_BRIDGE_REMOTE_PASSWORD=pass
LORA_MQTT_BRIDGE_REMOTE_TLS_ENABLED=true
LORA_MQTT_BRIDGE_REMOTE_TLS_VERIFY_HOSTNAME=true
LORA_MQTT_BRIDGE_REMOTE_DEVEUI_WHITELIST=00-11-22-33-44-55-66-77,aa-bb-cc-dd-ee-ff-00-11
LORA_MQTT_BRIDGE_REMOTE_EXCLUDE_FIELDS=rssi,snr,freq
```

### Multiple Remote Brokers (JSON)

```bash
LORA_MQTT_BRIDGE_REMOTE_BROKERS='[
  {"name": "broker1", "host": "broker1.example.com", "port": 8883},
  {"name": "broker2", "host": "broker2.example.com", "port": 8884}
]'
```

## Command Line Options

```
usage: lora-mqtt-bridge [-h] [-c CONFIG] [--env] [--log-level LEVEL] [--log-file FILE] [-v]

Options:
  -h, --help           Show help message
  -c, --config FILE    Path to configuration file (JSON)
  --env                Load configuration from environment variables
  --log-level LEVEL    Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --log-file FILE      Path to log file
  -v, --version        Show version
```
