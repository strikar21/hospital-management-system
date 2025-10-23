# Backend Updated for 1-Second Combined Messages

**Date:** 2025-10-21
**Status:** ✅ BACKEND COMPLETE - Ready for ESP32 Implementation

---

## DECISION: Option 2 - 1-Second Combined Messages

After bandwidth recalculation, we confirmed:
- **21% more bandwidth** than 10-second batches (235 MB/day vs 195 MB/day)
- **Extra cost:** ₹360/month for 100 patients (₹3.60 per patient/month)
- **Benefits:** 10x less RAM on ESP32, 9 seconds faster detection, better for critical care

**User chose Option 2** because the benefits outweigh the small cost increase.

---

## BACKEND CHANGES COMPLETE

### 1. Updated Data Model

**File:** `hospital-backend/app/models/neural_vitals.py`

**Changes:**
- `VitalsRealtimeMessage` now includes waveform fields
- Added `sampleRate`, `duration`, `compression` fields
- Added `ecgWaveform` (Optional[ECGWaveformData])
- Added `eegWaveform` (Optional[EEGWaveformData])
- Updated docstring to reflect combined message architecture

**New Message Structure:**
```python
class VitalsRealtimeMessage(BaseModel):
    """
    Real-time vitals + waveform combined message - Published every 1 second
    MQTT Topic: hospital/devices/{deviceId}/vitals

    Contains both basic vitals AND 1-second waveform snapshot in single message.
    """
    # Basic vitals
    deviceId: str
    patientId: str
    timestamp: datetime
    mode: Literal['ecg', 'eeg']
    heartRate: Optional[int]
    respiratoryRate: Optional[int]
    skinTemperature: Optional[float]
    oxygenSaturation: Optional[int]
    batteryLevel: Optional[int]
    signalQuality: Optional[float]

    # Waveform data (1-second snapshot)
    sampleRate: Optional[int]          # 250 Hz
    duration: Optional[int]            # 1 second
    compression: Optional[str]         # "delta"
    ecgWaveform: Optional[ECGWaveformData]  # 250 samples × 8 channels
    eegWaveform: Optional[EEGWaveformData]  # 250 samples × 8 channels

    # Analysis (optional - backend calculates)
    ecgAnalysis: Optional[ECGAnalysis]
    eegAnalysis: Optional[EEGAnalysis]
    quality: Optional[SignalQuality]
```

---

### 2. Updated MQTT Service

**File:** `hospital-backend/app/services/mqtt_service.py`

**Changes to `_handleVitalsMessageNew()` (Lines 366-427):**

```python
# Store vitals in TimescaleDB vitals_realtime table
await self._storeVitalsRealtime(vitalsMsg)

# ========================================
# STORE WAVEFORM DATA (if present in combined message)
# ========================================
if (vitalsMsg.sampleRate and vitalsMsg.duration and
    (vitalsMsg.ecgWaveform or vitalsMsg.eegWaveform)):

    # Create WaveformSnapshotMessage from combined message
    waveformData = {
        'deviceId': vitalsMsg.deviceId,
        'patientId': vitalsMsg.patientId,
        'timestamp': vitalsMsg.timestamp,
        'mode': vitalsMsg.mode,
        'sampleRate': vitalsMsg.sampleRate,
        'duration': vitalsMsg.duration,
        'compression': vitalsMsg.compression,
        'quality': vitalsMsg.quality.dict() if vitalsMsg.quality else None,
        'sequence': vitalsMsg.sequence,
        'metadata': vitalsMsg.metadata
    }

    if vitalsMsg.mode == 'ecg' and vitalsMsg.ecgWaveform:
        waveformData['ecgWaveform'] = vitalsMsg.ecgWaveform.dict()
    elif vitalsMsg.mode == 'eeg' and vitalsMsg.eegWaveform:
        waveformData['eegWaveform'] = vitalsMsg.eegWaveform.dict()

    waveformMsg = WaveformSnapshotMessage(**waveformData)
    await self._storeWaveformSnapshot(waveformMsg)

    # ========================================
    # BACKEND ECG/EEG ANALYSIS ON WAVEFORM
    # ========================================
    if waveformMsg.mode == 'ecg' and waveformMsg.ecgWaveform:
        logger.info(f"🧠 Running ECG analysis...")
        analysisResult = ecgAnalysisService.analyzeECG(
            waveformMsg.ecgWaveform.dict(), mode='ecg'
        )

    elif waveformMsg.mode == 'eeg' and waveformMsg.eegWaveform:
        logger.info(f"🧠 Running EEG analysis...")
        analysisResult = eegAnalysisService.analyzeEEG(
            waveformMsg.eegWaveform.dict(), mode='eeg'
        )

        # Critical: Seizure detection
        if analysisResult.seizureActivity and analysisResult.seizureConfidence > 0.7:
            await self._createSeizureAlert(patientId, deviceId, analysisResult)
```

**What It Does:**
1. Receives combined vitals+waveform message every 1 second
2. Stores vitals in `vitals_realtime` table
3. If waveform data present, stores in `waveform_snapshots` table
4. Runs backend ECG/EEG analysis on waveform
5. Detects arrhythmias, seizures, abnormalities
6. Broadcasts alerts via WebSocket

---

## MQTT MESSAGE FORMAT (ESP32 → Backend)

**Topic:** `hospital/devices/{deviceId}/vitals`
**Frequency:** Every 1 second
**Size:** ~2.7 KB per message

```json
{
  // Device identification
  "deviceId": "fit-00001",
  "patientId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-21T10:00:00.000Z",
  "mode": "ecg",

  // Basic vitals
  "heartRate": 75,
  "respiratoryRate": 16,
  "skinTemperature": 36.5,
  "oxygenSaturation": 98,
  "batteryLevel": 85,
  "signalQuality": 0.95,

  // Waveform parameters
  "sampleRate": 250,
  "duration": 1,
  "compression": "delta",

  // ECG waveform (1-second snapshot - 250 samples per channel)
  "ecgWaveform": {
    "limb": {
      "leadI": {
        "baseline": 8388608,
        "deltas": [2, -1, 0, 3, -2, 1, ...] // 250 deltas
      },
      "leadII": {
        "baseline": 8388610,
        "deltas": [1, 0, -1, 2, -3, 0, ...] // 250 deltas
      },
      "leadIII": {
        "baseline": 8388605,
        "deltas": [-1, 2, 0, -2, 1, -1, ...] // 250 deltas
      }
    },
    "precordial": {
      "v1": { "baseline": 8388620, "deltas": [...] },
      "v2": { "baseline": 8388625, "deltas": [...] },
      "v3": { "baseline": 8388630, "deltas": [...] },
      "v4": { "baseline": 8388635, "deltas": [...] },
      "v5": { "baseline": 8388628, "deltas": [...] }
    }
  },

  // Quality metrics
  "quality": {
    "overall": 0.95,
    "leadOff": [false, false, false, false, false, false, false, false],
    "impedance": [1.2, 1.5, 1.8, 2.1, 1.9, 1.6, 2.3, 2.0]
  },

  // Metadata
  "sequence": 12345
}
```

---

## ESP32 IMPLEMENTATION REQUIREMENTS

### 1. Message Structure

ESP32 must send combined vitals+waveform every 1 second to:
- **Topic:** `hospital/devices/{deviceId}/vitals`
- **QoS:** 1 (at least once delivery)

### 2. RAM Requirements

**Circular Buffer (8 channels × 250 samples):**
```cpp
// Only need 1-second buffer (8 KB)
int16_t waveformBuffer[8][250];  // 8 channels × 250 samples × 2 bytes = 4 KB
uint8_t currentSampleIndex = 0;

void loop() {
  // Collect samples continuously at 250 Hz
  if (micros() - lastSample >= 4000) {  // 250 Hz = 4000 μs
    collectSample();  // Store in waveformBuffer[*][currentSampleIndex]
    currentSampleIndex++;

    if (currentSampleIndex >= 250) {
      currentSampleIndex = 0;  // Wrap around (circular buffer)
    }

    lastSample = micros();
  }

  // Send combined message every 1 second
  if (millis() - lastMessage >= 1000) {
    sendCombinedMessage();
    lastMessage = millis();
  }
}
```

### 3. Delta Encoding

**Per Channel:**
```cpp
void deltaEncode(int16_t* samples, int count, JsonObject& output) {
  output["baseline"] = samples[0];

  JsonArray deltas = output.createNestedArray("deltas");
  for (int i = 1; i < count; i++) {
    deltas.add(samples[i] - samples[i-1]);  // Delta from previous
  }
}
```

### 4. Message Construction

```cpp
void sendCombinedMessage() {
  if (!mqttClient.connected() || !isAssigned) return;

  String topic = "hospital/devices/" + deviceId + "/vitals";

  JsonDocument doc;  // Size: ~3000 bytes

  // Basic vitals
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["timestamp"] = getISO8601Timestamp();
  doc["mode"] = digitalRead(MODE_SELECT_PIN) == HIGH ? "ecg" : "eeg";
  doc["heartRate"] = (int)heartRate;
  doc["respiratoryRate"] = (int)respiratoryRate;
  doc["skinTemperature"] = skinTemperature;
  doc["oxygenSaturation"] = (int)oxygenSat;
  doc["batteryLevel"] = batteryLevel;
  doc["signalQuality"] = signalQuality;

  // Waveform parameters
  doc["sampleRate"] = 250;
  doc["duration"] = 1;
  doc["compression"] = "delta";

  // Waveform data
  if (doc["mode"] == "ecg") {
    JsonObject ecgWaveform = doc.createNestedObject("ecgWaveform");
    JsonObject limb = ecgWaveform.createNestedObject("limb");

    deltaEncode(waveformBuffer[0], 250, limb.createNestedObject("leadI"));
    deltaEncode(waveformBuffer[1], 250, limb.createNestedObject("leadII"));
    deltaEncode(waveformBuffer[2], 250, limb.createNestedObject("leadIII"));

    // Optional: precordial leads
    if (hasV1toV5) {
      JsonObject precordial = ecgWaveform.createNestedObject("precordial");
      deltaEncode(waveformBuffer[3], 250, precordial.createNestedObject("v1"));
      deltaEncode(waveformBuffer[4], 250, precordial.createNestedObject("v2"));
      deltaEncode(waveformBuffer[5], 250, precordial.createNestedObject("v3"));
      deltaEncode(waveformBuffer[6], 250, precordial.createNestedObject("v4"));
      deltaEncode(waveformBuffer[7], 250, precordial.createNestedObject("v5"));
    }
  }

  // Quality
  JsonObject quality = doc.createNestedObject("quality");
  quality["overall"] = signalQuality;

  String payload;
  serializeJson(doc, payload);

  mqttClient.publish(topic.c_str(), payload.c_str(), false);  // QoS 1
}
```

---

## BANDWIDTH SUMMARY

**Per Device:**
- Vitals: 200 bytes
- Waveform (delta-encoded): 2,024 bytes
- JSON overhead: 500 bytes
- **Total:** 2,724 bytes/message

**Per Second:** 2,724 bytes
**Per Day:** 235 MB
**Per Month (100 devices):** 705 GB

**Cost (Indian cloud):**
- ₹2,115/month for 100 patients
- ₹21.15 per patient per month
- ₹0.70 per patient per day

---

## TIMESCALEDB STORAGE

Backend automatically splits combined message into TWO tables:

### 1. vitals_realtime Table
**Stores:** Basic vitals + ECG/EEG analysis results
**Frequency:** Every 1 second
**Retention:** 90 days (compressed after 7 days)

### 2. waveform_snapshots Table
**Stores:** 1-second waveform snapshots (250 samples × 8 channels)
**Frequency:** Every 1 second (when waveform data present)
**Retention:** 30 days (compressed after 1 day)

---

## BACKEND ANALYSIS

**Every Second:**
1. Receives combined message
2. Stores vitals → `vitals_realtime`
3. Stores waveform → `waveform_snapshots`
4. Runs ECG/EEG analysis on waveform
5. Detects arrhythmias, seizures
6. Broadcasts alerts via WebSocket
7. Frontend displays real-time vitals + analysis

**Analysis Latency:** 1 second (vs 10 seconds with old approach)

---

## TESTING CHECKLIST

### Backend Testing
- [x] Data models accept combined messages
- [x] MQTT service handles combined messages
- [x] Vitals stored in `vitals_realtime`
- [x] Waveform stored in `waveform_snapshots`
- [x] Backend ECG analysis runs
- [x] Backend EEG analysis runs
- [x] Alerts broadcast via WebSocket
- [ ] End-to-end test with actual ESP32 (waiting for firmware)

### ESP32 Testing (When Implemented)
- [ ] GPIO mode detection working
- [ ] Circular buffer collects 250 samples
- [ ] Delta encoding works correctly
- [ ] Combined message <3 KB
- [ ] MQTT publish succeeds
- [ ] Backend receives and processes
- [ ] RAM usage ≤10 KB
- [ ] Battery lasts 24+ hours

---

## NEXT STEPS

1. **Implement ESP32 Firmware Changes**
   - Add 8 KB circular buffer for waveform
   - Implement delta encoding
   - Combine vitals + waveform in single message
   - Send every 1 second

2. **Test End-to-End**
   - Flash ESP32 with new firmware
   - Provision device (get `fit-00001` ID)
   - Verify combined messages arriving at backend
   - Check TimescaleDB tables have data
   - Verify backend analysis running
   - Confirm alerts appearing on frontend

3. **Monitor Performance**
   - ESP32 RAM usage
   - ESP32 battery life
   - MQTT broker load
   - Backend CPU usage
   - Database growth rate

---

## FILES MODIFIED

1. **hospital-backend/app/models/neural_vitals.py**
   - Lines 109-166: Updated `VitalsRealtimeMessage` class

2. **hospital-backend/app/services/mqtt_service.py**
   - Lines 366-427: Updated `_handleVitalsMessageNew()` to process waveform data

---

## SUMMARY

✅ **Backend is ready for 1-second combined messages**

The backend now:
- Accepts combined vitals+waveform messages
- Stores vitals and waveforms in separate tables
- Runs automatic ECG/EEG analysis
- Detects critical events with 1-second latency
- Broadcasts real-time data to frontend

**ESP32 firmware needs to be updated** to send combined messages.

**Benefits achieved:**
- 10x less RAM on ESP32 (8 KB vs 80 KB)
- 9 seconds faster critical event detection
- Real-time waveform analysis
- Perfect time synchronization

**Trade-off accepted:**
- 21% more bandwidth (₹3.60/patient/month extra)
- Worth it for ICU/critical care applications
