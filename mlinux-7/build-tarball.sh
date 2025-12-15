#!/bin/bash

# Build script for LoRa MQTT Bridge mLinux 7.1.0 custom application tarball
# This creates a tarball that can be installed via the mPower AEP app-manager

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"
SRC_DIR="$SCRIPT_DIR/src"

# Get version from git tag, fallback to 1.0.0
VERSION=$(git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || echo "1.0.0")
TARBALL_NAME="lora_mqtt_bridge-${VERSION}-mlinux7.tar.gz"
BUILD_DIR="$SCRIPT_DIR/build"

echo "Building LoRa MQTT Bridge tarball for mLinux 7.1.0..."

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy required files to build directory (flat structure at top level)
cp "$DIST_DIR/Install" "$BUILD_DIR/"
cp "$DIST_DIR/Start" "$BUILD_DIR/"
cp "$DIST_DIR/status.json" "$BUILD_DIR/"

# Generate manifest.json with current version
cat > "$BUILD_DIR/manifest.json" << EOF
{
  "AppName": "lora_mqtt_bridge",
  "AppVersion": "$VERSION",
  "AppDescription": "Bridge MQTT messages from local LoRaWAN gateway to multiple remote MQTT brokers with filtering capabilities",
  "AppVersionNotes": "Release $VERSION for mLinux 7.1.0 (Python 3.10, paho-mqtt 1.6.x)"
}
EOF

# Copy provisioning directory
cp -r "$DIST_DIR/provisioning" "$BUILD_DIR/"

# Copy config directory
cp -r "$DIST_DIR/config" "$BUILD_DIR/"

# Copy the application source as lora_mqtt_bridge directory (excluding __pycache__)
mkdir -p "$BUILD_DIR/lora_mqtt_bridge"
find "$SRC_DIR/lora_mqtt_bridge" -type f -name "*.py" | while read f; do
    # Get relative path from src/lora_mqtt_bridge
    rel_path="${f#$SRC_DIR/lora_mqtt_bridge/}"
    # Create target directory if needed
    target_dir="$BUILD_DIR/lora_mqtt_bridge/$(dirname "$rel_path")"
    mkdir -p "$target_dir"
    cp "$f" "$BUILD_DIR/lora_mqtt_bridge/$rel_path"
done

# Make scripts executable
chmod +x "$BUILD_DIR/Install"
chmod +x "$BUILD_DIR/Start"

# Create the tarball with files at top level
cd "$BUILD_DIR"
tar -czvf "$SCRIPT_DIR/$TARBALL_NAME" \
    manifest.json \
    Install \
    Start \
    status.json \
    provisioning/ \
    config/ \
    lora_mqtt_bridge/

echo ""
echo "Tarball created: $SCRIPT_DIR/$TARBALL_NAME"
echo ""
echo "Contents:"
tar -tzvf "$SCRIPT_DIR/$TARBALL_NAME"

# Clean up
rm -rf "$BUILD_DIR"

echo ""
echo "To install on the device:"
echo "  1. Upload the tarball to the device"
echo "  2. Use app-manager to install: app-manager install $TARBALL_NAME"
echo "  3. Or install via the mPower web UI under Administration > Custom Applications"
