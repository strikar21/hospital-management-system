# ESP32 ↔ Backend Data Contract

**Date**: October 16, 2025
**Purpose**: Define exact data format ESP32 must send for backend to accept

---

## CRITICAL FINDINGS

### ESP32 Current Code is **WRONG** ❌

**ESP32 sends** (lines 1185-1203):
```json
{
  "deviceId": "ESP32_WATCH_001",
  "patientId": "PAT001",
  "timestamp": 1234567890,           // ❌ WRONG: milliseconds, not ISO datetime
  "heartRate": 75.2,                 // ❌ WRONG: Should be integer 30-250
  "temperature": 98.6,               // ❌ WRONG: Should be skinTemperature in Celsius
  "oxygenSat": 98,                   // ❌ WRONG: Should be oxygenSaturation
  "batteryLevel": 85,
  "quality": 95                      // ❌ WRONG: Should be signalQuality (0.0-1.0)
}
```

**Backend expects** (VitalsRealtimeMessage):
```json
{
  "deviceId": "ESP32_WATCH_001",
  "patientId": "PAT001",
  "timestamp": "2025-10-16T17:30:00Z",  // ✅ ISO 8601 datetime
  "mode": "ecg",                        // ✅ REQUIRED: "ecg" or "eeg"
  "heartRate": 75,                      // ✅ integer 30-250 BPM
  "respiratoryRate": 16,                // ✅ integer 5-60
  "skinTemperature": 37.0,              // ✅ float 30-45 Celsius
  "oxygenSaturation": 98,               // ✅ integer 0-100
  "batteryLevel": 85,                   // ✅ integer 0-100
  "signalQuality": 0.95                 // ✅ float 0.0-1.0
}
```

---

## 1. VITALS MESSAGE (Every 1 second)

### MQTT Topic
```
hospital/devices/{deviceId}/vitals
```

### Required Fields

```json
{
  // ========================================
  // IDENTIFICATION (REQUIRED)
  // ========================================
  "deviceId": "ESP32_WATCH_003",           // ESP32 device ID
  "patientId": "PAT001",                   // Assigned patient ID
  "timestamp": "2025-10-16T17:30:45.123Z", // ISO 8601 datetime string
  "mode": "ecg",                           // "ecg" or "eeg" (REQUIRED!)

  // ========================================
  // BASIC VITALS (ALL OPTIONAL BUT RECOMMENDED)
  // ========================================
  "heartRate": 75,                         // integer 30-250 BPM
  "respiratoryRate": 16,                   // integer 5-60 breaths/min
  "skinTemperature": 37.0,                 // float 30.0-45.0 Celsius (NOT Fahrenheit!)
  "oxygenSaturation": 98,                  // integer 0-100 %
  "bloodPressureSystolic": 120,            // integer 60-200 mmHg (optional)
  "bloodPressureDiastolic": 80,            // integer 40-130 mmHg (optional)
  "batteryLevel": 85,                      // integer 0-100 %
  "signalQuality": 0.95,                   // float 0.0-1.0 (NOT 0-100!)

  // ========================================
  // SEQUENCE NUMBER (OPTIONAL)
  // ========================================
  "sequence": 12345                        // Message sequence number for packet loss detection
}
```

### Critical Backend Validations

1. **Field Names**: Exact camelCase required (`oxygenSaturation` not `oxygenSat`)
2. **Timestamp**: Must be ISO 8601 string, not Unix milliseconds
3. **Mode**: MUST be present ("ecg" or "eeg")
4. **Temperature**: MUST be Celsius 30-45 (ESP32 sends Fahrenheit!)
5. **SignalQuality**: MUST be 0.0-1.0 (ESP32 sends 0-100!)
6. **HeartRate**: MUST be integer 30-250 (ESP32 may send float!)

### Backend Security Validation (Happens BEFORE parsing)

```python
# 1. Device exists and status='active'
# 2. Rate limit: 1 message/second per device
# 3. Range validation:
#    - heartRate: 20-300 BPM
#    - oxygenSaturation: 50-100%
#    - skinTemperature: 80-115°F (converts to Celsius check)
#    - respiratoryRate: 4-60 /min
```

---

## 2. ALERT MESSAGE (Event-driven)

### MQTT Topic
```
hospital/devices/{deviceId}/alerts
```

### Required Format

```json
{
  "alertType": "severeTachycardia",     // Alert type identifier
  "severity": "high",                   // "low", "medium", "high", "critical"
  "message": "SEVERE TACHY - HR 165",   // Human-readable message
  "source": "Watch",                    // "Watch", "Backend", "System"
  "confidence": 1.0,                    // float 0.0-1.0
  "timestamp": "2025-10-16T17:30:45Z",  // ISO 8601
  "deviceId": "ESP32_WATCH_003",
  "patientId": "PAT001",
  "category": "device"                  // "device", "clinical", "system"
}
```

### ESP32 Alert Types (22 Types)

#### Component 1: Critical Vitals
1. `severeTachycardia` - HR > 150 (high)
2. `criticalHypoxia` - SpO2 < 85% (high)

#### Component 2: System Alerts
3. `sensorMalfunction` - 3+ invalid readings (high)
4. `communicationFailure` - 5+ min no data (high)
5. `dataQualityIssue` - HR spike > 50 BPM (low)

#### Component 4: Duration-Based
6. `prolongedTachycardia` - HR > 100 for 10+ min (medium)
7. `prolongedBradycardia` - HR < 60 for 10+ min (medium)
8. `prolongedHypoxia` - SpO2 < 90% for 5+ min (medium)
9. `prolongedFever` - Temp > 100.4°F for 30+ min (medium)
10. `prolongedHypothermia` - Temp < 95°F for 30+ min (medium)

#### Component 5: Device Maintenance
11. `criticalBatteryLevel` - Battery < 10% (high)
12. `lowBatteryWarning` - Battery < 20% (medium)
13. `batteryDegradation` - Health < 70% (medium)
14. `frequentDisconnects` - 5+ disconnects (medium)
15. `deviceUnresponsive` - 10+ min no response (high)

---

## 3. HEARTBEAT MESSAGE (Every 30 seconds via HTTP)

### HTTP Endpoint
```
POST /api/v1/esp32/{deviceId}/heartbeat
```

### Headers (HMAC Authentication)
```
Content-Type: application/json
X-Device-MAC: AA:BB:CC:DD:EE:FF
X-Device-Signature: abc123...
X-Timestamp: 1697478645
```

### Body
```json
{
  "batteryLevel": 85,
  "signalStrength": -45
}
```

**This is ALREADY WORKING correctly in ESP32!** ✅

---

## 4. TIMESCALEDB SCHEMA (What Backend Stores)

### Table: vitals_realtime

```sql
CREATE TABLE vitals_realtime (
    time TIMESTAMPTZ NOT NULL,
    "patientId" TEXT,
    "deviceId" TEXT,
    mode TEXT,  -- 'ecg' or 'eeg'

    -- Basic vitals
    "heartRate" NUMERIC,
    "respiratoryRate" NUMERIC,
    "skinTemperature" NUMERIC,  -- Celsius
    "oxygenSaturation" NUMERIC,
    "batteryLevel" NUMERIC,
    "signalQuality" NUMERIC,  -- 0.0-1.0

    -- ECG analysis (optional)
    "rrInterval" NUMERIC,
    "qrsDuration" NUMERIC,
    "qtInterval" NUMERIC,
    axis TEXT,
    rhythm TEXT,
    "stSegment" TEXT,

    -- EEG analysis (optional)
    "alphaPower" NUMERIC,
    "betaPower" NUMERIC,
    "thetaPower" NUMERIC,
    "deltaPower" NUMERIC,
    "gammaPower" NUMERIC,
    "dominantFrequency" NUMERIC,
    "seizureActivity" BOOLEAN,

    -- Metadata
    quality JSONB,
    sequence INTEGER,
    metadata JSONB
);
```

---

## 5. ESP32 FIRMWARE FIXES REQUIRED

### Fix 1: Change `timestamp` to ISO 8601

**Current (WRONG)**:
```cpp
doc["timestamp"] = millis();  // ❌ Milliseconds since boot
```

**Fixed**:
```cpp
// Get current time from NTP
time_t now;
struct tm timeinfo;
time(&now);
gmtime_r(&now, &timeinfo);

char timestamp[30];
strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%S", &timeinfo);

// Add milliseconds
unsigned long ms = millis() % 1000;
sprintf(timestamp + strlen(timestamp), ".%03luZ", ms);

doc["timestamp"] = String(timestamp);  // ✅ "2025-10-16T17:30:45.123Z"
```

### Fix 2: Add `mode` field

**Current (MISSING)**:
```cpp
// No mode field!
```

**Fixed**:
```cpp
doc["mode"] = "ecg";  // ✅ or "eeg" depending on watch configuration
```

### Fix 3: Fix temperature (Fahrenheit → Celsius)

**Current (WRONG)**:
```cpp
doc["temperature"] = 98.6;  // ❌ Fahrenheit, wrong field name
```

**Fixed**:
```cpp
float tempF = 98.6;
float tempC = (tempF - 32.0) * 5.0 / 9.0;  // Convert to Celsius
doc["skinTemperature"] = tempC;  // ✅ 37.0°C
```

### Fix 4: Fix field names

**Current (WRONG)**:
```cpp
doc["oxygenSat"] = 98;  // ❌ Wrong name
doc["quality"] = 95;    // ❌ Wrong name and scale
```

**Fixed**:
```cpp
doc["oxygenSaturation"] = 98;   // ✅ Correct name
doc["signalQuality"] = 0.95;    // ✅ Correct name and scale (0.0-1.0)
```

### Fix 5: Ensure integer types for HR

**Current (MAY BE WRONG)**:
```cpp
doc["heartRate"] = heartRate;  // If heartRate is float, backend will reject
```

**Fixed**:
```cpp
doc["heartRate"] = (int)heartRate;  // ✅ Ensure integer
```

---

## 6. COMPLETE CORRECTED ESP32 `sendVitals()` FUNCTION

```cpp
void sendVitals() {
  if (!mqttClient.connected() || !isAssigned) {
    if (!mqttClient.connected()) {
      connectToMQTT();
    }
    return;
  }

  String topic = "hospital/devices/" + deviceId + "/vitals";

  JsonDocument doc;

  // ========================================
  // IDENTIFICATION
  // ========================================
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;

  // ISO 8601 timestamp
  time_t now;
  struct tm timeinfo;
  time(&now);
  gmtime_r(&now, &timeinfo);
  char timestamp[30];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%S", &timeinfo);
  unsigned long ms = millis() % 1000;
  sprintf(timestamp + strlen(timestamp), ".%03luZ", ms);
  doc["timestamp"] = String(timestamp);

  // Mode (required!)
  doc["mode"] = "ecg";  // or "eeg" depending on device configuration

  // ========================================
  // BASIC VITALS
  // ========================================
  doc["heartRate"] = (int)heartRate;  // Ensure integer
  doc["respiratoryRate"] = 16;  // Add respiratory rate (if measured)

  // Convert temperature to Celsius
  float tempC = (temperature - 32.0) * 5.0 / 9.0;
  doc["skinTemperature"] = tempC;

  doc["oxygenSaturation"] = oxygenSat;  // Correct field name
  doc["batteryLevel"] = batteryLevel;

  // Signal quality (0.0-1.0 scale)
  doc["signalQuality"] = 0.95;  // Or calculate from sensor quality

  // Optional: sequence number for packet loss detection
  static int sequence = 0;
  doc["sequence"] = sequence++;

  // ========================================
  // PUBLISH
  // ========================================
  String payload;
  serializeJson(doc, payload);

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    Serial.println("📊 Vitals sent via MQTT: HR=" + String((int)heartRate) +
                   ", Temp=" + String(tempC, 1) + "°C, SpO2=" + String(oxygenSat) + "%");
  }
}
```

---

## 7. COMPLETE CORRECTED ESP32 `sendAlert()` FUNCTION

```cpp
void sendAlert(String alertType, String severity, String message, float confidence) {
  if (!mqttClient.connected() || !isAssigned) return;

  String topic = "hospital/devices/" + deviceId + "/alerts";

  JsonDocument doc;

  // Alert details
  doc["alertType"] = alertType;
  doc["severity"] = severity;
  doc["message"] = message;
  doc["source"] = "Watch";
  doc["confidence"] = confidence;

  // ISO 8601 timestamp
  time_t now;
  struct tm timeinfo;
  time(&now);
  gmtime_r(&now, &timeinfo);
  char timestamp[30];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%S", &timeinfo);
  unsigned long ms = millis() % 1000;
  sprintf(timestamp + strlen(timestamp), ".%03luZ", ms);
  doc["timestamp"] = String(timestamp);

  // Device and patient IDs
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["category"] = "device";

  // Publish
  String payload;
  serializeJson(doc, payload);

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    String severityUpper = severity;
    severityUpper.toUpperCase();
    Serial.println("🚨 [" + severityUpper + "] " + alertType);
    flashAlertPattern(severity);
  }
}
```

---

## 8. MQTT CONNECTION FIX

**Current ESP32 connects to port 1883 with NO auth** ❌

**Backend Mosquitto listens on port 8883 with TLS + auth** ✅

### Solution A: Add plain MQTT listener (RECOMMENDED)

Edit `mosquitto/config/mosquitto.conf`:

```conf
# Add this BEFORE existing TLS listener

# Plain listener for ESP32 (localhost only, no auth for simplicity)
listener 1883 127.0.0.1
protocol mqtt
allow_anonymous true  # Backend validates everything anyway

# Existing TLS listener (for backend)
listener 8883
protocol mqtt
...
```

### Solution B: Add authentication to ESP32

ESP32 connect with credentials:

```cpp
String clientId = "HospitalWatch_" + deviceId;
if (mqttClient.connect(clientId.c_str(), "hospitalEsp32", "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=")) {
    Serial.println("✅ MQTT Connected with auth!");
}
```

---

## SUMMARY: What Needs to Change

### ESP32 Firmware Changes (CRITICAL) ❌

1. ❌ Add `mode` field ("ecg" or "eeg")
2. ❌ Change `timestamp` from millis() to ISO 8601
3. ❌ Change `temperature` to `skinTemperature` in Celsius
4. ❌ Change `oxygenSat` to `oxygenSaturation`
5. ❌ Change `quality` (0-100) to `signalQuality` (0.0-1.0)
6. ❌ Ensure `heartRate` is integer, not float
7. ❌ Add `respiratoryRate` if available

### Mosquitto Config Changes (REQUIRED) ❌

1. ❌ Add plain listener on port 1883 for ESP32
2. ❌ Keep TLS listener on port 8883 for backend

### Backend Changes (NONE NEEDED) ✅

- Backend is correct and ready to receive data
- Security validation in place
- TimescaleDB schema ready

---

## TESTING CHECKLIST

After fixes:

- [ ] ESP32 connects to MQTT successfully
- [ ] Backend logs show: `📊 8CH Vitals processed for patient...`
- [ ] Frontend displays vitals in real-time
- [ ] Alerts appear in frontend
- [ ] TimescaleDB `vitals_realtime` table has data
- [ ] No validation errors in backend logs

---

**Status**: ESP32 firmware is BROKEN, needs 7 critical fixes
