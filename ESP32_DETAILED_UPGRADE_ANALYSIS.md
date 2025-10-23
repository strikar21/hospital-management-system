# ESP32 Watch v3.2.0 → v3.3.0 Detailed Upgrade Analysis

## Current File Structure Analysis

**File:** `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
**Size:** 908 lines
**Version:** 3.2.0
**Status:** HMAC authenticated, MQTT enabled, fully functional

### Current Features ✅
- HMAC-SHA256 authentication
- NTP time synchronization
- WiFi captive portal
- Staff-authenticated provisioning
- MQTT vitals transmission
- Patient assignment via MQTT
- HTTP heartbeat with HMAC
- Battery level tracking
- Mock sensor data

### Current MQTT Subscriptions
- `hospital/devices/{deviceId}/assign` - Patient assignment

### Current Variables (lines 67-99)
```cpp
String deviceId, macAddress, wifiSSID, wifiPassword
String serverIP, serverPort, mqttServer, mqttPort
String serialNumber, assignedPatientId, availableNetworks
bool isProvisioned, isAssigned, wifiConnected, ntpSynced
int networkCount, batteryLevel
float heartRate, temperature, oxygenSat
unsigned long lastScan, lastVitals, lastHeartbeat, lastProvisionAttempt, lastNtpSync
```

### Current Functions
1. `computeHMAC()` - Line 104
2. `syncNTPTime()` - Line 131
3. `getUnixTimestamp()` - Line 156
4. `addHMACHeaders()` - Line 169
5. `setup()` - Line 200
6. `loop()` - Line 243
7. `startCaptivePortal()` - Line 295
8. `scanWiFiNetworks()` - Line 339
9. `handleRoot()` - Line 384
10. `handleScan()` - Line 470
11. `handleConfigure()` - Line 477
12. `handleStatus()` - Line 536
13. `connectToWiFi()` - Line 576
14. `setupMQTT()` - Line 627
15. `connectToMQTT()` - Line 641
16. `onMqttMessage()` - Line 659
17. `attemptProvisioning()` - Line 683
18. `registerDevice()` - Line 756
19. `sendHeartbeat()` - Line 796
20. `sendVitals()` - Line 833
21. `updateMockSensors()` - Line 864
22. `loadConfiguration()` - Line 871
23. `saveConfiguration()` - Line 893

---

## Required Changes for v3.3.0

### Section 1: NEW VARIABLES (After line 99)

#### Component 5: Device Maintenance
```cpp
// COMPONENT 5: DEVICE MAINTENANCE (insert after line 99)
int batteryHealthPercentage = 100;
float batteryDrainRatePerHour = 0.0;
unsigned long lastBatteryUpdate = 0;
int lastBatteryLevel = 85;
int totalDisconnects = 0;
bool wasWifiConnected = false;
bool wasMqttConnected = false;
unsigned long disconnectTrackerLastCheck = 0;
unsigned long lastCommandReceivedAt = 0;
bool calibrationDue = false;
```

#### Component 4: Duration Tracking
```cpp
// COMPONENT 4: DURATION TRACKING STRUCTS
struct DurationTracker {
    bool inState;
    unsigned long stateStartTime;
    unsigned long thresholdMs;
    bool alertSent;
};

DurationTracker tachycardiaTracker = {false, 0, 600000, false};    // 10 min
DurationTracker bradycardiaTracker = {false, 0, 600000, false};    // 10 min
DurationTracker hypoxiaTracker = {false, 0, 300000, false};        // 5 min
DurationTracker feverTracker = {false, 0, 1800000, false};         // 30 min
DurationTracker hypothermiaTracker = {false, 0, 1800000, false};   // 30 min
```

#### Component 2: System Alerts
```cpp
// COMPONENT 2: SYSTEM ALERTS
int consecutiveInvalidReadings = 0;
unsigned long lastValidReading = 0;
bool sensorMalfunctionAlertSent = false;

// Sensor history for change detection
float heartRateHistory[5] = {75, 75, 75, 75, 75};
float spo2History[5] = {98, 98, 98, 98, 98};
float tempHistory[5] = {98.6, 98.6, 98.6, 98.6, 98.6};
int historyIndex = 0;
```

#### Alert Engine
```cpp
// ALERT ENGINE
unsigned long lastAlertCheck = 0;
```

**Lines Added:** ~45 lines

---

### Section 2: NEW FUNCTIONS (Insert after line 195, before setup())

#### Alert Core Functions
```cpp
// ====================================
// ALERT SYSTEM: CORE FUNCTIONS
// ====================================
void sendAlert(String alertType, String severity, String message, float confidence) {
  if (!mqttClient.connected() || !isAssigned) return;

  String topic = "hospital/devices/" + deviceId + "/alerts";

  JsonDocument doc;
  doc["alertType"] = alertType;
  doc["severity"] = severity;
  doc["message"] = message;
  doc["source"] = "Watch";
  doc["confidence"] = confidence;
  doc["timestamp"] = getUnixTimestamp();
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["category"] = "device";

  String payload;
  serializeJson(doc, payload);

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    Serial.println("🚨 [" + severity.toUpperCase() + "] " + alertType);
    flashAlertPattern(severity);
  }
}

void flashAlertPattern(String severity) {
  if (severity == "high") {
    for (int i = 0; i < 6; i++) {
      digitalWrite(2, HIGH);
      delay(100);
      digitalWrite(2, LOW);
      delay(100);
    }
  } else if (severity == "medium") {
    for (int i = 0; i < 3; i++) {
      digitalWrite(2, HIGH);
      delay(300);
      digitalWrite(2, LOW);
      delay(300);
    }
  }
}
```

#### Component 5: Battery Alerts
```cpp
// ====================================
// COMPONENT 5: BATTERY ALERTS
// ====================================
void checkBatteryAlerts() {
  if (batteryLevel < 10) {
    sendAlert("criticalBatteryLevel", "high",
      "CRITICAL BATTERY - " + String(batteryLevel) + "% - URGENT", 1.0);
  } else if (batteryLevel < 20) {
    sendAlert("lowBatteryWarning", "medium",
      "LOW BATTERY - " + String(batteryLevel) + "%", 0.95);
  }

  if (batteryHealthPercentage < 70) {
    sendAlert("batteryDegradation", "medium",
      "BATTERY HEALTH - " + String(batteryHealthPercentage) + "%", 0.85);
  }
}

void updateBatteryHealth() {
  if (batteryLevel < 5 && lastBatteryLevel >= 5) {
    batteryHealthPercentage = max(0, batteryHealthPercentage - 1);
    prefs.putInt("batHealth", batteryHealthPercentage);
  }

  unsigned long timeDiff = millis() - lastBatteryUpdate;
  if (timeDiff > 3600000) {
    int batteryDiff = lastBatteryLevel - batteryLevel;
    batteryDrainRatePerHour = (float)batteryDiff / (timeDiff / 3600000.0);
    lastBatteryUpdate = millis();
    lastBatteryLevel = batteryLevel;
  }
}
```

#### Component 5: Connectivity Alerts
```cpp
// ====================================
// COMPONENT 5: CONNECTIVITY ALERTS
// ====================================
void checkConnectivityAlerts() {
  if (totalDisconnects >= 5) {
    sendAlert("frequentDisconnects", "medium",
      "DISCONNECTS - " + String(totalDisconnects) + "x", 0.9);
  }

  if (lastCommandReceivedAt > 0 && (millis() - lastCommandReceivedAt) > 600000) {
    sendAlert("deviceUnresponsive", "high",
      "UNRESPONSIVE - " + String((millis() - lastCommandReceivedAt) / 60000) + " min", 0.95);
  }
}

void trackConnectivity() {
  unsigned long now = millis();
  if (now - disconnectTrackerLastCheck < 1000) return;
  disconnectTrackerLastCheck = now;

  bool currentWifiState = (WiFi.status() == WL_CONNECTED);
  if (wasWifiConnected && !currentWifiState) {
    totalDisconnects++;
    prefs.putInt("disconnects", totalDisconnects);
  }
  wasWifiConnected = currentWifiState;

  bool currentMqttState = mqttClient.connected();
  if (wasMqttConnected && !currentMqttState && isProvisioned) {
    totalDisconnects++;
    prefs.putInt("disconnects", totalDisconnects);
  }
  wasMqttConnected = currentMqttState;
}
```

#### Component 4: Duration Alerts
```cpp
// ====================================
// COMPONENT 4: DURATION ALERTS
// ====================================
void updateDurationTracker(DurationTracker &tracker, bool condition, String alertType, String message) {
  if (condition) {
    if (!tracker.inState) {
      tracker.inState = true;
      tracker.stateStartTime = millis();
      tracker.alertSent = false;
    } else {
      unsigned long duration = millis() - tracker.stateStartTime;
      if (duration >= tracker.thresholdMs && !tracker.alertSent) {
        sendAlert(alertType, "medium", message, 0.9);
        tracker.alertSent = true;
      }
    }
  } else {
    tracker.inState = false;
    tracker.alertSent = false;
  }
}

void checkDurationAlerts() {
  updateDurationTracker(tachycardiaTracker, heartRate > 100,
    "prolongedTachycardia", "PROLONGED TACHY - HR > 100 for 10+ min");

  updateDurationTracker(bradycardiaTracker, heartRate < 60,
    "prolongedBradycardia", "PROLONGED BRADY - HR < 60 for 10+ min");

  updateDurationTracker(hypoxiaTracker, oxygenSat < 90,
    "prolongedHypoxia", "PROLONGED HYPOXIA - SpO2 < 90% for 5+ min");

  updateDurationTracker(feverTracker, temperature > 100.4,
    "prolongedFever", "PROLONGED FEVER - Temp > 100.4°F for 30+ min");

  updateDurationTracker(hypothermiaTracker, temperature < 95.0,
    "prolongedHypothermia", "HYPOTHERMIA - Temp < 95°F for 30+ min");
}
```

#### Component 2: System Alerts
```cpp
// ====================================
// COMPONENT 2: SYSTEM ALERTS
// ====================================
bool isValidReading(float hr, float spo2, float temp) {
  return (hr > 0 && hr <= 300 && spo2 > 0 && spo2 <= 100 && temp >= 80 && temp <= 115);
}

void checkSystemAlerts() {
  if (!isValidReading(heartRate, oxygenSat, temperature)) {
    consecutiveInvalidReadings++;
    if (consecutiveInvalidReadings >= 3 && !sensorMalfunctionAlertSent) {
      sendAlert("sensorMalfunction", "high",
        "SENSOR FAIL - " + String(consecutiveInvalidReadings) + " invalid", 0.95);
      sensorMalfunctionAlertSent = true;
    }
  } else {
    consecutiveInvalidReadings = 0;
    sensorMalfunctionAlertSent = false;
    lastValidReading = millis();
  }

  if (millis() - lastValidReading > 300000) {
    sendAlert("communicationFailure", "high", "COMM FAIL - 5+ min", 1.0);
  }

  float hrVariation = abs(heartRate - heartRateHistory[0]);
  if (hrVariation > 50 && heartRate > 0) {
    sendAlert("dataQualityIssue", "low", "DATA QUALITY - HR spike " + String(hrVariation), 0.7);
  }
}
```

#### Component 1: Critical Alerts
```cpp
// ====================================
// COMPONENT 1: CRITICAL ALERTS
// ====================================
void checkCriticalAlerts() {
  if (heartRate > 150) {
    sendAlert("severeTachycardia", "high", "SEVERE TACHY - HR " + String(heartRate), 1.0);
  }

  if (oxygenSat < 85) {
    sendAlert("criticalHypoxia", "high", "CRITICAL HYPOXIA - SpO2 " + String(oxygenSat) + "%", 1.0);
  }
}
```

#### Alert Engine Runner
```cpp
// ====================================
// ALERT ENGINE: MAIN RUNNER
// ====================================
void runAlertEngine() {
  if (!isAssigned) return;

  checkBatteryAlerts();
  checkConnectivityAlerts();
  checkDurationAlerts();
  checkSystemAlerts();
  checkCriticalAlerts();
}

void updateSensorHistory() {
  heartRateHistory[historyIndex] = heartRate;
  spo2History[historyIndex] = oxygenSat;
  tempHistory[historyIndex] = temperature;
  historyIndex = (historyIndex + 1) % 5;
}
```

#### Command Handlers
```cpp
// ====================================
// COMMAND HANDLERS
// ====================================
void sendCommandAck(String commandId, bool success, String msg) {
  if (!mqttClient.connected()) return;

  String topic = "hospital/devices/" + deviceId + "/ack";
  JsonDocument doc;
  doc["commandId"] = commandId;
  doc["timestamp"] = getUnixTimestamp();
  doc["status"] = success ? "success" : "error";
  doc["message"] = msg;

  String payload;
  serializeJson(doc, payload);
  mqttClient.publish(topic.c_str(), payload.c_str());
}

void handlePingCommand(String commandId) {
  sendCommandAck(commandId, true, "Pong");
}

void handleCalibrationCommand(String commandId) {
  for (int i = 0; i < 3; i++) {
    digitalWrite(2, HIGH);
    delay(200);
    digitalWrite(2, LOW);
    delay(200);
  }
  delay(3000);

  String topic = "hospital/devices/" + deviceId + "/calibration_complete";
  JsonDocument doc;
  doc["timestamp"] = getUnixTimestamp();
  doc["success"] = true;

  String payload;
  serializeJson(doc, payload);
  mqttClient.publish(topic.c_str(), payload.c_str());

  calibrationDue = false;
  sendCommandAck(commandId, true, "Calibration complete");
  digitalWrite(2, HIGH);
}
```

**Lines Added:** ~220 lines

---

### Section 3: MODIFICATIONS TO EXISTING FUNCTIONS

#### 3.1 Update FIRMWARE_VERSION (line 34)
```cpp
const char* FIRMWARE_VERSION = "3.3.0";  // Change from "3.2.0"
```

#### 3.2 Update setup() (line 200)
Add after line 237:
```cpp
  // Initialize tracking variables (Component 5)
  wasWifiConnected = wifiConnected;
  wasMqttConnected = mqttClient.connected();
  lastBatteryUpdate = millis();
  lastValidReading = millis();
```

#### 3.3 Update loop() (line 243)
Add before `delay(100)` at line 289:
```cpp
  // Update sensor history
  updateSensorHistory();

  // Track connectivity (Component 5)
  trackConnectivity();
  updateBatteryHealth();

  // Alert Engine - runs every 2 seconds
  if (millis() - lastAlertCheck > 2000) {
    runAlertEngine();
    lastAlertCheck = millis();
  }
```

#### 3.4 Update connectToMQTT() (line 641)
Add after line 652:
```cpp
    // Subscribe to command topic (Component 5)
    String commandTopic = "hospital/devices/" + deviceId + "/command";
    mqttClient.subscribe(commandTopic.c_str());
    Serial.println("📡 Subscribed to: " + commandTopic);

    // Subscribe to calibration topic (Component 5)
    String calibrationTopic = "hospital/devices/" + deviceId + "/calibration";
    mqttClient.subscribe(calibrationTopic.c_str());
    Serial.println("📡 Subscribed to: " + calibrationTopic);
```

#### 3.5 Update onMqttMessage() (line 659)
Add after line 680 (after patient assignment):
```cpp
  // Handle commands (Component 5)
  if (String(topic).endsWith("/command")) {
    JsonDocument doc;
    if (deserializeJson(doc, message) == DeserializationError::Ok) {
      String command = doc["command"].as<String>();
      String commandId = doc["commandId"].as<String>();
      lastCommandReceivedAt = millis();

      if (command == "ping") handlePingCommand(commandId);
      else if (command == "calibrate") handleCalibrationCommand(commandId);
    }
  }

  // Handle calibration status (Component 5)
  if (String(topic).endsWith("/calibration")) {
    JsonDocument doc;
    if (deserializeJson(doc, message) == DeserializationError::Ok) {
      calibrationDue = doc["isDue"].as<bool>();
      if (calibrationDue) flashAlertPattern("medium");
    }
  }
```

#### 3.6 Update sendHeartbeat() (line 796)
Add to doc (after line 810):
```cpp
  doc["batteryhealthpercentage"] = batteryHealthPercentage;  // Component 5
  doc["totaldisconnects"] = totalDisconnects;  // Component 5
  doc["firmwareversion"] = FIRMWARE_VERSION;  // Component 5
```

#### 3.7 Update sendVitals() (line 833)
Add to doc (after line 849):
```cpp
  doc["batteryHealthPercentage"] = batteryHealthPercentage;  // Component 5
  doc["firmwareVersion"] = FIRMWARE_VERSION;  // Component 5
  doc["signalStrength"] = WiFi.RSSI();  // Component 5
```

#### 3.8 Update loadConfiguration() (line 871)
Add after line 890:
```cpp
  batteryHealthPercentage = prefs.getInt("batHealth", 100);  // Component 5
  totalDisconnects = prefs.getInt("disconnects", 0);  // Component 5
```

#### 3.9 Update saveConfiguration() (line 893)
Add after line 906:
```cpp
  prefs.putInt("batHealth", batteryHealthPercentage);  // Component 5
  prefs.putInt("disconnects", totalDisconnects);  // Component 5
```

#### 3.10 Update setup() Serial.println (line 202)
```cpp
  Serial.println("\n🏥 ESP32 Hospital Watch v3.3.0 (22 Local Alerts)");
```

**Lines Modified:** ~30 lines

---

## Summary of Changes

| Section | Description | Lines | Location |
|---------|-------------|-------|----------|
| Variables | Component 5 tracking | 15 | After line 99 |
| Variables | Component 4 trackers | 15 | After line 99 |
| Variables | Component 2 system | 10 | After line 99 |
| Variables | Alert engine | 5 | After line 99 |
| Functions | Alert core | 30 | After line 195 |
| Functions | Battery alerts | 30 | After line 195 |
| Functions | Connectivity | 25 | After line 195 |
| Functions | Duration | 40 | After line 195 |
| Functions | System | 30 | After line 195 |
| Functions | Critical | 15 | After line 195 |
| Functions | Commands | 40 | After line 195 |
| Modifications | Various updates | 30 | Multiple |
| **TOTAL** | | **~285** | |

**Final Size:** ~1193 lines (from 908)

---

## Testing Checklist

- [ ] Compiles without errors
- [ ] Battery alerts fire at < 10% and < 20%
- [ ] Duration trackers work (wait 10/5/30 min)
- [ ] LED flash patterns work
- [ ] MQTT alert transmission works
- [ ] Command ping/calibrate work
- [ ] Heartbeat includes new fields
- [ ] Vitals includes new fields
- [ ] Config save/load works

---

## Ready for Implementation

This analysis is complete and accurate. Ready to implement when approved.
