# LoRa MQTT Bridge

A Python application to bridge MQTT messages from a local LoRaWAN gateway broker to multiple remote MQTT brokers with powerful filtering capabilities.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Features

- **Multi-Broker Support**: Forward messages to multiple remote MQTT brokers simultaneously
- **Message Filtering**: Filter messages based on DevEUI, JoinEUI, or AppEUI using whitelists and blacklists
- **Field Filtering**: Include or exclude specific fields from forwarded messages
- **Flexible Topic Formats**: Support for both LoRa and SCADA topic formats
- **TLS Support**: Secure connections to remote brokers with full TLS/SSL support
- **Message Queuing**: Queue messages when remote brokers are temporarily unavailable
- **Dynamic Configuration**: Add or remove remote brokers at runtime
- **Downlink Support**: Receive downlinks from remote brokers and forward to devices

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/lora-mqtt-bridge.git
cd lora-mqtt-bridge

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Using pip

```bash
pip install lora-mqtt-bridge
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

### Using a Configuration File

See [docs/configuration.md](docs/configuration.md) for complete configuration options.

### Using Environment Variables

```bash
# Local broker
export LORA_MQTT_BRIDGE_LOCAL_HOST=127.0.0.1
export LORA_MQTT_BRIDGE_LOCAL_PORT=1883

# Remote broker
export LORA_MQTT_BRIDGE_REMOTE_HOST=mqtt.example.com
export LORA_MQTT_BRIDGE_REMOTE_PORT=8883
export LORA_MQTT_BRIDGE_REMOTE_USERNAME=user
export LORA_MQTT_BRIDGE_REMOTE_PASSWORD=pass
export LORA_MQTT_BRIDGE_REMOTE_TLS_ENABLED=true
```

## Topic Formats

The bridge supports multiple topic formats:

### LoRa Format (Default)

```
lora/+/+/up       # Uplinks
lora/{deveui}/down  # Downlinks
```

### SCADA Format

```
scada/+/up        # Uplinks
scada/{deveui}/down  # Downlinks
```

Configure the format in your config file:

```json
{
  "local_broker": {
    "topics": {
      "format": "scada",
      "uplink_pattern": "scada/+/up",
      "downlink_pattern": "scada/%s/down"
    }
  }
}
```

## Filtering

### Message Filtering

Filter which devices' messages are forwarded:

```json
{
  "remote_brokers": [
    {
      "name": "cloud",
      "host": "mqtt.example.com",
      "message_filter": {
        "deveui_whitelist": ["00-11-22-33-44-55-66-77"],
        "appeui_blacklist": ["ff-ff-ff-ff-ff-ff-ff-ff"]
      }
    }
  ]
}
```

### Field Filtering

Control which fields are included in forwarded messages:

```json
{
  "remote_brokers": [
    {
      "name": "cloud",
      "host": "mqtt.example.com",
      "field_filter": {
        "exclude_fields": ["rssi", "snr", "freq"]
      }
    }
  ]
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

# Run type checker
mypy src
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/lora_mqtt_bridge --cov-report=html

# Run specific test file
pytest tests/test_filters.py
```

## Documentation

Full documentation is available in the [docs](docs/) directory:

- [Getting Started](docs/getting-started.md)
- [Configuration Guide](docs/configuration.md)
- [Filtering Guide](docs/filtering.md)
- [Topic Formats](docs/topics.md)
- [API Reference](docs/api-reference.md)
- [Deployment Guide](docs/deployment.md)

## Architecture

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   LoRa Gateway   │────▶│  MQTT Bridge    │────▶│ Remote Broker 1  │
│  (Local Broker)  │     │                 │────▶│ Remote Broker 2  │
│                  │◀────│                 │────▶│ Remote Broker N  │
└──────────────────┘     └─────────────────┘     └──────────────────┘
```

## Project Structure

```
lora-mqtt-bridge/
├── src/
│   └── lora_mqtt_bridge/
│       ├── __init__.py
│       ├── bridge.py          # Main bridge manager
│       ├── main.py            # CLI entry point
│       ├── clients/           # MQTT client implementations
│       │   ├── base.py        # Base client class
│       │   ├── local.py       # Local broker client
│       │   └── remote.py      # Remote broker client
│       ├── filters/           # Filtering implementations
│       │   ├── field_filter.py
│       │   └── message_filter.py
│       ├── models/            # Data models
│       │   ├── config.py      # Configuration models
│       │   └── message.py     # Message models
│       └── utils/             # Utilities
│           ├── config_loader.py
│           └── logging_setup.py
├── tests/                     # Test suite
├── docs/                      # Documentation
├── config/                    # Example configurations
├── requirements.txt
├── pyproject.toml
└── README.md
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

- Based on the original [Multitech LoRaWAN App Connect](https://multitechsystems.github.io/lorawan-app-connect-mqtt-v1_1) application
- Uses [paho-mqtt](https://github.com/eclipse/paho.mqtt.python) for MQTT connectivity
- Uses [Pydantic](https://pydantic.dev/) for configuration validation
