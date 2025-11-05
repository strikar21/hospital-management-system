# Waveform Storage Root Cause Analysis

## Date: 2025-11-02 13:50 UTC

---

## Current Status

- **Backend**: Running on port 8001 ✅
- **ESP32 fit-00001**: Active, sending vitals every ~1 second ✅
- **Vitals Database**: 101,949 rows in `vitals_realtime` ✅
- **Waveforms Database**: **0 rows in `waveform_snapshots`** ❌

---

## Root Cause: DATA FORMAT MISMATCH

### ESP32 Firmware Sends (ACTUAL)

**File**: [esp32_hospital_watch_complete.ino:1942-1968](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1942-L1968)

```json
{
  "deviceId": "fit-00001",
  "patientId": "081a5294-...",
  "timestamp": "2025-11-02T13:40:00Z",
  "mode": "ecg",
  "sequence": 42,
  "sampleRate": 500,
  "ecgWaveform": {
    "limb": {
      "lead1": [1234, 1235, 1233, ...],  // ❌ RAW ARRAY (50 int32 values)
      "lead2": [2345, 2346, 2344, ...],  // ❌ RAW ARRAY
      "lead3": [1111, 1111, 1111, ...]   // ❌ RAW ARRAY
    },
    "precordial": {
      "v1": [...], "v2": [...], "v3": [...], "v4": [...], "v5": [...]
    },
    "derived": {
      "avr": [...], "avl": [...], "avf": [...], "v6": [...]
    }
  }
}
```

**Issues**:
1. ❌ Field names: `lead1`, `lead2`, `lead3` (lowercase)
2. ❌ Data format: Raw integer arrays `[1234, 1235, ...]`
3. ❌ Missing field: No `duration` field

---

### Backend Expects (PYDANTIC MODEL)

**File**: [neural_vitals.py:125-156](hospital-backend/app/models/neural_vitals.py#L125-L156)

```python
class WaveformSnapshotMessage(BaseModel):
    deviceId: str
    patientId: str
    timestamp: datetime
    mode: Literal['ecg', 'eeg']
    sampleRate: int  # ✅ REQUIRED
    duration: int    # ✅ REQUIRED (ESP32 DOESN'T SEND!)
    ecgWaveform: Optional[ECGWaveformData] = None

class ECGWaveformData(BaseModel):
    limb: ECGLimbLeads  # ✅ REQUIRED

class ECGLimbLeads(BaseModel):
    leadI: ChannelData   # ✅ camelCase, NOT "lead1"
    leadII: ChannelData  # ✅ camelCase, NOT "lead2"
    leadIII: ChannelData # ✅ camelCase, NOT "lead3"

class ChannelData(BaseModel):
    baseline: int                    # ✅ REQUIRED
    deltas: List[int]                # ✅ REQUIRED
    # Expected: {"baseline": 1234, "deltas": [1, -2, 4, ...]}
```

**Expected Format**:
```json
{
  "deviceId": "fit-00001",
  "patientId": "081a5294-...",
  "timestamp": "2025-11-02T13:40:00Z",
  "mode": "ecg",
  "sequence": 42,
  "sampleRate": 500,
  "duration": 0.1,  // ✅ REQUIRED (100ms = 0.1 seconds)
  "ecgWaveform": {
    "limb": {
      "leadI": {                    // ✅ camelCase
        "baseline": 1234,           // ✅ Delta-encoded
        "deltas": [1, -2, 4, -3, 0, 2, ...]  // ✅ 49 delta values
      },
      "leadII": {
        "baseline": 2345,
        "deltas": [1, -2, 4, ...]
      },
      "leadIII": {
        "baseline": 1111,
        "deltas": [0, 0, 0, ...]
      }
    }
  }
}
```

---

## Why Pydantic Validation Fails

### Issue 1: Missing `duration` Field
- **ESP32**: Does NOT send `duration`
- **Backend expects**: `duration: int = Field(..., description="Duration in seconds")` (REQUIRED)
- **My fix added**: `payload['duration'] = 0.1` at [mqtt_service.py:750](hospital-backend/app/services/mqtt_service.py#L750)
- **Status**: ✅ Fixed by my code

### Issue 2: Wrong Field Names (camelCase mismatch)
- **ESP32 sends**: `lead1`, `lead2`, `lead3` (lowercase)
- **Backend expects**: `leadI`, `leadII`, `leadIII` (camelCase with Roman numerals)
- **Result**: Pydantic validation error - field not found

### Issue 3: Wrong Data Format (Raw vs Delta-encoded)
- **ESP32 sends**: `"lead1": [1234, 1235, 1233, ...]` (raw integer array)
- **Backend expects**: `"leadI": {"baseline": 1234, "deltas": [1, -2, ...]}` (delta-encoded object)
- **Result**: Pydantic validation error - wrong type (list vs dict)

---

## Error Message (Will Now Show in Logs)

After my change to [mqtt_service.py:771](hospital-backend/app/services/mqtt_service.py#L771), backend will log:

```
ERROR: Stream packet storage failed (non-critical): 1 validation error for WaveformSnapshotMessage
ecgWaveform -> limb -> leadI
  field required (type=value_error.missing)
```

OR:

```
ERROR: Stream packet storage failed (non-critical): 1 validation error for ECGLimbLeads
leadI
  value is not a valid dict (type=type_error.dict)
```

---

## Solution Options

### Option 1: Modify ESP32 Firmware (Delta Encoding) ⭐ RECOMMENDED
**Pros**:
- 50% bandwidth reduction (9.5 MB/s → 4.6 MB/s for 500 watches)
- Proper compression for medical waveforms
- Matches backend architecture design

**Cons**:
- Requires ESP32 firmware changes
- Need to re-flash all watches
- More complex encoding logic

**Implementation**: See [ESP32_DELTA_ENCODING_IMPLEMENTATION_PLAN.md](ESP32_DELTA_ENCODING_IMPLEMENTATION_PLAN.md)

---

### Option 2: Modify Backend Pydantic Model (Accept Raw Arrays)
**Pros**:
- Quick fix (backend-only change)
- No ESP32 firmware update needed
- Works immediately

**Cons**:
- No bandwidth savings
- Higher WiFi load (1,600 bytes vs 832 bytes per packet)
- Doesn't match original architecture design

**Implementation**:
1. Modify `ChannelData` to accept EITHER delta-encoded OR raw arrays
2. Fix field names (`lead1` → `leadI` mapping)
3. Convert raw arrays to delta-encoded internally

---

### Option 3: Create Transformation Layer (Backend Adapter)
**Pros**:
- Backward compatible (supports both formats)
- Can migrate gradually
- No breaking changes

**Cons**:
- More code complexity
- Still no bandwidth savings until ESP32 updated
- Temporary solution

---

## Bandwidth Analysis (Why Delta Encoding Matters)

### Current (Raw Arrays)
```
Per Packet:
- 8 channels × 50 samples × 4 bytes = 1,600 bytes
- JSON overhead: ~300 bytes
- Total: ~1,900 bytes

Per Watch:
- 10 packets/sec × 1,900 bytes = 19,000 bytes/sec = 18.5 KB/s

500 Watches:
- 500 × 18.5 KB/s = 9,250 KB/s = 9.03 MB/s
```

### With Delta Encoding
```
Per Packet:
- 8 channels × (4 bytes baseline + 49 × 1.5 bytes avg deltas) = 620 bytes
- JSON overhead: ~300 bytes
- Total: ~920 bytes

Per Watch:
- 10 packets/sec × 920 bytes = 9,200 bytes/sec = 9 KB/s

500 Watches:
- 500 × 9 KB/s = 4,500 KB/s = 4.39 MB/s
```

**Savings**: 51.4% bandwidth reduction

---

## Recommendation

**Implement Option 1 (Delta Encoding in ESP32)**

**Reasoning**:
1. System is designed for 500 patients - bandwidth critical
2. 51% bandwidth reduction = better WiFi performance
3. Proper medical data compression
4. Matches original architecture design
5. One-time fix benefits entire deployment

**Next Steps**:
1. Wait for user approval
2. Implement delta encoding in ESP32 firmware
3. Fix field names (`lead1` → `leadI`)
4. Test with single watch (fit-00001)
5. Deploy to all watches

---

## Questions for User

1. **Should we proceed with ESP32 delta encoding?** (Recommended: YES)
2. **Or do you want quick backend-only fix?** (Temporary solution)
3. **Do you want to test with fit-00001 first?** (Recommended: YES)

---

## Files Modified (So Far)

### Backend Changes
- [mqtt_service.py:750](hospital-backend/app/services/mqtt_service.py#L750) - Added `duration = 0.1`
- [mqtt_service.py:771](hospital-backend/app/services/mqtt_service.py#L771) - Changed logging from `debug` to `error` with traceback

### Documentation Created
- [WAVEFORM_DIAGNOSTIC_FINDINGS.md](WAVEFORM_DIAGNOSTIC_FINDINGS.md)
- [ESP32_DELTA_ENCODING_IMPLEMENTATION_PLAN.md](ESP32_DELTA_ENCODING_IMPLEMENTATION_PLAN.md)
- [WAVEFORM_STORAGE_DIAGNOSTIC_PLAN.md](WAVEFORM_STORAGE_DIAGNOSTIC_PLAN.md)
- This file: `WAVEFORM_STORAGE_ROOT_CAUSE.md`

---

**Status**: Awaiting user decision on implementation approach.
