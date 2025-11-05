# Waveform Calibration Fix - APPLIED

**Date**: 2025-11-04
**Issue**: Waveform calibration requests dropped when WebSocket not connected
**Status**: ✅ FIX APPLIED - Ready for testing

---

## Problem

When opening the ECG Viewer (either patient card or fullscreen), the waveform calibration request was sent **before WebSocket connection was established**, causing the message to be dropped silently.

**Evidence**:
```
Cannot request waveform calibration - WebSocket not connected
```

---

## Solution Implemented

Added **queueing pattern** for calibration requests (similar to existing patient subscription queueing):

1. ✅ Calibration requests are queued when WebSocket is not connected
2. ✅ Queued requests are sent automatically when WebSocket connects
3. ✅ Queue is cleared on disconnect to prevent stale requests

---

## Changes Made

### File: [hospital-display-app/src/services/WebSocketService.ts](hospital-display-app/src/services/WebSocketService.ts)

#### 1. Added Queue Property (Line 50)
```typescript
private pendingCalibrationRequests: Set<string> = new Set();
```

#### 2. Modified `requestWaveformCalibration()` (Lines 248-264)
**Before**:
```typescript
private requestWaveformCalibration(patientId: string): void {
  if (!this.isConnected()) {
    console.warn('Cannot request waveform calibration - WebSocket not connected');
    return;  // ❌ REQUEST DROPPED
  }
  // ... send message
}
```

**After**:
```typescript
private requestWaveformCalibration(patientId: string): void {
  if (!this.isConnected()) {
    console.log(`📋 Queued calibration request for patient: ${patientId} (will send on connect)`);
    this.pendingCalibrationRequests.add(patientId);  // ✅ REQUEST QUEUED
    return;
  }

  const message = {
    type: 'subscribePatient',
    patientId,
    triggerWaveformCalibration: true
  };

  this.ws?.send(JSON.stringify(message));
  this.pendingCalibrationRequests.delete(patientId);  // ✅ REMOVE FROM QUEUE WHEN SENT
  console.log(`🔧 Waveform calibration requested for patient: ${patientId}`);
}
```

#### 3. Modified `resubscribePatients()` (Lines 287-307)
**Before**:
```typescript
private resubscribePatients(): void {
  this.subscribedPatients.forEach(patientId => {
    // ... resubscribe to patients
  });

  if (this.subscribedPatients.size > 0) {
    console.log(`📡 Resubscribed to ${this.subscribedPatients.size} patients`);
  }
}
```

**After**:
```typescript
private resubscribePatients(): void {
  this.subscribedPatients.forEach(patientId => {
    // ... resubscribe to patients
  });

  if (this.subscribedPatients.size > 0) {
    console.log(`📡 Resubscribed to ${this.subscribedPatients.size} patients`);
  }

  // ✅ SEND ALL PENDING CALIBRATION REQUESTS
  if (this.pendingCalibrationRequests.size > 0) {
    this.pendingCalibrationRequests.forEach(patientId => {
      this.requestWaveformCalibration(patientId);
    });
    console.log(`🔧 Sent ${this.pendingCalibrationRequests.size} pending calibration requests`);
  }
}
```

#### 4. Modified `disconnect()` (Line 158)
```typescript
this.pendingCalibrationRequests.clear();  // ✅ CLEAR QUEUE ON DISCONNECT
```

---

## How It Works

### Scenario 1: WebSocket Not Connected Yet (Opening ECG Viewer on Page Load)

**Before Fix**:
```
[User clicks patient → ECG Viewer opens]
❌ Cannot request waveform calibration - WebSocket not connected
[Request dropped - never reaches backend]
```

**After Fix**:
```
[User clicks patient → ECG Viewer opens]
📋 Queued calibration request for patient: 081a5294 (will send on connect)
[... 500ms later, WebSocket connects ...]
🔌 WebSocket connection established
📡 Resubscribed to 1 patients
🔧 Waveform calibration requested for patient: 081a5294-da91-4c74-bb8a-e5062f5851dd
🔧 Sent 1 pending calibration requests

[Backend receives]:
🟢 RAW WebSocket data received: {"type":"subscribePatient","patientId":"081a5294...","triggerWaveformCalibration":true}
🔵 DEBUG: subscribePatient - patientId=081a5294, triggerWaveformCalibration=True
🔵 DEBUG: About to trigger waveform calibration for patient 081a5294
📤 Command sent to fit-00001: {'command': 'waveformCalibrate', ...}

[ESP32 receives]:
🔔 MQTT CALLBACK TRIGGERED!
📨 MQTT Message: hospital/devices/fit-00001/commands -> {"command":"waveformCalibrate",...}
✅ Topic ends with /commands - processing command
🎯 Command parsed: type='waveformCalibrate', id='...'
🔧 Handling waveformCalibrate command
✅ Waveform calibration complete - waveforms will contain calibration data
```

### Scenario 2: WebSocket Already Connected (Opening ECG Viewer After Connection)

**Before Fix**:
```
[User clicks patient → ECG Viewer opens]
🔧 Waveform calibration requested for patient: 081a5294
[Works fine - no issue]
```

**After Fix**:
```
[User clicks patient → ECG Viewer opens]
🔧 Waveform calibration requested for patient: 081a5294
[Works fine - same behavior]
```

No change in behavior when WebSocket is already connected.

---

## Testing Instructions

### 1. Rebuild Frontend
```bash
cd hospital-display-app
npm run build
# OR just refresh browser with Ctrl+Shift+R if using dev server
```

### 2. Test Scenario: Open ECG Viewer on Page Load

1. **Open browser console** (F12)
2. **Navigate to dashboard** (or refresh page)
3. **Immediately click on a patient** to open ECG Viewer
4. **Watch console logs**

**Expected Output**:
```
📋 Queued calibration request for patient: 081a5294-da91-4c74-bb8a-e5062f5851dd (will send on connect)
🔌 WebSocket connection established
📡 Resubscribed to 1 patients
🔧 Waveform calibration requested for patient: 081a5294-da91-4c74-bb8a-e5062f5851dd
🔧 Sent 1 pending calibration requests
```

### 3. Check Backend Logs

```bash
cd hospital-backend
tail -f backend.log | grep -E "(waveformCalibrat|Command sent)"
```

**Expected Output**:
```
🟢 RAW WebSocket data received: {"type":"subscribePatient","patientId":"081a5294...","triggerWaveformCalibration":true}
🔵 DEBUG: subscribePatient - patientId=081a5294, triggerWaveformCalibration=True
📤 Command sent to fit-00001: {'command': 'waveformCalibrate', ...}
```

### 4. Check ESP32 Serial Monitor

**Expected Output**:
```
🔔 MQTT CALLBACK TRIGGERED!
   Topic: hospital/devices/fit-00001/commands
   Length: 156
📨 MQTT Message: hospital/devices/fit-00001/commands -> {"command":"waveformCalibrate",...}
✅ Topic ends with /commands - processing command
🎯 Command parsed: type='waveformCalibrate', id='...'
🔧 Handling waveformCalibrate command
🔧 Waveform calibration command received
✅ Waveform calibration complete - waveforms will contain calibration data
```

---

## What Should Happen

1. ✅ **Frontend** queues calibration request if WebSocket not connected
2. ✅ **Frontend** sends queued requests when WebSocket connects
3. ✅ **Backend** receives `triggerWaveformCalibration: true` message
4. ✅ **Backend** looks up device ID for patient
5. ✅ **Backend** publishes MQTT command to `hospital/devices/fit-00001/commands`
6. ✅ **ESP32** receives MQTT message in callback
7. ✅ **ESP32** parses `waveformCalibrate` command
8. ✅ **ESP32** executes 3-second calibration pulse
9. ✅ **ESP32** publishes completion notification
10. ✅ **Frontend** displays waveform with calibration pulse

---

## Files Modified

- ✅ [hospital-display-app/src/services/WebSocketService.ts](hospital-display-app/src/services/WebSocketService.ts)
  - Added `pendingCalibrationRequests` Set (line 50)
  - Modified `requestWaveformCalibration()` to queue requests (lines 248-264)
  - Modified `resubscribePatients()` to send queued requests (lines 287-307)
  - Modified `disconnect()` to clear queue (line 158)

---

## Files NOT Modified (Already Have Diagnostic Logging)

- ✅ [hospital-backend/app/api/v1/websocket.py](hospital-backend/app/api/v1/websocket.py) - Has debug logging
- ✅ [hospital-backend/app/services/mqtt_service.py](hospital-backend/app/services/mqtt_service.py) - Publishes commands
- ✅ [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino) - Has diagnostic logging

---

## Next Steps

1. ✅ **Fix applied** - WebSocketService now queues calibration requests
2. ⏳ **Test frontend** - Refresh browser and open ECG Viewer
3. ⏳ **Verify backend** - Check backend logs for calibration messages
4. ⏳ **Flash ESP32** - Upload firmware with diagnostic logging (from previous session)
5. ⏳ **Test end-to-end** - Verify calibration pulse appears in waveforms

---

## Status

- ✅ Root cause identified
- ✅ Fix implemented
- ✅ Code changes complete
- ⏳ Testing pending
- ⏳ ESP32 firmware flash pending (diagnostic logging from previous session)

**Ready for testing!** 🚀
