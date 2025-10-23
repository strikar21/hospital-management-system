# ESP32 Watch - Component 5 Integration Plan

## Current State Analysis

### What ESP32 Currently Has (v3.2.0)
✅ HMAC-SHA256 authentication
✅ NTP time synchronization
✅ WiFi connectivity management
✅ MQTT vitals transmission
✅ Battery level monitoring (mock)
✅ Firmware version tracking (3.2.0)
✅ Heartbeat with HMAC auth
✅ Device provisioning and registration

### What's Missing for Component 5
❌ Battery health percentage tracking
❌ Disconnect event tracking
❌ Command acknowledgment system
❌ Calibration status awareness
❌ Enhanced battery drain monitoring
❌ Connection quality metrics
❌ Local alert generation capability

---

## Integration Requirements

### Backend Expectations (from Component 5)

#### Battery Alerts Need:
1. `batteryLevel` (%) - ✅ Already sending
2. `batteryHealthPercentage` - ❌ Need to add
3. Battery drain rate tracking - ❌ Need to calculate

#### Calibration Alerts Need:
1. Device aware of calibration status - ❌ Need MQTT subscription
2. Last calibration date - Backend manages ✅
3. Sensor drift detection - Backend manages ✅

#### Connectivity Alerts Need:
1. Disconnect count tracking - ❌ Need to track
2. Last command sent/ack timestamps - ❌ Need to implement
3. Firmware version - ✅ Already sending
4. Connection quality metrics - ❌ Need to add

---

## Detailed Integration Plan

### Phase 1: Battery Health Tracking
**Goal:** Add battery health percentage calculation and transmission

#### Changes:
1. Add `batteryHealthPercentage` variable (0-100)
2. Implement battery health degradation model
3. Send battery health in heartbeat
4. Track battery drain rate (% per hour)
5. Deep discharge detection (< 5%) reduces health

#### Implementation:
```cpp
int batteryHealthPercentage = 100;  // New variable
float batteryDrainRatePerHour = 0.0;  // New variable
unsigned long lastBatteryUpdate = 0;
int lastBatteryLevel = 100;

// Update battery health based on usage
void updateBatteryHealth() {
    // Degrade health on deep discharge
    if (batteryLevel < 5 && lastBatteryLevel >= 5) {
        batteryHealthPercentage = max(0, batteryHealthPercentage - 1);
        Serial.println("⚠️ Battery health degraded: " + String(batteryHealthPercentage) + "%");
    }

    // Calculate drain rate
    unsigned long timeDiff = millis() - lastBatteryUpdate;
    if (timeDiff > 3600000) {  // Every hour
        int batteryDiff = lastBatteryLevel - batteryLevel;
        batteryDrainRatePerHour = (float)batteryDiff / (timeDiff / 3600000.0);
        lastBatteryUpdate = millis();
        lastBatteryLevel = batteryLevel;
    }
}
```

#### Heartbeat Changes:
```cpp
doc["batterylevel"] = batteryLevel;
doc["batteryhealthpercentage"] = batteryHealthPercentage;  // NEW
doc["batterydrainrate"] = batteryDrainRatePerHour;  // NEW (optional)
```

---

### Phase 2: Disconnect Tracking
**Goal:** Track disconnection events for connectivity alerts

#### Changes:
1. Add `disconnectCount` variable
2. Detect WiFi disconnections
3. Detect MQTT disconnections
4. Send disconnect count in heartbeat
5. Reset counter periodically (backend manages)

#### Implementation:
```cpp
int totalDisconnects = 0;
bool wasWifiConnected = false;
bool wasMqttConnected = false;

void trackConnectivity() {
    // Track WiFi disconnects
    bool currentWifiState = WiFi.status() == WL_CONNECTED;
    if (wasWifiConnected && !currentWifiState) {
        totalDisconnects++;
        Serial.println("📶 WiFi disconnect detected (total: " + String(totalDisconnects) + ")");
    }
    wasWifiConnected = currentWifiState;

    // Track MQTT disconnects
    bool currentMqttState = mqttClient.connected();
    if (wasMqttConnected && !currentMqttState) {
        totalDisconnects++;
        Serial.println("📡 MQTT disconnect detected (total: " + String(totalDisconnects) + ")");
    }
    wasMqttConnected = currentMqttState;
}

// Call in loop()
if (millis() % 1000 == 0) {  // Check every second
    trackConnectivity();
}
```

#### Heartbeat Changes:
```cpp
doc["totaldisconnects"] = totalDisconnects;  // NEW
```

---

### Phase 3: Command Acknowledgment System
**Goal:** Implement two-way command system for responsiveness alerts

#### Changes:
1. Subscribe to device command topic
2. Acknowledge received commands
3. Track last command sent/ack timestamps
4. Backend can test device responsiveness

#### Implementation:
```cpp
unsigned long lastCommandReceivedAt = 0;

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
    // ... existing code ...

    // NEW: Handle commands
    if (String(topic).endsWith("/command")) {
        JsonDocument doc;
        if (deserializeJson(doc, message) == DeserializationError::Ok) {
            String command = doc["command"].as<String>();
            String commandId = doc["commandId"].as<String>();

            lastCommandReceivedAt = millis();

            Serial.println("📨 Command received: " + command);

            // Send acknowledgment
            sendCommandAck(commandId);

            // Process command
            if (command == "ping") {
                // Just ack
            } else if (command == "calibrate") {
                // Trigger calibration routine
                handleCalibrationCommand();
            } else if (command == "battery_test") {
                // Report detailed battery info
                sendBatteryReport();
            }
        }
    }
}

void sendCommandAck(String commandId) {
    if (!mqttClient.connected()) return;

    String topic = "hospital/devices/" + deviceId + "/ack";

    JsonDocument doc;
    doc["commandId"] = commandId;
    doc["timestamp"] = getUnixTimestamp();
    doc["status"] = "success";

    String payload;
    serializeJson(doc, payload);

    mqttClient.publish(topic.c_str(), payload.c_str());
    Serial.println("✅ Command ack sent: " + commandId);
}

// Subscribe to command topic in setupMQTT()
String commandTopic = "hospital/devices/" + deviceId + "/command";
mqttClient.subscribe(commandTopic.c_str());
```

---

### Phase 4: Calibration Awareness
**Goal:** Device knows when calibration is required

#### Changes:
1. Subscribe to calibration status topic
2. Display calibration due indicator
3. Allow staff to trigger calibration
4. Send calibration confirmation

#### Implementation:
```cpp
bool calibrationDue = false;
unsigned long calibrationDueDate = 0;

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
    // ... existing code ...

    // NEW: Handle calibration notifications
    if (String(topic).endsWith("/calibration")) {
        JsonDocument doc;
        if (deserializeJson(doc, message) == DeserializationError::Ok) {
            calibrationDue = doc["isDue"].as<bool>();
            calibrationDueDate = doc["dueTimestamp"].as<unsigned long>();

            if (calibrationDue) {
                Serial.println("⚠️ CALIBRATION REQUIRED!");
                // Flash LED in pattern
                flashCalibrationWarning();
            }
        }
    }
}

void handleCalibrationCommand() {
    Serial.println("🔧 Starting calibration routine...");

    // Simulate calibration process
    // In real device, this would:
    // - Reset sensor baselines
    // - Run self-tests
    // - Validate readings

    delay(5000);  // Simulate calibration time

    // Send calibration complete
    String topic = "hospital/devices/" + deviceId + "/calibration_complete";
    JsonDocument doc;
    doc["timestamp"] = getUnixTimestamp();
    doc["success"] = true;

    String payload;
    serializeJson(doc, payload);
    mqttClient.publish(topic.c_str(), payload.c_str());

    Serial.println("✅ Calibration complete");
}
```

---

### Phase 5: Enhanced Vitals Packet
**Goal:** Add Component 5 metrics to vitals transmission

#### Current Vitals Packet:
```cpp
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "...",
  "timestamp": 123456,
  "heartRate": 75,
  "temperature": 98.6,
  "oxygenSat": 98,
  "batteryLevel": 85,
  "quality": 95
}
```

#### Enhanced Vitals Packet:
```cpp
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "...",
  "timestamp": 123456,
  "heartRate": 75,
  "temperature": 98.6,
  "oxygenSat": 98,
  "batteryLevel": 85,
  "batteryHealthPercentage": 95,  // NEW
  "quality": 95,
  "firmwareVersion": "3.3.0",  // NEW
  "signalStrength": -45  // NEW (already have in heartbeat)
}
```

---

### Phase 6: Connection Quality Metrics
**Goal:** Provide detailed connection health data

#### Implementation:
```cpp
struct ConnectionMetrics {
    int wifiRssi;
    int wifiDisconnects24h;
    int mqttDisconnects24h;
    float packetLossRate;
    unsigned long lastSuccessfulSend;
};

ConnectionMetrics connMetrics = {0, 0, 0, 0.0, 0};

void updateConnectionMetrics() {
    connMetrics.wifiRssi = WiFi.RSSI();
    connMetrics.lastSuccessfulSend = millis();
    // Calculate packet loss (sent vs ack'd)
}

// Send in heartbeat
doc["connectionmetrics"] = {
    {"rssi", connMetrics.wifiRssi},
    {"disconnects24h", connMetrics.wifiDisconnects24h},
    {"packetloss", connMetrics.packetLossRate}
};
```

---

## Complete Code Structure Changes

### New Variables to Add:
```cpp
// Battery Health
int batteryHealthPercentage = 100;
float batteryDrainRatePerHour = 0.0;
unsigned long lastBatteryUpdate = 0;
int lastBatteryLevel = 100;

// Disconnect Tracking
int totalDisconnects = 0;
bool wasWifiConnected = false;
bool wasMqttConnected = false;

// Command System
unsigned long lastCommandReceivedAt = 0;
String lastCommandId = "";

// Calibration
bool calibrationDue = false;
unsigned long calibrationDueDate = 0;
unsigned long lastCalibrationDate = 0;
```

### New Functions to Add:
```cpp
void updateBatteryHealth();
void trackConnectivity();
void sendCommandAck(String commandId);
void handleCalibrationCommand();
void sendBatteryReport();
void flashCalibrationWarning();
void updateConnectionMetrics();
```

### Modified Functions:
```cpp
void sendHeartbeat();  // Add battery health, disconnect count
void sendVitals();  // Add battery health, firmware version
void onMqttMessage();  // Add command and calibration handlers
void setupMQTT();  // Subscribe to command and calibration topics
void loop();  // Add connectivity tracking calls
```

---

## Testing Plan

### Test 1: Battery Health Degradation
1. Set battery to 100%, health to 100%
2. Simulate deep discharge (< 5%)
3. Verify health decreases by 1%
4. Check heartbeat includes battery health

### Test 2: Disconnect Tracking
1. Start device connected
2. Disconnect WiFi manually
3. Reconnect WiFi
4. Verify disconnect count increases
5. Check heartbeat includes disconnect count

### Test 3: Command Acknowledgment
1. Send "ping" command from backend
2. Verify device receives command
3. Verify device sends ack
4. Check backend receives ack
5. Measure response time (< 10 seconds)

### Test 4: Calibration Workflow
1. Backend sends calibration due notification
2. Device displays warning
3. Staff triggers calibration via backend
4. Device runs calibration
5. Device sends completion message
6. Backend updates calibration date

---

## Backward Compatibility

### Considerations:
- ✅ New fields are additions, not replacements
- ✅ Existing heartbeat/vitals still work
- ✅ Backend handles missing fields gracefully
- ✅ Firmware version indicates capabilities

### Version Upgrade Path:
- v3.2.0 → v3.3.0: Component 5 integration
- Devices can identify feature set via firmware version
- Backend uses firmware version to determine available features

---

## Summary of Changes

### Critical Changes (Must Have):
1. ✅ Battery health percentage tracking
2. ✅ Disconnect count tracking
3. ✅ Command acknowledgment system
4. ✅ Enhanced heartbeat with new metrics

### Important Changes (Should Have):
5. ✅ Calibration awareness
6. ✅ Connection quality metrics
7. ✅ Enhanced vitals packet

### Nice to Have:
8. LED calibration warning patterns
9. Local battery alert generation
10. Connection quality dashboard on web UI

---

## Next Step: Implementation

Ready to generate the complete updated ESP32 code with all Component 5 integrations!

**Version:** 3.3.0
**Features:** All Component 5 device maintenance integration
**Estimated Code Size:** ~1200 lines (vs current 908 lines)
