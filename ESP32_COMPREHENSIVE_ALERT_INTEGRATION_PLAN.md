# ESP32 Watch - Components 1-5 Comprehensive Integration Plan

## Alert Capability Analysis: What ESP32 Can Detect Locally

### Component 1: Trend Analysis (Backend Heavy)
**ESP32 Cannot Do (Requires Historical DB):**
- ❌ Deterioration trends (needs 6+ hours history)
- ❌ Improvement trends (needs historical data)
- ❌ Rapid changes (needs baseline calculation)

**ESP32 CAN Do (Simple Tracking):**
- ✅ Sudden spike detection (compare current vs last 3 readings)
- ✅ Local trend direction (rising/falling over last minute)

**Verdict:** Mostly backend, but ESP32 can flag sudden changes

---

### Component 2: System Alerts (Mixed)
**ESP32 CAN Do:**
- ✅ Data quality alerts (sensor failure, invalid readings)
- ✅ Communication failure (WiFi/MQTT disconnect)
- ✅ Low battery alerts
- ✅ Sensor malfunction detection

**Backend Only:**
- ❌ Server-side system alerts
- ❌ Database alerts

**Verdict:** ESP32 can handle device-side system alerts

---

### Component 3: Impedance Tracking (Backend Heavy)
**ESP32 Cannot Do:**
- ❌ All impedance alerts require impedance sensor (not on basic watch)
- ❌ Fluid overload/dehydration detection needs impedance hardware

**Verdict:** Skip on ESP32 (no impedance sensor)

---

### Component 4: Duration/State Tracking (ESP32 Capable!)
**ESP32 CAN Do:**
- ✅ Prolonged tachycardia (HR > 100 for 10+ min)
- ✅ Prolonged bradycardia (HR < 60 for 10+ min)
- ✅ Prolonged hypoxia (SpO2 < 90% for 5+ min)
- ✅ Prolonged fever (Temp > 100.4°F for 30+ min)
- ✅ Prolonged hypothermia (Temp < 95°F for 30+ min)
- ✅ Sustained hypertension (BP > 140/90 for 20+ min) - if BP sensor available

**Verdict:** ESP32 PERFECT for duration tracking with timers

---

### Component 5: Device Maintenance (ESP32 Native!)
**ESP32 CAN Do:**
- ✅ Critical battery level (< 10%)
- ✅ Low battery warning (< 20%)
- ✅ Battery degradation tracking
- ✅ Frequent disconnects (5+ in 24h)
- ✅ Device unresponsive (no ack for 10+ min)
- ✅ Calibration due (backend notifies, ESP32 warns)

**Verdict:** ESP32 PERFECT - these are device-local alerts

---

## ESP32 Local Alert Strategy

### Priority 1: Component 5 - Device Maintenance (9 alerts)
**All 9 alerts can be detected locally on ESP32**

### Priority 2: Component 4 - Duration/State Tracking (6 alerts)
**6 alerts ESP32 can track with timers:**
1. prolongedTachycardia
2. prolongedBradycardia
3. prolongedHypoxia
4. prolongedFever
5. prolongedHypothermia
6. sustainedHypertension (if BP sensor)

### Priority 3: Component 2 - System Alerts (5 alerts)
**ESP32 device-side alerts:**
1. sensorMalfunction
2. communicationFailure
3. lowBattery (duplicate of Component 5)
4. dataQualityIssue
5. invalidReading

### Priority 4: Immediate Critical Alerts (Always Local)
**Traditional threshold alerts ESP32 should always check:**
1. Severe tachycardia (HR > 150)
2. Severe bradycardia (HR < 40)
3. Critical hypoxia (SpO2 < 85%)
4. High fever (Temp > 103°F)
5. Severe hypothermia (Temp < 90°F)

---

## ESP32 Alert Architecture

### Dual Alert System
```
ESP32 Watch
    ↓
┌─────────────────────────────────┐
│ LOCAL ALERT ENGINE              │
│ - Component 4: Duration alerts  │
│ - Component 5: Device alerts    │
│ - Component 2: System alerts    │
│ - Critical threshold alerts     │
└─────────────────────────────────┘
    ↓                    ↓
MQTT Alert         Display LED/Buzzer
    ↓
Backend Receives
    ↓
┌─────────────────────────────────┐
│ BACKEND ALERT ENGINE            │
│ - Component 1: Trend analysis   │
│ - Component 3: Impedance        │
│ - All other complex alerts      │
└─────────────────────────────────┘
    ↓
WebSocket → Frontend
```

### Alert Flow
1. **ESP32 detects alert** → Flash LED + Send MQTT
2. **Backend receives** → Validate + Deduplicate + Add to alert stream
3. **Frontend displays** → Both ESP32 and backend alerts

---

## Implementation Plan

### Phase 1: Alert Data Structure
```cpp
struct LocalAlert {
    String alertType;
    String severity;      // high, medium, low
    String message;
    float confidence;
    unsigned long timestamp;
    JsonObject context;   // Additional data
};

// Alert queue (max 10 pending)
LocalAlert alertQueue[10];
int alertQueueSize = 0;
```

### Phase 2: Duration Trackers
```cpp
// Component 4: Duration state tracking
struct DurationTracker {
    bool inState;
    unsigned long stateStartTime;
    unsigned long thresholdMs;
    bool alertSent;
};

DurationTracker tachycardiaTracker = {false, 0, 600000, false};   // 10 min
DurationTracker bradycardiaTracker = {false, 0, 600000, false};   // 10 min
DurationTracker hypoxiaTracker = {false, 0, 300000, false};       // 5 min
DurationTracker feverTracker = {false, 0, 1800000, false};        // 30 min
DurationTracker hypothermiaTracker = {false, 0, 1800000, false};  // 30 min
```

### Phase 3: Alert Detection Functions
```cpp
void checkDurationAlerts() {
    checkProlongedTachycardia();
    checkProlongedBradycardia();
    checkProlongedHypoxia();
    checkProlongedFever();
    checkProlongedHypothermia();
}

void checkDeviceAlerts() {
    checkBatteryAlerts();
    checkConnectivityAlerts();
    checkCalibrationAlerts();
}

void checkSystemAlerts() {
    checkSensorMalfunction();
    checkDataQuality();
    checkCommunicationFailure();
}

void checkCriticalAlerts() {
    checkSevereTachycardia();
    checkSevereBradycardia();
    checkCriticalHypoxia();
    checkHighFever();
}
```

### Phase 4: Alert Transmission
```cpp
void sendAlert(LocalAlert alert) {
    if (!mqttClient.connected()) return;

    // Add to queue
    if (alertQueueSize < 10) {
        alertQueue[alertQueueSize++] = alert;
    }

    // Send via MQTT
    String topic = "hospital/devices/" + deviceId + "/alerts";

    JsonDocument doc;
    doc["alertType"] = alert.alertType;
    doc["severity"] = alert.severity;
    doc["message"] = alert.message;
    doc["source"] = "Watch";  // Important: marks as ESP32-generated
    doc["confidence"] = alert.confidence;
    doc["timestamp"] = alert.timestamp;
    doc["deviceId"] = deviceId;
    doc["patientId"] = assignedPatientId;

    String payload;
    serializeJson(doc, payload);

    mqttClient.publish(topic.c_str(), payload.c_str());

    // Visual/audio notification
    flashAlertPattern(alert.severity);
}

void flashAlertPattern(String severity) {
    if (severity == "high") {
        // Rapid flashing
        for (int i = 0; i < 10; i++) {
            digitalWrite(2, HIGH);
            delay(100);
            digitalWrite(2, LOW);
            delay(100);
        }
    } else if (severity == "medium") {
        // Moderate flashing
        for (int i = 0; i < 5; i++) {
            digitalWrite(2, HIGH);
            delay(300);
            digitalWrite(2, LOW);
            delay(300);
        }
    }
}
```

---

## Code Structure

### New Variables
```cpp
// Alert system
LocalAlert alertQueue[10];
int alertQueueSize = 0;
unsigned long lastAlertCheck = 0;

// Duration trackers (Component 4)
DurationTracker tachycardiaTracker;
DurationTracker bradycardiaTracker;
DurationTracker hypoxiaTracker;
DurationTracker feverTracker;
DurationTracker hypothermiaTracker;

// Sensor history (for sudden change detection)
float heartRateHistory[5] = {75, 75, 75, 75, 75};
float spo2History[5] = {98, 98, 98, 98, 98};
float tempHistory[5] = {98.6, 98.6, 98.6, 98.6, 98.6};
int historyIndex = 0;

// Data quality tracking
int consecutiveInvalidReadings = 0;
unsigned long lastValidReading = 0;
```

### New Functions
```cpp
// Alert detection
void runAlertEngine();
void checkDurationAlerts();
void checkDeviceAlerts();
void checkSystemAlerts();
void checkCriticalAlerts();

// Specific alert checks
void checkProlongedTachycardia();
void checkProlongedBradycardia();
void checkProlongedHypoxia();
void checkProlongedFever();
void checkProlongedHypothermia();
void checkSevereTachycardia();
void checkCriticalHypoxia();
void checkBatteryAlerts();
void checkConnectivityAlerts();
void checkSensorMalfunction();
void checkDataQuality();

// Alert management
void sendAlert(LocalAlert alert);
void createAlert(String type, String severity, String message, float confidence);
void flashAlertPattern(String severity);
void updateSensorHistory();
bool isValidReading(float hr, float spo2, float temp);
```

### Modified Loop
```cpp
void loop() {
    // ... existing code ...

    // Run alert engine every 2 seconds
    if (millis() - lastAlertCheck > 2000) {
        runAlertEngine();
        lastAlertCheck = millis();
    }

    // Update sensor history
    updateSensorHistory();
}
```

---

## Alert Capability Summary

| Component | Total Alerts | ESP32 Can Detect | % ESP32 |
|-----------|--------------|------------------|---------|
| Component 1 | 20 | 2 | 10% |
| Component 2 | 15 | 5 | 33% |
| Component 3 | 24 | 0 | 0% |
| Component 4 | 45 | 6 | 13% |
| Component 5 | 9 | 9 | 100% |
| **TOTAL** | **113** | **22** | **19%** |

**ESP32 Can Locally Detect: 22 alerts**

### Categories:
- ✅ **Device Maintenance:** 9 alerts (Component 5)
- ✅ **Duration Tracking:** 6 alerts (Component 4)
- ✅ **System Alerts:** 5 alerts (Component 2)
- ✅ **Critical Immediate:** 2 alerts (Component 1)

---

## Benefits

### 1. Offline Alert Capability
- ESP32 can alert even if backend is down
- Critical alerts never missed

### 2. Faster Response Time
- No network latency for critical alerts
- Immediate LED/buzzer notification

### 3. Reduced Backend Load
- ESP32 pre-filters obvious alerts
- Backend focuses on complex analysis

### 4. Redundancy
- Dual alert detection (ESP32 + Backend)
- Backend can validate ESP32 alerts

---

## Testing Strategy

### Test 1: Prolonged Tachycardia
1. Set HR > 100
2. Wait 10 minutes
3. Verify ESP32 sends `prolongedTachycardia` alert
4. Verify LED flashes
5. Verify MQTT message received

### Test 2: Critical Battery
1. Set battery < 10%
2. Verify ESP32 sends `criticalBatteryLevel` alert immediately
3. Check LED rapid flash pattern

### Test 3: Communication Failure
1. Disconnect MQTT
2. Verify ESP32 detects and sends alert when reconnected
3. Check disconnect counter increments

### Test 4: Sensor Malfunction
1. Simulate invalid readings (HR = 0)
2. After 3 consecutive invalid readings
3. Verify `sensorMalfunction` alert sent

---

## Next Step: Implementation

Ready to generate complete ESP32 code with:
- ✅ All Component 5 alerts (9)
- ✅ Component 4 duration tracking (6)
- ✅ Component 2 system alerts (5)
- ✅ Critical immediate alerts (2)
- ✅ **Total: 22 local alerts**

**Firmware Version: 3.3.0**
**Features: Comprehensive local alert engine + full backend integration**
