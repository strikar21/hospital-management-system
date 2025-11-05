# ESP32 v5.2.5 Waveform Diagnosis

**Date:** 2025-11-02 15:26 UTC
**Device:** fit-00001
**Patient:** 081a5294-da91-4c74-bb8a-e5062f5851dd

---

## Current Status

### ✅ What's Working
1. **ESP32 is connected** - Device fit-00001 is actively sending data
2. **Vitals are flowing** - 25 vitals received in last 30 seconds (latest: 15:26:25 UTC)
3. **Backend is running** - Port 8001 active (PID 67332)
4. **Database is working** - 131,255 total vitals stored in TimescaleDB
5. **Assignment is active** - Device fit-00001 assigned to patient 081a5294...

### ❌ What's NOT Working
1. **Waveforms are NOT being stored** - 0 total waveforms in `waveform_snapshots` table
2. **Stream messages not reaching database** - No waveforms in last 10 seconds, 30 seconds, or ever

---

## Possible Root Causes

### 1. ESP32 Not Sending to `/stream` Topic
**Hypothesis:** ESP32 v5.2.5 code changes may have broken the stream message publishing

**Evidence:**
- Vitals use `/vitals` topic → working ✅
- Waveforms use `/stream` topic → not in database ❌

**How to Check:**
- Look at ESP32 serial output during operation
- Check MQTT broker logs for `/stream` topic activity
- Verify ESP32 code actually calls `publishWaveformStream()`

**ESP32 Code Location:**
- File: `esp32_hospital_watch_complete.ino`
- Function: `publishWaveformStream()` (around line 1880-2020)
- Topic: `hospital/devices/{deviceId}/stream`

### 2. Backend Pydantic Validation Failing
**Hypothesis:** Delta-encoded format doesn't match Pydantic model expectations

**Evidence:**
- Backend logging at line 771: `logger.error(f"Stream packet storage failed (non-critical): {e}", exc_info=True)`
- This error might be silent if logging level is too high

**Expected Format (Pydantic Model):**
```python
class ChannelData(BaseModel):
    baseline: int
    deltas: List[int]

class ECGLimbLeads(BaseModel):
    leadI: ChannelData
    leadII: ChannelData
    leadIII: ChannelData
```

**ESP32 Should Send:**
```json
{
  "deviceId": "fit-00001",
  "patientId": "081a...",
  "timestamp": "2025-11-02T15:26:00Z",
  "mode": "ecg",
  "sampleRate": 500,
  "duration": 0.1,
  "ecgWaveform": {
    "limb": {
      "leadI": {"baseline": 1234, "deltas": [1, -2, 3, ...]},
      "leadII": {"baseline": 2345, "deltas": [...]},
      "leadIII": {"baseline": 1111, "deltas": [...]}
    }
  }
}
```

### 3. ESP32 Code Not Calling Stream Function
**Hypothesis:** Delta encoding changes accidentally disabled stream publishing

**Check:**
- Line ~1880: `publishWaveformStream()` function exists ✅
- Line ~650-700: `loop()` calls `publishWaveformStream()` every 100ms?
- Waveform accumulator still filling with data?

### 4. Backend Not Storing Despite Receiving
**Hypothesis:** Backend receives messages but storage function fails silently

**Check:**
- Backend logs should show: `"🔍 _handleWaveformStream ENTERED for deviceId=fit-00001"`
- Backend logs should show: `"Stream packet storage failed"` if validation fails
- TimescaleDB connection working (vitals prove it works)

---

## Diagnostic Steps

### Step 1: Check ESP32 Serial Output
**Action:** Connect to ESP32 via serial monitor and watch for:
```
Waveform stream sent: 50 samples (seq: 123)
MQTT publish: hospital/devices/fit-00001/stream
```

**If NOT seen:** ESP32 not sending stream messages (code issue)
**If seen:** ESP32 is sending, backend or network issue

### Step 2: Check MQTT Broker Logs
**Action:**
```bash
tail -100 mosquitto/logs/mosquitto.log | grep "stream"
```

**Look for:**
- `hospital/devices/fit-00001/stream` topic activity
- Message size (should be ~1-2KB with delta encoding, ~5KB with raw arrays)

**If NOT seen:** ESP32-MQTT connection issue
**If seen:** Backend subscription or processing issue

### Step 3: Check Backend Logs
**Action:** Backend process 67332 - need to find where it's logging

**Look for:**
- `"📨 MQTT STREAM MESSAGE RECEIVED: hospital/devices/fit-00001/stream"`
- `"Stream packet storage failed (non-critical)"`
- Pydantic validation errors with traceback

**If NOT seen:** Backend not receiving from MQTT broker
**If seen with errors:** Pydantic validation failing (data format mismatch)

### Step 4: Test Backend Pydantic Validation
**Action:** Create test script with actual ESP32 delta-encoded format:

```python
from app.models.neural_vitals import WaveformSnapshotMessage

test_payload = {
    "deviceId": "fit-00001",
    "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd",
    "timestamp": "2025-11-02T15:26:00+00:00",
    "mode": "ecg",
    "sampleRate": 500,
    "duration": 0.1,
    "ecgWaveform": {
        "limb": {
            "leadI": {"baseline": 1234, "deltas": [1, -2, 3, 1, -1]},
            "leadII": {"baseline": 2345, "deltas": [2, -1, 4, 2, -2]},
            "leadIII": {"baseline": 1111, "deltas": [1, 1, 1, 1, 1]}
        },
        "precordial": {
            "v1": {"baseline": 3456, "deltas": [...]},
            # ... etc
        },
        "derived": {
            "avr": {"baseline": -1790, "deltas": [...]},
            # ... etc
        }
    }
}

try:
    msg = WaveformSnapshotMessage(**test_payload)
    print("✅ Pydantic validation PASSED")
    print(f"   Mode: {msg.mode}")
    print(f"   Sample rate: {msg.sampleRate} Hz")
    print(f"   Duration: {msg.duration} seconds")
except Exception as e:
    print(f"❌ Pydantic validation FAILED: {e}")
```

---

## Quick Fix Attempts

### Option A: Restart Backend with Debug Logging
```bash
cd hospital-backend
# Kill current backend
taskkill /PID 67332 /F

# Start with debug logging
$env:LOG_LEVEL="DEBUG"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Watch for stream message logs in console.

### Option B: Check ESP32 Code Compilation
Verify delta encoding code actually got flashed:
1. Open serial monitor
2. Look for firmware version: `"ESP32 Hospital Watch v5.2.5"`
3. If not v5.2.5, re-flash firmware

### Option C: Simplify Test
Comment out delta encoding temporarily, use raw arrays to verify flow works:
```cpp
// Quick test: Send raw array (old format)
JsonArray leadI = limb.createNestedArray("leadI");
for (int i = 0; i < 50; i++) {
  leadI.add(waveformAccumulator[0][i]);
}
```

If raw arrays work but delta doesn't → Pydantic validation issue
If neither works → ESP32 not sending or backend not receiving

---

## Most Likely Issue

Based on the evidence:
1. Vitals working = ESP32 → MQTT → Backend → TimescaleDB pipeline is healthy
2. Waveforms not working = Specific to `/stream` topic or waveform data format

**Probability:**
- 60% - ESP32 not calling `publishWaveformStream()` (code issue during delta encoding changes)
- 30% - Backend Pydantic validation failing silently (delta format mismatch)
- 10% - MQTT broker or backend subscription issue

**Next Action:**
Check ESP32 serial output to see if it's actually sending stream messages.
