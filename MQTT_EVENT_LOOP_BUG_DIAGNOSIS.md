# MQTT Event Loop Bug - Root Cause Analysis

**Date:** 2025-10-22
**Severity:** 🔴 **CRITICAL** - Blocks all ESP32 device functionality
**Status:** Bug confirmed, fix required

---

## Problem Statement

**Symptom:** ESP32 watch shows as "disconnected/offline" in frontend even though it's sending heartbeat messages every 30 seconds.

**User Report:**
> "i assigned watch to test patient. it shows disconnedted/ offline even when device is being able to send heartbeat."

---

## Root Cause

### The Bug

**File:** [hospital-backend/app/services/mqtt_service.py:239](hospital-backend/app/services/mqtt_service.py#L239)

```python
def _on_message(self, client, userdata, msg):
    """Handle incoming MQTT messages"""
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())

        logger.debug(f"📨 MQTT message: {topic} -> {payload}")

        # Route message to appropriate handler
        asyncio.create_task(self._routeMessage(topic, payload))  # ← BUG HERE

    except Exception as e:
        logger.error(f"❌ MQTT message processing error: {e}")
```

###

 Why It Fails

1. **`_on_message()` is a synchronous callback** from paho-mqtt library
2. **Paho-mqtt runs in its own thread** (`client.loop_start()` at line 113)
3. **No asyncio event loop** exists in that thread
4. **`asyncio.create_task()` requires an event loop** to schedule coroutines
5. **Exception thrown:** `RuntimeError: no running event loop`
6. **Messages are received but never processed** → handlers never called

---

## Evidence from Logs

### Backend Logs Show:

```
2025-10-21 10:56:47,203 - app.services.mqtt_service - ERROR - ❌ MQTT message processing error: no running event loop
2025-10-21 10:57:47,367 - app.services.mqtt_service - ERROR - ❌ MQTT message processing error: no running event loop
2025-10-21 10:58:17,474 - app.services.mqtt_service - ERROR - ❌ MQTT message processing error: no running event loop
... [repeats every ~30 seconds]
```

### What This Means:

- ✅ ESP32 IS connected to MQTT broker
- ✅ ESP32 IS sending heartbeat messages every 30 seconds
- ❌ Backend CANNOT process messages (async task creation fails)
- ❌ `_handleHeartbeatMessage()` is NEVER called
- ❌ Database `devices.lastSeen` is NEVER updated
- ❌ Frontend queries stale data → shows "offline"

---

## Impact Analysis

### What's Broken:

1. **Device Status Tracking** - `lastSeen` never updates → always shows offline
2. **Heartbeat Processing** - Battery level not updated
3. **Vitals Processing** - Patient vitals never reach database
4. **Waveform Streaming** - ECG/EEG data never processed
5. **Alert Detection** - No real-time alerts from devices
6. **Device Assignment** - Frontend can't see online devices

### What Still Works:

1. ✅ Device provisioning (HTTP endpoint, not MQTT)
2. ✅ Frontend UI (no crashes)
3. ✅ Database queries
4. ✅ MQTT broker connection
5. ✅ ESP32 sending messages

---

## Verification

### Backend Log Patterns:

**Expected (if working):**
```
💓 MQTT Heartbeat: fit-00001 Battery 98% Signal -45dBm
📊 8CH Vitals processed for patient PAT123 from device fit-00001
```

**Actual (broken):**
```
❌ MQTT message processing error: no running event loop
```

Every 30 seconds, exactly aligned with ESP32 heartbeat interval.

### Database Check:

```sql
SELECT id, "lastSeen", status FROM devices WHERE id = 'fit-00001';
```

**Expected:** `lastSeen` updates every 30 seconds
**Actual:** `lastSeen` frozen at provisioning time (11:00:06)

---

## The Correct Flow (How It Should Work)

```
ESP32 Watch
   │
   ├─ MQTT Publish → hospital/devices/fit-00001/heartbeat
   │                 {"batteryLevel": 95, "signalStrength": -50}
   │
   ├─ Mosquitto Broker (127.0.0.1:8883)
   │
   ├─ Backend MQTT Client (subscribed)
   │
   ├─ _on_message() callback [SYNC]
   │
   ├─ Schedule async task → _routeMessage() [ASYNC]  ← FAILS HERE
   │
   ├─ Parse topic → deviceId='fit-00001', type='heartbeat'
   │
   ├─ Security validation
   │
   ├─ _handleHeartbeatMessage() [ASYNC]
   │
   ├─ UPDATE devices SET lastSeen=NOW(), batteryLevel=95
   │
   └─ Frontend query → sees device online ✅
```

**Current Reality:**
```
ESP32 Watch → MQTT → Backend _on_message() → ❌ CRASH → Nothing happens
```

---

## Solution Requirements

### Must Fix:

1. **Bridge sync → async contexts** properly
2. **Maintain thread safety** (MQTT thread → asyncio thread)
3. **Preserve message order** for sequential processing
4. **Handle exceptions gracefully** (no silent failures)
5. **No blocking delays** in MQTT callback

### Approaches:

#### Option 1: `asyncio.run_coroutine_threadsafe()` ✅ RECOMMENDED

**Pros:**
- Thread-safe async task scheduling
- Works from any thread
- Built-in exception handling
- Maintains message order

**Implementation:**
```python
def _on_message(self, client, userdata, msg):
    """Handle incoming MQTT messages"""
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())

        logger.debug(f"📨 MQTT message: {topic} -> {payload}")

        # Get the main event loop (stored during startup)
        loop = self.eventLoop

        # Schedule coroutine in main event loop (thread-safe)
        asyncio.run_coroutine_threadsafe(
            self._routeMessage(topic, payload),
            loop
        )

    except Exception as e:
        logger.error(f"❌ MQTT message processing error: {e}")
```

**Required Changes:**
1. Store event loop reference during `start()`:
   ```python
   self.eventLoop = asyncio.get_running_loop()
   ```

2. Use `run_coroutine_threadsafe()` in callback

#### Option 2: Queue-based approach

**Pros:**
- Decouples MQTT thread from asyncio
- More control over processing

**Cons:**
- More complex
- Requires background consumer task

#### Option 3: Synchronous handlers

**Pros:**
- Simple, no async issues

**Cons:**
- Blocks MQTT thread
- Can't use async database operations
- Defeats purpose of asyncio backend

---

## Recommended Fix

Use **Option 1: `asyncio.run_coroutine_threadsafe()`**

### Changes Required:

**File:** `hospital-backend/app/services/mqtt_service.py`

**Change 1:** Store event loop during startup (line 118):
```python
async def start(self, config: Dict[str, Any] = None) -> bool:
    # ... existing code ...

    # Store event loop for thread-safe async task scheduling
    self.eventLoop = asyncio.get_running_loop()

    # ... rest of startup ...
```

**Change 2:** Use thread-safe task scheduling (line 239):
```python
def _on_message(self, client, userdata, msg):
    """Handle incoming MQTT messages"""
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())

        logger.debug(f"📨 MQTT message: {topic} -> {payload}")

        # Schedule coroutine in main event loop (thread-safe from MQTT thread)
        asyncio.run_coroutine_threadsafe(
            self._routeMessage(topic, payload),
            self.eventLoop
        )

    except Exception as e:
        logger.error(f"❌ MQTT message processing error: {e}")
```

---

## Testing Plan

### Step 1: Verify Fix Compilation
```bash
cd hospital-backend
python -c "from app.services.mqtt_service import mqttService; print('✅ Import successful')"
```

### Step 2: Restart Backend
```bash
# Backend should start without errors
# Look for: "✅ MQTT service started successfully"
```

### Step 3: Send Test Heartbeat
```bash
# ESP32 should send heartbeat every 30 seconds
# Backend logs should show:
💓 MQTT Heartbeat: fit-00001 Battery 95% Signal -50dBm
```

### Step 4: Check Database
```sql
SELECT id, "lastSeen", "batteryLevel", status
FROM devices
WHERE id = 'fit-00001';
```

Expected: `lastSeen` updating every 30 seconds.

### Step 5: Check Frontend
- Device should show "online" status
- Battery level should display correctly
- Watch icon should be green/connected

---

## Risk Assessment

### Risk of NOT Fixing:

- 🔴 **CRITICAL:** All ESP32 devices appear offline
- 🔴 **CRITICAL:** No patient vitals data
- 🔴 **CRITICAL:** No real-time alerts
- 🔴 **CRITICAL:** System unusable for actual patient monitoring

### Risk of Fixing:

- 🟢 **LOW:** Thread-safe async scheduling is standard Python asyncio pattern
- 🟢 **LOW:** No breaking changes to other code
- 🟢 **LOW:** Two-line fix with minimal surface area

---

## Conclusion

This is a **critical bug** that blocks all ESP32 functionality. The fix is straightforward using `asyncio.run_coroutine_threadsafe()`, which is the standard Python solution for bridging sync/async contexts across threads.

**Priority:** Fix immediately before any ESP32 testing.

**Estimated Fix Time:** 5 minutes
**Estimated Test Time:** 10 minutes
**Total:** 15 minutes to full resolution
