# Waveform Data Not Flowing - Root Cause Diagnosis

**Date:** 2025-11-02
**Patient ID:** `081a5294-da91-4c74-bb8a-e5062f5851dd`
**Symptom:** ECG viewer buffer stuck at 300 samples (calibration pulse only), no real waveform data

---

## 📊 Evidence From Console Logs

```
utils.ts:266 [ECGWaveformCanvas] dataLength=300
ECGWaveformCanvas.tsx:112 samplesVisible=6947
utils.ts:266 writePos=299, dataLen=300
```

**Analysis:**
- Buffer never grows beyond 300 samples
- 300 samples = calibration pulse only
- No real patient waveform data is arriving

---

## 🔍 Data Flow Path

```
ESP32 Watch (500Hz sampling)
    ↓ MQTT /stream topic
Backend MQTT Service (mqtt_service.py)
    ↓ WebSocket broadcast
Backend WebSocket Manager (websocket_manager.py:sendWaveformStream)
    ↓ WebSocket message type='waveformStream'
Frontend WebSocket Hook (useWebSocket.ts)
    ↓ subscription callback
Frontend ECG Hook (useECGViewer.ts:104-247)
    ↓ dataBufferRef.current[] update
ECGViewerContainer (calibration + buffer management)
    ↓ canvas rendering
ECGWaveformCanvas (display waveform)
```

---

## 🚨 Problem Location

**The buffer is stuck at calibration pulse (300 samples) and never grows.**

This means the data flow is BROKEN at one of these points:

### Possible Root Causes:

1. **ESP32 NOT Assigned to Patient** ❓
   - Check if patient `081a5294-da91-4c74-bb8a-e5062f5851dd` has `assignedDeviceId`
   - If no device assigned → no waveform data will be sent

2. **ESP32 NOT Sending Waveform Data** ❓
   - Check ESP32 serial monitor for waveform stream messages
   - Look for `📈 Waveform stream: ECG (seq: ...)` logs

3. **Backend NOT Receiving MQTT Waveforms** ❓
   - Check backend logs for MQTT waveform messages
   - Look for `📊 Waveform stream sent to N subscribers` logs

4. **Backend NOT Broadcasting to WebSocket** ❓
   - Check if `sendWaveformStream()` is being called in websocket_manager.py
   - Check if patient has WebSocket subscribers

5. **Frontend WebSocket NOT Receiving** ❓
   - Check browser console for WebSocket messages
   - Look for `waveformStream` type messages in Network tab

6. **Frontend Hook NOT Processing Messages** ❓
   - Check if `useECGViewer.ts` subscription callback is firing
   - Check if waveform data is being filtered out (wrong patientId, mode, etc.)

---

## ✅ Verified Working Components

1. ✅ **Calibration Pulse Generation** - Working (300 samples added to buffer)
2. ✅ **Canvas Rendering** - Working (displays calibration pulse correctly)
3. ✅ **Circular Buffer Logic** - Working (would advance if data arrives)
4. ✅ **Centralized Config** - Working (buffer size = 12 seconds)

---

## 🔧 Diagnostic Steps

### Step 1: Check Patient Device Assignment

```sql
SELECT id, "firstName", "lastName", "assignedDeviceId"
FROM patients
WHERE id = '081a5294-da91-4c74-bb8a-e5062f5851dd';
```

**Expected:** `assignedDeviceId` should be set to a device ID (e.g., `ESP32-WATCH-...`)

---

### Step 2: Check ESP32 Waveform Transmission

**Check ESP32 Serial Monitor:**
- Look for: `📈 Waveform stream: ECG (seq: X, size: Y bytes)`
- If missing → ESP32 is not sending waveform data
- Possible reasons:
  - Not assigned to patient
  - MQTT disconnected
  - Mode pin not set correctly (GPIO4 should be HIGH for ECG)

---

### Step 3: Check Backend MQTT Reception

**Check Backend Logs:**
```bash
grep "Waveform stream sent" hospital-backend/logs/*.log
```

**Expected:** Should see periodic logs like:
```
📊 Waveform stream sent to N subscribers for patient 081a5294-... (seq: 10)
```

If missing → Backend is not receiving waveform MQTT messages from ESP32

---

### Step 4: Check WebSocket Subscription

**Browser Console:**
```javascript
// Check if WebSocket is connected
console.log("WebSocket state:", WebSocketService.getState());

// Check active subscriptions
console.log("Active subscriptions:", WebSocketService.getSubscriptions());
```

**Expected:** Should show patient ID `081a5294-da91-4c74-bb8a-e5062f5851dd` in subscriptions

---

### Step 5: Check WebSocket Message Flow

**Browser Network Tab:**
1. Open DevTools → Network → WS (WebSocket)
2. Click on the WebSocket connection
3. Go to "Messages" tab
4. Look for messages with `type: "waveformStream"`

**Expected:** Should see periodic waveform messages arriving

If missing → WebSocket is connected but not receiving waveform messages

---

## 🎯 Most Likely Root Cause

Based on the symptoms, the **MOST LIKELY** cause is:

**❌ ESP32 is NOT assigned to this patient**

**Reasoning:**
- Calibration pulse works (frontend is functional)
- WebSocket vitals work (based on previous fixes)
- But waveform data is missing (specific to ECG viewer)

**Quick Test:**
1. Check patient device assignment in database
2. If no device assigned → assign an ESP32 watch
3. Verify ESP32 is sending waveform data (check serial monitor)
4. Verify backend is broadcasting waveforms (check logs)

---

## 🔨 Immediate Actions

**Option 1: Check Patient Assignment (RECOMMENDED)**
1. Query database for patient `081a5294-da91-4c74-bb8a-e5062f5851dd`
2. Check if `assignedDeviceId` is set
3. If not set → assign a device via Device Assignment page

**Option 2: Check ESP32 Serial Monitor**
1. Connect to ESP32 via Serial (115200 baud)
2. Look for waveform stream messages
3. Verify patient assignment and MQTT connection

**Option 3: Enable Frontend WebSocket Logging**
1. Add console.log in useECGViewer.ts subscription callback
2. Log all received WebSocket messages
3. Check if waveformStream messages are arriving

---

## 📝 Next Steps

**QUESTION FOR USER:**

1. Does patient `081a5294-da91-4c74-bb8a-e5062f5851dd` have a device assigned?
2. Is there an ESP32 watch connected and sending data?
3. Can you check the browser console for WebSocket waveformStream messages?

**Once you answer these questions, I can provide the exact fix!**
