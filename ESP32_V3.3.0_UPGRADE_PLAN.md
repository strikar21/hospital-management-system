# ESP32 v3.2.0 → v3.3.0 Upgrade Plan
## Components 1-5 Local Alert Integration

### Current State
**File:** `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
**Version:** 3.2.0 (908 lines)
**Base:** HMAC authentication, MQTT vitals, provisioning

### Target State
**Version:** 3.3.0
**New Features:** 22 local alerts across Components 1-5
**Estimated Size:** ~1100 lines

---

## Changes Required

### 1. Add Component 5 Variables (Device Maintenance)
```cpp
// After line 99 (batteryLevel)
int batteryHealthPercentage = 100;
float batteryDrainRatePerHour = 0.0;
unsigned long lastBatteryUpdate = 0;
int lastBatteryLevel = 100;
int totalDisconnects = 0;
bool wasWifiConnected = false;
bool wasMqttConnected = false;
unsigned long disconnectTrackerLastCheck = 0;
unsigned long lastCommandReceivedAt = 0;
bool calibrationDue = false;
```

### 2. Add Component 4 Variables (Duration Tracking)
```cpp
struct DurationTracker {
    bool inState;
    unsigned long stateStartTime;
    unsigned long thresholdMs;
    bool alertSent;
};

DurationTracker tachycardiaTracker = {false, 0, 600000, false};
DurationTracker bradycardiaTracker = {false, 0, 600000, false};
DurationTracker hypoxiaTracker = {false, 0, 300000, false};
DurationTracker feverTracker = {false, 0, 1800000, false};
DurationTracker hypothermiaTracker = {false, 0, 1800000, false};
```

### 3. Add Component 2 Variables (System Alerts)
```cpp
int consecutiveInvalidReadings = 0;
unsigned long lastValidReading = 0;
bool sensorMalfunctionAlertSent = false;
float heartRateHistory[5] = {75, 75, 75, 75, 75};
float spo2History[5] = {98, 98, 98, 98, 98};
float tempHistory[5] = {98.6, 98.6, 98.6, 98.6, 98.6};
int historyIndex = 0;
```

### 4. Add Alert Engine Variables
```cpp
unsigned long lastAlertCheck = 0;
```

### 5. Add Alert Functions (After line 195 - after addHMACHeaders)
```cpp
void sendAlert(String alertType, String severity, String message, float confidence);
void flashAlertPattern(String severity);
void checkBatteryAlerts();
void updateBatteryHealth();
void checkConnectivityAlerts();
void trackConnectivity();
void updateDurationTracker(DurationTracker &tracker, bool condition, String alertType, String message);
void checkDurationAlerts();
bool isValidReading(float hr, float spo2, float temp);
void checkSystemAlerts();
void checkCriticalAlerts();
void runAlertEngine();
void updateSensorHistory();
void sendCommandAck(String commandId, bool success, String msg);
void handlePingCommand(String commandId);
void handleCalibrationCommand(String commandId);
```

### 6. Update onMqttMessage (line 659)
Add command and calibration topic handling

### 7. Update connectToMQTT (line 641)
Subscribe to `/command` and `/calibration` topics

### 8. Update sendHeartbeat (line 796)
Add batteryHealthPercentage, totalDisconnects, firmwareVersion

### 9. Update sendVitals (line 833)
Add batteryHealthPercentage, firmwareVersion, signalStrength

### 10. Update loop() (line 243)
Add alert engine calls

### 11. Update loadConfiguration/saveConfiguration
Add battery health, disconnects, calibration fields

### 12. Update setup()
Initialize tracking variables

---

## Implementation Strategy

### Phase 1: Add All Variables
- Device maintenance tracking
- Duration state trackers
- System alert counters
- Sensor history arrays

### Phase 2: Implement Alert Functions
- Battery alerts (3)
- Connectivity alerts (2)
- Duration alerts (6)
- System alerts (5)
- Critical alerts (2)

### Phase 3: Integrate Alert Engine
- Add runAlertEngine() to loop
- Add tracking functions to loop
- Update MQTT subscriptions

### Phase 4: Update Communications
- Enhance heartbeat payload
- Enhance vitals payload
- Add command handlers

### Phase 5: Test
- Verify compilation
- Check alert generation
- Test MQTT transmission

---

## Key Additions Summary

| Section | Lines Added | Description |
|---------|-------------|-------------|
| Variables | ~40 | Tracking state for all alerts |
| Alert Functions | ~200 | Detection logic for 22 alerts |
| Integration | ~10 | Loop and MQTT updates |
| Command Handling | ~30 | Ping/calibrate commands |
| **TOTAL** | **~280** | New code lines |

**Final Size:** ~1190 lines (from 908)

---

## Testing Checklist

- [ ] Code compiles without errors
- [ ] Battery alerts fire correctly
- [ ] Duration trackers work (10min, 5min, 30min)
- [ ] System alerts detect sensor failures
- [ ] Critical alerts fire immediately
- [ ] LED flash patterns work
- [ ] MQTT alert transmission successful
- [ ] Command acknowledgments work
- [ ] Heartbeat includes new fields
- [ ] Vitals includes new fields

---

## Ready to Implement

Shall I proceed with updating `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino` to v3.3.0 with all Components 1-5 features?
