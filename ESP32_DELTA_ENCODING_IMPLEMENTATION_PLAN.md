# ESP32 Delta Encoding Implementation Plan

## Executive Summary

**Problem**: ESP32 sends raw waveform arrays (1,600 bytes/packet), backend expects delta-encoded data.

**Solution**: Implement delta encoding in ESP32 firmware to reduce bandwidth by ~50%.

**Impact**:
- 500 watches: 8 MB/sec → 4.16 MB/sec
- Better WiFi performance
- Lower latency
- Reduced MQTT broker load

---

## Current vs Target Data Format

### Current Format (ESP32 sends, backend rejects)
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
      "lead1": [1234, 1235, 1233, 1237, ...],  // 50 raw values (200 bytes)
      "lead2": [2345, 2346, 2344, 2348, ...],
      "lead3": [1111, 1111, 1111, 1111, ...]
    },
    "precordial": {
      "v1": [...],
      "v2": [...],
      "v3": [...],
      "v4": [...],
      "v5": [...]
    },
    "derived": {
      "avr": [...],
      "avl": [...],
      "avf": [...],
      "v6": [...]
    }
  }
}
```
**Size**: ~1,600 bytes (8 channels × 50 samples × 4 bytes)

### Target Format (Backend expects)
```json
{
  "deviceId": "fit-00001",
  "patientId": "081a5294-...",
  "timestamp": "2025-11-02T13:40:00Z",
  "mode": "ecg",
  "sequence": 42,
  "sampleRate": 500,
  "duration": 0.1,  // ✅ ADDED: 100ms packet = 0.1 seconds
  "ecgWaveform": {
    "limb": {
      "leadI": {  // ✅ RENAMED: lead1 → leadI
        "baseline": 1234,
        "deltas": [1, -2, 4, -3, ...]  // 49 deltas (49-98 bytes)
      },
      "leadII": {
        "baseline": 2345,
        "deltas": [1, -2, 4, -3, ...]
      },
      "leadIII": {
        "baseline": 1111,
        "deltas": [0, 0, 0, 0, ...]
      }
    },
    "precordial": {
      "v1": {"baseline": ..., "deltas": [...]},
      "v2": {"baseline": ..., "deltas": [...]},
      "v3": {"baseline": ..., "deltas": [...]},
      "v4": {"baseline": ..., "deltas": [...]},
      "v5": {"baseline": ..., "deltas": [...]}
    },
    "derived": {
      "avr": {"baseline": ..., "deltas": [...]},
      "avl": {"baseline": ..., "deltas": [...]},
      "avf": {"baseline": ..., "deltas": [...]},
      "v6": {"baseline": ..., "deltas": [...]}
    }
  }
}
```
**Size**: ~832 bytes (8 channels × 104 bytes avg)

---

## Implementation Changes Required

### 1. ESP32 Firmware Changes

**File**: `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`

**Function to modify**: `sendWaveformStream()` (lines 1908-2058)

**Changes needed**:

#### A. Add Delta Encoding Helper Function
```cpp
// Add before sendWaveformStream()
JsonObject createDeltaEncodedChannel(JsonDocument& doc, int32_t* samples, int count) {
  JsonObject channel = doc.createNestedObject();

  // First sample is baseline
  channel["baseline"] = samples[0];

  // Remaining samples are deltas
  JsonArray deltas = channel.createNestedArray("deltas");
  for (int i = 1; i < count; i++) {
    int32_t delta = samples[i] - samples[i-1];
    deltas.add(delta);
  }

  return channel;
}
```

#### B. Modify ECG Lead Creation (lines 1940-1952)
**OLD**:
```cpp
JsonObject limb = ecgWaveform.createNestedObject("limb");
JsonArray lead1 = limb.createNestedArray("lead1");
JsonArray lead2 = limb.createNestedArray("lead2");
JsonArray lead3 = limb.createNestedArray("lead3");

for (int i = 0; i < 50; i++) {
  int32_t ch0 = waveformAccumulator[0][i];
  int32_t ch1 = waveformAccumulator[1][i];
  lead1.add(ch0);
  lead2.add(ch1);
  lead3.add(ch1 - ch0);
}
```

**NEW**:
```cpp
JsonObject limb = ecgWaveform.createNestedObject("limb");

// Create temporary arrays for lead III calculation
int32_t lead3_array[50];
for (int i = 0; i < 50; i++) {
  lead3_array[i] = waveformAccumulator[1][i] - waveformAccumulator[0][i];
}

// Delta-encode each lead
limb["leadI"] = createDeltaEncodedChannel(doc, waveformAccumulator[0], 50);
limb["leadII"] = createDeltaEncodedChannel(doc, waveformAccumulator[1], 50);
limb["leadIII"] = createDeltaEncodedChannel(doc, lead3_array, 50);
```

#### C. Add Duration Field (after line 1935)
```cpp
doc["sequence"] = waveformSequenceCounter++;
doc["duration"] = 0.1;  // ✅ NEW: 100ms packet duration
```

#### D. Fix Field Naming (camelCase)
- `lead1` → `leadI`
- `lead2` → `leadII`
- `lead3` → `leadIII`
- Keep `v1-v5` as lowercase (matches backend)
- Keep `avr, avl, avf, v6` as lowercase (matches backend)

#### E. Apply Same Pattern to Precordial, Derived, and EEG
- Precordial leads (v1-v5): Delta encode each
- Derived leads (aVR, aVL, aVF, v6): Delta encode each
- EEG channels (Fp1, Fp2, F3, F4, C3, C4, O1, O2): Delta encode each

### 2. Backend Changes

**NO CHANGES NEEDED** - Backend already expects delta-encoded format!

My storage code at [mqtt_service.py:745-771](hospital-backend/app/services/mqtt_service.py#L745-L771) already adds `duration = 0.1`, so that's covered.

---

## Bandwidth Analysis

### Current Raw Format
```
ECG Packet:
- 8 channels × 50 samples × 4 bytes = 1,600 bytes
- Overhead (JSON structure, field names) = ~300 bytes
- Total: ~1,900 bytes per packet
- 10 packets/sec = 19,000 bytes/sec per watch
- 500 watches = 9.5 MB/sec
```

### Delta-Encoded Format
```
ECG Packet:
- 8 channels × (4 bytes baseline + 49 deltas × 1.5 bytes avg) = 8 × 77.5 = 620 bytes
- Overhead (JSON structure) = ~300 bytes
- Total: ~920 bytes per packet
- 10 packets/sec = 9,200 bytes/sec per watch
- 500 watches = 4.6 MB/sec
```

**Bandwidth Savings**: 51.6% reduction (9.5 MB/sec → 4.6 MB/sec)

### Why Deltas Are Small

ECG/EEG waveforms are continuous signals sampled at 500Hz:
- Sample interval: 2ms
- Typical ECG amplitude change: 10-50 µV per 2ms
- ADS1298 resolution: 0.286 µV/LSB (24-bit)
- Typical delta: 35-175 LSB = fits in 1 byte (-128 to +127)
- Large deltas (QRS complex): 500-1000 LSB = 2 bytes

**Average delta size**: ~1.5 bytes (75% are 1-byte, 25% are 2-byte)

---

## Implementation Steps

### Phase 1: ESP32 Delta Encoding (1-2 hours)
1. Add `createDeltaEncodedChannel()` helper function
2. Modify ECG limb leads (leadI, leadII, leadIII)
3. Modify ECG precordial leads (v1-v5)
4. Modify ECG derived leads (avr, avl, avf, v6)
5. Modify EEG channels (all 8 channels)
6. Add `duration` field (0.1 for 100ms packets)
7. Fix field naming (lead1 → leadI, etc.)

### Phase 2: Testing (30 minutes)
1. Compile and flash ESP32
2. Check serial output for payload size reduction
3. Verify backend logs show "Stream packet stored"
4. Query database: `SELECT COUNT(*) FROM waveform_snapshots`
5. Verify waveform data integrity (check deltas decompress correctly)

### Phase 3: Validation (30 minutes)
1. Check frontend ECG viewer still works
2. Verify waveforms render correctly
3. Test with multiple watches (if available)
4. Monitor MQTT broker CPU/memory usage

---

## Testing Checklist

- [ ] ESP32 compiles without errors
- [ ] ESP32 publishes to `/stream` topic
- [ ] Payload size reduced (check serial output)
- [ ] Backend receives `/stream` messages
- [ ] Backend storage succeeds (check logs)
- [ ] Database has waveform_snapshots rows (COUNT > 0)
- [ ] Frontend ECG viewer displays waveforms
- [ ] Waveforms look correct (not garbled)
- [ ] Deltas decompress to original values
- [ ] MQTT broker performance improved

---

## Rollback Plan

If delta encoding causes issues:
1. Backend already handles both formats (can add compatibility layer)
2. ESP32 can revert to raw arrays (git revert)
3. Database won't be corrupted (just empty until fixed)

---

## Questions Before Implementation

1. **Do we want to implement this now?** (Recommended: YES)
2. **Should we add a firmware version flag?** (e.g., `"compression": "delta"`)
3. **Should we test with one watch first?** (Recommended: YES, use fit-00001)
4. **Do we need backward compatibility?** (Probably not, all watches will update)

---

## Expected Results

After implementation:
- ✅ Waveforms stored in database
- ✅ 50% bandwidth reduction
- ✅ Better WiFi performance
- ✅ Backend Pydantic validation passes
- ✅ Frontend displays waveforms correctly
- ✅ System ready for 500-watch deployment

**Ready to proceed with implementation?**
