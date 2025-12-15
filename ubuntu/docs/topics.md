# Topic Formats

The LoRa MQTT Bridge supports flexible topic configuration for both local and remote brokers.

## Supported Topic Formats

### LoRa Format (Default)

Standard topic format used by Multitech gateways:

**Local Subscriptions:**
- `lora/+/+/up` - Device uplinks
- `lora/+/joined` - Join events
- `lora/+/+/moved` - Device moved events

**Local Publishes:**
- `lora/{deveui}/down` - Downlinks to devices
- `lora/{deveui}/clear` - Clear downlink queue

### SCADA Format

Alternative topic format for SCADA systems with decoded payload data:

**Local Subscriptions:**
- `scada/+/+/up` - Device uplinks (e.g., `scada/lorawan/{deveui}/up`)

**Local Publishes:**
- `scada/{deveui}/down` - Downlinks to devices

**Note:** SCADA topics contain JSON-decoded payload data instead of base64-encoded data.

## Configuration

### Local Broker Topics

```json
{
  "local_broker": {
    "topics": {
      "format": "lora",
      "uplink_pattern": "lora/+/+/up",
      "downlink_pattern": "lora/%s/down"
    }
  }
}
```

### Remote Broker Topics

Remote broker topics can use format strings with message fields:

```json
{
  "remote_brokers": [
    {
      "name": "cloud",
      "topics": {
        "format": "lora",
        "uplink_pattern": "lorawan/%(appeui)s/%(deveui)s/up",
        "downlink_pattern": "lorawan/%(deveui)s/down"
      }
    }
  ]
}
```

## Topic Pattern Variables

### For Uplink Patterns

Available variables for format strings:
- `%(deveui)s` - Device EUI (e.g., `00-80-00-00-0a-00-11-ba`)
- `%(appeui)s` - Application EUI (e.g., `16-ea-76-f6-ab-66-3d-80`)
- `%(joineui)s` - Join EUI (e.g., `16-ea-76-f6-ab-66-3d-80`)
- `%(gweui)s` - Gateway EUI (e.g., `00-80-00-00-d0-00-42-6e`)
- `%(gwuuid)s` - Gateway UUID, automatically retrieved at runtime (e.g., `244ab1fb-b08d-1dcc-d02d-bee6f5236ced`)

### For Downlink Patterns

- `%s` - Device EUI (simple format)
- `%(deveui)s` - Device EUI (named format)

## Examples

### Standard LoRa Topics

```json
{
  "topics": {
    "format": "lora",
    "uplink_pattern": "lora/+/+/up",
    "downlink_pattern": "lora/%s/down"
  }
}
```

Topic examples:
- Uplink: `lora/aa-bb-cc-dd/00-11-22-33/up`
- Downlink: `lora/00-11-22-33/down`

### Cloud-Style Topics

```json
{
  "topics": {
    "uplink_pattern": "lorawan/%(appeui)s/%(deveui)s/up",
    "downlink_pattern": "lorawan/%(deveui)s/down"
  }
}
```

Topic examples:
- Uplink: `lorawan/aa-bb-cc-dd-ee-ff-00-11/00-11-22-33-44-55-66-77/up`
- Downlink: `lorawan/00-11-22-33-44-55-66-77/down`

### Flat Topic Structure

```json
{
  "topics": {
    "uplink_pattern": "devices/%(deveui)s/uplink",
    "downlink_pattern": "devices/%s/downlink"
  }
}
```

### Including Gateway UUID

The gateway UUID is automatically retrieved from the system at runtime (from `/sys/devices/platform/mts-io/uuid` on MultiTech gateways):

```json
{
  "topics": {
    "uplink_pattern": "lorawan/%(gwuuid)s/%(appeui)s/%(deveui)s/up"
  }
}
```

Example output topic: `lorawan/244ab1fb-b08d-1dcc-d02d-bee6f5236ced/16-ea-76-f6-ab-66-3d-80/00-80-00-00-0a-00-11-ba/up`

## Wildcard Topics

### MQTT Wildcards in Subscriptions

- `+` - Single-level wildcard
- `#` - Multi-level wildcard

Example local subscription patterns:
```
lora/+/+/up       # Match: lora/appeui/deveui/up
lora/+/joined     # Match: lora/deveui/joined
lora/#            # Match all lora topics
```

### Wildcard Replacement on Publish

When publishing to remote brokers, wildcards in the configured pattern are replaced with actual values from the message:

Pattern: `lora/+/+/up`
Message DevEUI: `00-11-22-33-44-55-66-77`
Message AppEUI: `aa-bb-cc-dd-ee-ff-00-11`
Result: `lora/aa-bb-cc-dd-ee-ff-00-11/00-11-22-33-44-55-66-77/up`

## Switching Topic Formats

### Using Environment Variables

```bash
# Switch to SCADA format
export LORA_MQTT_BRIDGE_LOCAL_TOPIC_FORMAT=scada
export LORA_MQTT_BRIDGE_LOCAL_UPLINK_PATTERN=scada/+/up
export LORA_MQTT_BRIDGE_LOCAL_DOWNLINK_PATTERN=scada/%s/down
```

### Source Topic Format Selection

Each remote broker can specify which local topic formats to forward using `source_topic_format`. This allows you to selectively forward LoRa messages, SCADA messages, or both:

```json
{
  "remote_brokers": [
    {
      "name": "lora-only",
      "host": "lora.example.com",
      "source_topic_format": ["lora"],
      "topics": {
        "uplink_pattern": "lorawan/%(gwuuid)s/%(appeui)s/%(deveui)s/up"
      }
    },
    {
      "name": "scada-only",
      "host": "scada.example.com",
      "source_topic_format": ["scada"],
      "topics": {
        "uplink_pattern": "scada/%(deveui)s/up"
      }
    },
    {
      "name": "all-data",
      "host": "cloud.example.com",
      "source_topic_format": ["lora", "scada"],
      "topics": {
        "uplink_pattern": "devices/%(gwuuid)s/%(deveui)s/up"
      }
    }
  ]
}
```

**Note:** If `source_topic_format` is not specified, it defaults to `["lora"]`.

### Multiple Formats for Different Brokers

```json
{
  "remote_brokers": [
    {
      "name": "lora-server",
      "host": "lora.example.com",
      "source_topic_format": ["lora"],
      "topics": {
        "uplink_pattern": "lorawan/%(gwuuid)s/%(appeui)s/%(deveui)s/up"
      }
    },
    {
      "name": "scada-server",
      "host": "scada.example.com",
      "source_topic_format": ["scada"],
      "topics": {
        "uplink_pattern": "scada/%(deveui)s/up"
      }
    }
  ]
}
```
