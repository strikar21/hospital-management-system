# Waveform Calibration Root Cause - FOUND

**Date**: 2025-11-04
**Issue**: Waveform calibration commands never reach ESP32 watch
**Status**: ✅ ROOT CAUSE IDENTIFIED

---

## Problem Summary

When opening the ECG Viewer page, the waveform calibration request is sent **before WebSocket is connected**, so the message never reaches the backend or ESP32.

---

## Evidence

### Frontend Logs (SMOKING GUN):
```
Cannot request waveform calibration - WebSocket not connected
requestWaveformCalibration @ bundle.js:102672
```

This message appears in the console when trying to open the ECG Viewer.

### Backend Logs:
```
2025-11-04 23:49:41,663 - app.api.v1.websocket - INFO - 🟢 RAW WebSocket data received from connecec6ccc: {"type":"ping"}
2025-11-04 23:49:41,663 - app.api.v1.websocket - INFO - 🟢 Parsed WebSocket message from connecec6ccc: type=ping, keys=['type']
```

Backend is receiving WebSocket `ping` messages, but **NO** `subscribePatient` messages with `triggerWaveformCalibration: true`.

### What's Happening:

1. ❌ User clicks on patient → ECG Viewer opens
2. ❌ `useECGViewer` hook tries to subscribe with `triggerWaveformCalibration: true`
3. ❌ WebSocketService.subscribe() is called
4. ❌ WebSocket is **NOT YET CONNECTED**
5. ❌ Code hits this block in [WebSocketService.ts:260](hospital-display-app/src/services/WebSocketService.ts#L260):
   ```typescript
   private requestWaveformCalibration(patientId: string): void {
     if (!this.isConnected()) {
       console.warn('Cannot request waveform calibration - WebSocket not connected');
       return;  // <-- MESSAGE NEVER SENT!
     }
   ```
6. ❌ Message is **silently dropped**, never reaches backend
7. ❌ ESP32 never receives MQTT command

---

## Root Cause

**WebSocketService** sends calibration requests immediately, but WebSocket connection may not be established yet.

**File**: [hospital-display-app/src/services/WebSocketService.ts](hospital-display-app/src/services/WebSocketService.ts)

**Problem Code** (lines 245-262):
```typescript
public subscribe(patientId: string, triggerWaveformCalibration?: boolean): void {
  if (triggerWaveformCalibration) {
    this.requestWaveformCalibration(patientId);  // <-- Called immediately
  }
  // ... rest of subscription logic
}

private requestWaveformCalibration(patientId: string): void {
  if (!this.isConnected()) {
    console.warn('Cannot request waveform calibration - WebSocket not connected');
    return;  // <-- DROPS THE REQUEST!
  }

  const message = {
    type: 'subscribePatient',
    patientId,
    triggerWaveformCalibration: true
  };

  this.ws?.send(JSON.stringify(message));
}
```

**Why This Happens**:
- WebSocket connection is asynchronous
- Page load → WebSocket starts connecting → Components render → `useECGViewer` subscribes
- If subscription happens **before** WebSocket `onopen` fires, message is dropped

---

## Solution

### Option 1: Queue Calibration Requests (RECOMMENDED)

Store calibration requests and send them when WebSocket connects:

```typescript
class WebSocketService {
  private pendingCalibrationRequests: Set<string> = new Set();

  public subscribe(patientId: string, triggerWaveformCalibration?: boolean): void {
    if (triggerWaveformCalibration) {
      this.pendingCalibrationRequests.add(patientId);
      this.requestWaveformCalibration(patientId);
    }
    // ... existing code
  }

  private requestWaveformCalibration(patientId: string): void {
    if (!this.isConnected()) {
      console.log(`📋 Queued calibration request for patient: ${patientId} (will send on connect)`);
      return;  // Will be sent when connection is established
    }

    const message = {
      type: 'subscribePatient',
      patientId,
      triggerWaveformCalibration: true
    };

    this.ws?.send(JSON.stringify(message));
    this.pendingCalibrationRequests.delete(patientId);
    console.log(`🔧 Waveform calibration requested for patient: ${patientId}`);
  }

  private setupWebSocket(): void {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('🔌 WebSocket connection established');
      this.connected = true;

      // Send all pending calibration requests
      for (const patientId of this.pendingCalibrationRequests) {
        this.requestWaveformCalibration(patientId);
      }

      // ... existing resubscribe logic
    };
  }
}
```

**Pros**:
- ✅ Never drops calibration requests
- ✅ Works regardless of connection timing
- ✅ Minimal code changes
- ✅ Consistent with existing queue pattern (line 222-228)

**Cons**:
- None

---

### Option 2: Wait for Connection Before Subscribing

Delay subscription until WebSocket is connected:

```typescript
public async subscribe(patientId: string, triggerWaveformCalibration?: boolean): Promise<void> {
  // Wait for connection (with timeout)
  const maxWait = 5000; // 5 seconds
  const startTime = Date.now();

  while (!this.isConnected() && (Date.now() - startTime) < maxWait) {
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  if (!this.isConnected()) {
    console.warn('WebSocket not connected after 5s - queueing subscription');
  }

  if (triggerWaveformCalibration) {
    this.requestWaveformCalibration(patientId);
  }

  // ... existing subscription logic
}
```

**Pros**:
- ✅ Ensures connection before sending

**Cons**:
- ❌ Makes subscribe() async (breaks existing code)
- ❌ Adds complexity with timeouts
- ❌ Still needs fallback queue logic

---

### Option 3: Retry Failed Calibration Requests

Add retry logic to failed requests:

```typescript
private requestWaveformCalibration(patientId: string, retryCount: number = 0): void {
  if (!this.isConnected()) {
    if (retryCount < 3) {
      console.log(`⏳ WebSocket not connected - retrying calibration in 1s (attempt ${retryCount + 1}/3)`);
      setTimeout(() => this.requestWaveformCalibration(patientId, retryCount + 1), 1000);
    } else {
      console.warn(`❌ Failed to send calibration request after 3 retries`);
    }
    return;
  }

  // ... send message
}
```

**Pros**:
- ✅ Simple to implement

**Cons**:
- ❌ Introduces delays (3 seconds worst case)
- ❌ User may already have navigated away

---

## Recommended Fix: Option 1 (Queue Pattern)

**Why**: Already have queueing for patient subscriptions (line 222-228), just extend it for calibration requests.

**Implementation**:
1. Add `pendingCalibrationRequests` Set to track queued requests
2. Modify `requestWaveformCalibration()` to queue if not connected
3. In `onopen` handler, process all pending calibration requests after resubscribing to patients

**Code Location**: [hospital-display-app/src/services/WebSocketService.ts](hospital-display-app/src/services/WebSocketService.ts)

---

## Files to Modify

### 1. WebSocketService.ts (hospital-display-app/src/services/WebSocketService.ts)

**Add Property** (line ~69):
```typescript
private pendingCalibrationRequests: Set<string> = new Set();
```

**Modify requestWaveformCalibration()** (line ~260):
```typescript
private requestWaveformCalibration(patientId: string): void {
  if (!this.isConnected()) {
    console.log(`📋 Queued calibration request for patient: ${patientId} (will send on connect)`);
    this.pendingCalibrationRequests.add(patientId);
    return;
  }

  const message = {
    type: 'subscribePatient',
    patientId,
    triggerWaveformCalibration: true
  };

  this.ws?.send(JSON.stringify(message));
  this.pendingCalibrationRequests.delete(patientId);
  console.log(`🔧 Waveform calibration requested for patient: ${patientId}`);
}
```

**Modify onopen handler** (line ~88):
```typescript
this.ws.onopen = () => {
  console.log('🔌 WebSocket connection established');
  this.connected = true;

  // Resubscribe to all patients
  for (const patientId of this.subscribedPatients) {
    this.subscribeToPatient(patientId);
  }
  console.log(`📡 Resubscribed to ${this.subscribedPatients.size} patients`);

  // Send all pending calibration requests
  for (const patientId of this.pendingCalibrationRequests) {
    this.requestWaveformCalibration(patientId);
  }

  if (this.pendingCalibrationRequests.size > 0) {
    console.log(`🔧 Sent ${this.pendingCalibrationRequests.size} pending calibration requests`);
  }
};
```

---

## Expected Behavior After Fix

### Before Fix:
```
[User opens ECG Viewer]
Cannot request waveform calibration - WebSocket not connected  ❌
[Message dropped - never reaches backend]
[ESP32 never receives command]
```

### After Fix:
```
[User opens ECG Viewer]
📋 Queued calibration request for patient: 081a5294 (will send on connect)
[... WebSocket connects ...]
🔌 WebSocket connection established
📡 Resubscribed to 1 patients
🔧 Waveform calibration requested for patient: 081a5294-da91-4c74-bb8a-e5062f5851dd
🔧 Sent 1 pending calibration requests

[Backend receives message]
🟢 RAW WebSocket data received: {"type":"subscribePatient","patientId":"081a5294...","triggerWaveformCalibration":true}
📤 Command sent to fit-00001: {'command': 'waveformCalibrate', ...}

[ESP32 receives MQTT command]
🔔 MQTT CALLBACK TRIGGERED!
📨 MQTT Message: hospital/devices/fit-00001/commands -> {"command":"waveformCalibrate",...}
✅ Topic ends with /commands - processing command
🎯 Command parsed: type='waveformCalibrate', id='...'
🔧 Handling waveformCalibrate command
🔧 Waveform calibration command received
✅ Waveform calibration complete
```

---

## Testing Plan

1. **Apply the fix** to WebSocketService.ts
2. **Refresh the frontend** (Ctrl+Shift+R)
3. **Open browser console**
4. **Click on a patient** to open ECG Viewer
5. **Verify logs** show:
   - `📋 Queued calibration request for patient: ...`
   - `🔌 WebSocket connection established`
   - `🔧 Waveform calibration requested for patient: ...`
6. **Check backend logs** for:
   - `🟢 RAW WebSocket data received: {"type":"subscribePatient",...,"triggerWaveformCalibration":true}`
   - `📤 Command sent to fit-00001: {'command': 'waveformCalibrate', ...}`
7. **Check ESP32 Serial Monitor** for:
   - `🔔 MQTT CALLBACK TRIGGERED!`
   - `🎯 Command parsed: type='waveformCalibrate'`
   - `🔧 Waveform calibration command received`
   - `✅ Waveform calibration complete`

---

## Status

- ✅ Root cause identified: WebSocket not connected when calibration requested
- ✅ Solution designed: Queue pending calibration requests
- ⏳ Fix implementation: Ready to apply
- ⏳ Testing: Pending

---

**Next Action**: Apply the fix to WebSocketService.ts and test end-to-end flow.
