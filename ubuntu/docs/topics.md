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

Alternative topic format for SCADA systems:

**Local Subscriptions:**
- `scada/+/up` - Device uplinks

**Local Publishes:**
- `scada/{deveui}/down` - Downlinks to devices

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
- `%(deveui)s` - Device EUI
- `%(appeui)s` - Application EUI
- `%(joineui)s` - Join EUI
- `%(gweui)s` - Gateway EUI
- `%(gwuuid)s` - Gateway UUID (if available)

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

```json
{
  "topics": {
    "uplink_pattern": "gateways/%(gwuuid)s/devices/%(deveui)s/up"
  }
}
```

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

### Multiple Formats for Different Brokers

```json
{
  "remote_brokers": [
    {
      "name": "lora-server",
      "host": "lora.example.com",
      "topics": {
        "format": "lora",
        "uplink_pattern": "lorawan/%(appeui)s/%(deveui)s/up"
      }
    },
    {
      "name": "scada-server",
      "host": "scada.example.com",
      "topics": {
        "format": "scada",
        "uplink_pattern": "scada/%(deveui)s/up"
      }
    }
  ]
}
```
