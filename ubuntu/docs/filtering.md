# Filtering Guide

The LoRa MQTT Bridge provides powerful filtering capabilities to control which messages are forwarded and what data is included.

## Message Filtering

Message filtering allows you to control which devices' messages are forwarded to each remote broker based on device identifiers.

### Filter Types

#### DevEUI Filtering

Filter messages based on the device's DevEUI (Device Extended Unique Identifier).

```json
{
  "message_filter": {
    "deveui_whitelist": ["00-11-22-33-44-55-66-77"],
    "deveui_blacklist": ["ff-ff-ff-ff-ff-ff-ff-ff"]
  }
}
```

#### JoinEUI Filtering

Filter messages based on the JoinEUI (also known as AppEUI in LoRaWAN 1.0.x).

```json
{
  "message_filter": {
    "joineui_whitelist": ["aa-bb-cc-dd-ee-ff-00-11"],
    "joineui_blacklist": []
  }
}
```

#### AppEUI Filtering

Filter messages based on the AppEUI.

```json
{
  "message_filter": {
    "appeui_whitelist": ["aa-bb-cc-dd-ee-ff-00-11"],
    "appeui_blacklist": []
  }
}
```

### Filter Rules

1. **Blacklist takes precedence**: If a device is in both whitelist and blacklist, it will be blocked.

2. **Empty whitelist allows all**: If the whitelist is empty, all devices are allowed (subject to blacklist).

3. **Non-empty whitelist restricts**: If the whitelist has entries, only those devices are allowed.

4. **Multiple filter types combine with AND**: A message must pass all filter types (DevEUI, JoinEUI, AppEUI).

### Examples

#### Allow Only Specific Devices

```json
{
  "message_filter": {
    "deveui_whitelist": [
      "00-11-22-33-44-55-66-77",
      "00-11-22-33-44-55-66-88"
    ]
  }
}
```

#### Block Specific Devices

```json
{
  "message_filter": {
    "deveui_blacklist": [
      "ff-ff-ff-ff-ff-ff-ff-ff"
    ]
  }
}
```

#### Filter by Application

Forward only messages from devices belonging to a specific application:

```json
{
  "message_filter": {
    "appeui_whitelist": ["aa-bb-cc-dd-ee-ff-00-11"]
  }
}
```

#### Different Filters for Different Brokers

```json
{
  "remote_brokers": [
    {
      "name": "app1-broker",
      "host": "app1.example.com",
      "message_filter": {
        "appeui_whitelist": ["aa-bb-cc-dd-ee-ff-00-11"]
      }
    },
    {
      "name": "app2-broker",
      "host": "app2.example.com",
      "message_filter": {
        "appeui_whitelist": ["11-22-33-44-55-66-77-88"]
      }
    }
  ]
}
```

## Field Filtering

Field filtering allows you to control which fields are included in forwarded messages.

### Filter Options

#### Include Fields

Only include specified fields (plus always-include fields):

```json
{
  "field_filter": {
    "include_fields": ["deveui", "port", "data", "fcnt"]
  }
}
```

#### Exclude Fields

Exclude specific fields from messages:

```json
{
  "field_filter": {
    "exclude_fields": ["rssi", "snr", "freq", "dr"]
  }
}
```

#### Always Include Fields

Fields that are always included regardless of other filters:

```json
{
  "field_filter": {
    "always_include": ["deveui", "appeui", "time"]
  }
}
```

### Field Filter Rules

1. **Always-include takes precedence**: Fields in `always_include` are never filtered out.

2. **Include mode**: If `include_fields` is non-empty, only those fields (plus always-include) are forwarded.

3. **Exclude mode**: If `include_fields` is empty, all fields except those in `exclude_fields` are forwarded.

### Example: Minimal Payload

Forward only essential fields to reduce bandwidth:

```json
{
  "field_filter": {
    "include_fields": ["deveui", "port", "data"],
    "always_include": ["deveui", "time"]
  }
}
```

Input message:
```json
{
  "deveui": "00-11-22-33-44-55-66-77",
  "appeui": "aa-bb-cc-dd-ee-ff-00-11",
  "time": "2024-01-15T10:00:00Z",
  "port": 1,
  "data": "SGVsbG8=",
  "rssi": -85,
  "snr": 7.5,
  "freq": 868.1,
  "fcnt": 42
}
```

Output message:
```json
{
  "deveui": "00-11-22-33-44-55-66-77",
  "time": "2024-01-15T10:00:00Z",
  "port": 1,
  "data": "SGVsbG8="
}
```

### Example: Remove RF Metadata

Forward messages without RF-specific metadata:

```json
{
  "field_filter": {
    "exclude_fields": ["rssi", "snr", "freq", "dr", "chan"]
  }
}
```

## EUI Format Normalization

All EUI values are automatically normalized to lowercase with dashes:

- `0011223344556677` → `00-11-22-33-44-55-66-77`
- `00:11:22:33:44:55:66:77` → `00-11-22-33-44-55-66-77`
- `AA-BB-CC-DD-EE-FF-00-11` → `aa-bb-cc-dd-ee-ff-00-11`

This ensures consistent matching regardless of input format.
