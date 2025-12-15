# LoRa MQTT Bridge - mLinux 7.1.0 Version

This is the mLinux 7.1.0 compatible version of the LoRa MQTT Bridge application.

## Compatibility

- **Python**: 3.10+ (tested with Python 3.10.15 on mLinux 7.1.0)
- **paho-mqtt**: 1.6.x (available in mLinux opkg feeds as `python3-paho-mqtt`)
- **Target Hardware**: MTCAP3 (Cortex-A7)
- **No external dependencies**: Uses only standard library and paho-mqtt

## Key Differences from Other Versions

| Feature | Ubuntu Version | mLinux 6 | mLinux 7 |
|---------|----------------|----------|----------|
| Python | 3.10+ | 3.8+ | 3.10+ |
| paho-mqtt | 2.x | 1.6.x | 1.6.x |
| pydantic | Required | Not used | Not used |
| Type hints | Modern (`list[str]`) | Legacy (`List[str]`) | Modern (`list[str]`) |
| Config validation | Pydantic | Dataclasses | Dataclasses |

## Installation on mLinux 7

### Using opkg (Recommended)

```bash
# Install Python and paho-mqtt from mLinux feeds
opkg update
opkg install python3-core python3-paho-mqtt python3-json python3-logging
```

### Copy Application Files

```bash
# Copy the src directory to the device
scp -r src/ root@<gateway-ip>:/opt/lora-mqtt-bridge/

# Copy configuration
scp config/example-config.json root@<gateway-ip>:/etc/lora-mqtt-bridge/config.json
```

### Running

```bash
# Run directly
cd /opt/lora-mqtt-bridge
python3 -m lora_mqtt_bridge -c /etc/lora-mqtt-bridge/config.json

# Or with environment variables
export LORA_MQTT_BRIDGE_LOCAL_HOST=127.0.0.1
export LORA_MQTT_BRIDGE_REMOTE_HOST=mqtt.example.com
python3 -m lora_mqtt_bridge --env
```

## Configuration

See the [ubuntu/docs/configuration.md](../ubuntu/docs/configuration.md) for full configuration options. The configuration format is identical across all versions.

### Example Configuration

```json
{
  "local_broker": {
    "host": "127.0.0.1",
    "port": 1883,
    "topics": {
      "format": "lora",
      "uplink_pattern": "lora/+/+/up",
      "downlink_pattern": "lora/%s/down"
    }
  },
  "remote_brokers": [
    {
      "name": "cloud",
      "host": "mqtt.example.com",
      "port": 8883,
      "username": "user",
      "password": "pass",
      "tls": {
        "enabled": true
      },
      "message_filter": {
        "deveui_whitelist": ["00-11-22-33-44-55-66-77"]
      },
      "field_filter": {
        "exclude_fields": ["rssi", "snr"]
      }
    }
  ]
}
```

## Running as a Systemd Service

Create `/etc/systemd/system/lora-mqtt-bridge.service`:

```ini
[Unit]
Description=LoRa MQTT Bridge
After=network.target mosquitto.service
Wants=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -m lora_mqtt_bridge -c /etc/lora-mqtt-bridge/config.json
WorkingDirectory=/opt/lora-mqtt-bridge
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable lora-mqtt-bridge
systemctl start lora-mqtt-bridge
```

## Development

### Running Tests

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install 'paho-mqtt>=1.6.0,<2.0.0' pytest pytest-mock
pip install -e .

# Run tests
pytest -v
```

## Available Packages in mLinux 7.1.0

The following Python packages are available via opkg:

- `python3-core` (3.10.15)
- `python3-paho-mqtt` (1.6.1)
- `python3-json`
- `python3-logging`
- `python3-typing-extensions` (3.10.0)
- `python3-ssl` (for TLS support)
- And many more standard library modules

## Building the Install Tarball

To create the custom application tarball for installation via mPower app-manager:

```bash
./build-tarball.sh
```

This creates `lora_mqtt_bridge-1.0.0-mlinux7.tar.gz` which can be installed:

1. **Via mPower Web UI**: Administration > Custom Applications > Upload
2. **Via command line**: `app-manager install lora_mqtt_bridge-1.0.0-mlinux7.tar.gz`

The tarball contains:
- `manifest.json` - Application metadata
- `Install` - Dependency installation script
- `Start` - Application start/stop script
- `status.json` - Application status file (updated by running app)
- `provisioning/` - Package dependencies
- `config/` - Default configuration
- `lora_mqtt_bridge/` - Python application source

## Application Status Display

The application writes its status to `status.json` in the application directory (`$APP_DIR/status.json`). This file is read by the mPower app-manager to display the application status in the web UI and DeviceHQ.

The status includes:
- **Connection status**: Local and remote broker connection states
- **Message count**: Number of messages forwarded
- **Error count**: Number of recent errors
- **Timestamp**: Last status update time

Example status display in mPower UI:
```
Local:OK | Remote:2/3 | Msgs:1234 | @ 14:32:15
```

## License

Apache License 2.0
