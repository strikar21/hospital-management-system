# ESP32 Watch Message Format: OLD vs NEW Comparison

## Side-by-Side Comparison

### OLD (Current - Vitals Only)

**MQTT Topic:** `hospital/devices/fit-00001/vitals`
**Frequency:** Every 1 second
**Size:** ~200 bytes
**Bandwidth:** ~17 MB/day per watch

```json
{
  "timestamp": "2025-10-21T14:32:15.123Z",
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

**Contains:**
- ✅ Device identification
- ✅ Basic vitals (heart rate, temp, SpO2, etc.)
- ✅ Battery level
- ✅ Signal quality
- ❌ NO waveform data

---

### NEW (Proposed - Vitals + Waveform Combined)

**MQTT Topic:** `hospital/devices/fit-00001/vitals` (SAME)
**Frequency:** Every 1 second (SAME)
**Size:** ~2,350 bytes
**Bandwidth:** ~235 MB/day per watch

#### NEW - ECG Mode Message

```json
{
  // ========== EXISTING FIELDS (UNCHANGED) ==========
  "timestamp": "2025-10-21T14:32:15.123Z",
  "mode": "ecg",
  "deviceId": "fit-00001",
  "patientId": "PAT12345",
  "heartRate": 75,
  "skinTemperature": 36.8,
  "oxygenSaturation": 98,
  "signalQuality": 0.85,
  "respiratoryRate": 16,
  "batteryLevel": 87,

  // ========== NEW FIELDS (ADDED) ==========
  "sampleRate": 250,
  "duration": 1,
  "compression": "delta",

  "ecgWaveform": {
    "limb": {
      "leadI": {
        "baseline": 8388608,
        "deltas": [0, 2, -1, 3, -2, 1, 0, -1, 2, ...]  // 250 values
      },
      "leadII": {
        "baseline": 8388610,
        "deltas": [0, 1, -2, 2, -1, 0, 1, -2, 3, ...]  // 250 values
      },
      "leadIII": {
        "baseline": 8388605,
        "deltas": [0, -1, 1, -2, 3, -1, 0, 2, -1, ...]  // 250 values
      }
    }
  }
}
```

**Contains:**
- ✅ Everything from OLD message
- ✅ Waveform metadata (sampleRate, duration, compression)
- ✅ 1-second ECG snapshot (250 samples × 3 leads)
- ✅ Delta-encoded for bandwidth efficiency

---

#### NEW - EEG Mode Message

```json
{
  // ========== EXISTING FIELDS (UNCHANGED) ==========
  "timestamp": "2025-10-21T14:32:15.123Z",
  "mode": "eeg",
  "deviceId": "fit-00001",
  "patientId": "PAT12345",
  "heartRate": 75,
  "skinTemperature": 36.8,
  "oxygenSaturation": 98,
  "signalQuality": 0.85,
  "respiratoryRate": 16,
  "batteryLevel": 87,

  // ========== NEW FIELDS (ADDED) ==========
  "sampleRate": 250,
  "duration": 1,
  "compression": "delta",

  "eegWaveform": {
    "frontal": {
      "Fp1": {
        "baseline": 8388608,
        "deltas": [0, 5, -3, 2, -1, 4, ...]  // 250 values
      },
      "Fp2": {
        "baseline": 8388610,
        "deltas": [0, -2, 4, -3, 1, -1, ...]  // 250 values
      },
      "F3": {
        "baseline": 8388605,
        "deltas": [0, 3, -1, 2, -4, 3, ...]  // 250 values
      },
      "F4": {
        "baseline": 8388607,
        "deltas": [0, -1, 2, -3, 1, -2, ...]  // 250 values
      }
    },
    "central": {
      "C3": {
        "baseline": 8388609,
        "deltas": [0, 1, -2, 3, -1, 2, ...]  // 250 values
      },
      "C4": {
        "baseline": 8388611,
        "deltas": [0, -3, 1, 2, -1, 3, ...]  // 250 values
      }
    },
    "occipital": {
      "O1": {
        "baseline": 8388606,
        "deltas": [0, 2, -1, -2, 3, -1, ...]  // 250 values
      },
      "O2": {
        "baseline": 8388608,
        "deltas": [0, -1, 2, -3, 1, -2, ...]  // 250 values
      }
    }
  }
}
```

**Contains:**
- ✅ Everything from OLD message
- ✅ Waveform metadata (sampleRate, duration, compression)
- ✅ 1-second EEG snapshot (250 samples × 8 channels)
- ✅ Delta-encoded for bandwidth efficiency

---

## What Changes in ESP32 Code?

### OLD Code (Current)
```cpp
void sendVitals() {
  String topic = "hospital/devices/" + deviceId + "/vitals";
  JsonDocument doc;

  doc["timestamp"] = getISO8601Timestamp();
  doc["mode"] = isECGMode ? "ecg" : "eeg";
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["heartRate"] = (int)heartRate;
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

**Lines changed:** 0
**New functions:** 0
**Complexity:** Simple

---

### NEW Code (Proposed)
```cpp
void sendVitals() {
  String topic = "hospital/devices/" + deviceId + "/vitals";
  JsonDocument doc;

  // ===== EXISTING VITALS (SAME AS OLD) =====
  doc["timestamp"] = getISO8601Timestamp();
  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
  doc["mode"] = isECGMode ? "ecg" : "eeg";
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["heartRate"] = (int)heartRate;
  doc["skinTemperature"] = tempCelsius;
  doc["oxygenSaturation"] = (int)oxygenSat;
  doc["signalQuality"] = quality / 100.0;
  doc["respiratoryRate"] = (int)respiratoryRate;
  doc["batteryLevel"] = batteryLevel;

  // ===== NEW WAVEFORM METADATA =====
  doc["sampleRate"] = 250;
  doc["duration"] = 1;
  doc["compression"] = "delta";

  // ===== NEW WAVEFORM DATA =====
  if (isECGMode) {
    JsonObject ecgWaveform = doc.createNestedObject("ecgWaveform");
    JsonObject limb = ecgWaveform.createNestedObject("limb");

    // Add delta-encoded ECG leads
    addDeltaEncodedChannel(limb, "leadI", ecgBuffer[0], 250);
    addDeltaEncodedChannel(limb, "leadII", ecgBuffer[1], 250);
    addDeltaEncodedChannel(limb, "leadIII", ecgBuffer[2], 250);
  } else {
    JsonObject eegWaveform = doc.createNestedObject("eegWaveform");

    JsonObject frontal = eegWaveform.createNestedObject("frontal");
    addDeltaEncodedChannel(frontal, "Fp1", eegBuffer[0], 250);
    addDeltaEncodedChannel(frontal, "Fp2", eegBuffer[1], 250);
    addDeltaEncodedChannel(frontal, "F3", eegBuffer[2], 250);
    addDeltaEncodedChannel(frontal, "F4", eegBuffer[3], 250);

    JsonObject central = eegWaveform.createNestedObject("central");
    addDeltaEncodedChannel(central, "C3", eegBuffer[4], 250);
    addDeltaEncodedChannel(central, "C4", eegBuffer[5], 250);

    JsonObject occipital = eegWaveform.createNestedObject("occipital");
    addDeltaEncodedChannel(occipital, "O1", eegBuffer[6], 250);
    addDeltaEncodedChannel(occipital, "O2", eegBuffer[7], 250);
  }

  String payload;
  serializeJson(doc, payload);
  mqttClient.publish(topic.c_str(), payload.c_str());
}

// NEW HELPER FUNCTION
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

**Lines added:** ~40
**New functions:** 1 (addDeltaEncodedChannel)
**Complexity:** Moderate

---

## Bandwidth Impact

| Metric | OLD | NEW | Change |
|--------|-----|-----|--------|
| **Message size** | ~200 bytes | ~2,350 bytes | +2,150 bytes |
| **Messages/day** | 86,400 | 86,400 | No change |
| **Daily traffic/watch** | 17 MB | 235 MB | +218 MB (+12.8×) |
| **Monthly cost/watch** | ₹17.55 | ₹21.15 | +₹3.60 |
| **Monthly cost (100 watches)** | ₹1,755 | ₹2,115 | +₹360 |

**Note:** The bandwidth increase is expected because OLD doesn't send waveform data at all.

---

## Backend Compatibility

### OLD Message - Backend Support
✅ **Fully supported** - Backend stores in `vitals_realtime` table

### NEW Message - Backend Support
✅ **Fully supported** - Tested and validated
- ✅ Pydantic models accept combined messages
- ✅ Vitals stored in `vitals_realtime` table
- ✅ Waveforms extracted and stored in `waveform_snapshots` table
- ✅ Mode-based storage (ECG vs EEG) works correctly
- ✅ Backward compatible (can still receive OLD messages)

---

## Migration Path

### Phase 1: Current State (OLD)
```
ESP32 Watch
  └─ Sends vitals only (every 1 sec)
      └─ Backend stores in vitals_realtime table
```

### Phase 2: Proposed State (NEW)
```
ESP32 Watch
  ├─ Collects waveform samples (250 Hz continuous)
  └─ Sends vitals + 1-sec waveform snapshot (every 1 sec)
      └─ Backend receives combined message
          ├─ Stores vitals → vitals_realtime table
          └─ Stores waveform → waveform_snapshots table
```

### Backward Compatibility
✅ **Backend accepts BOTH formats:**
- OLD messages (vitals only) → stores vitals, ignores missing waveform
- NEW messages (vitals + waveform) → stores both

---

## Summary

| Feature | OLD | NEW |
|---------|-----|-----|
| **Vitals data** | ✅ Yes | ✅ Yes (unchanged) |
| **Waveform data** | ❌ No | ✅ Yes (added) |
| **MQTT topic** | `hospital/devices/{id}/vitals` | `hospital/devices/{id}/vitals` (same) |
| **Frequency** | 1/sec | 1/sec (same) |
| **Message size** | 200 bytes | 2,350 bytes |
| **Backend ready** | ✅ Yes | ✅ Yes (tested) |
| **ESP32 ready** | ✅ Yes | ❌ Needs implementation |

**Bottom line:** NEW message adds waveform data to existing vitals message, using the same topic and frequency. Backend is ready. ESP32 needs code changes.
