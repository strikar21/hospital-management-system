# Waveform Storage Diagnostic Findings

## Date: 2025-11-02 13:40 UTC

## Verified Facts

### ✅ ESP32 Firmware Analysis
- **File**: [esp32_hospital_watch_complete.ino:1925](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1925)
- **Publishes to**: `hospital/devices/{deviceId}/stream`
- **Payload Structure**:
  - `deviceId`, `patientId`, `timestamp`, `mode`, `sequence`
  - **ECG Mode**: `ecgWaveform.limb`, `ecgWaveform.precordial`, `ecgWaveform.derived`
  - **EEG Mode**: `eegWaveform.frontal`, `eegWaveform.central`, `eegWaveform.occipital`
  - `sampleRate`: 500 Hz
  - **NO `duration` field** - ESP32 does not send duration!

### ✅ Backend Handler Analysis
- **File**: [mqtt_service.py:406-409](hospital-backend/app/services/mqtt_service.py#L406-L409)
- **Routes**: `/stream` → `_handleWaveformStream()` ✅
- **Subscription**: Line 154 subscribes to `hospital/devices/+/stream` ✅

### ✅ Backend Storage Code
- **File**: [mqtt_service.py:745-771](hospital-backend/app/services/mqtt_service.py#L745-L771)
- **Added by me**: Stores `/stream` packets to `waveform_snapshots` table
- **My code adds**: `payload['duration'] = 0.1` (100ms = 0.1 seconds)
- **Uses**: `WaveformSnapshotMessage(**payload)` - Pydantic model validation

### ✅ Database Status
- **Table**: `waveform_snapshots` exists ✅
- **Rows**: 0 (NO DATA) ❌
- **Vitals table**: `vitals_realtime` has 101,949 rows ✅
- **Vitals flowing**: 8 vitals in last 10 seconds from `fit-00001` ✅

### ✅ Device Status
- **Active device**: `fit-00001`
- **Assignment**: Active (assigned to patient `081a5294-...`)
- **Connection**: Sending vitals every ~1 second ✅

## Root Cause Hypothesis

### Most Likely: Pydantic Validation Failing

**Evidence**:
1. ESP32 does NOT send `duration` field
2. My storage code ADDS `duration = 0.1` to payload
3. `WaveformSnapshotMessage` Pydantic model likely REQUIRES `sampleRate` but ESP32 sends it ✅
4. Error is being caught silently by `except Exception as e:` block (line 769-771)

**Testing Required**:
- Check if `WaveformSnapshotMessage` model requires fields ESP32 doesn't send
- Check backend logs for "Stream packet storage failed" errors
- Verify Pydantic model matches ESP32 payload structure

### Secondary: ESP32 Not Publishing

**Evidence Against This**:
- ESP32 code shows clear `/stream` publishing (line 1925)
- No conditional blocking (would publish if assigned and connected)
- Device `fit-00001` IS sending vitals (proven by database)

**Evidence For This**:
- We haven't seen actual backend logs confirming `/stream` message reception
- Cannot verify if "MQTT STREAM MESSAGE RECEIVED" log appears

## Next Steps (Prioritized)

### 1. Check Pydantic Model Definition ⚡ HIGH PRIORITY
**File to read**: `hospital-backend/app/models/neural_vitals.py`
**Look for**: `WaveformSnapshotMessage` class definition
**Verify**: Required fields match ESP32 payload

### 2. Add Detailed Error Logging
**Modify**: [mqtt_service.py:769-771](hospital-backend/app/services/mqtt_service.py#L769-L771)
**Change**: From `logger.debug()` to `logger.error()` with full traceback
**Purpose**: See actual Pydantic validation errors

### 3. Test Backend Restart
**Action**: Restart backend to check if new logs appear
**Purpose**: Verify backend is actually receiving `/stream` messages

### 4. Check ESP32 Serial Output
**Action**: Connect to ESP32 serial monitor
**Look for**: "📈 Waveform stream" messages (line 2049)
**Verify**: ESP32 is actually publishing waveforms

## Questions to Answer

1. **Does `WaveformSnapshotMessage` require `duration`?** (My code adds it, but maybe wrong type?)
2. **Does `WaveformSnapshotMessage` require `sampleRate`?** (ESP32 sends it ✅)
3. **Are there other required fields ESP32 doesn't send?**
4. **Is backend actually receiving `/stream` messages?** (No logs to confirm)
5. **Is my added `duration = 0.1` the correct data type?** (Should be `int` or `float`?)

## Code Review Required

**My storage code** (mqtt_service.py:745-771):
```python
# ✅ NEW: Store stream packet to database for historical analysis
try:
    payload['duration'] = 0.1  # 100ms packet

    if 'timestamp' in payload:
        timestampStr = payload['timestamp']
        if isinstance(timestampStr, str):
            if timestampStr.endswith('Z'):
                timestampStr = timestampStr.replace('Z', '+00:00')
            payload['timestamp'] = datetime.fromisoformat(timestampStr)

    waveformMsg = WaveformSnapshotMessage(**payload)
    await self._storeWaveformSnapshot(waveformMsg)

    sequence = payload.get('sequence', 0)
    if sequence % 10 == 0:
        logger.debug(f"💾 Stream packet #{sequence} stored to database")

except Exception as e:
    logger.debug(f"Stream packet storage failed (non-critical): {e}")
```

**Issues**:
- `duration` might need to be `int` (milliseconds) not `float` (seconds)
- Exception is caught and logged as `debug` - should be `error` for diagnostics
- No traceback shown - should use `exc_info=True`

## Recommended Fix

**Option 1**: Check Pydantic model first, then adjust my code
**Option 2**: Change `logger.debug()` to `logger.error()` with traceback to see actual error
**Option 3**: Test with minimal payload to verify Pydantic model works

**I recommend**: Read Pydantic model FIRST, then we know exactly what's wrong.
