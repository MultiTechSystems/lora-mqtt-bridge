# Getting Started

This guide will help you get the LoRa MQTT Bridge up and running quickly.

## Prerequisites

- Python 3.10 or higher
- Access to a local MQTT broker (typically on the LoRaWAN gateway)
- Access to one or more remote MQTT brokers

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

## Basic Configuration

Create a `config.json` file:

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

## Running the Bridge

```bash
# Using configuration file
lora-mqtt-bridge -c config.json

# Or using the Python module
python -m lora_mqtt_bridge -c config.json
```

## Verifying Operation

1. Check the logs for successful connection messages:
   ```
   2024-01-15 10:00:00 - INFO - Connected to local broker
   2024-01-15 10:00:01 - INFO - Connected to remote broker: cloud
   ```

2. Send a test uplink from a device and verify it appears on your remote broker.

## Next Steps

- Read the [Configuration Guide](configuration.md) for detailed configuration options
- Learn about [Message Filtering](filtering.md) to filter which messages are forwarded
- Check the [Topic Formats](topics.md) guide for different topic configurations
