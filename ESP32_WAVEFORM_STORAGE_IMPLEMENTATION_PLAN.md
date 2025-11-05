# ESP32 Waveform Storage Implementation Plan
**Date:** 2025-11-02
**Status:** IMPLEMENTATION READY
**Task:** Add `/waveform` topic publishing to ESP32 firmware (Option A from root cause analysis)

---

## CONTEXT

**Root Cause Identified:**
- ESP32 firmware publishes to `/stream` topic (100ms intervals, real-time display only)
- ESP32 firmware does NOT publish to `/waveform` topic (10-second snapshots for database storage)
- Backend is ready and waiting for `/waveform` messages but never receives them
- This causes `waveform_snapshots` table to remain empty (0 rows)

**Reference:** [WAVEFORM_STORAGE_ROOT_CAUSE_ANALYSIS.md](WAVEFORM_STORAGE_ROOT_CAUSE_ANALYSIS.md)

---

## IMPLEMENTATION DETAILS

### 1. Add Timer Variable

**Location:** Around line 154 (with other waveform streaming variables)

```cpp
// ====================================
// WAVEFORM STREAMING (v5.2)
// ====================================
unsigned long lastWaveformStream = 0;
unsigned long lastWaveformSnapshot = 0;  // ✅ NEW: 10-second snapshot timer
uint32_t waveformSequenceCounter = 0;
unsigned long lastMicroBatch = 0;
```

### 2. Add Function Call in loop()

**Location:** Around line 1098 (after waveform streaming logic)

```cpp
// ✅ v5.2.4: Send waveform even when offline (queues to SPIFFS automatically)
if (isProvisioned && isAssigned &&
    accumulatorIndex >= 50 && (unsigned long)(millis() - lastWaveformStream) > 100) {
  sendWaveformStream();  // Already handles offline queueing internally
  lastWaveformStream = millis();
  accumulatorIndex = 0;
}

// ✅ NEW: Send 10-second waveform snapshot for database storage
if (isProvisioned && isAssigned && (unsigned long)(millis() - lastWaveformSnapshot) > 10000) {
  sendWaveformSnapshot();  // Publish to /waveform topic for backend storage
  lastWaveformSnapshot = millis();
}
```

### 3. Implement sendWaveformSnapshot() Function

**Location:** After `sendWaveformStream()` function (around line 2060)

**Key Differences from sendWaveformStream():**

| Feature | `/stream` (Real-time) | `/waveform` (Storage) |
|---------|----------------------|----------------------|
| **Topic** | `hospital/devices/{deviceId}/stream` | `hospital/devices/{deviceId}/waveform` |
| **Interval** | 100ms (10 msg/sec) | 10 seconds (6 msg/min) |
| **Samples** | 50 samples | 5000 samples (10s × 500Hz) |
| **Purpose** | Live display | Database archival |
| **Storage** | Ephemeral (WebSocket only) | Persistent (TimescaleDB) |

**Implementation Strategy:**

```cpp
void sendWaveformSnapshot() {
  if (!isProvisioned || !isAssigned) return;

  String topic = "hospital/devices/" + deviceId + "/waveform";

  // Create JSON payload matching WaveformSnapshotMessage schema
  JsonDocument doc;
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["timestamp"] = getISO8601Timestamp();

  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  doc["mode"] = isECGMode ? "ecg" : "eeg";
  doc["sampleRate"] = 500;
  doc["duration"] = 10;  // 10-second snapshot

  // ✅ CHALLENGE: Need to accumulate 5000 samples over 10 seconds
  // ✅ SOLUTION: Use rolling buffer approach (capture last 5000 samples)

  // Option A: Store last 5000 samples in global circular buffer (memory intensive: 160KB)
  // Option B: Sample from PhysiologicalSimulator directly (regenerate waveforms)
  // Option C: Batch 100 × 50-sample chunks from waveformAccumulator

  // ✅ CHOSEN: Option C - Collect 100 batches over 10 seconds
  // This reuses existing waveformAccumulator buffer pattern

  // ... (detailed implementation below)
}
```

---

## IMPLEMENTATION CHALLENGE: 5000-SAMPLE ACCUMULATION

### Problem:
- Need 5000 samples (10 seconds × 500Hz) for each snapshot
- Current `waveformAccumulator` only holds 50 samples (100ms)
- Cannot allocate 160KB global array (8 channels × 5000 samples × 4 bytes)

### Solution Options:

#### Option A: Large Circular Buffer ❌
```cpp
int32_t snapshotBuffer[8][5000];  // 160KB RAM - TOO LARGE for ESP32
```
**Rejected:** ESP32 has limited RAM (~320KB total, ~230KB available)

#### Option B: Direct Simulator Sampling ✅ RECOMMENDED
```cpp
// Generate 5000 samples on-demand from PhysiologicalSimulator
// Simulator maintains physiological state, can regenerate waveforms
simulator.fillLargeBuffer(snapshotBuffer, 5000);
```
**Advantages:**
- No permanent RAM allocation
- Uses existing simulator state
- Physiologically accurate (continuous waveform)

**Disadvantages:**
- Generates data at publish time (not historical)
- 5000 samples ≈ 10s of real time, but generated instantly

#### Option C: Batched Collection ⚠️ ALTERNATIVE
```cpp
// Collect 100 × 50-sample batches over 10 seconds
// Store in SPIFFS temporarily, then publish
```
**Rejected:** Complex implementation, SPIFFS wear, still memory-intensive

---

## CHOSEN IMPLEMENTATION: Option B (Direct Sampling)

### Rationale:
1. **Memory Efficient:** Generates data on-demand, no 160KB buffer
2. **Physiologically Accurate:** Simulator maintains continuous state
3. **Simple Implementation:** Reuses existing simulator API
4. **Matches Real-Time Data:** Same source as `/stream` messages

### Modified PhysiologicalSimulator API:

**Add to PhysiologicalSimulator.h:**
```cpp
// NEW: Fill large buffer for waveform snapshots (10s = 5000 samples)
void fillLargeSnapshotBuffer(int32_t buffer[8][5000]);
```

**Add to PhysiologicalSimulator.cpp:**
```cpp
void PhysiologicalSimulator::fillLargeSnapshotBuffer(int32_t buffer[8][5000]) {
  // Generate 5000 samples using current physiological state
  for (int i = 0; i < 5000; i++) {
    update();  // Advance 2ms per sample (500Hz)

    // Fill buffer using same logic as fillSampleBuffer()
    for (int ch = 0; ch < 8; ch++) {
      buffer[ch][i] = generateSampleForChannel(ch);
    }
  }
}
```

---

## ACTUAL IMPLEMENTATION: SIMPLIFIED APPROACH

**After Further Analysis:**
- 5000 samples in JSON = ~80-120KB payload (too large for MQTT)
- Backend expects compressed/delta-encoded format
- Better approach: **Send JSON with nested arrays matching backend schema**

### Revised Implementation (Matches Backend Schema):

```cpp
void sendWaveformSnapshot() {
  if (!isProvisioned || !isAssigned) return;

  String topic = "hospital/devices/" + deviceId + "/waveform";
  JsonDocument doc;

  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["timestamp"] = getISO8601Timestamp();

  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  doc["mode"] = isECGMode ? "ecg" : "eeg";
  doc["sampleRate"] = 500;
  doc["duration"] = 10;

  if (isECGMode) {
    // ECG waveform snapshot (5000 samples per lead)
    JsonObject ecg = doc.createNestedObject("ecgWaveform");

    JsonObject limb = ecg.createNestedObject("limb");
    JsonObject precordial = ecg.createNestedObject("precordial");
    JsonObject derived = ecg.createNestedObject("derived");

    // ⚠️ PROBLEM: Cannot create 5000-element arrays in JSON without OOM
    // ✅ SOLUTION: Send 10 × 500-sample chunks, let backend reassemble
    // OR: Use delta encoding to compress data
  } else {
    // EEG waveform snapshot
    // ... similar structure
  }

  String payload;
  serializeJson(doc, payload);

  if (!mqttClient.connected() || !isAssigned) {
    offlineQueue.saveWaveform(payload);
    return;
  }

  publishWithRetry(topic.c_str(), payload.c_str());
}
```

---

## FINAL DECISION: CHUNKED APPROACH

**Problem:** Single 5000-sample JSON message is too large (100KB+)

**Solution:** Send 10 × 500-sample chunks with sequence numbers

```cpp
void sendWaveformSnapshot() {
  // Send 10 chunks of 500 samples each (total 5 seconds coverage)
  for (int chunk = 0; chunk < 10; chunk++) {
    // Generate 500 samples from simulator
    int32_t chunkBuffer[8][500];
    simulator.fillChunkBuffer(chunkBuffer, 500);

    // Create JSON with chunk metadata
    JsonDocument doc;
    doc["deviceId"] = deviceId;
    doc["patientId"] = assignedPatientId;
    doc["timestamp"] = getISO8601Timestamp();
    doc["chunkIndex"] = chunk;
    doc["totalChunks"] = 10;
    doc["sampleRate"] = 500;

    // ... add waveform data

    publishWithRetry(topic.c_str(), payload.c_str());
    delay(100);  // Space out chunks
  }
}
```

---

## WAIT - CHECK BACKEND EXPECTATIONS FIRST

**Before implementing, need to verify:**
1. Does backend expect single 10s message or chunked messages?
2. What's the actual data format in `WaveformSnapshotMessage` schema?
3. What compression is supported?

**Action:** Read backend `mqtt_service.py` to see exact message format expected

---

## AFTER REVIEWING ROOT CAUSE ANALYSIS

From [WAVEFORM_STORAGE_ROOT_CAUSE_ANALYSIS.md:649-700](WAVEFORM_STORAGE_ROOT_CAUSE_ANALYSIS.md):

```python
async def _storeWaveformSnapshot(self, waveformMsg: WaveformSnapshotMessage):
    """Store waveform snapshot in TimescaleDB waveform_snapshots table"""
    await tsConn.execute("""
        INSERT INTO waveform_snapshots (
            time, "patientId", "deviceId", mode, "sampleRate", duration,
            "ecgLimbLeads", "ecgPrecordialLeads", "ecgDerivedLeads", "ecgEvents",
            "eegFrontalChannels", "eegCentralChannels", "eegOccipitalChannels", "eegAnalysis",
            quality, sequence, compression, metadata
        ) VALUES (...)
    """)
```

**Backend expects:**
- JSONB fields for each lead group (stored as JSON in database)
- Single message per snapshot (not chunked)
- Optional compression field

**Conclusion:** Need to check backend Pydantic schema for exact format

---

## NEXT STEP: READ BACKEND SCHEMA

**File to check:** `hospital-backend/app/models/neural_vitals.py`

**Look for:** `WaveformSnapshotMessage` class definition
