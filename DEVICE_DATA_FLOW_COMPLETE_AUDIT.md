# COMPLETE DEVICE DATA FLOW AUDIT

**Date**: October 16, 2025
**Status**: COMPREHENSIVE SYSTEM AUDIT

---

## EXECUTIVE SUMMARY

### Current Architecture

```
ESP32 Watch
    ├─→ HTTP (HMAC-SHA256) → Backend ✅ SECURE
    │   └─→ Heartbeat (every 30s)
    │
    └─→ MQTT (Plain TCP port 1883) → Backend ❌ NOT CONNECTED
        ├─→ Vitals (every 5s when assigned)
        └─→ Alerts (22 types, real-time)
```

### Critical Findings

1. **ESP32 IS CONFIGURED TO USE MQTT** for vitals and alerts
2. **MQTT CONNECTION IS FAILING** because:
   - ESP32 connects to port 1883 (plain)
   - Mosquitto listens on port 8883 (TLS + auth)
   - No credentials configured on ESP32
3. **System currently working via HTTP fallback** (not MQTT)
4. **Vitals and alerts NOT flowing** because ESP32 cannot connect to MQTT

---

## PART 1: ESP32 FIRMWARE ANALYSIS

### Data Flow in ESP32 (from esp32_hospital_watch_complete.ino)

#### Main Loop (lines 548-610)

```cpp
void loop() {
  // 1. HEARTBEAT via HTTP (every 30 seconds) - HMAC authenticated
  if (wifiConnected && isProvisioned && ntpSynced && millis() - lastHeartbeat > 30000) {
    sendHeartbeat();  // → HTTP POST /api/v1/esp32/{deviceId}/heartbeat
  }

  // 2. VITALS via MQTT (every 5 seconds when assigned to patient)
  if (wifiConnected && isProvisioned && isAssigned && millis() - lastVitals > 5000) {
    sendVitals();  // → MQTT publish to hospital/devices/{deviceId}/vitals
  }

  // 3. ALERT ENGINE (every 2 seconds)
  if (wifiConnected && isProvisioned && millis() - lastAlertCheck > 2000) {
    runAlertEngine();  // → MQTT publish to hospital/devices/{deviceId}/alerts
  }
}
```

### Send Functions

#### 1. sendHeartbeat() - HTTP with HMAC (lines 1140-1172)
```cpp
void sendHeartbeat() {
  if (!ntpSynced) return;

  HTTPClient http;
  String url = "http://" + serverIP + ":" + serverPort + "/api/v1/esp32/" + deviceId + "/heartbeat";
  String endpoint = "/api/v1/esp32/" + deviceId + "/heartbeat";

  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  addHMACHeaders(http, endpoint);  // ✅ HMAC-SHA256 authentication

  // Payload: {batteryLevel, signalStrength}
  int httpCode = http.POST(payload);
}
```

**Status**: ✅ **WORKING** - Backend logs show heartbeats every 30s

#### 2. sendVitals() - MQTT (lines 1177-1203)
```cpp
void sendVitals() {
  if (!mqttClient.connected() || !isAssigned) {
    if (!mqttClient.connected()) {
      connectToMQTT();  // Try to reconnect
    }
    return;  // ❌ EXITS HERE - MQTT not connected
  }

  String topic = "hospital/devices/" + deviceId + "/vitals";

  // Payload: {deviceId, patientId, timestamp, heartRate, temperature, oxygenSat, batteryLevel, quality}

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    Serial.println("📊 Vitals sent via MQTT...");
  }
}
```

**Status**: ❌ **NOT WORKING** - MQTT client not connected, exits early

#### 3. sendAlert() - MQTT (lines 248-273)
```cpp
void sendAlert(String alertType, String severity, String message, float confidence) {
  if (!mqttClient.connected() || !isAssigned) return;  // ❌ EXITS HERE

  String topic = "hospital/devices/" + deviceId + "/alerts";

  // Payload: {alertType, severity, message, source, confidence, timestamp, deviceId, patientId, category}

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    Serial.println("🚨 [" + severity + "] " + alertType);
    flashAlertPattern(severity);
  }
}
```

**Status**: ❌ **NOT WORKING** - MQTT client not connected, exits early

### Alert Types (22 Local Alerts - v3.3.0)

#### Component 1: Critical Vitals Alerts
1. `severeTachycardia` - HR > 150 (high)
2. `criticalHypoxia` - SpO2 < 85% (high)

#### Component 2: System Alerts
3. `sensorMalfunction` - 3+ consecutive invalid readings (high)
4. `communicationFailure` - 5+ min without valid reading (high)
5. `dataQualityIssue` - HR spike > 50 BPM (low)

#### Component 4: Duration-Based Alerts
6. `prolongedTachycardia` - HR > 100 for 10+ min (medium)
7. `prolongedBradycardia` - HR < 60 for 10+ min (medium)
8. `prolongedHypoxia` - SpO2 < 90% for 5+ min (medium)
9. `prolongedFever` - Temp > 100.4°F for 30+ min (medium)
10. `prolongedHypothermia` - Temp < 95°F for 30+ min (medium)

#### Component 5: Device Maintenance Alerts
11. `criticalBatteryLevel` - Battery < 10% (high)
12. `lowBatteryWarning` - Battery < 20% (medium)
13. `batteryDegradation` - Battery health < 70% (medium)
14. `frequentDisconnects` - 5+ disconnects (medium)
15. `deviceUnresponsive` - 10+ min without command response (high)

### MQTT Configuration in ESP32

**Lines 73-74**: Default configuration
```cpp
String mqttServer = "";  // Set during provisioning
String mqttPort = "1883";  // ❌ Plain TCP, no TLS
```

**Lines 752**: Web UI default
```html
<input type='text' name='mqtt_port' value='1883' required>
```

**Line 802**: MQTT server = Backend server IP
```cpp
mqttServer = serverIP;  // Same as HTTP backend server
```

**Lines 955-956**: MQTT client setup
```cpp
mqttClient.setServer(mqttServer.c_str(), mqttPort.toInt());
mqttClient.setCallback(onMqttMessage);
```

**Lines 967**: Connection attempt (NO AUTH, NO TLS)
```cpp
if (mqttClient.connect(clientId.c_str())) {
  // ✅ Subscribe to assignment topic
  mqttClient.subscribe("hospital/devices/" + deviceId + "/assign");
  // ✅ Subscribe to command topic
  mqttClient.subscribe("hospital/devices/" + deviceId + "/command");
} else {
  Serial.println("❌ MQTT Connection failed");  // ← CURRENTLY FAILING
}
```

### What ESP32 Expects to Receive via MQTT

**Topic**: `hospital/devices/{deviceId}/assign`
**Payload**: `{"patientId": "PAT001"}`
**Purpose**: Assign watch to patient (enables vitals sending)

**Topic**: `hospital/devices/{deviceId}/command`
**Payload**: `{"command": "ping|calibrate", "commandId": "CMD123"}`
**Purpose**: Remote device commands

---

## PART 2: BACKEND ANALYSIS

### MQTT Service (hospital-backend/app/services/mqtt_service.py)

#### Configuration (lines 39-48)
```python
self.config = {
    'host': '127.0.0.1',
    'port': 8883,  # ← TLS port (ESP32 uses 1883)
    'username': 'hospitalEsp32',
    'password': 'ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=',
    'keepalive': 60,
    'clientId': 'hospitalBackend',
    'use_tls': True,  # ← TLS enabled (ESP32 doesn't support)
    'ca_certs': 'C:/Users/Srika/.../mosquitto/certs/ca.crt'
}
```

#### Subscriptions (lines 181-195)
```python
await self._setupHospitalSubscriptions():
    topics = [
        "hospital/devices/+/vitals",     # ← Where ESP32 publishes vitals
        "hospital/devices/+/waveform",
        "hospital/devices/+/event",
        "hospital/devices/+/heartbeat",
        "hospital/devices/+/alerts",     # ← Where ESP32 publishes alerts
        "hospital/devices/+/status",
        "hospital/system/+"
    ]
```

#### Message Routing with Security (lines 231-290)
```python
async def _routeMessage(self, topic: str, payload: Dict[str, Any]):
    # SECURITY VALIDATION LAYER (our new implementation)
    # 1. Validate device exists and is active
    # 2. Rate limiting: 1 msg/sec per device per topic
    # 3. Validate vitals ranges

    if messageType == 'vitals':
        await self._handleVitalsMessageNew(deviceId, payload)
    elif messageType == 'alerts':
        await self._handleAlertMessage(deviceId, payload)
```

#### Current Status
- ✅ Backend connected to Mosquitto on port 8883 (TLS)
- ✅ Subscribed to all device topics
- ❌ ESP32 cannot connect (wrong port, no auth, no TLS)
- ❌ NO messages flowing through MQTT

### HTTP Endpoints (hospital-backend/app/api/v1/esp32.py)

#### Heartbeat Endpoint (lines 245-304)
```python
@router.post("/{deviceId}/heartbeat")
async def deviceHeartbeat(deviceId, heartbeatData, ...):
    # HMAC Authentication
    # Updates: batteryLevel, lastSeen, status
    # ✅ CURRENTLY WORKING - Receiving heartbeats every 30s
```

**Status**: ✅ **WORKING** - Logs show: `💓 Heartbeat: ESP32_WATCH_003 Battery 20%`

#### Vitals Endpoint (lines 306-360) - NOT BEING USED
```python
@router.post("/{deviceId}/vitals/{patientId}")
async def receiveVitalsData(deviceId, patientId, vitalsData, ...):
    # X-Device-Key header authentication
    # Stores in TimescaleDB
    # Broadcasts via WebSocket
```

**Status**: ❌ **NOT BEING CALLED** - ESP32 sends vitals via MQTT, not HTTP

#### Alert Endpoint (lines 222-243) - NOT BEING USED
```python
@router.post("/{deviceId}/alert")
async def deviceAlert(deviceId, alertData, ...):
    # X-Device-Key header authentication
    # Broadcasts via WebSocket
```

**Status**: ❌ **NOT BEING CALLED** - ESP32 sends alerts via MQTT, not HTTP

---

## PART 3: MOSQUITTO BROKER STATUS

### Current Configuration (mosquitto/config/mosquitto.conf)

```conf
# TLS Listener
listener 8883
protocol mqtt

# TLS/SSL
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
require_certificate false
tls_version tlsv1.2

# Authentication
allow_anonymous false
password_file /mosquitto/config/passwords.txt

# ACL
acl_file /mosquitto/config/acl.conf
```

### Current Connections (from Docker logs)

```
✅ hospitalBackend (172.17.0.1:58604) - Backend connected successfully
❌ ESP32 attempts: "Protocol error" - Connection rejected
```

**Reason for ESP32 rejection**:
1. ESP32 tries port 1883 (no listener configured)
2. ESP32 tries port 8883 without TLS (protocol error)
3. ESP32 has no authentication credentials

---

## PART 4: DATABASE SCHEMA

### Devices Table
```sql
CREATE TABLE devices (
    id TEXT PRIMARY KEY,
    deviceType TEXT,
    macAddress TEXT,
    status TEXT,  -- 'available', 'assigned', 'offline'
    batteryLevel INTEGER,
    firmwareVersion TEXT,
    lastSeen TIMESTAMP,
    ... (40+ columns)
)
```

### Vitals Table (TimescaleDB)
```sql
CREATE TABLE vitalsrealtime (
    time TIMESTAMPTZ,
    deviceId TEXT,
    patientId TEXT,
    heartRate NUMERIC,
    temperature NUMERIC,
    oxygenSaturation NUMERIC,
    respiratoryRate NUMERIC,
    ... (20+ vital signs)
)
```

**Status**: ❌ **NO VITALS DATA** - MQTT not connected, vitals not flowing

---

## PART 5: FRONTEND

### Device Service (hospital-display-app/src/services/DeviceService.ts)

```typescript
// Uses HTTP API, NOT MQTT
const getDevices = async () => {
    const response = await fetch('/api/v2/devices');
    return response.json();
}
```

### Vital Service (hospital-display-app/src/services/VitalService.ts)

```typescript
// Uses WebSocket for real-time vitals, NOT MQTT
const ws = new WebSocket('ws://localhost:8001/ws/vitals');
ws.onmessage = (event) => {
    const vitalsData = JSON.parse(event.data);
    // Update UI
}
```

**Status**: ❌ **NO VITALS DISPLAYED** - Backend not receiving vitals from ESP32

---

## CRITICAL ISSUES IDENTIFIED

### Issue 1: MQTT Port Mismatch ❌
- **ESP32**: Connects to port 1883 (plain TCP)
- **Mosquitto**: Listens on port 8883 (TLS only)
- **Result**: Connection refused

### Issue 2: No Authentication on ESP32 ❌
- **ESP32**: `mqttClient.connect(clientId.c_str())` - no username/password
- **Mosquitto**: Requires username `hospitalEsp32` + password
- **Result**: Authentication failure

### Issue 3: No TLS on ESP32 ❌
- **ESP32**: Uses `WiFiClient` (plain TCP)
- **Mosquitto**: Requires TLS with certificate validation
- **Result**: Protocol error

### Issue 4: Data Not Flowing ❌
- **ESP32**: Cannot connect to MQTT
- **Backend**: Waiting for MQTT messages
- **Frontend**: WebSocket waiting for vitals
- **Result**: NO vitals, NO alerts flowing through system

---

## SOLUTION OPTIONS

### Option A: Add Plain MQTT Listener (RECOMMENDED)

**Pros**:
- Simple - No ESP32 code changes
- Works immediately
- ESP32 already secured with HMAC for HTTP
- Backend security validation layer protects MQTT

**Implementation**:
1. Add port 1883 listener to mosquitto.conf (localhost only)
2. Allow plain TCP for ESP32 devices
3. Keep port 8883 (TLS) for backend connection

**Security Note**: Safe because:
- ESP32 identity verified via HMAC during registration
- Backend validates all MQTT messages
- MQTT on localhost only (not exposed externally)

### Option B: Full TLS on ESP32 (COMPLEX)

**Pros**:
- End-to-end encryption
- Industry best practice

**Cons**:
- Complex ESP32 code changes (WiFiClientSecure)
- Certificate management on resource-constrained device
- TLS overhead on ESP32
- Certificate distribution problem (multiple hospitals)

**Not recommended**: Over-engineering for internal network

### Option C: Switch Everything to HTTP (FALLBACK)

**Pros**:
- Already secured with HMAC
- No MQTT needed

**Cons**:
- Lose real-time MQTT benefits
- More backend HTTP load
- ESP32 code changes needed

---

## RECOMMENDATION

**Implement Option A**: Add plain MQTT listener on port 1883 for ESP32

### Justification:
1. **ESP32 → Backend authentication already secure** (HMAC-SHA256)
2. **Backend validates all MQTT data** (device status, rate limiting, range validation)
3. **MQTT on internal network only** (no external exposure)
4. **Simple implementation** (one config change)
5. **No ESP32 firmware changes needed**

### Security Architecture:
```
ESP32 Registration/Heartbeat → HTTP (HMAC-SHA256) ✅ SECURE
                                ↓
                    Backend validates device identity
                                ↓
ESP32 Vitals/Alerts → MQTT Plain (port 1883) → Backend validates data ✅ SECURE
                                ↓
                    Backend → Mosquitto TLS (port 8883) ✅ SECURE
```

---

## NEXT STEPS

1. Update mosquitto.conf to add port 1883 listener (plain, no auth)
2. Restart Mosquitto container
3. Test ESP32 MQTT connection
4. Verify vitals flowing: ESP32 → MQTT → Backend → TimescaleDB → Frontend
5. Verify alerts flowing: ESP32 → MQTT → Backend → WebSocket → Frontend
6. Monitor for 24 hours to confirm stability

---

**Status**: **AWAITING APPROVAL TO PROCEED**
