# ECG/EEG Data Flow Analysis

## Summary

**ESP32 sends TWO separate types of messages:**

### 1. Vitals Message (Every 1 Second)
**Topic:** `hospital/devices/{deviceId}/vitals`
**Contains:** Basic vital signs + OPTIONAL ECG/EEG analysis

### 2. Waveform Snapshot Message (Every 10 Seconds)
**Topic:** `hospital/devices/{deviceId}/waveform`
**Contains:** Raw waveform data (ECG 12-lead or EEG 8-channel)

---

## Current ESP32 Implementation Status

### ✅ What IS Implemented:

**Vitals Message (1 second interval)**
- Heart Rate
- Temperature
- SpO2
- Respiratory Rate
- Battery Level
- Signal Quality
- Mode field: `"mode": "ecg"` (hardcoded)

**Location:** [esp32_hospital_watch_complete.ino:1313-1345](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1313-L1345)

```cpp
void sendVitals() {
  String topic = "hospital/devices/" + deviceId + "/vitals";

  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();
  doc["mode"] = "ecg";  // ← Hardcoded, always "ecg"
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["heartRate"] = (int)heartRate;
  doc["skinTemperature"] = tempCelsius;
  doc["oxygenSaturation"] = (int)oxygenSat;
  doc["signalQuality"] = quality / 100.0;
  doc["respiratoryRate"] = (int)respiratoryRate;
  doc["batteryLevel"] = batteryLevel;

  // ❌ MISSING: ecgAnalysis object
  // ❌ MISSING: ecgLeads object
  // ❌ MISSING: eegAnalysis object
  // ❌ MISSING: eegChannels object

  String payload;
  serializeJson(doc, payload);
  mqttClient.publish(topic.c_str(), payload.c_str());
}
```

### ❌ What IS NOT Implemented:

**Waveform Snapshot Message (10 second interval)**
- **NO sendWaveform() function exists**
- **NO waveform data is being sent**
- Backend MQTT service is subscribed and waiting, but ESP32 never publishes

**Expected but Missing:**
- ECG waveform data (12-lead)
- EEG waveform data (8-channel)
- Delta-encoded compression
- Event detection (PVCs, PACs, seizures)

---

## Backend Expectations

### Backend IS Listening For:

**MQTT Service Subscriptions:** [mqtt_service.py:149](hospital-backend/app/services/mqtt_service.py#L149)

```python
mqtt_topics = [
    "hospital/devices/+/vitals",      # ✅ ESP32 sends this
    "hospital/devices/+/waveform",    # ❌ ESP32 DOES NOT send this
    "hospital/devices/+/event",       # ❌ ESP32 DOES NOT send this
    "hospital/devices/+/heartbeat",   # ✅ ESP32 sends this
    "hospital/devices/+/alerts",      # ⚠️ ESP32 sends some device alerts
    "hospital/devices/+/status",      # ✅ ESP32 sends this
]
```

### Data Models Defined:

**1. VitalsRealtimeMessage** - Every 1 Second
[neural_vitals.py:109-147](hospital-backend/app/models/neural_vitals.py#L109-L147)

```python
class VitalsRealtimeMessage(BaseModel):
    deviceId: str
    patientId: str
    timestamp: datetime
    mode: Literal['ecg', 'eeg']

    # Basic vitals (ESP32 sends these ✅)
    heartRate: Optional[int]
    respiratoryRate: Optional[int]
    skinTemperature: Optional[float]
    oxygenSaturation: Optional[int]
    batteryLevel: Optional[int]
    signalQuality: Optional[float]

    # ❌ ESP32 NOT SENDING THESE:
    ecgAnalysis: Optional[ECGAnalysis] = None      # RR interval, QRS, QT, rhythm
    ecgLeads: Optional[ECGLeadValues] = None       # Lead I, II, III, aVR, aVL, aVF, V1-V6
    eegAnalysis: Optional[EEGAnalysis] = None      # Band powers, dominant freq, seizure flag
    eegChannels: Optional[EEGChannelValues] = None # Fp1, Fp2, F3, F4, C3, C4, O1, O2
```

**2. WaveformSnapshotMessage** - Every 10 Seconds
[neural_vitals.py:274-303](hospital-backend/app/models/neural_vitals.py#L274-L303)

```python
class WaveformSnapshotMessage(BaseModel):
    deviceId: str
    patientId: str
    timestamp: datetime
    mode: Literal['ecg', 'eeg']
    sampleRate: int  # 250 Hz or 500 Hz
    duration: int    # 10 seconds
    compression: Optional[str] = 'delta'

    # ❌ ESP32 NOT SENDING AT ALL:
    ecgWaveform: Optional[ECGWaveformData] = None  # 12-lead ECG raw data
    eegWaveform: Optional[EEGWaveformData] = None  # 8-channel EEG raw data
    quality: Optional[SignalQuality] = None
    sequence: Optional[int] = None
```

**3. NeuralEventMessage** - When Event Detected
[neural_vitals.py:309-342](hospital-backend/app/models/neural_vitals.py#L309-L342)

```python
class NeuralEventMessage(BaseModel):
    deviceId: str
    patientId: str
    timestamp: datetime
    mode: Literal['ecg', 'eeg']
    eventType: str  # "bradycardia", "tachycardia", "afib", "seizure", etc.
    severity: Literal['low', 'medium', 'high', 'critical']
    confidence: float

    # ❌ ESP32 NOT SENDING:
    waveform: Optional[Dict[str, Any]]  # Waveform snippet around event
    actions: Optional[List[str]]  # Recommended actions
```

---

## ECG/EEG Hardware Integration

### Required Hardware:

**For 8-12 Channel ECG/EEG:**
- **ADS1298** - Texas Instruments 8-channel 24-bit ADC
  - Sample rate: 250-500 Hz per channel
  - Resolution: 24-bit (high precision)
  - Communication: SPI
  - Channels: 8 simultaneous channels

**For 12-lead ECG:**
- 3 limb leads (I, II, III) - measured
- 3 augmented leads (aVR, aVL, aVF) - calculated
- 6 precordial leads (V1-V6) - measured (requires 12-lead system or ADS1299)

**For 8-channel EEG:**
- Fp1, Fp2 (Frontal pole)
- F3, F4 (Frontal)
- C3, C4 (Central)
- O1, O2 (Occipital)

---

## ESP32 Code Needed

### 1. Add ADS1298 Library and Initialization

```cpp
#include <SPI.h>
#include "ADS1298.h"

ADS1298 ads1298;

void setup() {
  // ... existing setup ...

  // Initialize ADS1298
  SPI.begin();
  if (ads1298.begin()) {
    Serial.println("✅ ADS1298 initialized");
    ads1298.setChannels(8);  // Enable 8 channels
    ads1298.setSampleRate(250);  // 250 Hz
    ads1298.startConversion();
  } else {
    Serial.println("❌ ADS1298 not found");
  }
}
```

### 2. Read Waveform Data

```cpp
// Buffer to store waveform data (10 seconds at 250 Hz = 2500 samples per channel)
#define SAMPLE_RATE 250
#define SNAPSHOT_DURATION 10
#define SAMPLES_PER_SNAPSHOT (SAMPLE_RATE * SNAPSHOT_DURATION)

int32_t ecgBuffer[8][SAMPLES_PER_SNAPSHOT];  // 8 channels × 2500 samples
int sampleIndex = 0;
unsigned long lastWaveformSend = 0;

void loop() {
  // ... existing loop code ...

  // Read ADC continuously
  if (ads1298.dataReady()) {
    ads1298.readChannels(ecgBuffer, sampleIndex);
    sampleIndex++;

    // Send waveform snapshot every 10 seconds
    if (sampleIndex >= SAMPLES_PER_SNAPSHOT) {
      sendWaveform();
      sampleIndex = 0;
    }
  }
}
```

### 3. Send Waveform Snapshot Message

```cpp
void sendWaveform() {
  if (!mqttClient.connected() || !isAssigned) return;

  String topic = "hospital/devices/" + deviceId + "/waveform";

  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();
  doc["mode"] = "ecg";
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["sampleRate"] = SAMPLE_RATE;
  doc["duration"] = SNAPSHOT_DURATION;
  doc["compression"] = "delta";

  // Delta-encode the waveform data for compression
  JsonObject ecgWaveform = doc.createNestedObject("ecgWaveform");
  JsonObject limb = ecgWaveform.createNestedObject("limb");

  // Lead I (channel 0)
  JsonObject leadI = limb.createNestedObject("leadI");
  deltaEncode(ecgBuffer[0], SAMPLES_PER_SNAPSHOT, leadI);

  // Lead II (channel 1)
  JsonObject leadII = limb.createNestedObject("leadII");
  deltaEncode(ecgBuffer[1], SAMPLES_PER_SNAPSHOT, leadII);

  // Lead III (channel 2)
  JsonObject leadIII = limb.createNestedObject("leadIII");
  deltaEncode(ecgBuffer[2], SAMPLES_PER_SNAPSHOT, leadIII);

  // Precordial leads (channels 3-7)
  JsonObject precordial = ecgWaveform.createNestedObject("precordial");
  JsonObject v1 = precordial.createNestedObject("v1");
  deltaEncode(ecgBuffer[3], SAMPLES_PER_SNAPSHOT, v1);
  // ... repeat for V2-V5

  String payload;
  serializeJson(doc, payload);

  if (mqttClient.publish(topic.c_str(), payload.c_str())) {
    Serial.println("📈 Waveform snapshot sent");
  }
}

void deltaEncode(int32_t* data, int length, JsonObject& output) {
  output["baseline"] = data[0];
  JsonArray deltas = output.createNestedArray("deltas");

  for (int i = 1; i < length; i++) {
    deltas.add(data[i] - data[i-1]);  // Store delta from previous sample
  }
}
```

### 4. Enhanced Vitals Message with ECG Analysis

```cpp
void sendVitals() {
  // ... existing basic vitals code ...

  // Add ECG analysis (if in ECG mode)
  if (mode == "ecg") {
    JsonObject ecgAnalysis = doc.createNestedObject("ecgAnalysis");
    ecgAnalysis["rrInterval"] = calculateRRInterval();  // milliseconds
    ecgAnalysis["qrsDuration"] = calculateQRSDuration();
    ecgAnalysis["qtInterval"] = calculateQTInterval();
    ecgAnalysis["rhythm"] = detectRhythm();  // "sinus", "afib", etc.

    JsonObject ecgLeads = doc.createNestedObject("ecgLeads");
    ecgLeads["leadI"] = getCurrentLeadValue(0);
    ecgLeads["leadII"] = getCurrentLeadValue(1);
    ecgLeads["leadIII"] = getCurrentLeadValue(2);
    // ... add all 12 leads
  }

  // ... rest of function
}
```

---

## Data Size Estimation

### Vitals Message (1 second):
```json
{
  "timestamp": "2025-10-21T10:00:00.000Z",
  "mode": "ecg",
  "deviceId": "fit-00001",
  "patientId": "PAT0001",
  "heartRate": 75,
  "skinTemperature": 37.0,
  "oxygenSaturation": 98,
  "respiratoryRate": 16,
  "batteryLevel": 85,
  "signalQuality": 0.95,
  "ecgAnalysis": {
    "rrInterval": 800,
    "qrsDuration": 100,
    "qtInterval": 400,
    "rhythm": "sinus"
  }
}
```
**Size:** ~400 bytes (small, every 1 second = 400 bytes/sec)

### Waveform Snapshot (10 seconds):
**Uncompressed:**
- 8 channels × 2500 samples × 4 bytes (int32) = 80,000 bytes = 80 KB

**Delta-compressed:**
- Baseline: 8 × 4 bytes = 32 bytes
- Deltas: 8 × 2500 × 2 bytes (int16) = 40,000 bytes = 40 KB
- **Total:** ~40 KB every 10 seconds = 4 KB/sec

**Combined bandwidth:**
- Vitals: 0.4 KB/sec
- Waveform: 4 KB/sec
- **Total:** 4.4 KB/sec = 35.2 Kbps

This is well within WiFi bandwidth limits.

---

## What Happens When ADS1298 Is Connected

### Scenario 1: ADS1298 Connected (Real ECG/EEG)

**ESP32 sends:**
1. **Vitals every 1 second** with ecgAnalysis/eegAnalysis
2. **Waveform every 10 seconds** with full 8-channel data
3. **Events when detected** (arrhythmia, seizure)

**Backend receives:**
- Real-time vital trends
- Full waveform for cardiologist review
- Automated arrhythmia detection
- EEG seizure detection

### Scenario 2: NO ADS1298 (Current State)

**ESP32 sends:**
1. **Vitals every 1 second** (basic only, no ECG analysis)
2. **NO waveform data** (sendWaveform() doesn't exist)
3. **NO events** (no waveform to analyze)

**Backend receives:**
- Basic vitals only (HR, SpO2, temp from MAX30102/MLX90614)
- No ECG/EEG waveforms
- No advanced cardiac monitoring

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│ ESP32 Watch                                             │
│                                                         │
│  MAX30102 ──► HR, SpO2 ──────────┐                     │
│  MLX90614 ──► Temperature ────────┤                     │
│  Battery ADC ──► Battery Level ───┤                     │
│                                   ▼                     │
│                          sendVitals() ──► 1 sec ──► MQTT
│                                                         │
│  ADS1298 ──► 8-ch ECG/EEG ──┐                          │
│                             ▼                           │
│                    sendWaveform() ──► 10 sec ──► MQTT   │
│                             │                           │
│                    Event Detection ──► on event ──► MQTT│
└─────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│ MQTT Broker (Mosquitto)                                 │
│  Topics:                                                │
│   - hospital/devices/{id}/vitals     (1 sec)           │
│   - hospital/devices/{id}/waveform   (10 sec)          │
│   - hospital/devices/{id}/event      (on detection)    │
└─────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│ Backend (FastAPI)                                       │
│                                                         │
│  MQTT Service ──► Receives all messages                │
│       │                                                 │
│       ├──► Vitals ──► TimescaleDB (vitals_realtime)    │
│       ├──► Waveform ──► TimescaleDB (waveform_snapshots)│
│       └──► Events ──► TimescaleDB (neural_events)       │
│                                                         │
│  Alert Detection Service ──► Analyzes waveforms        │
│  ECG Analysis Service ──► Arrhythmia detection         │
│  EEG Analysis Service ──► Seizure detection            │
└─────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│ Frontend (React)                                        │
│                                                         │
│  PatientCard ──► Shows current vitals                  │
│  ECG Viewer ──► Displays 12-lead ECG waveform          │
│  EEG Viewer ──► Displays 8-channel EEG                 │
│  Alert Panel ──► Shows detected events                 │
└─────────────────────────────────────────────────────────┘
```

---

## Current Status Summary

### ✅ Working:
- Basic vitals (HR, SpO2, Temp) every 1 second
- MQTT vitals topic publishing
- Backend vitals storage in TimescaleDB
- Frontend vitals display

### ❌ Missing:
- Waveform data publishing (no sendWaveform() function)
- ADS1298 hardware integration
- ECG/EEG analysis in vitals message
- Event detection and publishing
- Waveform display in frontend

### 🔧 To Implement:
1. **Add ADS1298 library** and hardware support
2. **Create sendWaveform()** function
3. **Add delta encoding** for compression
4. **Add ECG analysis** to vitals message
5. **Add event detection** logic
6. **Update mode switching** (ECG vs EEG)

---

## Recommendation

**Current System:** Works for basic vital signs monitoring (hospital watch use case)

**For Advanced Cardiac/Neural Monitoring:** Need to add:
1. ADS1298 hardware module
2. Waveform sending code (sendWaveform function)
3. Event detection code
4. Frontend ECG/EEG viewers

**This is a separate feature** - the current basic vitals system is complete and functional for its intended purpose.
