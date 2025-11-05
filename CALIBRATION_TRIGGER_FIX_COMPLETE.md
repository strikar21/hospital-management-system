# Calibration Trigger Fix - COMPLETE

## Problem
Calibration wasn't triggering when opening ECG viewer because:
1. Patient was already subscribed from dashboard view
2. `subscribeToPatient()` had check: `if (!this.subscribedPatients.has(patientId))`
3. So when ECG viewer opened, it skipped sending the calibration trigger

## Solution Implemented

### Frontend Changes

#### 1. WebSocketService.ts
**Modified `subscribe()` method** to accept `triggerCalibration` parameter:
```typescript
public subscribe(subscriberId: string, callback: (message: WebSocketMessage) => void, patientId?: string, triggerCalibration?: boolean): void {
    // ... existing code ...

    if (patientId && !this.subscribedPatients.has(patientId)) {
        this.subscribeToPatient(patientId, triggerCalibration);
    } else if (patientId && triggerCalibration) {
        // ✅ NEW: Already subscribed, but still send calibration trigger
        this.requestCalibration(patientId);
    }
}
```

**Modified `subscribeToPatient()` to accept trigger parameter**:
```typescript
private subscribeToPatient(patientId: string, triggerCalibration?: boolean): void {
    this.subscribedPatients.add(patientId);

    if (!this.isConnected()) {
        console.log(`📋 Queued subscription for patient: ${patientId} (will subscribe on connect)`);
        return;
    }

    const message = {
        type: 'subscribePatient',
        patientId,
        ...(triggerCalibration && { triggerCalibration: true })  // ✅ Only add if true
    };

    this.ws?.send(JSON.stringify(message));
    console.log(`📡 Subscribed to patient updates: ${patientId}${triggerCalibration ? ' (with calibration trigger)' : ''}`);
}
```

**Added `requestCalibration()` method**:
```typescript
private requestCalibration(patientId: string): void {
    if (!this.isConnected()) {
        console.warn('Cannot request calibration - WebSocket not connected');
        return;
    }

    const message = {
        type: 'subscribePatient',
        patientId,
        triggerCalibration: true
    };

    this.ws?.send(JSON.stringify(message));
    console.log(`🔧 Calibration requested for patient: ${patientId}`);
}
```

#### 2. useWebSocket.ts
**Updated hook interface and subscribe function**:
```typescript
interface UseWebSocketReturn {
    subscribe: (callback: (message: WebSocketMessage) => void, patientId?: string, triggerCalibration?: boolean) => string;
    // ... rest ...
}

const subscribe = useCallback((
    callback: (message: WebSocketMessage) => void,
    patientId?: string,
    triggerCalibration?: boolean
): string => {
    const subscriberId = crypto.randomUUID();
    logger.log('🔵 [DEBUG] useWebSocket subscribe() called:', { subscriberId, patientId, triggerCalibration });
    wsService.current.subscribe(subscriberId, callback, patientId, triggerCalibration);
    return subscriberId;
}, []);
```

#### 3. useECGViewer.ts
**Updated WebSocket subscription to pass `triggerCalibration: true`**:
```typescript
const subscriptionId = subscribe((message: any) => {
    // ... message handling ...
}, patient.id, true); // ✅ Pass true for calibration trigger
```

---

## How It Works Now

### Scenario 1: First time viewing patient (not subscribed yet)
1. ECG viewer opens
2. `useECGViewer` calls `subscribe(callback, patientId, true)`
3. `WebSocketService.subscribe()` checks: not in `subscribedPatients` set
4. Calls `subscribeToPatient(patientId, true)`
5. Sends WebSocket message: `{type: 'subscribePatient', patientId: '...', triggerCalibration: true}`
6. Backend receives it → Sends MQTT calibration command to ESP32

### Scenario 2: Already viewing patient on dashboard (already subscribed)
1. ECG viewer opens
2. `useECGViewer` calls `subscribe(callback, patientId, true)`
3. `WebSocketService.subscribe()` checks: **already in `subscribedPatients` set**
4. Goes to `else if` branch: `requestCalibration(patientId)`  ← ✅ **This is the fix!**
5. Sends WebSocket message: `{type: 'subscribePatient', patientId: '...', triggerCalibration: true}`
6. Backend receives it → Sends MQTT calibration command to ESP32

---

## Testing Instructions

### 1. Test from Dashboard View
```
1. Login to http://localhost:3000
2. Navigate to patient card (already subscribed to vitals)
3. Click "ECG Viewer" button
4. Check browser console for: "🔧 Calibration requested for patient: ..."
5. Check backend logs for: "🔧 Calibration triggered for device fit-00001"
```

### 2. Test from Direct ECG Open
```
1. Login to http://localhost:3000
2. Directly open ECG viewer (not from dashboard)
3. Check browser console for: "📡 Subscribed to patient updates: ... (with calibration trigger)"
4. Check backend logs for: "🔧 Calibration triggered for device fit-00001"
```

### 3. Test Multiple Opens
```
1. Open ECG viewer
2. Close it
3. Open again
4. **Expected**: Calibration triggers BOTH times
```

---

## Backend Logs to Watch For

When calibration triggers successfully, you'll see:
```
🔧 Calibration triggered for device fit-00001 (patient 081a5294-da91-4c74-bb8a-e5062f5851dd)
📤 Calibration command sent to device fit-00001 (commandId: ...)
```

---

## ESP32 Firmware Status

⚠️ **ESP32 firmware needs to be flashed** with updated code containing:
- `startCalibrationPulse()` function
- `isCalibrationActive()` function
- Modified `generateECGSample()` for calibration pulse generation

Until firmware is flashed:
- Backend will send MQTT command ✅
- ESP32 will receive command ✅
- But won't generate calibration pulse (old firmware doesn't have the functions) ❌

---

## Files Modified

### Frontend
1. [hospital-display-app/src/services/WebSocketService.ts](hospital-display-app/src/services/WebSocketService.ts)
   - Line 162-180: Modified `subscribe()` method
   - Line 221-240: Modified `subscribeToPatient()` method
   - Line 245-259: Added `requestCalibration()` method

2. [hospital-display-app/src/hooks/useWebSocket.ts](hospital-display-app/src/hooks/useWebSocket.ts)
   - Line 35: Updated interface
   - Line 62-72: Updated `subscribe()` callback

3. [hospital-display-app/src/hooks/useECGViewer.ts](hospital-display-app/src/hooks/useECGViewer.ts)
   - Line 102: Updated log message
   - Line 241: Pass `triggerCalibration: true` to subscribe

### Backend
Already complete from previous implementation:
- [hospital-backend/app/api/v1/websocket.py](hospital-backend/app/api/v1/websocket.py#L93-L134)

### ESP32
Already complete from previous implementation:
- [esp32_hospital_watch_complete/PhysiologicalSimulator.cpp](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp)
- [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino)

---

## Status: ✅ READY FOR TESTING

**Next Steps**:
1. Refresh browser to load new frontend code
2. Open ECG viewer
3. Check if calibration trigger is sent
4. Flash ESP32 firmware to see actual calibration pulse

---
**Fix Date**: 2025-11-02
**Issue**: Calibration not triggering when patient already subscribed
**Root Cause**: Subscription check prevented resending trigger
**Solution**: Added separate `requestCalibration()` method for already-subscribed patients
