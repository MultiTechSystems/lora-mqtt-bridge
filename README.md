# LoRa MQTT Bridge

A Python application to bridge MQTT messages from a local LoRaWAN gateway broker to multiple remote MQTT brokers with powerful filtering capabilities.

[![CI](https://github.com/MultiTechSystems/lora-mqtt-bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/MultiTechSystems/lora-mqtt-bridge/actions/workflows/ci.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Features

- **Multi-Broker Support**: Forward messages to multiple remote MQTT brokers simultaneously
- **Flexible Topic Forwarding**: Each remote broker can receive LoRa topics, SCADA topics, or both
- **Message Filtering**: Filter messages based on DevEUI, JoinEUI, or AppEUI using whitelists and blacklists
- **Field Filtering**: Include or exclude specific fields from forwarded messages
- **Dynamic Topic Patterns**: Use variables like `%(gwuuid)s`, `%(deveui)s`, `%(appeui)s` in remote topics
- **Gateway UUID**: Automatically retrieve gateway UUID for topic patterns
- **TLS Support**: Secure connections to remote brokers with full TLS/SSL support
- **Message Queuing**: Queue messages when remote brokers are temporarily unavailable
- **Status Reporting**: Write status.json for mLinux app-manager integration
- **Syslog Logging**: Native syslog support for gateway deployments

## Platform Support

| Platform | Python Version | Status |
|----------|---------------|--------|
| Ubuntu/Debian | 3.10+ | ✅ Supported |
| MultiTech mLinux 7 | 3.10 | ✅ Supported |
| MultiTech mLinux 6 | 3.8 | ✅ Supported |

## Installation

### MultiTech Conduit Gateway (mLinux)

Download the appropriate tarball from the [releases page](https://github.com/MultiTechSystems/lora-mqtt-bridge/releases):

- `lora_mqtt_bridge-1.0.0-mlinux7.tar.gz` for mLinux 7.x
- `lora_mqtt_bridge-1.0.0-mlinux6.tar.gz` for mLinux 6.x

Install via the mPower web UI:
1. Navigate to **Administration > Custom Applications**
2. Click **Upload** and select the tarball
3. Click **Install**
4. Configure via the app's config file at `/var/config/app/lora_mqtt_bridge/config/config.json`
5. Start the application

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/MultiTechSystems/lora-mqtt-bridge.git
cd lora-mqtt-bridge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

## Quick Start

### 1. Create a Configuration File

Create `config.json`:

```json
{
  "local_broker": {
    "host": "127.0.0.1",
    "port": 1883
  },
  "remote_brokers": [
    {
      "name": "cloud",
      "host": "mqtt.example.com",
      "port": 8883,
      "username": "your-username",
      "password": "your-password",
      "tls": {
        "enabled": true
      },
      "source_topic_format": ["lora", "scada"],
      "topics": {
        "uplink_pattern": "lorawan/%(gwuuid)s/%(appeui)s/%(deveui)s/up"
      }
    }
  ]
}
```

### 2. Run the Bridge

```bash
# Using configuration file
lora-mqtt-bridge -c config.json

# Or using environment variables
export LORA_MQTT_BRIDGE_LOCAL_HOST=127.0.0.1
export LORA_MQTT_BRIDGE_REMOTE_HOST=mqtt.example.com
lora-mqtt-bridge --env
```

## Configuration

### Source Topic Format

Each remote broker can specify which local topics to forward:

```json
{
  "remote_brokers": [
    {
      "name": "lora-only",
      "host": "lora.example.com",
      "source_topic_format": ["lora"]
    },
    {
      "name": "scada-only", 
      "host": "scada.example.com",
      "source_topic_format": ["scada"]
    },
    {
      "name": "all-data",
      "host": "cloud.example.com",
      "source_topic_format": ["lora", "scada"]
    }
  ]
}
```

### Topic Pattern Variables

Use these variables in remote broker `uplink_pattern`:

| Variable | Description | Example |
|----------|-------------|---------|
| `%(gwuuid)s` | Gateway UUID (auto-detected) | `244ab1fb-b08d-1dcc-d02d-bee6f5236ced` |
| `%(deveui)s` | Device EUI | `00-80-00-00-0a-00-11-ba` |
| `%(appeui)s` | Application EUI | `16-ea-76-f6-ab-66-3d-80` |
| `%(joineui)s` | Join EUI | `16-ea-76-f6-ab-66-3d-80` |
| `%(gweui)s` | Gateway EUI | `00-80-00-00-d0-00-42-6e` |

Example:
```json
{
  "topics": {
    "uplink_pattern": "lorawan/%(gwuuid)s/%(appeui)s/%(deveui)s/up"
  }
}
```

### Message Filtering

Filter which devices' messages are forwarded:

```json
{
  "message_filter": {
    "deveui_whitelist": ["00-11-22-33-44-55-66-77"],
    "appeui_blacklist": ["ff-ff-ff-ff-ff-ff-ff-ff"]
  }
}
```

### Field Filtering

Control which fields are included in forwarded messages:

```json
{
  "field_filter": {
    "exclude_fields": ["rssi", "snr", "freq"],
    "always_include": ["deveui", "appeui", "time"]
  }
}
```

See [docs/configuration.md](docs/configuration.md) for complete configuration options.

## Topic Formats

### LoRa Format (Default)

Local subscriptions:
- `lora/+/+/up` - Device uplinks
- `lora/+/joined` - Join events
- `lora/+/+/moved` - Device moved events

### SCADA Format

Local subscriptions:
- `scada/+/+/up` - Device uplinks (e.g., `scada/lorawan/{deveui}/up`)

SCADA topics contain JSON-decoded payload data instead of base64-encoded data.

## Status Monitoring

On mLinux gateways, the application writes status to `/var/config/app/lora_mqtt_bridge/status.json`:

```json
{
  "pid": 12345,
  "AppInfo": "Local:OK | Remote:2/2 | Msgs:1234 @ 14:30:00"
}
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src tests

# Run formatter
ruff format src tests

# Run type checker
mypy src --ignore-missing-imports
```

### Project Structure

```
lora-mqtt-bridge/
├── src/lora_mqtt_bridge/      # Main source (Python 3.10+)
├── mlinux-6/                  # mLinux 6 version (Python 3.8)
├── mlinux-7/                  # mLinux 7 version (Python 3.10)
├── ubuntu/                    # Ubuntu/server version
├── tests/                     # Test suite
├── docs/                      # Documentation
├── config/                    # Example configurations
└── dist/                      # Built tarballs
```

## Documentation

- [Getting Started](docs/getting-started.md)
- [Configuration Guide](docs/configuration.md)
- [Filtering Guide](docs/filtering.md)
- [Topic Formats](docs/topics.md)
- [API Reference](docs/api-reference.md)
- [Deployment Guide](docs/deployment.md)
- [Cursor Agent Development Guide](docs/cursor-agent-guide.md)

## Architecture

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   LoRa Gateway   │────▶│  MQTT Bridge    │────▶│ Remote Broker 1  │
│  (Local Broker)  │     │                 │────▶│ Remote Broker 2  │
│                  │◀────│                 │────▶│ Remote Broker N  │
└──────────────────┘     └─────────────────┘     └──────────────────┘
```

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- Based on the [MultiTech LoRaWAN App Connect](https://multitechsystems.github.io/lorawan-app-connect-mqtt-v1_1) specification
- Uses [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) for MQTT connectivity
