# Delta Encoding Waveform Storage Status Report

**Date:** 2025-11-03 02:15 UTC
**Status:** ✅ Frontend Delta Decoding Complete | ❌ Database Storage Not Working

---

## 📊 Current Status Summary

### ✅ WORKING:
1. **ESP32 v5.2.5** - Sending delta-encoded waveforms correctly
2. **Backend MQTT Service** - Receiving waveform stream packets
3. **Backend WebSocket** - Broadcasting waveforms to frontend
4. **Frontend Delta Decoding** - Decoding delta format correctly
5. **Frontend Display** - Waveforms rendering smoothly on screen
6. **Vitals Storage** - 138,953 vitals records in TimescaleDB

### ❌ NOT WORKING:
1. **Waveform Database Storage** - 0 waveform records in TimescaleDB despite code calling storage function

---

## 🔍 Investigation Findings

### Database Check Results

```bash
# TimescaleDB Connection: localhost:5433, database: hospitaltimescale

1. VITALS (last 10 seconds):
   Device: fit-00001, Patient: 081a5294-..., Time: 2025-11-03 02:13:23
   ✅ VITALS ARE FLOWING NORMALLY

2. WAVEFORMS (last 10 seconds):
   ❌ No waveforms in last 10 seconds

3. TOTAL COUNTS:
   Total vitals: 138,953  ✅
   Total waveforms: 0      ❌
```

### Backend Code Analysis

**File:** [hospital-backend/app/services/mqtt_service.py:694-777](hospital-backend/app/services/mqtt_service.py#L694-L777)

The `_handleWaveformStream()` function DOES attempt to store waveforms:

```python
# Line 746-762: Storage attempt in waveform stream handler
try:
    # Prepare waveform data for storage
    # ESP32 stream format is compatible with WaveformSnapshotMessage schema
    # Set duration to 0.1 seconds (100ms packet = 0.1s)
    payload['duration'] = 0.1

    # Parse timestamp if needed
    if 'timestamp' in payload:
        timestampStr = payload['timestamp']
        if isinstance(timestampStr, str):
            if timestampStr.endswith('Z'):
                timestampStr = timestampStr.replace('Z', '+00:00')
            payload['timestamp'] = datetime.fromisoformat(timestampStr)

    # Create WaveformSnapshotMessage and store using existing function
    waveformMsg = WaveformSnapshotMessage(**payload)
    await self._storeWaveformSnapshot(waveformMsg)

    # Log storage success (every 10th packet to avoid spam)
    sequence = payload.get('sequence', 0)
    if sequence % 10 == 0:
        logger.debug(f"💾 Stream packet #{sequence} stored to database")

except Exception as e:
    # Don't fail WebSocket broadcast if storage fails
    logger.error(f"Stream packet storage failed (non-critical): {e}", exc_info=True)
```

**Storage Function:** [hospital-backend/app/services/mqtt_service.py:534-585](hospital-backend/app/services/mqtt_service.py#L534-L585)

```python
async def _storeWaveformSnapshot(self, waveformMsg: WaveformSnapshotMessage):
    """Store waveform snapshot in TimescaleDB waveform_snapshots table"""
    try:
        async with getTimescaleConnection() as tsConn:
            # Convert waveform data to JSON
            ecgLimbJson = None
            ecgPrecordialJson = None
            ecgDerivedJson = None
            # ... (converts Pydantic models to JSON)

            # Insert into waveform_snapshots table
            await tsConn.execute("""
                INSERT INTO waveform_snapshots (
                    time, "patientId", "deviceId", mode, "sampleRate", duration,
                    "ecgLimbLeads", "ecgPrecordialLeads", "ecgDerivedLeads", "ecgEvents",
                    "eegFrontalChannels", "eegCentralChannels", "eegOccipitalChannels", "eegAnalysis",
                    quality, sequence, compression, metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
                )
            """,
                waveformMsg.timestamp, waveformMsg.patientId, waveformMsg.deviceId,
                waveformMsg.mode, waveformMsg.sampleRate, waveformMsg.duration,
                ecgLimbJson, ecgPrecordialJson, ecgDerivedJson, ecgEventsJson,
                eegFrontalJson, eegCentralJson, eegOccipitalJson, eegAnalysisJson,
                qualityJson, waveformMsg.sequence, waveformMsg.compression,
                json.dumps(waveformMsg.metadata) if waveformMsg.metadata else None
            )
    except Exception as e:
        logger.error(f"❌ Failed to store waveform in TimescaleDB: {e}", exc_info=True)
```

---

## 🐛 Probable Root Causes

### 1. **Silent Exception in Storage Function**
The code has a try/except block that catches errors and logs them with `logger.error()`, but:
- Backend logs are **NOT being written to file** (last log entry: October 11, 2025)
- Console output may not be captured if backend is running in background
- Storage errors are **silently failing** without user visibility

### 2. **Pydantic Validation Failure**
The `WaveformSnapshotMessage(**payload)` validation may be failing because:
- ESP32 sends delta-encoded format: `{leadI: {baseline, deltas}}`
- Pydantic model may expect different field structure
- Validation errors would be caught by outer exception handler

### 3. **TimescaleDB Connection Issue**
- Connection to port 5433 may be failing intermittently
- `getTimescaleConnection()` may be returning None or timing out
- Database connection errors would be caught by exception handler

### 4. **Missing `duration` Field in Payload**
ESP32 may not be sending `duration` field, and code adds it manually:
```python
payload['duration'] = 0.1  # Added by backend
```
But if Pydantic validation runs BEFORE this line, validation would fail.

---

## 🔧 Recommended Diagnostic Steps

### Step 1: Enable Detailed Logging
Add explicit print statements to see what's happening:

```python
# In _handleWaveformStream() at line 760:
print(f"🔍 DEBUG: Attempting to store waveform for patient {payload.get('patientId')}")
print(f"   Payload keys: {payload.keys()}")
print(f"   Has duration: {'duration' in payload}")
print(f"   Sample rate: {payload.get('sampleRate')}")

try:
    waveformMsg = WaveformSnapshotMessage(**payload)
    print(f"✅ DEBUG: Pydantic validation passed")
    await self._storeWaveformSnapshot(waveformMsg)
    print(f"✅ DEBUG: Storage function completed")
except Exception as e:
    print(f"❌ DEBUG: Storage failed: {e}")
    import traceback
    traceback.print_exc()
```

### Step 2: Verify Pydantic Model Compatibility
Check if ESP32 delta-encoded format matches backend Pydantic expectations:

**ESP32 Sends:**
```json
{
  "deviceId": "fit-00001",
  "patientId": "081a5294-...",
  "timestamp": "2025-11-03T02:13:23.000Z",
  "mode": "ecg",
  "sampleRate": 500,
  "sequence": 123,
  "ecgWaveform": {
    "limb": {
      "leadI": {"baseline": 32768, "deltas": [1, -2, 3, ...]},
      "leadII": {"baseline": 32770, "deltas": [0, 1, -1, ...]},
      "leadIII": {"baseline": 2, "deltas": [-1, 1, 0, ...]}
    }
  }
}
```

**Backend Expects:** (from [neural_vitals.py:295-323](hospital-backend/app/models/neural_vitals.py#L295-L323))
```python
class ChannelData(BaseModel):
    baseline: int
    deltas: List[int]

class ECGLimbLeads(BaseModel):
    leadI: ChannelData
    leadII: ChannelData
    leadIII: ChannelData

class WaveformSnapshotMessage(BaseModel):
    deviceId: str
    patientId: str
    timestamp: datetime
    mode: Literal['ecg', 'eeg']
    sampleRate: int = Field(..., description="Sampling rate in Hz")  # REQUIRED
    duration: int = Field(..., description="Duration in seconds")    # REQUIRED ⚠️
    ecgWaveform: Optional[ECGWaveformData] = None
```

**ISSUE:** ESP32 doesn't send `duration` field! Backend adds it manually, but Pydantic validation may run first.

### Step 3: Check Database Connection
Verify TimescaleDB connection is working:

```bash
cd hospital-backend
python -c "
import asyncio
from app.core.database import getTimescaleConnection

async def test():
    try:
        async with getTimescaleConnection() as conn:
            result = await conn.fetchval('SELECT COUNT(*) FROM waveform_snapshots')
            print(f'✅ TimescaleDB connection OK - {result} waveform rows')
    except Exception as e:
        print(f'❌ TimescaleDB connection failed: {e}')

asyncio.run(test())
"
```

### Step 4: Test Manual Waveform Insert
Try inserting a test waveform directly:

```bash
cd hospital-backend
python -c "
import asyncio
import json
from datetime import datetime
from app.core.database import getTimescaleConnection

async def test():
    async with getTimescaleConnection() as conn:
        testData = {
            'leadI': {'baseline': 32768, 'deltas': [1, -2, 3]},
            'leadII': {'baseline': 32770, 'deltas': [0, 1, -1]},
            'leadIII': {'baseline': 2, 'deltas': [-1, 1, 0]}
        }
        await conn.execute('''
            INSERT INTO waveform_snapshots (
                time, \"patientId\", \"deviceId\", mode, \"sampleRate\", duration,
                \"ecgLimbLeads\"
            ) VALUES (\$1, \$2, \$3, \$4, \$5, \$6, \$7)
        ''',
            datetime.now(),
            '081a5294-da91-4c74-bb8a-e5062f5851dd',
            'fit-00001',
            'ecg',
            500,
            0.1,
            json.dumps(testData)
        )
        print('✅ Test waveform inserted successfully')

asyncio.run(test())
"
```

---

## 🎯 Most Likely Fix

**Root Cause:** Pydantic validation fails because `duration` field is missing from ESP32 payload.

**Solution 1: Fix ESP32 Firmware (Recommended)**

Update ESP32 firmware to include `duration` field:

**File:** [esp32_hospital_watch_complete.ino:1948-1949](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1948-L1949)

```cpp
// Already present in v5.2.5! ✅
doc["sequence"] = waveformSequenceCounter++;
doc["duration"] = 0.1;  // ✅ v5.2.5: 100ms packet = 0.1 seconds
doc["sampleRate"] = 500;
```

**WAIT - ESP32 v5.2.5 ALREADY SENDS `duration`!** This should be working!

**Solution 2: Check Pydantic Model for `duration` Field Type**

The issue might be that Pydantic expects `duration` as **integer** (seconds), but ESP32 sends **float** (0.1 seconds).

**Backend Pydantic Model:**
```python
duration: int = Field(..., description="Duration in seconds")  # ⚠️ INT, not FLOAT!
```

**ESP32 Sends:**
```cpp
doc["duration"] = 0.1;  // ⚠️ FLOAT (0.1 seconds)
```

**FIX:** Change Pydantic model to accept float:
```python
duration: float = Field(..., description="Duration in seconds")  # ✅ FLOAT
```

---

## 📋 Summary

**Situation:**
- Waveforms display correctly in frontend (delta decoding works)
- Waveforms are NOT being stored in TimescaleDB database
- Code exists to store waveforms but appears to fail silently

**Most Likely Root Cause:**
- Pydantic validation fails because `duration` field type mismatch (int vs float)
- ESP32 sends `duration: 0.1` (float)
- Backend expects `duration: int`
- Validation error is caught by exception handler and logged (but logs aren't visible)

**Recommended Immediate Action:**
1. Add debug print statements to see actual error messages
2. Fix Pydantic model `duration` field type from `int` to `float`
3. Restart backend
4. Verify waveforms are now being stored in database

---

## 🚀 Next Steps

Once we identify and fix the storage issue, we should see:
- Waveforms accumulating in `waveform_snapshots` table
- Database growing at ~10 rows/second per patient (100ms packets = 10 msg/sec)
- Historical waveform data available for analysis
- 51% bandwidth savings realized in database storage as well as transmission
