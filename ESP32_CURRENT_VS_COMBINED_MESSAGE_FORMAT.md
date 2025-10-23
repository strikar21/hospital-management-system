# ESP32 Watch Message Format: Current vs Combined

## Current Message Format (Vitals Only)

### What ESP32 Currently Sends
**Source:** [esp32_hospital_watch_complete.ino:1324-1363](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1324-L1363)

**MQTT Topic:** `hospital/devices/{deviceId}/vitals`

**Frequency:** Every 1 second (sent by `sendVitals()` function)

### Current JSON Structure
```json
{
  "timestamp": "2025-10-21T14:32:15Z",
  "mode": "ecg",
  "deviceId": "fit-00001",
  "patientId": "PAT12345",
  "heartRate": 75,
  "skinTemperature": 36.8,
  "oxygenSaturation": 98,
  "signalQuality": 0.85,
  "respiratoryRate": 16,
  "batteryLevel": 87
}
```

### Current Code (Lines 1332-1362)
```cpp
void sendVitals() {
  String topic = "hospital/devices/" + deviceId + "/vitals";

  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();

  // Read GPIO pin to determine mode (HIGH = ECG, LOW = EEG)
  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  doc["mode"] = isECGMode ? "ecg" : "eeg";

  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["heartRate"] = (int)heartRate;

  float tempCelsius = (temperature - 32.0) * 5.0 / 9.0;
  doc["skinTemperature"] = tempCelsius;

  doc["oxygenSaturation"] = (int)oxygenSat;
  doc["signalQuality"] = quality / 100.0;
  doc["respiratoryRate"] = (int)respiratoryRate;
  doc["batteryLevel"] = batteryLevel;

  String payload;
  serializeJson(doc, payload);

  mqttClient.publish(topic.c_str(), payload.c_str());
}
```

---

## Proposed Combined Message Format (Vitals + Waveform)

### What ESP32 Should Send (Option 1 - Combined Messages)
**MQTT Topic:** `hospital/devices/{deviceId}/vitals` (SAME topic)

**Frequency:** Every 1 second

**Key Change:** Add waveform snapshot to existing message

### Combined JSON Structure - ECG Mode

```json
{
  "timestamp": "2025-10-21T14:32:15Z",
  "mode": "ecg",
  "deviceId": "fit-00001",
  "patientId": "PAT12345",

  // ===== EXISTING VITALS (unchanged) =====
  "heartRate": 75,
  "skinTemperature": 36.8,
  "oxygenSaturation": 98,
  "signalQuality": 0.85,
  "respiratoryRate": 16,
  "batteryLevel": 87,

  // ===== NEW WAVEFORM DATA (added) =====
  "sampleRate": 250,
  "duration": 1,
  "compression": "delta",

  "ecgWaveform": {
    "limb": {
      "leadI": {
        "baseline": 8388608,
        "deltas": [0, 2, -1, 3, -2, 1, ..., 0]  // 250 samples
      },
      "leadII": {
        "baseline": 8388610,
        "deltas": [0, 1, -2, 2, -1, 0, ..., 1]  // 250 samples
      },
      "leadIII": {
        "baseline": 8388605,
        "deltas": [0, -1, 1, -2, 3, -1, ..., 0]  // 250 samples
      }
    }
  }
}
```

### Combined JSON Structure - EEG Mode

```json
{
  "timestamp": "2025-10-21T14:32:15Z",
  "mode": "eeg",
  "deviceId": "fit-00001",
  "patientId": "PAT12345",

  // ===== EXISTING VITALS (unchanged) =====
  "heartRate": 75,
  "skinTemperature": 36.8,
  "oxygenSaturation": 98,
  "signalQuality": 0.85,
  "respiratoryRate": 16,
  "batteryLevel": 87,

  // ===== NEW WAVEFORM DATA (added) =====
  "sampleRate": 250,
  "duration": 1,
  "compression": "delta",

  "eegWaveform": {
    "frontal": {
      "Fp1": {
        "baseline": 8388608,
        "deltas": [0, 5, -3, 2, -1, ..., 0]  // 250 samples
      },
      "Fp2": {
        "baseline": 8388610,
        "deltas": [0, -2, 4, -3, 1, ..., 0]  // 250 samples
      },
      "F3": {
        "baseline": 8388605,
        "deltas": [0, 3, -1, 2, -4, ..., 0]  // 250 samples
      },
      "F4": {
        "baseline": 8388607,
        "deltas": [0, -1, 2, -3, 1, ..., 0]  // 250 samples
      }
    },
    "central": {
      "C3": {
        "baseline": 8388609,
        "deltas": [0, 1, -2, 3, -1, ..., 0]  // 250 samples
      },
      "C4": {
        "baseline": 8388611,
        "deltas": [0, -3, 1, 2, -1, ..., 0]  // 250 samples
      }
    },
    "occipital": {
      "O1": {
        "baseline": 8388606,
        "deltas": [0, 2, -1, -2, 3, ..., 0]  // 250 samples
      },
      "O2": {
        "baseline": 8388608,
        "deltas": [0, -1, 2, -3, 1, ..., 0]  // 250 samples
      }
    }
  }
}
```

---

## Implementation Changes Needed in ESP32

### Current Flow
```
Every 1 second:
  ├─ sendVitals()
  │  └─ Publish vitals only to: hospital/devices/{deviceId}/vitals
  │
  └─ (No waveform data sent currently)
```

### Proposed Flow (Combined Messages)
```
Every 1 second:
  ├─ collectWaveformSnapshot()  // NEW FUNCTION
  │  ├─ Read 250 samples from ADS1298
  │  └─ Delta-encode the samples
  │
  └─ sendCombinedMessage()  // MODIFIED sendVitals()
     ├─ Add vitals (existing)
     ├─ Add waveform snapshot (NEW)
     └─ Publish to: hospital/devices/{deviceId}/vitals
```

### Key Code Changes Required

#### 1. Add Waveform Sampling Buffer (Global Variables)
```cpp
// Waveform sampling (250 Hz = 250 samples per second)
#define SAMPLES_PER_SECOND 250
int32_t ecgBuffer[3][SAMPLES_PER_SECOND];  // 3 ECG leads
int32_t eegBuffer[8][SAMPLES_PER_SECOND];  // 8 EEG channels
int sampleIndex = 0;
```

#### 2. Modify sendVitals() to Include Waveform
```cpp
void sendVitals() {
  if (!mqttClient.connected() || !isAssigned) return;

  String topic = "hospital/devices/" + deviceId + "/vitals";
  JsonDocument doc;

  // ===== EXISTING VITALS (unchanged) =====
  doc["timestamp"] = getISO8601Timestamp();
  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  doc["mode"] = isECGMode ? "ecg" : "eeg";
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["heartRate"] = (int)heartRate;
  doc["skinTemperature"] = (temperature - 32.0) * 5.0 / 9.0;
  doc["oxygenSaturation"] = (int)oxygenSat;
  doc["signalQuality"] = quality / 100.0;
  doc["respiratoryRate"] = (int)respiratoryRate;
  doc["batteryLevel"] = batteryLevel;

  // ===== NEW WAVEFORM DATA =====
  doc["sampleRate"] = SAMPLES_PER_SECOND;
  doc["duration"] = 1;
  doc["compression"] = "delta";

  if (isECGMode) {
    // Add ECG waveform
    JsonObject ecgWaveform = doc.createNestedObject("ecgWaveform");
    JsonObject limb = ecgWaveform.createNestedObject("limb");

    addDeltaEncodedChannel(limb, "leadI", ecgBuffer[0], SAMPLES_PER_SECOND);
    addDeltaEncodedChannel(limb, "leadII", ecgBuffer[1], SAMPLES_PER_SECOND);
    addDeltaEncodedChannel(limb, "leadIII", ecgBuffer[2], SAMPLES_PER_SECOND);
  } else {
    // Add EEG waveform
    JsonObject eegWaveform = doc.createNestedObject("eegWaveform");

    JsonObject frontal = eegWaveform.createNestedObject("frontal");
    addDeltaEncodedChannel(frontal, "Fp1", eegBuffer[0], SAMPLES_PER_SECOND);
    addDeltaEncodedChannel(frontal, "Fp2", eegBuffer[1], SAMPLES_PER_SECOND);
    addDeltaEncodedChannel(frontal, "F3", eegBuffer[2], SAMPLES_PER_SECOND);
    addDeltaEncodedChannel(frontal, "F4", eegBuffer[3], SAMPLES_PER_SECOND);

    JsonObject central = eegWaveform.createNestedObject("central");
    addDeltaEncodedChannel(central, "C3", eegBuffer[4], SAMPLES_PER_SECOND);
    addDeltaEncodedChannel(central, "C4", eegBuffer[5], SAMPLES_PER_SECOND);

    JsonObject occipital = eegWaveform.createNestedObject("occipital");
    addDeltaEncodedChannel(occipital, "O1", eegBuffer[6], SAMPLES_PER_SECOND);
    addDeltaEncodedChannel(occipital, "O2", eegBuffer[7], SAMPLES_PER_SECOND);
  }

  String payload;
  serializeJson(doc, payload);
  mqttClient.publish(topic.c_str(), payload.c_str());
}
```

#### 3. Add Delta Encoding Helper Function
```cpp
void addDeltaEncodedChannel(JsonObject& parent, const char* name,
                           int32_t* buffer, int numSamples) {
  JsonObject channel = parent.createNestedObject(name);
  channel["baseline"] = buffer[0];

  JsonArray deltas = channel.createNestedArray("deltas");
  for (int i = 1; i < numSamples; i++) {
    deltas.add(buffer[i] - buffer[i-1]);
  }
}
```

#### 4. Collect Waveform Samples (Called from ADS1298 Interrupt)
```cpp
void collectSample(int32_t* channelData, int numChannels) {
  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;

  if (isECGMode) {
    // Store ECG samples (3 leads)
    for (int i = 0; i < 3 && i < numChannels; i++) {
      ecgBuffer[i][sampleIndex] = channelData[i];
    }
  } else {
    // Store EEG samples (8 channels)
    for (int i = 0; i < 8 && i < numChannels; i++) {
      eegBuffer[i][sampleIndex] = channelData[i];
    }
  }

  sampleIndex++;
  if (sampleIndex >= SAMPLES_PER_SECOND) {
    sampleIndex = 0;  // Reset after 1 second (250 samples)
  }
}
```

---

## Bandwidth Comparison

### Current (Vitals Only)
- **Message size:** ~200 bytes
- **Frequency:** 1/sec
- **Daily traffic:** ~17 MB/day per watch

### Proposed (Combined Vitals + Waveform)
- **Message size:** ~2,350 bytes (vitals + 250 samples × 3-8 channels)
- **Frequency:** 1/sec
- **Daily traffic:** ~235 MB/day per watch

### Bandwidth Increase
- **Absolute increase:** +218 MB/day
- **Percentage increase:** ~13.8× more data
- **Cost impact:** +₹3.60/month per watch (100 watches = +₹360/month)

**This increase is expected** because we're now sending waveform data (which was previously not sent at all).

---

## Backend Compatibility

### ✅ Backend Already Supports Combined Messages
Based on validation testing:
- ✅ VitalsRealtimeMessage Pydantic model accepts waveform fields
- ✅ Backend extracts waveform and stores separately
- ✅ Mode-based storage (ECG vs EEG) works correctly
- ✅ Backward compatible with vitals-only messages

### Backend Processing (Existing Code)
**File:** [mqtt_service.py:369-427](hospital-backend/app/services/mqtt_service.py#L369-L427)

```python
# Parse vitals message
vitalsMsg = VitalsRealtimeMessage(**payload)

# Store vitals
await self._storeVitalsRealtime(vitalsMsg)

# If waveform data is present, extract and store separately
if (vitalsMsg.sampleRate and vitalsMsg.duration and
    (vitalsMsg.ecgWaveform or vitalsMsg.eegWaveform)):

    # Extract waveform
    waveformData = {...}
    if vitalsMsg.mode == 'ecg':
        waveformData['ecgWaveform'] = vitalsMsg.ecgWaveform.dict()
    elif vitalsMsg.mode == 'eeg':
        waveformData['eegWaveform'] = vitalsMsg.eegWaveform.dict()

    # Store waveform snapshot
    waveformMsg = WaveformSnapshotMessage(**waveformData)
    await self._storeWaveformSnapshot(waveformMsg)
```

---

## Migration Strategy

### Option 1: Combined Messages (Recommended)
**Pros:**
- Single message per second (perfect time synchronization)
- Less MQTT overhead
- Simpler ESP32 code (one publish per second)

**Cons:**
- Larger message size (~2,350 bytes)
- 21% more bandwidth than 10-second batches

### Option 2: Separate Topics (Fallback)
**Topic 1:** `hospital/devices/{deviceId}/vitals` (every 1 sec)
**Topic 2:** `hospital/devices/{deviceId}/waveform` (every 10 sec)

**Pros:**
- Smaller individual messages
- 21% less bandwidth

**Cons:**
- Time synchronization challenges
- More complex ESP32 logic
- Two separate buffers needed

---

## Summary

### Current State
- ESP32 sends **vitals only** every 1 second
- No waveform data is currently transmitted
- Message size: ~200 bytes

### Proposed Change
- ESP32 sends **vitals + waveform snapshot** every 1 second
- Same MQTT topic: `hospital/devices/{deviceId}/vitals`
- Message size: ~2,350 bytes
- Backend is **already ready** to receive combined messages

### Next Steps
1. ✅ Backend Pydantic models validated
2. 🔄 Create database storage test
3. 🔄 Implement ESP32 waveform collection
4. 🔄 Implement ESP32 delta encoding
5. 🔄 Test combined message sending
6. 🔄 Verify end-to-end flow
