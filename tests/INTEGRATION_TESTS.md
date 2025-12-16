# Integration Tests for LoRa MQTT Bridge

This document describes the integration tests that should be performed to validate the end-to-end functionality of the LoRa MQTT Bridge application. Integration tests verify that different components work together correctly in realistic scenarios.

## Table of Contents

1. [Test Environment Setup](#test-environment-setup)
2. [Broker Connection Tests](#broker-connection-tests)
3. [Message Forwarding Tests](#message-forwarding-tests)
4. [Message Filtering Tests](#message-filtering-tests)
5. [Field Filtering Tests](#field-filtering-tests)
6. [Topic Format Tests](#topic-format-tests)
7. [Downlink Message Tests](#downlink-message-tests)
8. [Reconnection and Resilience Tests](#reconnection-and-resilience-tests)
9. [Configuration Tests](#configuration-tests)
10. [Multi-Broker Tests](#multi-broker-tests)
11. [TLS/SSL Tests](#tlsssl-tests)
12. [Performance Tests](#performance-tests)
13. [Status Writer Tests](#status-writer-tests)

---

## Test Environment Setup

### Prerequisites

- Docker or local MQTT broker (Mosquitto recommended)
- Python 3.10+
- pytest with pytest-asyncio
- Two or more MQTT broker instances (can be separate ports on localhost)

### Test Broker Configuration

```bash
# Start local MQTT broker on port 1883 (simulates gateway broker)
mosquitto -p 1883 -v

# Start remote MQTT broker on port 1884 (simulates cloud broker)
mosquitto -p 1884 -v

# Start second remote MQTT broker on port 1885 (for multi-broker tests)
mosquitto -p 1885 -v
```

---

## Broker Connection Tests

### IT-CONN-001: Local Broker Connection

**Description:** Verify the bridge can connect to a local MQTT broker successfully.

**Preconditions:**
- Local MQTT broker is running on `127.0.0.1:1883`
- Bridge is configured with valid local broker settings

**Steps:**
1. Create a `BridgeConfig` with local broker settings pointing to the test broker
2. Initialize `MQTTBridge` with the config
3. Call `bridge.start()`
4. Check `bridge.local_client.is_connected`
5. Call `bridge.stop()`

**Expected Results:**
- Bridge connects to local broker without errors
- `local_client.is_connected` returns `True` after start
- Connection is cleanly closed after stop

---

### IT-CONN-002: Remote Broker Connection

**Description:** Verify the bridge can connect to a remote MQTT broker successfully.

**Preconditions:**
- Remote MQTT broker is running on `127.0.0.1:1884`
- Bridge is configured with one enabled remote broker

**Steps:**
1. Create a `BridgeConfig` with remote broker pointing to the test broker
2. Initialize `MQTTBridge` with the config
3. Call `bridge.start()`
4. Check `bridge.remote_clients["test-remote"].is_connected`
5. Call `bridge.stop()`

**Expected Results:**
- Bridge connects to remote broker without errors
- Remote client `is_connected` returns `True` after start
- Connection is cleanly closed after stop

---

### IT-CONN-003: Authentication with Username/Password

**Description:** Verify the bridge can authenticate with username and password.

**Preconditions:**
- MQTT broker is configured with authentication enabled
- Credentials: username=`testuser`, password=`testpass`

**Steps:**
1. Configure broker with username/password requirement
2. Create `BridgeConfig` with valid credentials
3. Start bridge and verify connection succeeds
4. Stop bridge
5. Create `BridgeConfig` with invalid credentials
6. Start bridge and verify connection fails

**Expected Results:**
- Valid credentials: Connection succeeds
- Invalid credentials: Connection fails with authentication error

---

### IT-CONN-004: Connection Failure Handling

**Description:** Verify the bridge handles connection failures gracefully.

**Preconditions:**
- No MQTT broker running on the configured port

**Steps:**
1. Create `BridgeConfig` pointing to non-existent broker (e.g., port 9999)
2. Initialize `MQTTBridge`
3. Call `bridge.start()`
4. Observe error handling behavior

**Expected Results:**
- Bridge logs connection failure
- Local broker failure raises exception (critical failure)
- Remote broker failure is logged but bridge continues running

---

## Message Forwarding Tests

### IT-FWD-001: Basic Uplink Message Forwarding

**Description:** Verify uplink messages from local broker are forwarded to remote broker.

**Preconditions:**
- Both local (1883) and remote (1884) brokers running
- Bridge started and connected to both

**Steps:**
1. Start the bridge
2. Subscribe to the expected topic on the remote broker
3. Publish a valid uplink message to local broker on `lora/app-eui/dev-eui/up`:
   ```json
   {
     "deveui": "00-11-22-33-44-55-66-77",
     "appeui": "aa-bb-cc-dd-ee-ff-00-11",
     "port": 1,
     "data": "SGVsbG8gV29ybGQ=",
     "time": "2024-01-15T10:30:00Z"
   }
   ```
4. Wait for message on remote broker
5. Verify message content

**Expected Results:**
- Message is received on remote broker
- Message contains all expected fields
- Topic matches configured uplink pattern

---

### IT-FWD-002: Multiple Message Types Forwarding

**Description:** Verify different message types (uplink, joined, moved) are forwarded correctly.

**Preconditions:**
- Bridge connected to local and remote brokers

**Steps:**
1. Publish uplink message to `lora/app-eui/dev-eui/up`
2. Verify it's forwarded
3. Publish joined message to `lora/dev-eui/joined`
4. Verify it's forwarded
5. Publish moved message to `lora/app-eui/dev-eui/moved`
6. Verify it's forwarded

**Expected Results:**
- All message types are correctly identified and forwarded
- Message type affects routing appropriately

---

### IT-FWD-003: Message with Missing Optional Fields

**Description:** Verify messages with only required fields are forwarded successfully.

**Preconditions:**
- Bridge connected to local and remote brokers

**Steps:**
1. Publish minimal uplink message with only required fields:
   ```json
   {
     "deveui": "00-11-22-33-44-55-66-77"
   }
   ```
2. Verify message is forwarded

**Expected Results:**
- Message is forwarded successfully
- Missing optional fields do not cause errors

---

### IT-FWD-004: Message Queue During Disconnect

**Description:** Verify messages are queued when remote broker is disconnected and delivered when reconnected.

**Preconditions:**
- Local broker running, remote broker initially stopped

**Steps:**
1. Start bridge (remote connection will fail)
2. Publish 5 uplink messages to local broker
3. Start remote broker
4. Wait for reconnection
5. Verify all 5 messages are delivered to remote broker

**Expected Results:**
- Messages are queued when remote is disconnected
- All queued messages are delivered upon reconnection
- Messages are delivered in order

---

## Message Filtering Tests

### IT-FILT-001: DevEUI Whitelist Filtering

**Description:** Verify only messages from whitelisted DevEUIs are forwarded.

**Preconditions:**
- Remote broker configured with `deveui_whitelist: ["00-11-22-33-44-55-66-77"]`

**Steps:**
1. Start bridge
2. Publish message with whitelisted DevEUI `00-11-22-33-44-55-66-77`
3. Verify message is forwarded
4. Publish message with non-whitelisted DevEUI `ff-ee-dd-cc-bb-aa-99-88`
5. Verify message is NOT forwarded

**Expected Results:**
- Whitelisted DevEUI messages: Forwarded
- Non-whitelisted DevEUI messages: Filtered out

---

### IT-FILT-002: DevEUI Blacklist Filtering

**Description:** Verify messages from blacklisted DevEUIs are blocked.

**Preconditions:**
- Remote broker configured with `deveui_blacklist: ["ff-ff-ff-ff-ff-ff-ff-ff"]`

**Steps:**
1. Start bridge
2. Publish message with blacklisted DevEUI `ff-ff-ff-ff-ff-ff-ff-ff`
3. Verify message is NOT forwarded
4. Publish message with non-blacklisted DevEUI `00-11-22-33-44-55-66-77`
5. Verify message IS forwarded

**Expected Results:**
- Blacklisted DevEUI messages: Blocked
- Non-blacklisted DevEUI messages: Forwarded

---

### IT-FILT-003: AppEUI/JoinEUI Whitelist Filtering

**Description:** Verify only messages with whitelisted AppEUI are forwarded.

**Preconditions:**
- Remote broker configured with `appeui_whitelist: ["aa-bb-cc-dd-ee-ff-00-11"]`

**Steps:**
1. Start bridge
2. Publish message with whitelisted AppEUI
3. Verify message is forwarded
4. Publish message with non-whitelisted AppEUI `11-22-33-44-55-66-77-88`
5. Verify message is NOT forwarded

**Expected Results:**
- Whitelisted AppEUI messages: Forwarded
- Non-whitelisted AppEUI messages: Filtered out

---

### IT-FILT-004: Combined Whitelist and Blacklist

**Description:** Verify blacklist takes precedence over whitelist.

**Preconditions:**
- Remote broker configured with:
  - `deveui_whitelist: ["00-11-22-33-44-55-66-77", "00-11-22-33-44-55-66-88"]`
  - `deveui_blacklist: ["00-11-22-33-44-55-66-88"]`

**Steps:**
1. Start bridge
2. Publish message with DevEUI in whitelist only `00-11-22-33-44-55-66-77`
3. Verify message IS forwarded
4. Publish message with DevEUI in both lists `00-11-22-33-44-55-66-88`
5. Verify message is NOT forwarded (blacklist wins)

**Expected Results:**
- DevEUI only in whitelist: Forwarded
- DevEUI in both whitelist and blacklist: Blocked

---

### IT-FILT-005: EUI Format Normalization

**Description:** Verify different EUI formats are normalized and matched correctly.

**Preconditions:**
- Remote broker configured with `deveui_whitelist: ["00-11-22-33-44-55-66-77"]`

**Steps:**
1. Publish message with DevEUI `00-11-22-33-44-55-66-77` (dashes)
2. Verify message is forwarded
3. Publish message with DevEUI `00:11:22:33:44:55:66:77` (colons)
4. Verify message is forwarded
5. Publish message with DevEUI `0011223344556677` (no separators)
6. Verify message is forwarded
7. Publish message with DevEUI `00-11-22-33-44-55-66-78` (different)
8. Verify message is NOT forwarded

**Expected Results:**
- All normalized variations of whitelisted EUI: Forwarded
- Different EUI: Filtered out

---

### IT-FILT-006: DevEUI Range Filtering

**Description:** Verify messages are filtered based on DevEUI ranges.

**Preconditions:**
- Remote broker configured with:
  ```json
  {
    "deveui_ranges": [["00-11-22-33-44-55-66-00", "00-11-22-33-44-55-66-ff"]]
  }
  ```

**Steps:**
1. Start bridge
2. Publish message with DevEUI `00-11-22-33-44-55-66-50` (in range)
3. Verify message IS forwarded
4. Publish message with DevEUI `00-11-22-33-44-55-66-00` (min boundary)
5. Verify message IS forwarded
6. Publish message with DevEUI `00-11-22-33-44-55-66-ff` (max boundary)
7. Verify message IS forwarded
8. Publish message with DevEUI `00-11-22-33-44-55-67-00` (out of range)
9. Verify message is NOT forwarded

**Expected Results:**
- DevEUIs within range (inclusive): Forwarded
- DevEUIs outside range: Filtered out

---

### IT-FILT-007: DevEUI Mask Pattern Filtering

**Description:** Verify messages are filtered based on DevEUI mask patterns.

**Preconditions:**
- Remote broker configured with:
  ```json
  {
    "deveui_masks": ["00-11-22-xx-xx-xx-xx-xx"]
  }
  ```

**Steps:**
1. Start bridge
2. Publish message with DevEUI `00-11-22-33-44-55-66-77` (matches prefix)
3. Verify message IS forwarded
4. Publish message with DevEUI `00-11-22-00-00-00-00-00` (matches prefix)
5. Verify message IS forwarded
6. Publish message with DevEUI `00-11-23-33-44-55-66-77` (different 3rd byte)
7. Verify message is NOT forwarded
8. Publish message with DevEUI `ff-11-22-33-44-55-66-77` (different 1st byte)
9. Verify message is NOT forwarded

**Expected Results:**
- DevEUIs matching mask pattern: Forwarded
- DevEUIs not matching mask pattern: Filtered out

---

### IT-FILT-008: Multiple Ranges Filter

**Description:** Verify multiple DevEUI ranges work with OR logic.

**Preconditions:**
- Remote broker configured with:
  ```json
  {
    "deveui_ranges": [
      ["00-11-22-33-44-55-00-00", "00-11-22-33-44-55-00-ff"],
      ["aa-bb-cc-dd-ee-ff-00-00", "aa-bb-cc-dd-ee-ff-00-ff"]
    ]
  }
  ```

**Steps:**
1. Publish message with DevEUI in first range
2. Verify message IS forwarded
3. Publish message with DevEUI in second range
4. Verify message IS forwarded
5. Publish message with DevEUI in neither range
6. Verify message is NOT forwarded

**Expected Results:**
- DevEUI in any range: Forwarded
- DevEUI in no range: Filtered out

---

### IT-FILT-009: Combined Whitelist, Range, and Mask Filters

**Description:** Verify whitelist, ranges, and masks work together with OR logic.

**Preconditions:**
- Remote broker configured with:
  ```json
  {
    "deveui_whitelist": ["ff-ff-ff-ff-ff-ff-ff-ff"],
    "deveui_ranges": [["00-11-22-33-44-55-00-00", "00-11-22-33-44-55-00-ff"]],
    "deveui_masks": ["aa-bb-xx-xx-xx-xx-xx-xx"]
  }
  ```

**Steps:**
1. Publish message with DevEUI in whitelist `ff-ff-ff-ff-ff-ff-ff-ff`
2. Verify message IS forwarded
3. Publish message with DevEUI in range `00-11-22-33-44-55-00-50`
4. Verify message IS forwarded
5. Publish message with DevEUI matching mask `aa-bb-cc-dd-ee-ff-00-11`
6. Verify message IS forwarded
7. Publish message with DevEUI matching none `cc-cc-cc-cc-cc-cc-cc-cc`
8. Verify message is NOT forwarded

**Expected Results:**
- DevEUI matching any allow filter: Forwarded
- DevEUI matching no allow filter: Filtered out

---

### IT-FILT-010: Blacklist Overrides Range and Mask

**Description:** Verify blacklist takes precedence over range and mask filters.

**Preconditions:**
- Remote broker configured with:
  ```json
  {
    "deveui_ranges": [["00-11-22-33-44-55-00-00", "00-11-22-33-44-55-ff-ff"]],
    "deveui_masks": ["aa-bb-xx-xx-xx-xx-xx-xx"],
    "deveui_blacklist": ["00-11-22-33-44-55-00-50", "aa-bb-cc-dd-ee-ff-00-11"]
  }
  ```

**Steps:**
1. Publish message with DevEUI in range but blacklisted `00-11-22-33-44-55-00-50`
2. Verify message is NOT forwarded
3. Publish message with DevEUI matching mask but blacklisted `aa-bb-cc-dd-ee-ff-00-11`
4. Verify message is NOT forwarded
5. Publish message with DevEUI in range and not blacklisted `00-11-22-33-44-55-00-60`
6. Verify message IS forwarded

**Expected Results:**
- Blacklisted DevEUI: Always blocked, regardless of other filters
- Non-blacklisted DevEUI in allow filters: Forwarded

---

## Field Filtering Tests

### IT-FIELD-001: Include Fields Filter

**Description:** Verify only specified fields are included in forwarded messages.

**Preconditions:**
- Remote broker configured with `include_fields: ["deveui", "time", "port", "data"]`

**Steps:**
1. Start bridge
2. Publish message with many fields:
   ```json
   {
     "deveui": "00-11-22-33-44-55-66-77",
     "appeui": "aa-bb-cc-dd-ee-ff-00-11",
     "time": "2024-01-15T10:30:00Z",
     "port": 1,
     "data": "SGVsbG8=",
     "rssi": -50,
     "snr": 10.5,
     "freq": 868.1,
     "dr": "SF7BW125"
   }
   ```
3. Capture forwarded message
4. Verify only included fields are present

**Expected Results:**
- Forwarded message contains: `deveui`, `time`, `port`, `data`
- Forwarded message does NOT contain: `rssi`, `snr`, `freq`, `dr`
- `appeui` included if in `always_include` list

---

### IT-FIELD-002: Exclude Fields Filter

**Description:** Verify specified fields are excluded from forwarded messages.

**Preconditions:**
- Remote broker configured with `exclude_fields: ["rssi", "snr", "freq", "dr"]`

**Steps:**
1. Start bridge
2. Publish message with all fields
3. Capture forwarded message
4. Verify excluded fields are not present

**Expected Results:**
- Forwarded message does NOT contain: `rssi`, `snr`, `freq`, `dr`
- All other fields are present

---

### IT-FIELD-003: Always Include Fields

**Description:** Verify always_include fields are present regardless of other filters.

**Preconditions:**
- Remote broker configured with:
  - `include_fields: ["port", "data"]`
  - `always_include: ["deveui", "appeui", "time"]`

**Steps:**
1. Start bridge
2. Publish message with all fields
3. Capture forwarded message
4. Verify always_include fields are present

**Expected Results:**
- Message contains: `deveui`, `appeui`, `time` (always_include)
- Message contains: `port`, `data` (include_fields)
- Message does NOT contain other fields

---

## Topic Format Tests

### IT-TOPIC-001: LoRa Topic Format Forwarding

**Description:** Verify messages from lora/* topics are forwarded when source_topic_format includes "lora".

**Preconditions:**
- Remote broker configured with `source_topic_format: ["lora"]`

**Steps:**
1. Start bridge
2. Publish message to `lora/app-eui/dev-eui/up`
3. Verify message is forwarded
4. Publish message to `scada/lorawan/dev-eui/up`
5. Verify message is NOT forwarded

**Expected Results:**
- LoRa format messages: Forwarded
- SCADA format messages: Not forwarded

---

### IT-TOPIC-002: SCADA Topic Format Forwarding

**Description:** Verify messages from scada/* topics are forwarded when source_topic_format includes "scada".

**Preconditions:**
- Remote broker configured with `source_topic_format: ["scada"]`

**Steps:**
1. Start bridge
2. Publish message to `scada/lorawan/dev-eui/up`
3. Verify message is forwarded
4. Publish message to `lora/app-eui/dev-eui/up`
5. Verify message is NOT forwarded

**Expected Results:**
- SCADA format messages: Forwarded
- LoRa format messages: Not forwarded

---

### IT-TOPIC-003: Both Topic Formats

**Description:** Verify messages from both formats are forwarded when source_topic_format includes both.

**Preconditions:**
- Remote broker configured with `source_topic_format: ["lora", "scada"]`

**Steps:**
1. Start bridge
2. Publish message to `lora/app-eui/dev-eui/up`
3. Verify message is forwarded
4. Publish message to `scada/lorawan/dev-eui/up`
5. Verify message is forwarded

**Expected Results:**
- Both LoRa and SCADA format messages are forwarded

---

### IT-TOPIC-004: Custom Uplink Topic Pattern

**Description:** Verify messages are published to custom topic patterns with variable substitution.

**Preconditions:**
- Remote broker configured with `uplink_pattern: "lorawan/%(gwuuid)s/%(appeui)s/%(deveui)s/up"`

**Steps:**
1. Start bridge
2. Publish uplink message with:
   - deveui: `00-11-22-33-44-55-66-77`
   - appeui: `aa-bb-cc-dd-ee-ff-00-11`
3. Subscribe to remote broker on pattern matching expected topic
4. Verify topic substitution

**Expected Results:**
- Topic contains correct deveui, appeui, and gwuuid values
- Pattern variables are correctly substituted

---

## Downlink Message Tests

### IT-DOWN-001: Basic Downlink Processing

**Description:** Verify downlink messages from remote broker are published to local broker.

**Preconditions:**
- Bridge connected to local and remote brokers

**Steps:**
1. Start bridge
2. Subscribe to `lora/00-11-22-33-44-55-66-77/down` on local broker
3. Publish downlink to remote broker:
   ```json
   {
     "deveui": "00-11-22-33-44-55-66-77",
     "port": 1,
     "data": "SGVsbG8="
   }
   ```
4. Verify message received on local broker

**Expected Results:**
- Downlink message is published to local broker
- Topic matches expected pattern for device
- Payload is preserved

---

### IT-DOWN-002: Queue Clear Command

**Description:** Verify queue clear commands from remote broker are processed.

**Preconditions:**
- Bridge connected to local and remote brokers

**Steps:**
1. Start bridge
2. Subscribe to `lora/00-11-22-33-44-55-66-77/clear` on local broker
3. Publish clear command to remote broker:
   ```json
   {
     "deveui": "00-11-22-33-44-55-66-77"
   }
   ```
4. Verify clear message received on local broker

**Expected Results:**
- Clear command is published to local broker
- Topic includes "clear" suffix

---

### IT-DOWN-003: Invalid Downlink Handling

**Description:** Verify invalid downlink messages are handled gracefully.

**Preconditions:**
- Bridge connected to local and remote brokers

**Steps:**
1. Start bridge
2. Subscribe to all topics on local broker
3. Publish invalid downlink (missing deveui) to remote broker:
   ```json
   {
     "port": 1,
     "data": "SGVsbG8="
   }
   ```
4. Verify no message published to local broker
5. Verify bridge logs error

**Expected Results:**
- Invalid downlink is rejected
- Error is logged
- Bridge continues running

---

## Reconnection and Resilience Tests

### IT-RECON-001: Automatic Reconnection to Local Broker

**Description:** Verify the bridge automatically reconnects to local broker after disconnect.

**Preconditions:**
- Bridge connected to local broker

**Steps:**
1. Start bridge
2. Verify connection to local broker
3. Stop local broker
4. Wait for disconnect detection
5. Restart local broker
6. Wait for reconnection (up to health check interval + reconnect delay)
7. Verify connection is restored

**Expected Results:**
- Bridge detects disconnect
- Bridge attempts reconnection
- Connection is restored automatically
- Status writer reflects connection state changes

---

### IT-RECON-002: Automatic Reconnection to Remote Broker

**Description:** Verify the bridge automatically reconnects to remote broker after disconnect.

**Preconditions:**
- Bridge connected to remote broker

**Steps:**
1. Start bridge
2. Verify connection to remote broker
3. Stop remote broker
4. Wait for disconnect detection
5. Restart remote broker
6. Wait for reconnection
7. Verify connection is restored
8. Publish message and verify it's forwarded

**Expected Results:**
- Bridge detects remote disconnect
- Bridge attempts reconnection
- Connection is restored automatically
- Message forwarding resumes

---

### IT-RECON-003: Message Preservation During Remote Disconnect

**Description:** Verify messages are queued and not lost during remote broker disconnection.

**Preconditions:**
- Bridge connected to both brokers

**Steps:**
1. Start bridge
2. Stop remote broker
3. Publish 10 uplink messages to local broker
4. Start remote broker
5. Wait for reconnection
6. Verify all 10 messages are delivered

**Expected Results:**
- Messages are queued during disconnect
- All messages are delivered after reconnection
- Message order is preserved

---

### IT-RECON-004: Queue Size Limit

**Description:** Verify queue size limit is enforced when remote broker is disconnected.

**Preconditions:**
- Bridge configured with max queue size (default 10000)
- Remote broker stopped

**Steps:**
1. Start bridge with remote broker offline
2. Publish messages exceeding queue size limit
3. Verify oldest messages are dropped when limit exceeded
4. Start remote broker
5. Verify remaining queued messages are delivered

**Expected Results:**
- Queue size is limited
- Oldest messages are dropped when full
- Warning is logged when dropping messages

---

## Configuration Tests

### IT-CFG-001: Load Configuration from File

**Description:** Verify configuration is correctly loaded from JSON file.

**Preconditions:**
- Valid configuration file exists

**Steps:**
1. Create configuration file with all settings
2. Start bridge with `-c config.json` argument
3. Verify all settings are applied correctly

**Expected Results:**
- All configuration values are loaded
- Bridge behaves according to configuration

---

### IT-CFG-002: Load Configuration from Environment Variables

**Description:** Verify configuration can be loaded from environment variables.

**Preconditions:**
- Environment variables are set

**Steps:**
1. Set environment variables:
   - `LORA_MQTT_BRIDGE_LOCAL_HOST=127.0.0.1`
   - `LORA_MQTT_BRIDGE_LOCAL_PORT=1883`
   - `LORA_MQTT_BRIDGE_REMOTE_BROKERS=[...]`
2. Start bridge with `--env` argument
3. Verify configuration is applied

**Expected Results:**
- Environment variables are parsed correctly
- Bridge connects to specified brokers

---

### IT-CFG-003: Configuration Validation

**Description:** Verify invalid configurations are rejected with helpful error messages.

**Steps:**
1. Create config with invalid port number (e.g., -1)
2. Attempt to start bridge
3. Verify error message is clear

**Expected Results:**
- Invalid configuration is detected
- Clear error message is displayed
- Bridge does not start with invalid config

---

### IT-CFG-004: Disabled Remote Broker

**Description:** Verify disabled remote brokers are not connected.

**Preconditions:**
- Configuration with one enabled and one disabled broker

**Steps:**
1. Create config with two remote brokers, one with `enabled: false`
2. Start bridge
3. Verify only enabled broker is connected
4. Publish message
5. Verify message only goes to enabled broker

**Expected Results:**
- Disabled broker is not initialized
- No connection attempt to disabled broker
- Messages not forwarded to disabled broker

---

## Multi-Broker Tests

### IT-MULTI-001: Forward to Multiple Remote Brokers

**Description:** Verify messages are forwarded to all configured remote brokers.

**Preconditions:**
- Two remote brokers running (ports 1884 and 1885)
- Bridge configured with both remote brokers

**Steps:**
1. Start bridge
2. Subscribe to expected topics on both remote brokers
3. Publish uplink message to local broker
4. Verify message received on both remote brokers

**Expected Results:**
- Message is forwarded to all enabled remote brokers
- Each broker receives independent copy

---

### IT-MULTI-002: Different Filters per Broker

**Description:** Verify each remote broker applies its own filters independently.

**Preconditions:**
- Remote broker 1: `deveui_whitelist: ["00-11-22-33-44-55-66-77"]`
- Remote broker 2: `deveui_whitelist: ["00-11-22-33-44-55-66-88"]`

**Steps:**
1. Start bridge
2. Publish message with DevEUI `00-11-22-33-44-55-66-77`
3. Verify received on broker 1 only
4. Publish message with DevEUI `00-11-22-33-44-55-66-88`
5. Verify received on broker 2 only
6. Publish message with DevEUI `ff-ff-ff-ff-ff-ff-ff-ff`
7. Verify received on neither broker

**Expected Results:**
- Each broker applies its own whitelist
- Messages are routed based on per-broker filters

---

### IT-MULTI-003: Dynamic Broker Addition

**Description:** Verify brokers can be added dynamically at runtime.

**Preconditions:**
- Bridge running with one remote broker

**Steps:**
1. Start bridge with one remote broker
2. Verify messages go to first broker
3. Call `bridge.add_remote_broker(new_config)`
4. Verify new broker is connected
5. Publish message
6. Verify message goes to both brokers

**Expected Results:**
- New broker is added without restart
- New broker receives subsequent messages

---

### IT-MULTI-004: Dynamic Broker Removal

**Description:** Verify brokers can be removed dynamically at runtime.

**Preconditions:**
- Bridge running with two remote brokers

**Steps:**
1. Start bridge with two remote brokers
2. Verify messages go to both brokers
3. Call `bridge.remove_remote_broker("broker-2")`
4. Verify broker is disconnected
5. Publish message
6. Verify message only goes to remaining broker

**Expected Results:**
- Broker is removed without restart
- Removed broker no longer receives messages

---

## TLS/SSL Tests

### IT-TLS-001: TLS Connection with CA Certificate

**Description:** Verify TLS connection works with CA certificate.

**Preconditions:**
- Remote broker configured with TLS
- CA certificate available

**Steps:**
1. Configure remote broker with TLS enabled and CA cert path
2. Start bridge
3. Verify connection succeeds
4. Publish message
5. Verify message is forwarded

**Expected Results:**
- TLS handshake succeeds
- Messages are encrypted in transit
- Connection is established

---

### IT-TLS-002: TLS with Client Certificate Authentication

**Description:** Verify TLS connection with mutual authentication.

**Preconditions:**
- Remote broker requires client certificate
- Client cert and key available

**Steps:**
1. Configure remote broker with TLS, CA cert, client cert, and client key
2. Start bridge
3. Verify connection succeeds

**Expected Results:**
- Mutual TLS authentication succeeds
- Connection is established

---

### IT-TLS-003: Insecure TLS Mode

**Description:** Verify insecure mode allows connection without certificate verification.

**Preconditions:**
- Remote broker with self-signed certificate

**Steps:**
1. Configure remote broker with `tls.insecure: true`
2. Start bridge
3. Verify connection succeeds despite invalid certificate

**Expected Results:**
- Connection succeeds with self-signed cert
- Warning is logged about insecure mode

---

## Performance Tests

### IT-PERF-001: High Message Throughput

**Description:** Verify bridge handles high message volume without message loss.

**Preconditions:**
- Bridge connected to local and remote brokers

**Steps:**
1. Start bridge
2. Publish 1000 messages to local broker in rapid succession
3. Count messages received on remote broker
4. Measure message latency

**Expected Results:**
- All 1000 messages are delivered
- Latency is within acceptable bounds (<100ms average)
- No errors or warnings

---

### IT-PERF-002: Large Message Handling

**Description:** Verify bridge handles large message payloads.

**Preconditions:**
- Bridge connected

**Steps:**
1. Create message with large payload (100KB of data)
2. Publish to local broker
3. Verify message is forwarded complete

**Expected Results:**
- Large message is forwarded without truncation
- No memory errors

---

### IT-PERF-003: Concurrent Message Processing

**Description:** Verify bridge handles concurrent messages from multiple devices.

**Preconditions:**
- Bridge connected

**Steps:**
1. Simulate 100 different devices sending messages concurrently
2. Publish messages from all devices simultaneously
3. Verify all messages are forwarded correctly

**Expected Results:**
- All messages from all devices are forwarded
- No message mixing or corruption
- Device identifiers are preserved correctly

---

## Status Writer Tests

### IT-STATUS-001: Status File Updates

**Description:** Verify status file is updated with connection and message information.

**Preconditions:**
- Status writer initialized

**Steps:**
1. Start bridge
2. Read status file
3. Verify local connection status
4. Verify remote connection status
5. Publish messages
6. Verify message count increments

**Expected Results:**
- Status file exists and is readable
- Connection status reflects actual state
- Message count is accurate

---

### IT-STATUS-002: Status Updates on State Changes

**Description:** Verify status file updates when connection state changes.

**Preconditions:**
- Bridge running with status writer

**Steps:**
1. Start bridge
2. Verify status shows connected
3. Stop remote broker
4. Wait for status update
5. Verify status shows disconnected
6. Restart remote broker
7. Verify status shows connected again

**Expected Results:**
- Status file reflects real-time connection state
- Updates occur promptly on state changes

---

## Test Execution Guidelines

### Running Integration Tests

```bash
# Run all integration tests
pytest tests/ -m integration -v

# Run specific test category
pytest tests/ -m "integration and connection" -v

# Run with coverage
pytest tests/ -m integration --cov=lora_mqtt_bridge --cov-report=html
```

### Test Markers

Add the following markers to test functions:

```python
import pytest

@pytest.mark.integration
@pytest.mark.connection
def test_local_broker_connection():
    ...

@pytest.mark.integration
@pytest.mark.slow
def test_high_throughput():
    ...
```

### Fixtures Needed

```python
@pytest.fixture
def local_broker():
    """Start and return a local MQTT broker for testing."""
    ...

@pytest.fixture
def remote_broker():
    """Start and return a remote MQTT broker for testing."""
    ...

@pytest.fixture
def bridge_with_brokers(local_broker, remote_broker):
    """Create a configured bridge with test brokers."""
    ...
```

---

## Appendix: Sample Test Implementation

```python
"""Sample integration test implementation."""

import json
import pytest
from unittest.mock import MagicMock
import paho.mqtt.client as mqtt

from lora_mqtt_bridge.bridge import MQTTBridge
from lora_mqtt_bridge.models.config import (
    BridgeConfig,
    LocalBrokerConfig,
    RemoteBrokerConfig,
)


@pytest.mark.integration
class TestMessageForwarding:
    """Integration tests for message forwarding."""

    @pytest.fixture
    def integration_config(self):
        """Create config for integration testing."""
        return BridgeConfig(
            local_broker=LocalBrokerConfig(
                host="127.0.0.1",
                port=1883,
            ),
            remote_brokers=[
                RemoteBrokerConfig(
                    name="test-remote",
                    host="127.0.0.1",
                    port=1884,
                    enabled=True,
                )
            ],
        )

    def test_uplink_forwarding(self, integration_config):
        """Test basic uplink message forwarding."""
        received_messages = []
        
        # Set up receiver on remote broker
        receiver = mqtt.Client()
        receiver.on_message = lambda c, u, m: received_messages.append(m)
        receiver.connect("127.0.0.1", 1884)
        receiver.subscribe("#")
        receiver.loop_start()
        
        try:
            # Start bridge
            bridge = MQTTBridge(integration_config)
            bridge.start()
            
            # Publish message to local broker
            publisher = mqtt.Client()
            publisher.connect("127.0.0.1", 1883)
            payload = json.dumps({
                "deveui": "00-11-22-33-44-55-66-77",
                "appeui": "aa-bb-cc-dd-ee-ff-00-11",
                "port": 1,
                "data": "SGVsbG8=",
            })
            publisher.publish("lora/app-eui/dev-eui/up", payload)
            
            # Wait for forwarding
            import time
            time.sleep(1)
            
            # Verify message received
            assert len(received_messages) == 1
            received_data = json.loads(received_messages[0].payload)
            assert received_data["deveui"] == "00-11-22-33-44-55-66-77"
            
        finally:
            bridge.stop()
            receiver.loop_stop()
            receiver.disconnect()
            publisher.disconnect()
```

---

## Version History

| Version | Date       | Author     | Changes                    |
|---------|------------|------------|----------------------------|
| 1.0     | 2024-12-16 | Generated  | Initial integration tests  |
