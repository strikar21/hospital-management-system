# Complete Bandwidth Analysis - All ECG/EEG Configurations
**Comprehensive Permutation Analysis for Hospital Management System**

Generated: 2025-10-22
Hardware: ADS1298 8-Channel Medical ADC

---

## Table of Contents
1. [Lead Configuration Matrix](#lead-configuration-matrix)
2. [Sample Rate & Batch Analysis](#sample-rate--batch-analysis)
3. [Complete Permutation Table](#complete-permutation-table)
4. [Worst-Case Scenarios](#worst-case-scenarios)
5. [Severity-Based Recommendations](#severity-based-recommendations)
6. [Implementation Requirements](#implementation-requirements)

---

## 1. Lead Configuration Matrix

### ECG Lead Configurations

#### 1-Lead ECG (Apple Watch Style)
**Leads:** Lead II only
**Channels used:** 1 of 8
**Clinical use:** Basic heart rate monitoring, simple arrhythmia detection
**Severity:** Low-risk patients, wellness monitoring
**Sample per snapshot:** 1 channel
**Data structure:**
```json
{
  "ecgWaveform": {
    "limb": {
      "leadII": {"baseline": 8388608, "deltas": [...]}
    }
  }
}
```

#### 3-Lead ECG (Standard Holter)
**Leads:** Lead I, II, III
**Channels used:** 3 of 8
**Clinical use:** Standard cardiac monitoring, basic arrhythmia classification
**Severity:** Medium-risk patients, post-op monitoring
**Sample per snapshot:** 3 channels
**Data structure:**
```json
{
  "ecgWaveform": {
    "limb": {
      "leadI": {"baseline": X, "deltas": [...]},
      "leadII": {"baseline": X, "deltas": [...]},
      "leadIII": {"baseline": X, "deltas": [...]}
    }
  }
}
```

#### 5-Lead ECG (ICU Standard)
**Leads:** I, II, III, V1, V5
**Channels used:** 5 of 8
**Clinical use:** ICU monitoring, MI detection, advanced arrhythmia
**Severity:** High-risk patients, ICU, cardiac care unit
**Sample per snapshot:** 5 channels
**Data structure:**
```json
{
  "ecgWaveform": {
    "limb": {
      "leadI": {...},
      "leadII": {...},
      "leadIII": {...}
    },
    "precordial": {
      "v1": {...},
      "v5": {...}
    }
  }
}
```

#### 7-Lead ECG (Enhanced ICU)
**Leads:** I, II, III, V1, V2, V3, V5
**Channels used:** 7 of 8
**Clinical use:** Detailed MI localization, complex arrhythmia
**Severity:** Critical care, cardiac surgery recovery
**Sample per snapshot:** 7 channels

#### 8-Lead ECG (Full Hardware)
**Leads:** I, II, III, V1, V2, V3, V4, V5
**Channels used:** 8 of 8 (all ADC channels)
**Clinical use:** Maximum cardiac detail without derived leads
**Severity:** Critical arrhythmia, acute MI, research
**Sample per snapshot:** 8 channels

#### 12-Lead ECG (Full Diagnostic)
**Leads:** I, II, III, aVR, aVL, aVF, V1, V2, V3, V4, V5, V6
**Channels used:** 8 physical + 4 derived (calculated on backend)
**Clinical use:** Complete cardiac assessment, diagnostic ECG
**Severity:** Critical care, pre-surgical assessment, ER
**Sample per snapshot:** 8 physical channels (12 total after backend processing)
**Data structure:**
```json
{
  "ecgWaveform": {
    "limb": {
      "leadI": {...},
      "leadII": {...},
      "leadIII": {...}
    },
    "precordial": {
      "v1": {...},
      "v2": {...},
      "v3": {...},
      "v4": {...},
      "v5": {...}
    },
    "derived": {
      "aVR": {...},   // Calculated by backend
      "aVL": {...},   // Calculated by backend
      "aVF": {...},   // Calculated by backend
      "v6": {...}     // Calculated by backend
    }
  }
}
```

---

### EEG Channel Configurations

#### 2-Channel EEG (Minimal Seizure Detection)
**Channels:** F3, F4 (frontal bilateral)
**Channels used:** 2 of 8
**Clinical use:** Basic seizure detection, sleep monitoring
**Severity:** Low-risk epilepsy, sleep studies
**Sample per snapshot:** 2 channels
**Data structure:**
```json
{
  "eegWaveform": {
    "frontal": {
      "F3": {"baseline": X, "deltas": [...]},
      "F4": {"baseline": X, "deltas": [...]}
    }
  }
}
```

#### 4-Channel EEG (Standard Monitoring)
**Channels:** Fp1, Fp2, F3, F4 (frontal lobe focus)
**Channels used:** 4 of 8
**Clinical use:** Frontal lobe monitoring, standard seizure detection
**Severity:** Medium-risk epilepsy, consciousness monitoring
**Sample per snapshot:** 4 channels
**Data structure:**
```json
{
  "eegWaveform": {
    "frontal": {
      "Fp1": {...},
      "Fp2": {...},
      "F3": {...},
      "F4": {...}
    }
  }
}
```

#### 8-Channel EEG (Full Monitoring)
**Channels:** Fp1, Fp2, F3, F4, C3, C4, O1, O2
**Channels used:** 8 of 8 (all ADC channels)
**Clinical use:** Complete brain monitoring, localization of seizure focus
**Severity:** High-risk epilepsy, neurosurgery, ICU brain monitoring
**Sample per snapshot:** 8 channels
**Data structure:**
```json
{
  "eegWaveform": {
    "frontal": {
      "Fp1": {...},
      "Fp2": {...},
      "F3": {...},
      "F4": {...}
    },
    "central": {
      "C3": {...},
      "C4": {...}
    },
    "occipital": {
      "O1": {...},
      "O2": {...}
    }
  }
}
```

---

## 2. Sample Rate & Batch Analysis

### Sample Rate Comparison

| Sample Rate | Clinical Use | Nyquist Limit | Waveform Detail | Standard |
|-------------|--------------|---------------|-----------------|----------|
| **125 Hz** | Consumer wearables | 62.5 Hz | Low | Consumer |
| **250 Hz** | Clinical ECG/EEG | 125 Hz | Standard | **Medical Standard** |
| **500 Hz** | High-res ECG/EEG | 250 Hz | High | Research/ICU |
| **1000 Hz** | Research | 500 Hz | Very High | Research only |

**Recommendation:** 250 Hz for standard clinical use, 500 Hz for critical patients

---

### Batch Interval Options

| Batch Interval | Samples (250 Hz) | Samples (500 Hz) | Latency | Use Case |
|----------------|------------------|------------------|---------|----------|
| **50ms** | 12.5 | 25 | 50ms | Ultra-low latency (not practical) |
| **100ms** | 25 | 50 | 100ms | Very low latency, high overhead |
| **200ms** | 50 | 100 | 200ms | Low latency, reasonable overhead |
| **500ms** | 125 | 250 | 500ms | Balanced |
| **1 sec** | 250 | 500 | 1 sec | Standard clinical monitoring |
| **2 sec** | 500 | 1000 | 2 sec | Reduced bandwidth |
| **5 sec** | 1250 | 2500 | 5 sec | Low bandwidth |
| **10 sec** | 2500 | 5000 | 10 sec | Minimal bandwidth |

---

### Message Architecture Options

#### Option A: Combined Messages (Vitals + Waveform in one message)
**MQTT Topic:** `hospital/devices/{deviceId}/vitals`
**Frequency:** Same as batch interval
**Pros:**
- Perfect time synchronization
- Single message per batch
- Simpler ESP32 code

**Cons:**
- Larger individual messages
- Vitals only updated at batch interval

---

#### Option B: Separate Messages (Vitals every 1 sec, Waveforms at batch interval)
**MQTT Topics:**
- `hospital/devices/{deviceId}/vitals` (every 1 sec)
- `hospital/devices/{deviceId}/waveform` (at batch interval)

**Pros:**
- Vitals always updated at 1 Hz
- Can subscribe to vitals only to save bandwidth
- Flexible batch intervals

**Cons:**
- Need sequence numbers for time sync
- More complex ESP32 code
- More MQTT messages

---

## 3. Complete Permutation Table

### Message Size Calculations

#### Base Overhead (Every Message)
```
Metadata (deviceId, patientId, timestamp, mode, etc.): ~150 bytes
Quality metrics (signalQuality, batteryLevel, etc.): ~50 bytes
JSON structure overhead: ~100 bytes
---
Total Base: ~300 bytes
```

#### Per-Channel Waveform Data (Delta-Encoded)
```
Channel name: ~10 bytes
Baseline (int32): 4 bytes
Delta array (int8 per sample, assuming deltas fit in 8-bit):
  - 50 samples (200ms @ 250Hz): ~50 bytes
  - 100 samples (200ms @ 500Hz): ~100 bytes
  - 250 samples (1sec @ 250Hz): ~250 bytes
  - 500 samples (1sec @ 500Hz): ~500 bytes

Per-channel formula: 14 + (samples × 1 byte)
```

#### Vitals-Only Message
```
Base overhead: ~300 bytes
Vitals (HR, temp, SpO2, RR, BP, battery): ~100 bytes
---
Total: ~400 bytes (rounded to 200 bytes in previous docs - corrected here)
```

---

### ECG Configuration Message Sizes

#### 250 Hz Sample Rate

| Config | Leads | 200ms Batch | 1sec Batch | 10sec Batch |
|--------|-------|-------------|------------|-------------|
| **1-Lead** | 1 | 364 bytes | 564 bytes | 2,800 bytes |
| **3-Lead** | 3 | 492 bytes | 1,062 bytes | 7,800 bytes |
| **5-Lead** | 5 | 620 bytes | 1,560 bytes | 12,800 bytes |
| **7-Lead** | 7 | 748 bytes | 2,058 bytes | 17,800 bytes |
| **8-Lead** | 8 | 812 bytes | 2,306 bytes | 20,300 bytes |
| **12-Lead** | 8 phys | 812 bytes | 2,306 bytes | 20,300 bytes |

**Formula:** 300 (base) + (leads × (14 + samples))

#### 500 Hz Sample Rate

| Config | Leads | 200ms Batch | 1sec Batch | 10sec Batch |
|--------|-------|-------------|------------|-------------|
| **1-Lead** | 1 | 414 bytes | 814 bytes | 5,300 bytes |
| **3-Lead** | 3 | 642 bytes | 1,842 bytes | 15,300 bytes |
| **5-Lead** | 5 | 870 bytes | 2,870 bytes | 25,300 bytes |
| **7-Lead** | 7 | 1,098 bytes | 3,898 bytes | 35,300 bytes |
| **8-Lead** | 8 | 1,212 bytes | 4,412 bytes | 40,300 bytes |
| **12-Lead** | 8 phys | 1,212 bytes | 4,412 bytes | 40,300 bytes |

---

### EEG Configuration Message Sizes

#### 250 Hz Sample Rate

| Config | Channels | 200ms Batch | 1sec Batch | 10sec Batch |
|--------|----------|-------------|------------|-------------|
| **2-Channel** | 2 | 428 bytes | 828 bytes | 5,300 bytes |
| **4-Channel** | 4 | 556 bytes | 1,326 bytes | 10,300 bytes |
| **8-Channel** | 8 | 812 bytes | 2,306 bytes | 20,300 bytes |

#### 500 Hz Sample Rate

| Config | Channels | 200ms Batch | 1sec Batch | 10sec Batch |
|--------|----------|-------------|------------|-------------|
| **2-Channel** | 2 | 528 bytes | 1,328 bytes | 10,300 bytes |
| **4-Channel** | 4 | 756 bytes | 2,356 bytes | 20,300 bytes |
| **8-Channel** | 8 | 1,212 bytes | 4,412 bytes | 40,300 bytes |

---

## 4. Worst-Case Scenarios

### Absolute Worst Case: 12-Lead ECG @ 500 Hz, 200ms Batches, Separate Messages

#### Configuration Details:
- **ECG Leads:** 12 (8 physical + 4 derived on backend)
- **Sample Rate:** 500 Hz
- **Waveform Batch:** Every 200ms (5× per second)
- **Vitals:** Every 1 second
- **Message Architecture:** Separate topics

#### Message Flow:
```
Every 200ms (5× per second):
  Waveform message: 1,212 bytes

Every 1 second (1× per second):
  Vitals message: 400 bytes
```

#### Bandwidth Calculation:
```
Waveform traffic: 1,212 bytes × 5/sec = 6,060 bytes/sec
Vitals traffic: 400 bytes × 1/sec = 400 bytes/sec
---
Total: 6,460 bytes/sec = 6.31 KB/sec

Per Day: 6,460 × 86,400 = 558,144,000 bytes = 532 MB/day
Per Month: 532 MB × 30 = 15,960 MB = 15.96 GB/month
```

#### Cost Calculation (₹0.09 per MB):
```
Per device/month: 15,960 MB × ₹0.09 = ₹1,436.40
100 devices/month: ₹143,640
```

#### MQTT Message Count:
```
Per day: (5 waveform + 1 vital) × 86,400 sec/day = 518,400 messages/day
Per month: 15,552,000 messages
```

#### Storage Requirements (TimescaleDB):
```
Per device/month: 15.96 GB raw data
100 devices/month: 1.596 TB
Per year (100 devices): 19.152 TB
```

---

### Second Worst Case: 8-Channel EEG @ 500 Hz, 200ms Batches, Separate Messages

#### Bandwidth:
```
Waveform: 1,212 bytes × 5/sec = 6,060 bytes/sec
Vitals: 400 bytes/sec
Total: 6,460 bytes/sec = 532 MB/day

Monthly (100 devices): ₹143,640
```

**Same as 12-lead ECG since both use all 8 physical ADC channels**

---

### Best Case: 1-Lead ECG @ 250 Hz, 10sec Batches, Separate Messages

#### Bandwidth:
```
Waveform: 2,800 bytes × 0.1/sec = 280 bytes/sec
Vitals: 400 bytes/sec
Total: 680 bytes/sec = 59 MB/day

Monthly cost: 59 MB × 30 × ₹0.09 = ₹159.30 per device
100 devices: ₹15,930/month
```

---

## 5. Complete Permutation Table - Daily Bandwidth

### ECG @ 250 Hz

| Config | 200ms Sep | 200ms Comb | 1sec Sep | 1sec Comb | 10sec Sep | 10sec Comb |
|--------|-----------|------------|----------|-----------|-----------|------------|
| **1-Lead** | 65 MB | 31 MB | 83 MB | 49 MB | 276 MB | 242 MB |
| **3-Lead** | 77 MB | 43 MB | 126 MB | 92 MB | 708 MB | 674 MB |
| **5-Lead** | 88 MB | 54 MB | 169 MB | 135 MB | 1,140 MB | 1,106 MB |
| **7-Lead** | 99 MB | 65 MB | 212 MB | 178 MB | 1,572 MB | 1,538 MB |
| **8-Lead** | 104 MB | 70 MB | 233 MB | 199 MB | 1,788 MB | 1,754 MB |
| **12-Lead** | 104 MB | 70 MB | 233 MB | 199 MB | 1,788 MB | 1,754 MB |

### ECG @ 500 Hz

| Config | 200ms Sep | 200ms Comb | 1sec Sep | 1sec Comb | 10sec Sep | 10sec Comb |
|--------|-----------|------------|----------|-----------|-----------|------------|
| **1-Lead** | 71 MB | 36 MB | 105 MB | 70 MB | 492 MB | 458 MB |
| **3-Lead** | 90 MB | 55 MB | 193 MB | 159 MB | 1,356 MB | 1,322 MB |
| **5-Lead** | 109 MB | 75 MB | 282 MB | 248 MB | 2,220 MB | 2,186 MB |
| **7-Lead** | 129 MB | 95 MB | 371 MB | 337 MB | 3,084 MB | 3,050 MB |
| **8-Lead** | 139 MB | 105 MB | 416 MB | 381 MB | 3,516 MB | 3,482 MB |
| **12-Lead** | **532 MB** | **498 MB** | **416 MB** | **381 MB** | **3,516 MB** | **3,482 MB** |

### EEG @ 250 Hz

| Config | 200ms Sep | 200ms Comb | 1sec Sep | 1sec Comb | 10sec Sep | 10sec Comb |
|--------|-----------|------------|----------|-----------|-----------|------------|
| **2-Ch** | 71 MB | 37 MB | 106 MB | 72 MB | 492 MB | 458 MB |
| **4-Ch** | 83 MB | 48 MB | 149 MB | 115 MB | 924 MB | 890 MB |
| **8-Ch** | 104 MB | 70 MB | 233 MB | 199 MB | 1,788 MB | 1,754 MB |

### EEG @ 500 Hz

| Config | 200ms Sep | 200ms Comb | 1sec Sep | 1sec Comb | 10sec Sep | 10sec Comb |
|--------|-----------|------------|----------|-----------|-----------|------------|
| **2-Ch** | 80 MB | 46 MB | 149 MB | 115 MB | 924 MB | 890 MB |
| **4-Ch** | 100 MB | 65 MB | 237 MB | 203 MB | 1,788 MB | 1,754 MB |
| **8-Ch** | **532 MB** | **498 MB** | **416 MB** | **381 MB** | **3,516 MB** | **3,482 MB** |

**Legend:**
- **Sep** = Separate messages (vitals 1/sec + waveform at batch interval)
- **Comb** = Combined messages (vitals + waveform together)

---

## 6. Severity-Based Recommendations

### Low Severity (Wellness/Post-Discharge Monitoring)

**Configuration:**
- **ECG:** 1-lead @ 250 Hz, 10-second batches, separate messages
- **Bandwidth:** 276 MB/day
- **Cost:** ₹743/month per device
- **Latency:** 10 seconds
- **Clinical use:** Basic heart rate monitoring, simple arrhythmia detection

**Rationale:** Minimal bandwidth, sufficient for wellness monitoring

---

### Medium Severity (Standard Hospital Ward)

**Configuration:**
- **ECG:** 3-lead @ 250 Hz, 1-second batches, separate messages
- **Bandwidth:** 126 MB/day
- **Cost:** ₹340/month per device
- **Latency:** 1 second
- **Clinical use:** Standard cardiac monitoring, arrhythmia classification

**Rationale:** Good balance of clinical utility and bandwidth efficiency

---

### High Severity (ICU/CCU)

**Configuration:**
- **ECG:** 5-lead @ 500 Hz, 200ms batches, separate messages
- **Bandwidth:** 109 MB/day
- **Cost:** ₹294/month per device
- **Latency:** 200ms
- **Clinical use:** Detailed MI detection, advanced arrhythmia, quick response

**Rationale:** Low latency for rapid response, high-quality waveforms

---

### Critical Severity (Cardiac Surgery/ER)

**Configuration:**
- **ECG:** 12-lead @ 500 Hz, 200ms batches, separate messages
- **Bandwidth:** 532 MB/day
- **Cost:** ₹1,436/month per device
- **Latency:** 200ms
- **Clinical use:** Complete diagnostic ECG, complex arrhythmia, surgical monitoring

**Rationale:** Maximum data collection for critical decision-making

---

### Neurological Monitoring (Epilepsy/Post-Surgery)

**Configuration:**
- **EEG:** 8-channel @ 250 Hz, 1-second batches, separate messages
- **Bandwidth:** 233 MB/day
- **Cost:** ₹629/month per device
- **Latency:** 1 second
- **Clinical use:** Full brain monitoring, seizure localization

**Rationale:** Complete brain coverage without excessive bandwidth

---

## 7. Dynamic Switching Strategy

### Adaptive Bandwidth Management

```python
# Pseudo-code for dynamic configuration switching

def select_configuration(patient):
    severity = patient.severity_level
    condition = patient.primary_diagnosis

    if severity == "CRITICAL" or condition in ["MI", "CARDIAC_ARREST"]:
        return {
            "mode": "ecg",
            "leads": 12,
            "sampleRate": 500,
            "batchInterval": 0.2,  # 200ms
            "messageType": "separate"
        }

    elif severity == "HIGH" or condition in ["UNSTABLE_ANGINA", "ARRHYTHMIA"]:
        return {
            "mode": "ecg",
            "leads": 5,
            "sampleRate": 500,
            "batchInterval": 0.2,
            "messageType": "separate"
        }

    elif severity == "MEDIUM" or condition in ["POST_OP", "CARDIAC_MONITORING"]:
        return {
            "mode": "ecg",
            "leads": 3,
            "sampleRate": 250,
            "batchInterval": 1,
            "messageType": "separate"
        }

    elif condition in ["EPILEPSY", "SEIZURE", "NEURO"]:
        return {
            "mode": "eeg",
            "channels": 8,
            "sampleRate": 250,
            "batchInterval": 1,
            "messageType": "separate"
        }

    else:  # Low severity, wellness
        return {
            "mode": "ecg",
            "leads": 1,
            "sampleRate": 250,
            "batchInterval": 10,
            "messageType": "separate"
        }

# Backend can send configuration update to ESP32 via MQTT
def update_device_configuration(deviceId, config):
    mqtt.publish(f"hospital/devices/{deviceId}/config", config)
```

---

## 8. Implementation Requirements

### Backend Changes (neural_vitals.py)

✅ **ALREADY SUPPORTS:**
- Variable lead configurations (1-12 leads ECG)
- Variable channel configurations (2-8 channels EEG)
- Flexible sample rates (any integer)
- Flexible batch durations (any integer)
- Both combined and separate message architectures

❌ **NO CHANGES NEEDED** - Backend models are fully flexible

---

### ESP32 Firmware Changes Required

#### Current State (From Code Review):
```cpp
// Currently sends ZERO waveform data
void sendVitals() {
  doc["heartRate"] = heartRate;
  doc["temperature"] = temperature;
  doc["oxygenSat"] = oxygenSat;
  doc["batteryLevel"] = batteryLevel;
  // NO ecgWaveform or eegWaveform fields
}
```

#### Required Implementation:

**1. Add Configuration Variables:**
```cpp
// Configurable parameters (set via MQTT config message)
int activeLeads = 3;  // 1, 3, 5, 7, 8, or 12
int sampleRate = 250;  // 250 or 500 Hz
int batchIntervalMs = 1000;  // 200, 500, 1000, 10000 ms
bool separateMessages = true;  // true = separate, false = combined
```

**2. Add Waveform Buffers:**
```cpp
// Circular buffers for continuous sampling
#define MAX_BUFFER_SIZE 5000  // 10 seconds @ 500 Hz
int32_t ecgBuffers[8][MAX_BUFFER_SIZE];  // 8 ADC channels
int sampleIndex = 0;
```

**3. Add ADS1298 Sampling Loop:**
```cpp
// Called from hardware interrupt (every 2ms @ 500 Hz or 4ms @ 250 Hz)
void onADS1298DataReady() {
  // Read all 8 channels from ADS1298
  for (int ch = 0; ch < 8; ch++) {
    ecgBuffers[ch][sampleIndex] = ADS1298_readChannel(ch);
  }

  sampleIndex = (sampleIndex + 1) % MAX_BUFFER_SIZE;
}
```

**4. Add Delta Encoding Function:**
```cpp
void addDeltaEncodedChannel(JsonObject& parent, const char* name,
                           int32_t* buffer, int startIndex, int numSamples) {
  JsonObject channel = parent.createNestedObject(name);

  int32_t baseline = buffer[startIndex];
  channel["baseline"] = baseline;

  JsonArray deltas = channel.createNestedArray("deltas");
  for (int i = 1; i < numSamples; i++) {
    int idx = (startIndex + i) % MAX_BUFFER_SIZE;
    deltas.add(buffer[idx] - buffer[(startIndex + i - 1) % MAX_BUFFER_SIZE]);
  }
}
```

**5. Modify sendVitals() to Include Waveforms:**
```cpp
void sendVitalsAndWaveform() {
  JsonDocument doc;

  // Existing vitals
  doc["timestamp"] = getISO8601Timestamp();
  doc["mode"] = "ecg";  // or "eeg" based on GPIO
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["heartRate"] = heartRate;
  // ... other vitals ...

  // NEW: Waveform data
  doc["sampleRate"] = sampleRate;
  doc["duration"] = batchIntervalMs / 1000.0;
  doc["compression"] = "delta";

  int samplesInBatch = (sampleRate * batchIntervalMs) / 1000;
  int startIndex = (sampleIndex - samplesInBatch + MAX_BUFFER_SIZE) % MAX_BUFFER_SIZE;

  bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;

  if (isECGMode) {
    JsonObject ecgWaveform = doc.createNestedObject("ecgWaveform");
    JsonObject limb = ecgWaveform.createNestedObject("limb");

    // Add leads based on activeLeads configuration
    if (activeLeads >= 1) {
      addDeltaEncodedChannel(limb, "leadI", ecgBuffers[0], startIndex, samplesInBatch);
    }
    if (activeLeads >= 2) {
      addDeltaEncodedChannel(limb, "leadII", ecgBuffers[1], startIndex, samplesInBatch);
    }
    if (activeLeads >= 3) {
      addDeltaEncodedChannel(limb, "leadIII", ecgBuffers[2], startIndex, samplesInBatch);
    }

    if (activeLeads >= 4) {
      JsonObject precordial = ecgWaveform.createNestedObject("precordial");
      addDeltaEncodedChannel(precordial, "v1", ecgBuffers[3], startIndex, samplesInBatch);
    }
    // ... add more leads based on activeLeads ...
  }

  String payload;
  serializeJson(doc, payload);
  mqttClient.publish(topic.c_str(), payload.c_str());
}
```

**6. Add Configuration Listener:**
```cpp
void onMqttConfigMessage(String payload) {
  JsonDocument config;
  deserializeJson(config, payload);

  activeLeads = config["leads"] | 3;
  sampleRate = config["sampleRate"] | 250;
  batchIntervalMs = config["batchInterval"] | 1000;
  separateMessages = config["separateMessages"] | true;

  Serial.println("Config updated: " + String(activeLeads) + " leads @ " +
                 String(sampleRate) + " Hz, " + String(batchIntervalMs) + "ms batches");
}

void setup() {
  // Subscribe to configuration topic
  mqttClient.subscribe(("hospital/devices/" + deviceId + "/config").c_str());
}
```

---

### Database Schema Validation

From code review, current schema in `neural_vitals.py` already supports:

✅ **ECGWaveformData:**
- Limb leads (required): leadI, leadII, leadIII
- Precordial leads (optional): v1, v2, v3, v4, v5
- Derived leads (optional): aVR, aVL, aVF, v6
- Events (optional): detected arrhythmias

✅ **EEGWaveformData:**
- Frontal channels (required): Fp1, Fp2, F3, F4
- Central channels (required): C3, C4
- Occipital channels (required): O1, O2
- Analysis (optional): band powers, asymmetry

✅ **WaveformSnapshotMessage:**
- Flexible sampleRate (any integer)
- Flexible duration (any integer)
- Supports both ECG and EEG modes

**No database changes required** - all configurations supported

---

### Frontend Display Requirements

#### For Variable Lead Configurations:

**Low severity patients (1-lead):**
- Simple line chart showing single lead
- Heart rate number display
- Basic arrhythmia alerts

**Medium severity (3-lead):**
- Three synchronized waveform traces
- Lead I, II, III display
- Enhanced arrhythmia detection UI

**High/Critical severity (5-12 lead):**
- Multi-panel ECG viewer
- Standard 12-lead grid layout
- Detailed ST segment analysis
- Advanced interpretation display

**EEG patients:**
- Multi-channel montage view
- Color-coded by brain region
- Band power visualization
- Seizure event markers

---

## 9. Recommended Implementation Phases

### Phase 1: Basic 3-Lead ECG (2 weeks)
- Implement ADS1298 continuous sampling
- Add 3-lead waveform transmission
- 250 Hz, 1-second batches, separate messages
- Test with 10 devices

**Bandwidth:** 126 MB/day per device
**Cost:** ₹340/month per device

---

### Phase 2: Variable Lead Support (1 week)
- Add configuration system
- Support 1, 3, 5 lead modes
- Backend dynamic configuration updates
- Test severity-based switching

---

### Phase 3: High-Resolution Mode (1 week)
- Add 500 Hz sampling
- Implement 200ms batching for critical patients
- Test with ICU scenarios

---

### Phase 4: 12-Lead Diagnostic (2 weeks)
- Add all 8 physical channels
- Implement derived lead calculations on backend
- Add 12-lead ECG viewer to frontend
- Test with cardiology department

---

### Phase 5: EEG Support (2 weeks)
- Add EEG mode switching
- Implement 8-channel EEG sampling
- Add EEG montage viewer to frontend
- Test with neurology department

---

## 10. Summary & Recommendations

### Key Findings:

1. **Worst-case bandwidth:** 532 MB/day (12-lead ECG @ 500 Hz, 200ms batches)
2. **Best-case bandwidth:** 59 MB/day (1-lead ECG @ 250 Hz, 10sec batches)
3. **Recommended standard:** 126 MB/day (3-lead ECG @ 250 Hz, 1sec batches)
4. **Backend is ready:** No code changes needed - fully flexible
5. **ESP32 needs work:** Waveform sampling and transmission not implemented

### Cost Projections (100 devices, mixed severities):

**Conservative Mix:**
- 60% Medium severity (3-lead, 250 Hz, 1 sec): 60 × ₹340 = ₹20,400
- 30% High severity (5-lead, 500 Hz, 200ms): 30 × ₹294 = ₹8,820
- 10% Critical severity (12-lead, 500 Hz, 200ms): 10 × ₹1,436 = ₹14,360

**Total: ₹43,580/month for 100 devices**

### Final Recommendation:

**Start with Phase 1:** 3-lead ECG @ 250 Hz, 1-second batches, separate messages

**Rationale:**
- Clinical standard for cardiac monitoring
- Reasonable bandwidth (126 MB/day)
- Affordable cost (₹340/device/month)
- Upgradeable to higher configurations when needed
- Proven in Holter monitor industry

**Next steps:**
1. Confirm user approval of Phase 1 configuration
2. Implement ESP32 ADS1298 sampling code
3. Implement waveform transmission
4. Test with 1-2 devices before scaling
5. Add dynamic configuration system for severity-based switching

---

**Document Complete - Ready for Implementation Planning**
