# WebSocket Missing - Root Cause Analysis

**Date:** 2025-10-23
**Issue:** Vitals, alerts, and waveforms not displaying on dashboard despite ESP32 sending data successfully

## ROOT CAUSE ✅

**Frontend has NO WebSocket implementation.**

The `createWebSocketConnection()` method exists in `BaseService.ts` but is **NEVER CALLED** anywhere in the codebase.

## Evidence

### Backend Status: ✅ WORKING
```
📊 8CH Vitals processed for patient 081a5294-da91-4c74-bb8a-e5062f5851dd from device fit-00001 (mode: ecg)
🚨 Detected 2 alert(s) for patient 081a5294-da91-4c74-bb8a-e5062f5851dd
   → [HIGH] watchTampering: WATCH TAMPERING - Impedance fluctuation 234.2% in 5 minutes
   → [MEDIUM] electrodeGelDried: ELECTRODE GEL DRIED - Impedance increased 93.6% over 4 hours
```

- ✅ ESP32 fit-00001 sending vitals via MQTT
- ✅ Backend receiving and processing vitals
- ✅ Backend storing vitals in TimescaleDB
- ✅ Backend detecting alerts
- ✅ Backend calling `connectionManager.sendVitalsUpdate()` and `sendAlert()`

### Frontend Status: ❌ NOT CONNECTED
```
# Grep search results:
Found 2 files with WebSocket:
- c:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-display-app\src\config\apiConfig.ts
- c:\Users\Srika\OneDrive\Desktop\hospital-management-system\hospital-display-app\src\services\BaseService.ts

# Grep search for WebSocket usage in components:
Found 0 files
```

- ❌ No WebSocket connections in backend logs
- ❌ No `🔌 WebSocket connection established` messages
- ❌ No `📡 Connection subscribed to patient` messages
- ❌ `createWebSocketConnection()` method exists but **unused**
- ❌ No WebSocket hooks in components
- ❌ No WebSocket service layer

## The Problem

### Backend WebSocket Flow (Line 204-206 in websocket_manager.py):
```python
sentCount = await self.broadcastToPatientSubscribers(patientId, data)
if sentCount > 0:
    logger.info(f"📊 Vitals update sent to {sentCount} subscribers...")
```

**This log NEVER appears** because:
- `patientSubscriptions` dictionary is empty (no frontend connections)
- `broadcastToPatientSubscribers()` returns 0 (line 94-95)
- No logging occurs
- Dashboard never receives updates

### Expected Flow vs Actual Flow

**EXPECTED:**
```
ESP32 → MQTT → Backend → TimescaleDB ✅
                      ↓
                WebSocket Broadcast → Frontend Dashboard ✅
```

**ACTUAL:**
```
ESP32 → MQTT → Backend → TimescaleDB ✅
                      ↓
                WebSocket Broadcast → 0 subscribers ❌ → Dashboard shows nothing ❌
```

## What's Missing

### 1. WebSocket Service Layer
**File needed:** `hospital-display-app/src/services/WebSocketService.ts`

Should provide:
- Connection management
- Auto-reconnect on disconnect
- Patient subscription management
- Message handlers for vitals, alerts, waveforms

### 2. WebSocket React Hook
**File needed:** `hospital-display-app/src/hooks/useWebSocket.ts`

Should provide:
- `useWebSocket()` hook for components
- Real-time vitals state updates
- Alert notifications
- Connection status

### 3. Component Integration
**Files to modify:**
- `hospital-display-app/src/App.tsx` - Initialize WebSocket connection on login
- `hospital-display-app/src/components/PatientCard/PatientCardContainer.tsx` - Subscribe to patient vitals
- `hospital-display-app/src/components/PatientDetail/PatientOverview.tsx` - Display real-time vitals

## Solution Required

The frontend needs a complete WebSocket implementation:

1. **WebSocketService** - Singleton service to manage WebSocket connection
2. **useWebSocket Hook** - React hook for components to subscribe to updates
3. **Patient Subscription** - Subscribe to specific patient IDs when viewing patient cards
4. **Message Handlers** - Handle `vitalsUpdate`, `alert`, `waveformStream` messages from backend
5. **Auto-reconnect** - Handle disconnections and reconnect automatically

## Backend WebSocket API (Already Implemented)

### Connection Endpoint
```
wss://localhost:8001/ws?token={jwt_token}
```

### Messages Frontend Should Send
```json
{
  "action": "subscribePatient",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd"
}
```

### Messages Backend Sends
```json
// Vitals Update
{
  "type": "vitalsUpdate",
  "patientId": "081a5294-...",
  "deviceId": "fit-00001",
  "timestamp": "2025-10-23T10:19:40Z",
  "vitals": {
    "heartRate": 75,
    "oxygenSaturation": 98,
    "temperature": 36.8,
    "respiratoryRate": 16
  }
}

// Alert
{
  "type": "alert",
  "patientId": "081a5294-...",
  "timestamp": "2025-10-23T10:19:53Z",
  "alert": {
    "severity": "high",
    "alertType": "watchTampering",
    "message": "WATCH TAMPERING - Impedance fluctuation 234.2% in 5 minutes"
  }
}

// Waveform Stream (10 times/sec)
{
  "type": "waveformStream",
  "patientId": "081a5294-...",
  "deviceId": "fit-00001",
  "timestamp": "2025-10-23T10:19:40.123Z",
  "waveform": {
    "sequence": 42,
    "ecgData": [0.5, 0.6, 0.7, ...],
    "eegData": [0.1, 0.2, 0.3, ...]
  }
}
```

## Next Steps

**Option 1:** Implement WebSocket frontend (recommended)
- Complete real-time updates
- No polling overhead
- Scalable for multiple patients

**Option 2:** Use REST API polling (not recommended)
- High server load
- Delayed updates (poll every 5-10 seconds)
- Not suitable for waveform streaming

## Files to Create/Modify

### Create:
- `hospital-display-app/src/services/WebSocketService.ts`
- `hospital-display-app/src/hooks/useWebSocket.ts`
- `hospital-display-app/src/hooks/usePatientVitals.ts`

### Modify:
- `hospital-display-app/src/App.tsx`
- `hospital-display-app/src/components/PatientCard/PatientCardContainer.tsx`
- `hospital-display-app/src/components/PatientDetail/PatientOverview.tsx`

## Summary

**The vitals ARE being processed successfully by the backend.** The issue is purely that the frontend never connects via WebSocket, so it never receives the updates. The dashboard shows stale data from the initial REST API fetch only.

Implementing WebSocket on the frontend will immediately enable:
- ✅ Real-time vitals display
- ✅ Live alerts
- ✅ ECG/EEG waveform streaming
- ✅ Device status updates
