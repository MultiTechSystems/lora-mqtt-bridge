# Deployment Guide

This guide covers deployment options for the LoRa MQTT Bridge.

## Running as a Service

### Systemd Service (Linux)

Create a systemd service file `/etc/systemd/system/lora-mqtt-bridge.service`:

```ini
[Unit]
Description=LoRa MQTT Bridge
After=network.target mosquitto.service
Wants=network.target

[Service]
Type=simple
User=lora
Group=lora
WorkingDirectory=/opt/lora-mqtt-bridge
ExecStart=/opt/lora-mqtt-bridge/venv/bin/python -m lora_mqtt_bridge -c /etc/lora-mqtt-bridge/config.json
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=lora-mqtt-bridge

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable lora-mqtt-bridge
sudo systemctl start lora-mqtt-bridge
sudo systemctl status lora-mqtt-bridge
```

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY pyproject.toml .

RUN pip install --no-cache-dir -e .

CMD ["lora-mqtt-bridge", "--env"]
```

Build and run:

```bash
docker build -t lora-mqtt-bridge .
docker run -d \
  --name lora-bridge \
  --restart unless-stopped \
  -e LORA_MQTT_BRIDGE_LOCAL_HOST=host.docker.internal \
  -e LORA_MQTT_BRIDGE_REMOTE_HOST=mqtt.example.com \
  lora-mqtt-bridge
```

### Docker Compose

```yaml
version: '3.8'

services:
  lora-mqtt-bridge:
    build: .
    restart: unless-stopped
    environment:
      - LORA_MQTT_BRIDGE_LOCAL_HOST=${LOCAL_MQTT_HOST:-localhost}
      - LORA_MQTT_BRIDGE_LOCAL_PORT=1883
      - LORA_MQTT_BRIDGE_REMOTE_HOST=${REMOTE_MQTT_HOST}
      - LORA_MQTT_BRIDGE_REMOTE_PORT=${REMOTE_MQTT_PORT:-8883}
      - LORA_MQTT_BRIDGE_REMOTE_USERNAME=${REMOTE_MQTT_USER}
      - LORA_MQTT_BRIDGE_REMOTE_PASSWORD=${REMOTE_MQTT_PASS}
      - LORA_MQTT_BRIDGE_REMOTE_TLS_ENABLED=true
    volumes:
      - ./config.json:/app/config.json:ro
      - ./certs:/app/certs:ro
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Configuration Management

### Using Configuration Files

Store configuration in `/etc/lora-mqtt-bridge/config.json`:

```bash
sudo mkdir -p /etc/lora-mqtt-bridge
sudo cp config.json /etc/lora-mqtt-bridge/
sudo chmod 600 /etc/lora-mqtt-bridge/config.json
```

### Using Environment Variables

Create an environment file `/etc/lora-mqtt-bridge/env`:

```bash
LORA_MQTT_BRIDGE_LOCAL_HOST=127.0.0.1
LORA_MQTT_BRIDGE_REMOTE_HOST=mqtt.example.com
LORA_MQTT_BRIDGE_REMOTE_USERNAME=user
LORA_MQTT_BRIDGE_REMOTE_PASSWORD=secret
```

Load in systemd:

```ini
[Service]
EnvironmentFile=/etc/lora-mqtt-bridge/env
ExecStart=/opt/lora-mqtt-bridge/venv/bin/python -m lora_mqtt_bridge --env
```

## Monitoring

### Log Management

Configure logging to file:

```json
{
  "log": {
    "level": "INFO",
    "file": "/var/log/lora-mqtt-bridge/bridge.log"
  }
}
```

Set up log rotation `/etc/logrotate.d/lora-mqtt-bridge`:

```
/var/log/lora-mqtt-bridge/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 lora lora
    postrotate
        systemctl reload lora-mqtt-bridge 2>/dev/null || true
    endscript
}
```

### Health Checks

The bridge provides a status method that can be used for health checks:

```python
from lora_mqtt_bridge import MQTTBridge

bridge = MQTTBridge(config)
status = bridge.get_status()

if not status["running"]:
    raise Exception("Bridge not running")

if not status["local_broker"]["connected"]:
    raise Exception("Local broker disconnected")

for name, info in status["remote_brokers"].items():
    if not info["connected"]:
        print(f"Warning: {name} disconnected")
```

## Security Best Practices

### TLS Configuration

Always use TLS for remote connections:

```json
{
  "remote_brokers": [
    {
      "name": "cloud",
      "host": "mqtt.example.com",
      "port": 8883,
      "tls": {
        "enabled": true,
        "ca_cert": "/etc/lora-mqtt-bridge/certs/ca.pem",
        "client_cert": "/etc/lora-mqtt-bridge/certs/client.pem",
        "client_key": "/etc/lora-mqtt-bridge/certs/client.key",
        "verify_hostname": true
      }
    }
  ]
}
```

### Credential Management

- Store credentials in environment variables, not in config files
- Use secrets management systems in production
- Restrict file permissions on configuration files

```bash
sudo chmod 600 /etc/lora-mqtt-bridge/config.json
sudo chown lora:lora /etc/lora-mqtt-bridge/config.json
```

### Network Security

- Use firewalls to restrict access to MQTT ports
- Consider using VPNs for remote broker connections
- Monitor connection attempts and failures

## Performance Tuning

### Message Queue Size

Adjust queue size for high-volume deployments:

```python
# In RemoteMQTTClient
client._max_queue_size = 50000  # Default is 10000
```

### Keepalive Intervals

Configure appropriate keepalive values:

```json
{
  "local_broker": {
    "keepalive": 60
  },
  "remote_brokers": [
    {
      "keepalive": 120
    }
  ]
}
```

### Reconnection Strategy

Configure reconnection behavior:

```json
{
  "reconnect_delay": 1.0,
  "max_reconnect_delay": 60.0
}
```

## Troubleshooting

### Common Issues

1. **Connection refused to local broker**
   - Check that the local broker is running
   - Verify the host and port configuration
   - Check firewall rules

2. **TLS handshake failures**
   - Verify certificate validity
   - Check hostname verification settings
   - Ensure CA certificate is correct

3. **Messages not forwarding**
   - Check filter configurations
   - Verify topic patterns match incoming messages
   - Enable DEBUG logging to see filter decisions

4. **High memory usage**
   - Check message queue sizes
   - Monitor for connection issues causing queue buildup
   - Consider reducing max queue size

### Debug Mode

Enable debug logging:

```bash
lora-mqtt-bridge -c config.json --log-level DEBUG
```

Or in configuration:

```json
{
  "log": {
    "level": "DEBUG"
  }
}
```
