# LoRa MQTT Bridge Documentation

## Overview

The LoRa MQTT Bridge is a Python application designed to bridge MQTT messages from a local LoRaWAN gateway broker to multiple remote MQTT brokers. It provides powerful filtering capabilities based on device identifiers and message fields.

## Table of Contents

- [Getting Started](getting-started.md)
- [Configuration Guide](configuration.md)
- [API Reference](api-reference.md)
- [Filtering Guide](filtering.md)
- [Topic Formats](topics.md)
- [Deployment Guide](deployment.md)

## Features

- **Multi-Broker Support**: Forward messages to multiple remote MQTT brokers simultaneously
- **Message Filtering**: Filter messages based on DevEUI, JoinEUI (AppEUI) using whitelists and blacklists
- **Field Filtering**: Include or exclude specific fields from forwarded messages
- **Flexible Topic Formats**: Support for both LoRa and SCADA topic formats
- **TLS Support**: Secure connections to remote brokers with full TLS/SSL support
- **Message Queuing**: Queue messages when remote brokers are temporarily unavailable
- **Dynamic Configuration**: Add or remove remote brokers at runtime
- **Downlink Support**: Receive downlinks from remote brokers and forward to devices

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with configuration file
python -m lora_mqtt_bridge -c config.json

# Or run with environment variables
export LORA_MQTT_BRIDGE_LOCAL_HOST=127.0.0.1
export LORA_MQTT_BRIDGE_REMOTE_HOST=cloud.example.com
python -m lora_mqtt_bridge --env
```

## Architecture

```
┌──────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   LoRa Gateway   │────▶│  MQTT Bridge    │────▶│ Remote Broker 1  │
│  (Local Broker)  │     │                 │────▶│ Remote Broker 2  │
│                  │◀────│                 │────▶│ Remote Broker N  │
└──────────────────┘     └─────────────────┘     └──────────────────┘
```

## License

This project is licensed under the Apache License 2.0.
