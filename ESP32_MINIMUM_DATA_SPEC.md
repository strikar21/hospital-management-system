# ESP32 Watch - Minimum Data Specification

**Philosophy:** Watch is a sensor - reads raw data, sends it. Backend does analysis and generates alerts.

---

## What ESP32 Watch MUST Send

### 1. Vitals Message (Every 1 Second)
**Topic:** `hospital/devices/{deviceId}/vitals`

```json
{
  // Device identification
  "deviceId": "ESP32_WATCH_003",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd",
  "timestamp": "2025-10-15T10:30:45Z",
  "mode": "ecg",  // or "eeg"

  // Basic vitals (simple calculations, battery-friendly)
  "heartRate": 75,              // Count R peaks in last second
  "respiratoryRate": 16,        // From impedance or chest movement
  "skinTemperature": 37.2,      // Direct thermistor reading
  "oxygenSaturation": 98,       // Direct MAX30102/MAX30100 reading
  "batteryLevel": 85,           // Battery percentage
  "signalQuality": 0.95,        // Overall signal quality (0-1)

  // Optional: Blood pressure (if you have a BP sensor)
  "bloodPressureSystolic": 120,
  "bloodPressureDiastolic": 80,

  // Quality metrics (per-channel)
  "quality": {
    "overall": 0.92,
    "leadOff": [false, false, false, false, false, false, false, false],  // 8 channels
    "noise": [0.05, 0.03, 0.04, 0.02, 0.06, 0.03, 0.04, 0.05],          // 8 channels
    "impedance": [5.2, 4.8, 6.1, 5.5, 4.9, 5.3, 5.7, 5.1]               // kOhm
  },

  "sequence": 12345
}
```

**NO ECG/EEG analysis here!** Backend will calculate from waveform.

---

### 2. Waveform Message (Every 10 Seconds)
**Topic:** `hospital/devices/{deviceId}/waveform`

**Purpose:** Send raw ADC waveform data for backend analysis

```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd",
  "timestamp": "2025-10-15T10:30:50Z",
  "mode": "ecg",
  "sampleRate": 250,  // Hz
  "duration": 10,     // seconds
  "compression": "delta",  // or "none" if not compressed

  // ECG Mode: Send 1/3/5/8 leads based on what's connected
  "ecgWaveform": {
    "limb": {
      "leadI": {"baseline": 2048, "deltas": [1, 2, -1, 0, 1, ...]},
      "leadII": {"baseline": 2050, "deltas": [2, 1, 0, -1, 2, ...]},
      "leadIII": {"baseline": 2045, "deltas": [0, 1, 1, 2, -1, ...]}
    }
    // Add precordial/derived only if you have 5/8 lead setup
  },

  // OR EEG Mode: Send 1/3/5/8 channels based on what's connected
  "eegWaveform": {
    "frontal": {
      "Fp1": {"baseline": 1500, "deltas": [5, -3, 2, 0, ...]},
      "Fp2": {"baseline": 1505, "deltas": [-2, 4, 1, -1, ...]},
      // Only include channels that are actually connected
    }
  },

  "quality": {
    "overall": 0.89,
    "leadOff": [false, false, false],  // Per channel
    "noise": [0.05, 0.03, 0.04]
  },

  "sequence": 124
}
```

**Key Points:**
- Send only leads/channels that are **actually connected**
- 1-lead setup: Send only that 1 channel
- 3-lead setup: Send 3 channels
- 8-lead setup: Send all 8 channels
- Backend will work with whatever you send

---

### 3. Watch Health/Status Message (Every 30 Seconds)
**Topic:** `hospital/devices/{deviceId}/heartbeat`

**Purpose:** Keep backend informed about watch hardware health

```json
{
  "deviceId": "ESP32_WATCH_003",
  "timestamp": "2025-10-15T10:31:00Z",
  "battery": 85,
  "charging": false,
  "temperature": 32.5,  // ESP32 internal temp (°C)
  "freeHeap": 245000,   // Free memory (bytes)
  "uptime": 86400,      // Seconds since boot
  "wifiRssi": -45,      // WiFi signal strength (dBm)
  "version": "3.2.0"    // Firmware version
}
```

**Backend uses this to:**
- Update device status (online/offline)
- Show battery warnings
- Monitor hardware health

---

## What ESP32 Watch CAN Send (Battery Permitting)

### 4. Critical Event Alerts (Only If ESP32 Detects)
**Topic:** `hospital/devices/{deviceId}/event`

**Only if ESP32 has enough power to do basic detection:**

```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd",
  "timestamp": "2025-10-15T10:35:00Z",
  "mode": "ecg",
  "eventType": "bradycardia",  // or "tachycardia", "irregularRhythm"
  "severity": "high",
  "confidence": 0.75,

  "context": {
    "heartRate": 45,  // HR at time of event
    "signalQuality": 0.9
  }
}
```

**What ESP32 CAN detect with low power:**
- ✅ Bradycardia (HR < 50 BPM) - simple threshold
- ✅ Tachycardia (HR > 120 BPM) - simple threshold
- ✅ Irregular rhythm - RR interval variance
- ✅ SpO2 < 90% - simple threshold
- ❌ Complex arrhythmias (afib, VT, PVCs) - backend should analyze

**Philosophy:**
- ESP32 can send **basic threshold alerts** (fast, battery-friendly)
- Backend does **deep analysis** on waveform data (slow, accurate)
- Frontend shows both types of alerts

---

## Summary - What To Implement in ESP32

### Minimum Required (Phase 1):
1. ✅ Vitals message (1 sec) - basic vitals only
2. ✅ Waveform message (10 sec) - raw ADC data, 1-8 leads
3. ✅ Heartbeat message (30 sec) - watch health

### Optional If Battery Allows (Phase 2):
4. ⏳ Event message - basic threshold alerts only

---

## Data Flow Summary

```
ESP32 Watch
    ├─→ Vitals (1 sec)
    │   └─→ HR, SpO2, temp, quality (NO analysis)
    │
    ├─→ Waveform (10 sec)
    │   └─→ Raw ADC data (1-8 leads)
    │
    ├─→ Heartbeat (30 sec)
    │   └─→ Battery, WiFi, memory
    │
    └─→ Event (when detected)
        └─→ Basic alerts (bradycardia, tachycardia)

Backend Receives
    ├─→ Stores vitals in TimescaleDB
    ├─→ Stores waveform for analysis
    ├─→ Analyzes waveform → ECG metrics
    │   ├─→ RR interval, QRS, QT (complex)
    │   ├─→ Rhythm detection (afib, VT)
    │   └─→ ST segment analysis
    ├─→ Generates alerts from analysis
    └─→ Broadcasts to frontend

Frontend Displays
    └─→ Shows everything (vitals + alerts)
```

---

## Recommendation

**For mock data, ESP32 should send:**

1. **Vitals message (1 sec):**
   ```json
   {
     "heartRate": 75,
     "respiratoryRate": 16,
     "skinTemperature": 37.2,
     "oxygenSaturation": 98,
     "batteryLevel": 85,
     "signalQuality": 0.95
   }
   ```

2. **Waveform message (10 sec):**
   ```json
   {
     "mode": "ecg",
     "sampleRate": 250,
     "ecgWaveform": {
       "limb": {
         "leadI": {"baseline": 2048, "deltas": [...]},
         "leadII": {"baseline": 2050, "deltas": [...]},
         "leadIII": {"baseline": 2045, "deltas": [...]}
       }
     }
   }
   ```

3. **Heartbeat message (30 sec):**
   ```json
   {
     "battery": 85,
     "wifiRssi": -45
   }
   ```

4. **Event message (only for critical situations):**
   ```json
   {
     "eventType": "bradycardia",
     "severity": "high",
     "context": {"heartRate": 45}
   }
   ```

**Does this make sense?** ESP32 stays lean, backend does heavy analysis.
