# Calibration Pulse Flow - Complete Audit

## Issue
"now calibration pulse request doesnt come to the watch ever"

## Calibration Flow Architecture

### Expected Flow:
```
Frontend (ECG Viewer)
  → WebSocket (triggerCalibration=true)
  → Backend WebSocket Handler
  → Backend _triggerDeviceCalibration()
  → MQTT Service publishCommand()
  → MQTT Broker (hospital/devices/{deviceId}/commands)
  → ESP32 (subscribed to commands topic)
  → ESP32 handleCalibrationCommand()
  → Simulator generates calibration pulse
```

## Code Audit Results

### ✅ 1. Frontend - Calibration Trigger

**File:** `hospital-display-app/src/hooks/useECGViewer.ts:317`

```typescript
}, patient.id, true); // ← ADD patientId and triggerCalibration=true for calibration pulse
```

**Status:** ✅ Frontend passes `triggerCalibration=true` when subscribing to waveform data

---

### ✅ 2. Frontend - WebSocket Service

**File:** `hospital-display-app/src/services/WebSocketService.ts:163-180`

```typescript
public subscribe(subscriberId: string, callback: (message: WebSocketMessage) => void,
                 patientId?: string, triggerCalibration?: boolean): void {
  // ...
  if (patientId && !this.subscribedPatients.has(patientId)) {
    this.subscribeToPatient(patientId, triggerCalibration);
  } else if (patientId && triggerCalibration) {
    // Already subscribed, but still send calibration trigger
    this.requestCalibration(patientId);
  }
}

private subscribeToPatient(patientId: string, triggerCalibration?: boolean): void {
  const message = {
    type: 'subscribePatient',
    patientId,
    ...(triggerCalibration && { triggerCalibration: true })
  };
  this.ws?.send(JSON.stringify(message));
}
```

**Status:** ✅ WebSocket service sends `triggerCalibration: true` to backend

---

### ✅ 3. Backend - WebSocket Handler

**File:** `hospital-backend/app/api/v1/websocket.py:93-120`

```python
if messageType == 'subscribePatient':
    patientId = message.get('patientId')
    triggerCalibration = message.get('triggerCalibration', False)  # ✅ NEW: ECG viewer can request calibration

    if patientId:
        # ... subscription logic ...

        # ✅ NEW: Trigger calibration pulse on ECG viewer open
        if success and triggerCalibration:
            try:
                deviceId = await _getDeviceForPatient(patientId)
                if deviceId:
                    await _triggerDeviceCalibration(deviceId, patientId)
                    logger.info(f"🔧 Calibration triggered for device {deviceId} (patient {patientId})")
            except Exception as e:
                logger.warning(f"⚠️  Could not trigger calibration for patient {patientId}: {e}")
```

**Status:** ✅ Backend receives `triggerCalibration` and calls helper functions

---

### ✅ 4. Backend - Get Device for Patient

**File:** `hospital-backend/app/api/v1/websocket.py:246-259`

```python
async def _getDeviceForPatient(patientId: str) -> str | None:
    """Get device ID assigned to a patient"""
    async with getDbConnection() as conn:
        result = await fetchOne(conn, """
            SELECT d.id as deviceId
            FROM deviceassignments da
            JOIN devices d ON da."deviceId" = d.id
            WHERE da."patientId" = $1
            AND da."assignedAt" IS NOT NULL
            AND da."unassignedAt" IS NULL
            ORDER BY da."assignedAt" DESC
            LIMIT 1
        """, (patientId,))
        return result['deviceid'] if result else None
```

**Status:** ✅ Query looks correct - should find `fit-00001` for patient `081a5294-da91-4c74-bb8a-e5062f5851dd`

**Actual Data:**
- Device: `fit-00001`
- Patient: `081a5294-da91-4c74-bb8a-e5062f5851dd`
- Status: `assigned` (active assignment)

---

### ✅ 5. Backend - Trigger Device Calibration

**File:** `hospital-backend/app/api/v1/websocket.py:261-276`

```python
async def _triggerDeviceCalibration(deviceId: str, patientId: str) -> None:
    """Send MQTT calibration command to device"""
    from ...services.mqtt_service import mqttService
    from datetime import datetime, timezone

    commandId = str(uuid.uuid4())
    command = {
        'command': 'calibrate',
        'commandId': commandId,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'triggeredBy': 'ecgViewerOpen',
        'patientId': patientId
    }

    await mqttService.publishCommand(deviceId, command)
    logger.info(f"📤 Calibration command sent to device {deviceId} (commandId: {commandId})")
```

**Status:** ✅ Creates proper command structure and calls MQTT service

---

### ✅ 6. Backend - MQTT Service

**File:** `hospital-backend/app/services/mqtt_service.py:176-191`

```python
async def publishCommand(self, deviceId: str, command: Dict[str, Any]) -> bool:
    """Send command to specific ESP32 device"""
    if not self.client or not self.connected:
        logger.warning("⚠️ MQTT not connected - cannot send command")
        return False

    topic = f"hospital/devices/{deviceId}/commands"
    payload = json.dumps(command)

    try:
        result = self.client.publish(topic, payload, qos=1)  # QoS 1 for reliability
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"📤 Command sent to {deviceId}: {command}")
            return True
        else:
            logger.error(f"❌ Failed to send command to {deviceId}")
```

**Status:** ✅ Publishes to correct topic with QoS 1

**Expected Topic:** `hospital/devices/fit-00001/commands`

---

### ✅ 7. ESP32 - MQTT Subscription

**File:** `esp32_hospital_watch_complete.ino:1647-1649`

```cpp
String commandTopic = "hospital/devices/" + deviceId + "/commands";
mqttClient.subscribe(commandTopic.c_str());
Serial.println("📡 Subscribed to: " + commandTopic);
```

**Status:** ✅ ESP32 subscribes to commands topic on connection

**Expected Topic:** `hospital/devices/fit-00001/commands`

---

### ✅ 8. ESP32 - MQTT Message Handler

**File:** `esp32_hospital_watch_complete.ino:1664-1702`

```cpp
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  Serial.println("📨 MQTT Message: " + String(topic) + " -> " + message);

  if (String(topic).endsWith("/commands")) {
    lastCommandReceivedAt = millis();
    deviceUnresponsiveAlertSent = false;

    JsonDocument doc;
    if (deserializeJson(doc, message) == DeserializationError::Ok) {
      String commandType = doc["command"].as<String>();
      String commandId = doc["commandId"].as<String>();

      if (commandType == "ping") {
        handlePingCommand(commandId);
      } else if (commandType == "calibrate") {
        handleCalibrationCommand(commandId);
      } else {
        sendCommandAck(commandId, false, "Unknown command: " + commandType);
      }
    }
  }
}
```

**Status:** ✅ ESP32 handles "calibrate" command and calls `handleCalibrationCommand()`

---

### ✅ 9. ESP32 - Calibration Handler

**File:** `esp32_hospital_watch_complete.ino:941-974`

```cpp
void handleCalibrationCommand(String commandId) {
  Serial.println("🔧 Calibration command received");

  // ✅ Trigger physiological simulator calibration pulse (3000ms: 1000ms head + 1000ms pulse + 1000ms tail)
  simulator.startCalibrationPulse();

  // Flash LED to indicate calibration in progress (non-blocking pattern)
  for (int i = 0; i < 3; i++) {
    digitalWrite(2, HIGH);
    delay(100);
    digitalWrite(2, LOW);
    delay(100);
  }

  // Wait for calibration pulse to complete (3000ms + margin)
  delay(3100);

  // Publish completion notification
  String topic = "hospital/devices/" + deviceId + "/calibration_complete";
  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();
  doc["success"] = true;
  doc["commandId"] = commandId;

  String payload;
  serializeJson(doc, payload);
  publishWithRetry(topic.c_str(), payload.c_str());

  calibrationDue = false;
  sendCommandAck(commandId, true, "Calibration pulse sent to all ECG leads (3000ms)");

  Serial.println("✅ Calibration pulse complete - waveforms will contain calibration data");
  digitalWrite(2, HIGH);
}
```

**Status:** ✅ ESP32 triggers simulator calibration pulse and sends acknowledgment

---

## Potential Issues Found

### ❌ ISSUE 1: Device ID Mismatch

**Backend expects:** `fit-00001` (from database)
**ESP32 device ID:** Unknown - need to check what ESP32 is using

**Check:** ESP32 must be using device ID `fit-00001` to receive commands on the right topic

**How to verify:**
1. Check ESP32 Serial Monitor - look for "Device ID: XXX" on boot
2. Check MQTT subscription - look for "📡 Subscribed to: hospital/devices/XXX/commands"

---

### ❌ ISSUE 2: MQTT Connection Status

**Check:** Is ESP32 actually connected to MQTT broker?

**How to verify:**
1. Check ESP32 Serial Monitor - look for "✅ MQTT Connected"
2. Check backend MQTT service - look for connection log
3. Check Mosquitto broker status

---

### ❌ ISSUE 3: Backend MQTT Service Not Connected

**Check:** Is backend MQTT service actually connected to broker?

**File:** `hospital-backend/app/services/mqtt_service.py:178-180`

```python
if not self.client or not self.connected:
    logger.warning("⚠️ MQTT not connected - cannot send command")
    return False
```

**How to verify:**
1. Check backend logs for MQTT connection status
2. Check if `mqttService.connected` is True
3. Check if backend subscribed to topics successfully

---

## Diagnostic Steps

### Step 1: Check ESP32 Device ID
```bash
# Check ESP32 Serial Monitor output
# Look for: "Device ID: XXX"
```

### Step 2: Check ESP32 MQTT Connection
```bash
# Check ESP32 Serial Monitor output
# Look for: "✅ MQTT Connected"
# Look for: "📡 Subscribed to: hospital/devices/XXX/commands"
```

### Step 3: Check Backend MQTT Connection
```bash
# Check backend logs
# Look for: "✅ MQTT Connected" or "⚠️ MQTT not connected"
```

### Step 4: Test Calibration Manually
```bash
# Publish test command to MQTT broker
mosquitto_pub -h localhost -p 8883 \
  --cafile mosquitto/certs/ca.crt \
  --cert mosquitto/certs/client.crt \
  --key mosquitto/certs/client.key \
  -t "hospital/devices/fit-00001/commands" \
  -m '{"command":"calibrate","commandId":"test-123","timestamp":"2025-01-04T00:00:00Z"}'
```

### Step 5: Monitor MQTT Traffic
```bash
# Subscribe to all device topics
mosquitto_sub -h localhost -p 8883 \
  --cafile mosquitto/certs/ca.crt \
  --cert mosquitto/certs/client.crt \
  --key mosquitto/certs/client.key \
  -t "hospital/devices/#" \
  -v
```

## Summary

**Code Architecture:** ✅ All code is correct and follows proper flow

**Potential Root Causes:**
1. ❌ ESP32 device ID doesn't match database device ID (`fit-00001`)
2. ❌ ESP32 not connected to MQTT broker
3. ❌ Backend MQTT service not connected to broker
4. ❌ Network/firewall blocking MQTT traffic

**Next Steps:**
1. Check ESP32 Serial Monitor for device ID and MQTT connection status
2. Check backend logs for MQTT connection status
3. Test manual MQTT publish to verify broker connectivity
4. Monitor MQTT traffic to see if commands are being sent
