# Filtering Guide

The LoRa MQTT Bridge provides powerful filtering capabilities to control which messages are forwarded and what data is included.

## Message Filtering

Message filtering allows you to control which devices' messages are forwarded to each remote broker based on device identifiers.

### Filter Types

The bridge supports three types of EUI-based filtering:

1. **Exact Match (Whitelist/Blacklist)** - Match specific EUI values
2. **Range Filters** - Match EUIs within a numeric range `[min, max]`
3. **Mask Patterns** - Match EUIs using wildcard patterns with `x` or `X`

These can be combined for flexible filtering strategies.

#### DevEUI Filtering

Filter messages based on the device's DevEUI (Device Extended Unique Identifier).

```json
{
  "message_filter": {
    "deveui_whitelist": ["00-11-22-33-44-55-66-77"],
    "deveui_blacklist": ["ff-ff-ff-ff-ff-ff-ff-ff"],
    "deveui_ranges": [
      ["00-11-22-33-44-55-00-00", "00-11-22-33-44-55-ff-ff"]
    ],
    "deveui_masks": ["00-11-22-xx-xx-xx-xx-xx"]
  }
}
```

#### JoinEUI Filtering

Filter messages based on the JoinEUI (also known as AppEUI in LoRaWAN 1.0.x).

```json
{
  "message_filter": {
    "joineui_whitelist": ["aa-bb-cc-dd-ee-ff-00-11"],
    "joineui_blacklist": [],
    "joineui_ranges": [],
    "joineui_masks": []
  }
}
```

#### AppEUI Filtering

Filter messages based on the AppEUI.

```json
{
  "message_filter": {
    "appeui_whitelist": ["aa-bb-cc-dd-ee-ff-00-11"],
    "appeui_blacklist": [],
    "appeui_ranges": [],
    "appeui_masks": []
  }
}
```

### Filter Rules

1. **Blacklist takes precedence**: If a device is in the blacklist, it will always be blocked, regardless of other filters.

2. **Allow filters (whitelist, ranges, masks) are combined with OR**: A message is allowed if it matches ANY of the allow filters.

3. **Empty allow filters means allow all**: If no whitelist, ranges, or masks are defined, all devices are allowed (subject to blacklist).

4. **Multiple filter types combine with AND**: A message must pass all EUI filter types (DevEUI, JoinEUI, AppEUI).

### Range Filters

Range filters allow you to specify a contiguous range of EUI values using `[min, max]` pairs. Both values are inclusive.

```json
{
  "message_filter": {
    "deveui_ranges": [
      ["00-11-22-33-44-55-66-00", "00-11-22-33-44-55-66-ff"]
    ]
  }
}
```

This allows devices with DevEUI from `00-11-22-33-44-55-66-00` to `00-11-22-33-44-55-66-ff` (256 devices).

**Multiple Ranges:**

```json
{
  "message_filter": {
    "deveui_ranges": [
      ["00-11-22-33-44-55-00-00", "00-11-22-33-44-55-00-ff"],
      ["00-11-22-33-44-55-ff-00", "00-11-22-33-44-55-ff-ff"]
    ]
  }
}
```

### Mask Patterns

Mask patterns use `x` or `X` as wildcards for any hexadecimal digit (0-9, a-f). This is useful for matching devices by manufacturer prefix or organizational unit.

```json
{
  "message_filter": {
    "deveui_masks": ["00-11-22-xx-xx-xx-xx-xx"]
  }
}
```

This matches any device whose DevEUI starts with `00-11-22-`.

**Pattern Examples:**

| Pattern | Matches |
|---------|---------|
| `00-11-22-xx-xx-xx-xx-xx` | Any device starting with `00-11-22-` |
| `xx-xx-xx-xx-xx-55-66-77` | Any device ending with `-55-66-77` |
| `00-xx-22-xx-44-xx-66-xx` | Alternating fixed and wildcard bytes |

**Multiple Masks:**

```json
{
  "message_filter": {
    "deveui_masks": [
      "00-11-xx-xx-xx-xx-xx-xx",
      "aa-bb-xx-xx-xx-xx-xx-xx"
    ]
  }
}
```

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

#### Allow Devices by Manufacturer Prefix

Forward messages from devices manufactured by a specific vendor (identified by OUI prefix):

```json
{
  "message_filter": {
    "deveui_masks": ["00-11-22-xx-xx-xx-xx-xx"]
  }
}
```

#### Allow a Range of Provisioned Devices

Forward messages from a batch of sequentially-numbered devices:

```json
{
  "message_filter": {
    "deveui_ranges": [
      ["00-11-22-33-44-55-00-01", "00-11-22-33-44-55-00-64"]
    ]
  }
}
```

This allows exactly 100 devices (0x01 to 0x64).

#### Combine Multiple Filter Types

Use whitelist, ranges, and masks together for complex filtering:

```json
{
  "message_filter": {
    "deveui_whitelist": ["ff-ff-ff-ff-ff-ff-ff-ff"],
    "deveui_ranges": [
      ["00-11-22-33-44-55-00-00", "00-11-22-33-44-55-00-ff"]
    ],
    "deveui_masks": ["aa-bb-cc-xx-xx-xx-xx-xx"],
    "deveui_blacklist": ["aa-bb-cc-00-00-00-00-00"]
  }
}
```

This allows:
- The specific device `ff-ff-ff-ff-ff-ff-ff-ff`
- Devices in the range `00-11-22-33-44-55-00-00` to `00-11-22-33-44-55-00-ff`
- Devices matching the mask `aa-bb-cc-xx-xx-xx-xx-xx`

But blocks:
- The specific device `aa-bb-cc-00-00-00-00-00` (blacklist overrides mask)

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
        "deveui_masks": ["00-11-xx-xx-xx-xx-xx-xx"]
      }
    },
    {
      "name": "batch-broker",
      "host": "batch.example.com",
      "message_filter": {
        "deveui_ranges": [
          ["00-00-00-00-00-00-00-01", "00-00-00-00-00-00-00-ff"]
        ]
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
