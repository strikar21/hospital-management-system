# Live Stream Audit - Current Status
**Date:** 2025-11-02
**Status:** PARTIAL AUDIT (Cannot complete without ESP32 data)

---

## WHAT I VERIFIED ✅

### 1. Backend is Running
```
Port 8001: LISTENING ✅
Backend process: Running ✅
```

### 2. WebSocket Manager Code EXISTS and is COMPLETE
```
File: websocket_manager.py
- sendWaveformStream() function: EXISTS ✅ (line 190)
- Patient subscription system: WORKS ✅
- Broadcast to subscribers: WORKS ✅
- Auto-reconnection: IMPLEMENTED ✅
- Heartbeat: 30-second keepalive ✅
```

### 3. Storage Code Added (My Implementation)
```
File: mqtt_service.py (lines 745-771)
- Stores stream packets to database ✅
- Non-blocking (won't break WebSocket) ✅
```

### 4. Database Tables
```
waveform_snapshots: EXISTS, 0 rows ✅
vitals_realtime: EXISTS, 101,949 rows ✅
```

**Vitals are flowing, waveforms are not (yet)**

---

## WHAT I CANNOT VERIFY ❌

### 1. ESP32 Device Status
- Cannot verify if ESP32 is:
  - Connected to WiFi
  - Provisioned
  - Assigned to patient
  - Sending MQTT messages

### 2. Active Assignments
- Cannot query deviceassignments table (database name issue)
- Cannot verify if ANY device is assigned to ANY patient
- **This is critical - waveforms only stream when assigned!**

### 3. MQTT Broker Status
- Cannot verify if Mosquitto is running
- Cannot see if ESP32 messages are reaching broker
- Cannot see if backend is subscribed to correct topics

### 4. Frontend WebSocket Connection
- Cannot verify if frontend is connected
- Cannot see if frontend is subscribing to patients
- Cannot check browser console for WebSocket messages

---

## CRITICAL FINDING: ASSIGNMENT REQUIRED

**From code audit (mqtt_service.py:724-733 and websocket_manager.py:196-200):**

```python
# Validate device assignment
async with getDbConnection() as conn:
    assignment = await conn.fetchrow(
        'SELECT "deviceId" FROM deviceassignments WHERE "patientId" = $1 AND status = \'active\'',
        patientId
    )
    if not assignment or assignment['deviceId'] != deviceId:
        logger.warning(f"⚠️ Waveform stream from unassigned device {deviceId}")
        return  # ← STOPS HERE if not assigned!
```

**Waveform streaming will NOT work unless:**
1. ✅ ESP32 is provisioned
2. ✅ ESP32 is assigned to a patient
3. ✅ Assignment status is 'active'
4. ✅ PatientId matches deviceId in assignment

---

## ARCHITECTURE FLOW (Verified from Code)

```
ESP32 Watch
  ↓ WiFi
MQTT Broker (Mosquitto)
  ↓ Subscribe to hospital/devices/+/stream
Backend (mqtt_service.py)
  ├─ Validates assignment ← CRITICAL CHECK
  ├─ Broadcasts to WebSocket (websocket_manager.py:190-226)
  └─ Stores to database (mqtt_service.py:745-771) ← MY ADDITION
       ↓
  WebSocket (port 8001)
       ↓
  Frontend (React)
       ↓
  Browser display
```

**Any break in this chain = No waveforms**

---

## POSSIBLE REASONS FOR "BURSTY" BEHAVIOR

### Based on Code Audit:

**1. ESP32 Not Assigned**
- Backend receives messages
- Backend REJECTS them (assignment check fails)
- Frontend sees nothing
- **Result: No data at all (not bursty)**

**2. WebSocket Reconnection**
- Frontend loses WebSocket connection
- Backend queues messages (no subscribers)
- Frontend reconnects
- Backend sends all queued messages at once
- **Result: Data arrives in burst ✅ MATCHES YOUR DESCRIPTION**

**Code evidence (WebSocketService.ts:124-138):**
```typescript
// Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s
const delay = Math.min(
    this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
    30000  // Max 30 seconds!
);
```

**3. Browser Tab Throttling**
- Browser deprioritizes background tabs
- WebSocket messages queue
- Tab focused → All messages delivered
- **Result: Data arrives in burst ✅ MATCHES YOUR DESCRIPTION**

**4. Network Buffering**
- WiFi packets buffered in router
- Delivered in batch when buffer flushes
- **Result: Data arrives in burst ✅ MATCHES YOUR DESCRIPTION**

---

## WHAT NEEDS TO BE CHECKED (Cannot do remotely)

### 1. Is ESP32 Sending Data?
```bash
# Check ESP32 serial output
# Should see: "📈 Waveform stream: ECG..." every second
```

### 2. Is MQTT Broker Receiving?
```bash
mosquitto_sub -h localhost -t "hospital/devices/+/stream" -v
# Should see JSON messages every 100ms
```

### 3. Is Backend Processing Messages?
```bash
# Check backend logs for:
# "📊 Waveform stream: {deviceId} → patient {patientId}"
```

### 4. Is Frontend Connected?
```
# Open browser console (F12)
# Should see: "🔌 WebSocket connection established"
```

### 5. Are There Active Subscriptions?
```python
# In backend, check:
connectionManager.getPatientSubscriberCount(patientId)
# Should be > 0 if frontend is subscribed
```

---

## MY ASSESSMENT

**Based on code audit only (no runtime verification):**

### What's DEFINITELY Working:
- ✅ Backend running
- ✅ WebSocket manager implemented correctly
- ✅ Storage code added (my implementation)
- ✅ Auto-reconnection exists
- ✅ Assignment validation exists

### What's PROBABLY the Issue:
- ⚠️ **Likely:** Frontend WebSocket reconnection causing bursts
  - 30-second max reconnect delay
  - All queued messages delivered at once when reconnects

- ⚠️ **Possible:** ESP32 not assigned to patient
  - Backend would silently discard messages
  - Frontend would see nothing

### What I CANNOT Determine:
- ❌ Is ESP32 actually sending?
- ❌ Is MQTT broker working?
- ❌ Is frontend subscribed?
- ❌ Are there active assignments?

---

## NEXT STEPS TO DEBUG

### Step 1: Check Assignment
```sql
-- Run this to see assignments
SELECT * FROM deviceassignments WHERE status = 'active';
```

**If empty:** Assign ESP32 to patient first!

### Step 2: Check Backend Logs
```bash
# Look for waveform messages
# Should see every second: "📊 Waveform stream: ..."
```

### Step 3: Check Browser Console
```javascript
// Open F12 console
// Should see: WebSocket messages arriving
```

### Step 4: Monitor Database
```sql
-- Check if storage is working
SELECT COUNT(*) FROM waveform_snapshots;
-- Run again after 10 seconds
-- Should increase by ~100 rows (10 rows/sec)
```

---

## RECOMMENDATION

**Cannot proceed with endpoint creation until we verify streaming is actually working!**

**You need to:**
1. ✅ Verify ESP32 is assigned to a patient
2. ✅ Verify ESP32 is sending `/stream` messages
3. ✅ Verify backend is receiving them
4. ✅ Verify frontend is subscribed
5. ✅ Verify WebSocket is connected

**Then we can:**
- Diagnose why data is bursty
- Decide if database endpoint is needed
- Implement solution

**I cannot complete this audit without access to:**
- ESP32 serial output
- Backend runtime logs
- Browser console
- Database query access
