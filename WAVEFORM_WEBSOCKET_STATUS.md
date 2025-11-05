# Waveform WebSocket Streaming Status

**Date:** 2025-11-03
**Summary:** Waveforms are flowing but not reaching frontend

## ✅ WORKING Components

### 1. ESP32 → MQTT → Backend
- ESP32 sending waveforms every ~100ms (10 Hz rate)
- MQTT messages received successfully
- Backend processing messages correctly
- **Field names CORRECT**: `leadI`, `leadII`, `leadIII` (camelCase with Roman numerals)
- **Delta encoding PRESENT**: `{baseline: 8388651, deltas: [...]}`

**Evidence:**
```
2025-11-03 09:05:27,714 - app.services.mqtt_service - INFO - 📨 MQTT STREAM MESSAGE RECEIVED: hospital/devices/fit-00001/stream
2025-11-03 09:05:27,714 - app.services.mqtt_service - INFO -    Payload keys: ['deviceId', 'patientId', 'timestamp', 'mode', 'sequence', 'duration', 'sampleRate', 'ecgWaveform']
2025-11-03 09:05:27,714 - app.services.mqtt_service - INFO -    Has ecgWaveform: True
2025-11-03 09:05:27,720 - app.services.mqtt_service - INFO - 📡 Broadcasting waveform to WebSocket for patient 081a5294-da91-4c74-bb8a-e5062f5851dd
2025-11-03 09:05:27,720 - app.services.mqtt_service - INFO - ✅ WebSocket broadcast completed
```

### 2. Database Storage
- Waveforms storing successfully in TimescaleDB
- **Total waveforms:** 9,105 snapshots
- **Latest waveform:**
  - Device: fit-00001
  - Patient: 081a5294-da91-4c74-bb8a-e5062f5851dd
  - Mode: ecg
  - Sample Rate: 500 Hz
  - Duration: 0.10 seconds
- **Field names in DB:** `leadI`, `leadII`, `leadIII` ✅
- **Delta format in DB:** `{baseline: 8388651, deltas: [49 values]}` ✅

### 3. Backend WebSocket Service
- WebSocket connection established: `conn6a81ccb5` (09:25:17)
- Backend broadcasting waveforms (no errors)
- Field name fix applied correctly in [websocket_manager.py:373-432](hospital-backend/app/services/websocket_manager.py#L373-L432)

## ❌ BROKEN Component

### WebSocket Subscription Missing
**Problem:** Frontend WebSocket connected BUT NOT subscribed to patient!

**Evidence from logs:**
```
# Old connection (closed at 09:21:48)
2025-11-03 09:06:38 - WebSocket connection established: connb7b631e9
2025-11-03 09:06:38 - Connection connb7b631e9 subscribed to patient 081a5294...  ✅

# New connection (established at 09:25:17)
2025-11-03 09:25:17 - WebSocket connection established: conn6a81ccb5
# ❌ NO SUBSCRIPTION MESSAGES FOR conn6a81ccb5!
```

**Result:** Backend is broadcasting waveforms to **zero subscribers**
- `sendWaveformStream()` called successfully
- `broadcastToPatientSubscribers()` sends to 0 connections
- No `sentCount` logs because no one is listening

## 🔧 Root Cause

Frontend WebSocket service at [WebSocketService.ts:162-180](hospital-display-app/src/services/WebSocketService.ts#L162-L180):

```typescript
public subscribe(subscriberId: string, callback: ..., patientId?: string, triggerCalibration?: boolean): void {
  // ...
  // Subscribe to patient updates on backend
  if (patientId && !this.subscribedPatients.has(patientId)) {
    this.subscribeToPatient(patientId, triggerCalibration);  // ← Sends WebSocket message
  }
}
```

**Issue:** Frontend established WebSocket connection but never called `.subscribe()` for the active patient.

## 📋 Next Steps

1. **Check frontend Dashboard/PatientCard components** - verify they call `WebSocketService.getInstance().subscribe()`
2. **Verify subscription timing** - ensure subscription happens AFTER WebSocket connects
3. **Test with browser dev tools** - check WebSocket frames to see if subscription messages are sent
4. **Backend enhancement** - add debug logging to show number of subscribers per patient

## 🔍 Data Flow Verification

**Expected flow:**
```
ESP32 → MQTT → Backend → WebSocket → Frontend
                         (with delta encoding)
```

**Current status:**
```
ESP32 → MQTT → Backend → WebSocket → [NO SUBSCRIBERS]
                         ✅ Field names correct
                         ✅ Delta encoding present
```

**To fix:** Frontend must send subscription message:
```json
{
  "type": "subscribePatient",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd"
}
```

---

## Technical Details

### Backend Field Names (CORRECT)
- ECG Limb: `leadI`, `leadII`, `leadIII`
- EEG Frontal: `Fp1`, `Fp2`, `F3`, `F4`
- EEG Central: `C3`, `C4`
- EEG Occipital: `O1`, `O2`

### Delta Encoding Format
```json
{
  "leadI": {
    "baseline": 8388651,
    "deltas": [-3629, 22, -22, -20, 72, -72, 73, ...]
  }
}
```

### WebSocket Message Structure
```json
{
  "type": "waveformStream",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd",
  "deviceId": "fit-00001",
  "timestamp": "2025-11-03T09:05:27.720Z",
  "waveform": {
    "mode": "ecg",
    "sampleRate": 500,
    "duration": 0.10,
    "ecgWaveform": {
      "limb": {
        "leadI": { "baseline": 8388651, "deltas": [...] },
        "leadII": { "baseline": 8388617, "deltas": [...] },
        "leadIII": { "baseline": -34, "deltas": [...] }
      }
    }
  }
}
```
