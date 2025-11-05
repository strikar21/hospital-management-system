# Calibration Root Cause - FOUND!

## Evidence from Frontend Logs

```
🔧 Calibration requested for patient: 081a5294-da91-4c74-bb8a-e5062f5851dd
```

**Frontend IS sending the calibration request!**

## The Problem

**Backend is NOT processing the calibration request.**

### What Should Happen:

1. ✅ Frontend sends: `{type: 'subscribePatient', patientId: '081a5294...', triggerCalibration: true}`
2. ❌ Backend should log: `"🔧 Calibration triggered for device XXX"`
3. ❌ Backend should log: `"📤 Calibration command sent to device XXX"`
4. ❌ ESP32 should receive calibration command

### What's Actually Happening:

1. ✅ Frontend sends calibration request
2. ❌ **Backend logs show NOTHING** - no calibration messages at all
3. ❌ ESP32 never receives command

## Root Cause

**Backend WebSocket handler is either:**
1. Not executing the calibration code at all
2. Silently catching an exception (line 120: `except Exception as e: logger.warning(...)`)
3. Not connected to patient subscription logic

## Most Likely Issues

### Issue 1: Backend Exception Being Caught Silently

**File:** `hospital-backend/app/api/v1/websocket.py:113-120`

```python
if success and triggerCalibration:
    try:
        deviceId = await _getDeviceForPatient(patientId)
        if deviceId:
            await _triggerDeviceCalibration(deviceId, patientId)
            logger.info(f"🔧 Calibration triggered for device {deviceId} (patient {patientId})")
    except Exception as e:
        logger.warning(f"⚠️  Could not trigger calibration for patient {patientId}: {e}")
```

**If an exception is thrown, it's caught and only logged as a warning.**

You would see: `"⚠️ Could not trigger calibration for patient XXX"` in backend logs.

**But you see NOTHING in backend logs - so either:**
- `success` is False (code never runs)
- Exception happens before the try block
- Backend not receiving the WebSocket message at all

---

### Issue 2: `success` is False

```python
success = connectionManager.subscribeToPatient(connectionId, patientId)

if success and triggerCalibration:
    # This code never runs if success is False!
```

**What makes `success` False?**
- Patient ID not in connectionManager
- Connection not established properly
- Subscription failed

**This is the most likely issue!**

---

### Issue 3: Backend Not Receiving WebSocket Message

The WebSocket message might not be reaching the backend at all.

**How to verify:** Add logging at the TOP of `handleClientMessage()`:

```python
async def handleClientMessage(connectionId: str, message: Dict[str, Any]) -> None:
    """Handle incoming messages from WebSocket clients"""

    logger.info(f"📨 Received WebSocket message: {message}")  # ← ADD THIS

    messageType = message.get('type')

    if messageType == 'subscribePatient':
        # ...
```

---

## Next Steps

### Step 1: Check Backend Logs

**Look for these specific messages:**

1. `"📨 Received WebSocket message:"` - Is backend receiving the message?
2. `"🔧 Calibration triggered for device"` - Is calibration code running?
3. `"⚠️ Could not trigger calibration"` - Is an exception being caught?
4. `"📤 Calibration command sent to device"` - Is MQTT publish happening?

**If you see NONE of these**, the code is not running at all.

---

### Step 2: Add Debug Logging

Add this to `websocket.py` line 93:

```python
if messageType == 'subscribePatient':
    patientId = message.get('patientId')
    triggerCalibration = message.get('triggerCalibration', False)

    logger.info(f"🔍 DEBUG: subscribePatient - patientId={patientId}, triggerCalibration={triggerCalibration}")

    if patientId:
        # ... rest of code

        logger.info(f"🔍 DEBUG: success={success}, triggerCalibration={triggerCalibration}")

        if success and triggerCalibration:
            logger.info(f"🔍 DEBUG: About to trigger calibration")
            try:
                deviceId = await _getDeviceForPatient(patientId)
                logger.info(f"🔍 DEBUG: deviceId={deviceId}")
                if deviceId:
                    logger.info(f"🔍 DEBUG: Calling _triggerDeviceCalibration")
                    await _triggerDeviceCalibration(deviceId, patientId)
                    logger.info(f"🔧 Calibration triggered for device {deviceId} (patient {patientId})")
                else:
                    logger.warning(f"⚠️ No device found for patient {patientId}")
            except Exception as e:
                logger.error(f"⚠️ Could not trigger calibration for patient {patientId}: {e}", exc_info=True)
```

This will show exactly where the code is failing.

---

## Summary

**Frontend:** ✅ Sending calibration request correctly

**Backend:** ❌ Not processing calibration request (no logs at all)

**Most Likely Cause:** `success = connectionManager.subscribeToPatient()` returns False, so `if success and triggerCalibration:` never executes.

**Fix:** Need to debug why `subscribeToPatient()` is returning False, or add logging to see what's actually happening in the backend.

**Next:** Add debug logging to backend and check what the logs show when you open ECG viewer.
