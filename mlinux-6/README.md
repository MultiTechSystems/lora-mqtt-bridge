# LoRa MQTT Bridge - mLinux 6.3.5 Version

This is the mLinux 6.3.5 compatible version of the LoRa MQTT Bridge application.

## Compatibility

- **Python**: 3.8+ (tested with Python 3.8.13 on mLinux 6.3.5)
- **paho-mqtt**: 1.6.x (available in mLinux opkg feeds as `python3-paho-mqtt`)
- **No external dependencies**: Uses only standard library and paho-mqtt

## Key Differences from Ubuntu Version

| Feature | Ubuntu Version | mLinux Version |
|---------|----------------|----------------|
| Python | 3.10+ | 3.8+ |
| paho-mqtt | 2.x | 1.6.x |
| pydantic | Required | Not used (dataclasses) |
| python-dotenv | Required | Not used (os.environ) |
| structlog | Required | Not used (logging) |
| Type hints | Modern syntax (`list[str]`) | Legacy syntax (`List[str]`) |

## Installation on mLinux

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

See the [ubuntu/docs/configuration.md](../ubuntu/docs/configuration.md) for full configuration options. The configuration format is identical between versions.

### Example Configuration

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
      "username": "user",
      "password": "pass",
      "tls": {
        "enabled": true
      }
    }
  ]
}
```

## Running as a Service

Create `/etc/init.d/lora-mqtt-bridge`:

```bash
#!/bin/sh

DAEMON=/opt/lora-mqtt-bridge/src/lora_mqtt_bridge/main.py
CONFIG=/etc/lora-mqtt-bridge/config.json
PIDFILE=/var/run/lora-mqtt-bridge.pid

start() {
    echo "Starting lora-mqtt-bridge..."
    start-stop-daemon -S -b -m -p $PIDFILE -x python3 -- $DAEMON -c $CONFIG
}

stop() {
    echo "Stopping lora-mqtt-bridge..."
    start-stop-daemon -K -p $PIDFILE
    rm -f $PIDFILE
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    *)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
esac
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

## Building the Install Tarball

To create the custom application tarball for installation via mPower app-manager:

```bash
./build-tarball.sh
```

This creates `lora_mqtt_bridge-1.0.0-mlinux6.tar.gz` which can be installed:

1. **Via mPower Web UI**: Administration > Custom Applications > Upload
2. **Via command line**: `app-manager install lora_mqtt_bridge-1.0.0-mlinux6.tar.gz`

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
