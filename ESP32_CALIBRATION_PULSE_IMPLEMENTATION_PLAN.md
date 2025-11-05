# ESP32 Calibration Pulse Implementation Plan

## Current State Analysis

### Frontend (Current)
- **Location**: [ECGViewerContainer.tsx:48-80](hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx#L48-L80)
- **Implementation**: Frontend generates calibration pulse on component mount
- **Format**: 100 head samples → 100 pulse samples (1mV) → 100 tail samples = 300 total samples
- **Timing**: 600ms total (200ms + 200ms + 200ms)
- **Value**: Hardcoded ADC values (8388608 baseline, 8488608 for 1mV pulse)

### ESP32 (Current)
- **PhysiologicalSimulator.h:72-73**: Functions declared but NOT implemented
  - `void startCalibrationPulse()`
  - `bool isCalibrationActive()`
- **State variables exist**: `calibrationActive`, `calibrationStartTime`, `calibrationDuration`
- **Initialized**: calibrationDuration = 600ms

### Backend (Current)
- **esp32_hospital_watch_complete.ino:901-922**: `handleCalibrationCommand()` exists
  - Responds to MQTT command `{"command": "calibrate"}`
  - Current implementation: Just flashes LED, no waveform calibration
  - Publishes to `hospital/devices/{deviceId}/calibration_complete`

## User Request

> "remove the calibration thinng temporaritly. tell me what to do / change to get the same calibration thing from watch when i open ecg window?"

**Interpretation**:
1. Remove frontend-generated calibration pulse
2. Make ESP32 send a real calibration pulse when ECG viewer opens
3. ESP32 calibration pulse should flow through the normal waveform stream

## Implementation Options

### Option A: Automatic Calibration (RECOMMENDED)
**Trigger**: Backend detects new WebSocket subscription to waveformStream messages
**Flow**:
1. User opens ECG viewer → Frontend subscribes to WebSocket
2. Backend detects new subscriber for patientId
3. Backend sends MQTT command to ESP32: `{"command": "startCalibration", "commandId": "..."}`
4. ESP32 starts calibration pulse in PhysiologicalSimulator
5. Next waveform batch includes calibration samples
6. Frontend receives calibration via normal waveform stream
7. Calibration displays on canvas

**Pros**:
- Fully automatic, no user action needed
- Tests end-to-end data flow (ESP32 → MQTT → Backend → WebSocket → Frontend)
- Verifies watch is responding
- Medical-grade workflow

**Cons**:
- Requires backend modification to detect WebSocket subscriptions
- More complex implementation

### Option B: Manual Calibration Command
**Trigger**: User clicks "Calibrate" button in ECG viewer header
**Flow**:
1. User clicks button → Frontend calls `/api/v1/device/calibrate/{deviceId}`
2. Backend sends MQTT command to ESP32
3. ESP32 generates calibration pulse
4. Pulse flows through normal stream
5. Frontend displays it

**Pros**:
- Simpler backend logic
- User has explicit control
- Easy to add UI button

**Cons**:
- Requires manual user action
- Extra UI complexity

### Option C: On-Demand via Existing Command
**Trigger**: Use existing `handleCalibrationCommand()` in ESP32
**Flow**:
1. Backend/Frontend triggers existing calibrate command
2. ESP32 receives via MQTT
3. PhysiologicalSimulator generates pulse
4. Streams normally

**Pros**:
- Reuses existing infrastructure
- Minimal new code

**Cons**:
- Still requires backend trigger

## Recommended Solution: **Option A (Automatic)**

### Step-by-Step Implementation

#### Phase 1: ESP32 - Implement Calibration Pulse Generation

**File**: `esp32_hospital_watch_complete/PhysiologicalSimulator.cpp`

Add two functions:

```cpp
// ====================================
// CALIBRATION PULSE (NEW)
// ====================================

void PhysiologicalSimulator::startCalibrationPulse() {
    calibrationActive = true;
    calibrationStartTime = millis();
    Serial.println("🔧 Calibration pulse started (600ms: 200ms head + 200ms pulse + 200ms tail)");
}

bool PhysiologicalSimulator::isCalibrationActive() {
    if (!calibrationActive) return false;

    // Check if 600ms has elapsed
    unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);
    if (elapsed >= calibrationDuration) {
        calibrationActive = false;
        Serial.println("✅ Calibration pulse complete");
        return false;
    }

    return true;
}
```

**Modify** `generateECGSample()` to check calibration state:

```cpp
void PhysiologicalSimulator::generateECGSample(int lead, int32_t& sample) {
    // ✅ NEW: Check if calibration pulse is active
    if (isCalibrationActive()) {
        unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);

        // Medical standard: 200ms head (flat) → 200ms pulse (1mV) → 200ms tail (flat)
        if (elapsed < 200) {
            // Head: baseline (0mV)
            sample = 8388608;  // ADC midpoint
        } else if (elapsed < 400) {
            // Pulse: 1.0mV square wave
            sample = 8388608 + 100000;  // 1mV above baseline
        } else {
            // Tail: baseline (0mV)
            sample = 8388608;
        }

        // Update ECG timing (500 Hz = 2ms per sample)
        ecgCycleTime += 2.0;
        return;  // Skip normal ECG generation during calibration
    }

    // Normal ECG generation follows...
    // (existing code continues here)
```

#### Phase 2: ESP32 - Wire Command Handler

**File**: `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:901-922`

**Modify** `handleCalibrationCommand()`:

```cpp
void handleCalibrationCommand(String commandId) {
  Serial.println("🔧 Calibration command received");

  // ✅ NEW: Trigger physiological simulator calibration pulse
  simulator.startCalibrationPulse();

  // Flash LED to indicate calibration in progress
  for (int i = 0; i < 3; i++) {
    digitalWrite(2, HIGH);
    delay(100);
    digitalWrite(2, LOW);
    delay(100);
  }

  // Wait for calibration to complete (600ms)
  delay(700);  // Extra 100ms margin

  // Publish completion
  String topic = "hospital/devices/" + deviceId + "/calibration_complete";
  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();
  doc["success"] = true;

  String payload;
  serializeJson(doc, payload);
  publishWithRetry(topic.c_str(), payload.c_str());

  calibrationDue = false;
  sendCommandAck(commandId, true, "Calibration complete");
  Serial.println("✅ Calibration pulse sent to all leads");
}
```

#### Phase 3: Backend - Add WebSocket Subscription Hook

**File**: `hospital-backend/app/api/v1/websocket.py`

**Add** calibration trigger on new ECG viewer connection:

```python
# In websocket.py connection handler
async def websocket_endpoint(websocket: WebSocket, patient_id: str):
    await websocket_manager.connect(websocket, patient_id)

    # ✅ NEW: Trigger calibration pulse when ECG viewer opens
    try:
        device = await get_device_for_patient(patient_id)
        if device:
            await trigger_device_calibration(device.device_id)
    except Exception as e:
        logger.warning(f"Could not trigger calibration: {e}")

    # Rest of connection logic...
```

**Add** new function to send MQTT command:

```python
async def trigger_device_calibration(device_id: str):
    """Send calibration command to device via MQTT"""
    from app.services.mqtt_service import mqtt_service

    command_id = str(uuid.uuid4())
    topic = f"hospital/devices/{device_id}/command"
    payload = {
        "command": "calibrate",
        "commandId": command_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    mqtt_service.publish(topic, json.dumps(payload))
    logger.info(f"📤 Calibration command sent to device {device_id}")
```

#### Phase 4: Frontend - Remove Calibration Pulse Generation

**File**: [ECGViewerContainer.tsx:48-80](hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx#L48-L80)

**Option 1**: Comment out calibration effect:

```typescript
// TEMPORARILY DISABLED - Calibration now comes from ESP32
/*
useEffect(() => {
  if (isECGMode && !hasPulseAdded.current.every(Boolean)) {
    // ... calibration code ...
  }
}, [isECGMode, leads, dataBufferRef, patient.id]);
*/
```

**Option 2**: Remove entire effect block (lines 48-81)

## Testing Plan

### Phase 1 Test: ESP32 Calibration Generation
1. Flash ESP32 with new firmware
2. Send manual MQTT command: `mosquitto_pub -h 192.168.0.113 -p 8883 -t "hospital/devices/{deviceId}/command" -m '{"command":"calibrate","commandId":"test-1"}'`
3. Watch serial monitor for:
   - `🔧 Calibration pulse started (600ms...)`
   - Waveform stream messages containing calibration data
   - `✅ Calibration pulse complete`
4. **Expected**: Waveform batches show 0mV → 1mV → 0mV pattern

### Phase 2 Test: End-to-End Flow
1. Start backend, ensure MQTT connected
2. Open ECG viewer for assigned patient
3. **Expected**:
   - Backend sends MQTT calibration command
   - ESP32 generates calibration pulse
   - Frontend receives via WebSocket waveformStream
   - Canvas shows calibration pulse (1mV square wave for 200ms)

### Phase 3 Test: Verify Data Flow
1. Check browser console: `🌐 WebSocket message received: waveformStream`
2. Verify samples: First 100 samples ≈ 8388608 (baseline), next 100 ≈ 8488608 (1mV), last 100 ≈ 8388608
3. **Expected**: Calibration pulse visible on ALL 12 leads simultaneously

## Rollback Plan

If calibration from ESP32 doesn't work:
1. Uncomment frontend calibration code in ECGViewerContainer.tsx
2. System returns to previous working state
3. Debug ESP32 → MQTT → Backend → WebSocket flow

## Benefits of ESP32 Calibration

1. **End-to-End Validation**: Tests full data pipeline
2. **Hardware Simulation**: Mimics real medical device behavior
3. **Automatic Trigger**: No user action needed
4. **Medical Standard**: 600ms calibration pulse format
5. **All Leads**: Calibration appears on all 12 ECG leads simultaneously
6. **Realistic Timing**: Generated at 500Hz like actual ECG data

---

## What You Need to Do

### Immediate Steps:
1. **Decide**: Option A (automatic) or Option B (manual button)?
2. **Frontend**: Comment out or remove calibration generation in ECGViewerContainer.tsx
3. **ESP32**: Implement `startCalibrationPulse()` and `isCalibrationActive()` functions
4. **ESP32**: Modify `generateECGSample()` to check calibration state
5. **ESP32**: Update `handleCalibrationCommand()` to trigger simulator
6. **Backend** (if Option A): Add WebSocket subscription hook to trigger calibration
7. **Test**: Verify calibration pulse flows through waveform stream

### Questions to Answer:
1. Do you want **automatic calibration** when ECG viewer opens (Option A)?
2. Or **manual calibration** via button click (Option B)?
3. Should calibration pulse be 600ms (medical standard) or different duration?
4. Should calibration apply to **all leads** or just selected lead?

---
**Ready to proceed?** Let me know which option you prefer and I'll implement it.
