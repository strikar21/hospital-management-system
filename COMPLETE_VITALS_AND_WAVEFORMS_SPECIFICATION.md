# Complete Vitals and Waveforms Specification

**Date:** 2025-10-21
**System:** Hospital Management - ESP32 Watch
**Status:** Backend Ready | ESP32 Partial Implementation

---

## OVERVIEW

The system supports **3 types of MQTT messages** from ESP32 devices:

1. **Vitals** - Every 1 second (basic physiological parameters)
2. **Waveforms** - Every 10 seconds (full ECG/EEG waveform data)
3. **Events** - On-demand (arrhythmia/seizure detection alerts)

All data uses **camelCase** naming convention throughout the stack.

---

## MESSAGE TYPE 1: VITALS (Every 1 Second)

**MQTT Topic:** `hospital/devices/{deviceId}/vitals`
**Frequency:** 1 second intervals
**Current ESP32 Status:** ✅ Implemented (sending zeros currently)

### Complete Vitals Data Structure

```json
{
  // ============================================
  // DEVICE IDENTIFICATION (REQUIRED)
  // ============================================
  "deviceId": "fit-00001",
  "patientId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-21T10:00:00.000Z",
  "mode": "ecg",  // ✅ NOW DYNAMIC: "ecg" or "eeg" (GPIO-based)

  // ============================================
  // BASIC VITALS (OPTIONAL)
  // ============================================
  "heartRate": 75,                    // BPM (30-250 valid range)
  "respiratoryRate": 16,              // breaths/min (5-60 valid range)
  "skinTemperature": 36.5,            // Celsius (30-45 valid range)
  "oxygenSaturation": 98,             // % SpO2 (0-100 valid range)
  "bloodPressureSystolic": 120,       // mmHg (60-200 valid range)
  "bloodPressureDiastolic": 80,       // mmHg (40-130 valid range)
  "batteryLevel": 85,                 // % (0-100)
  "signalQuality": 0.95,              // 0.0-1.0 (overall quality)

  // ============================================
  // ECG ANALYSIS (MODE='ecg' ONLY)
  // ============================================
  "ecgAnalysis": {
    "rrInterval": 850,                // milliseconds (R-R interval)
    "qrsDuration": 100,               // milliseconds (QRS complex duration)
    "qtInterval": 380,                // milliseconds (QT interval)
    "axis": 45,                       // degrees (heart electrical axis)
    "rhythm": "sinus",                // "sinus", "afib", "aflutter", etc.
    "stSegment": "normal"             // "normal", "elevated", "depressed"
  },

  "ecgLeads": {
    // Instantaneous or averaged ECG lead values
    "leadI": 0.5,
    "leadII": 1.2,
    "leadIII": 0.7,
    "aVR": -0.85,
    "aVL": 0.35,
    "aVF": 0.95,
    "v1": -0.3,
    "v2": 0.8,
    "v3": 1.5,
    "v4": 1.8,
    "v5": 1.3,
    "v6": 0.9
  },

  // ============================================
  // EEG ANALYSIS (MODE='eeg' ONLY)
  // ============================================
  "eegAnalysis": {
    "bandPowers": {
      "alpha": 25.5,                  // µV² (8-13 Hz)
      "beta": 12.3,                   // µV² (13-30 Hz)
      "theta": 18.7,                  // µV² (4-8 Hz)
      "delta": 45.2,                  // µV² (0.5-4 Hz)
      "gamma": 5.8                    // µV² (30-100 Hz) [optional]
    },
    "dominantFrequency": 10.5,        // Hz (0-100)
    "asymmetry": 0.15,                // Left-right hemispheric asymmetry
    "seizureActivity": false          // boolean flag
  },

  "eegChannels": {
    // Instantaneous or averaged EEG channel values
    "Fp1": 45.2,                      // Frontal pole 1 (µV)
    "Fp2": 43.8,                      // Frontal pole 2 (µV)
    "F3": 38.5,                       // Frontal 3 (µV)
    "F4": 39.2,                       // Frontal 4 (µV)
    "C3": 35.7,                       // Central 3 (µV)
    "C4": 36.1,                       // Central 4 (µV)
    "O1": 42.3,                       // Occipital 1 (µV)
    "O2": 41.9                        // Occipital 2 (µV)
  },

  // ============================================
  // SIGNAL QUALITY (OPTIONAL)
  // ============================================
  "quality": {
    "overall": 0.95,                  // 0.0-1.0
    "leadOff": [false, false, false, false, false, false, false, false],  // 8 channels
    "noise": [0.1, 0.15, 0.08, 0.12, 0.09, 0.11, 0.14, 0.10],            // 8 channels (0-1)
    "impedance": [1.2, 1.5, 1.8, 2.1, 1.9, 1.6, 2.3, 2.0]                // 8 channels (kOhm)
  },

  // ============================================
  // METADATA (OPTIONAL)
  // ============================================
  "sequence": 12345,                  // Message sequence number
  "metadata": {
    "firmwareVersion": "5.0.0",
    "sensorType": "ADS1298",
    "calibrationDate": "2025-10-20"
  }
}
```

---

## MESSAGE TYPE 2: WAVEFORMS (Every 10 Seconds)

**MQTT Topic:** `hospital/devices/{deviceId}/waveform`
**Frequency:** 10 second intervals
**Current ESP32 Status:** ❌ NOT IMPLEMENTED (requires ADS1298 hardware)

### ECG Mode Waveform (12-Lead)

```json
{
  // ============================================
  // DEVICE IDENTIFICATION (REQUIRED)
  // ============================================
  "deviceId": "fit-00001",
  "patientId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-21T10:00:00.000Z",
  "mode": "ecg",

  // ============================================
  // WAVEFORM PARAMETERS (REQUIRED)
  // ============================================
  "sampleRate": 250,                  // Hz (samples per second)
  "duration": 10,                     // seconds
  "compression": "delta",             // "delta", "none", "zlib"

  // ============================================
  // ECG WAVEFORM DATA (12 LEADS)
  // ============================================
  "ecgWaveform": {
    // LIMB LEADS (REQUIRED - Minimum 3 leads)
    "limb": {
      "leadI": {
        "baseline": 512,              // ADC baseline value (0-1023 for 10-bit, 0-16777215 for 24-bit)
        "deltas": [2, -1, 0, 3, -2, ...] // Array of 2500 delta values (250 Hz * 10 sec)
      },
      "leadII": {
        "baseline": 518,
        "deltas": [1, 0, -1, 2, -3, ...]
      },
      "leadIII": {
        "baseline": 506,
        "deltas": [-1, 2, 0, -2, 1, ...]
      }
    },

    // PRECORDIAL LEADS (OPTIONAL - V1-V5)
    "precordial": {
      "v1": {
        "baseline": 520,
        "deltas": [...]
      },
      "v2": {
        "baseline": 525,
        "deltas": [...]
      },
      "v3": {
        "baseline": 530,
        "deltas": [...]
      },
      "v4": {
        "baseline": 535,
        "deltas": [...]
      },
      "v5": {
        "baseline": 528,
        "deltas": [...]
      }
    },

    // DERIVED LEADS (OPTIONAL - Calculated from limb leads)
    "derived": {
      "aVR": {
        "baseline": 490,
        "deltas": [...]
      },
      "aVL": {
        "baseline": 515,
        "deltas": [...]
      },
      "aVF": {
        "baseline": 522,
        "deltas": [...]
      },
      "v6": {
        "baseline": 524,
        "deltas": [...]
      }
    },

    // DETECTED EVENTS (OPTIONAL)
    "events": [
      {
        "timestamp": 3250,            // milliseconds from start
        "eventType": "pvc",           // "pvc" (premature ventricular contraction), "pac", etc.
        "confidence": 0.95,           // 0.0-1.0
        "location": "leadII"          // which lead detected the event
      }
    ]
  },

  // ============================================
  // SIGNAL QUALITY (OPTIONAL)
  // ============================================
  "quality": {
    "overall": 0.92,
    "leadOff": [false, false, false, false, false, false, false, false],
    "impedance": [1.2, 1.5, 1.8, 2.1, 1.9, 1.6, 2.3, 2.0]
  },

  // ============================================
  // METADATA (OPTIONAL)
  // ============================================
  "sequence": 123,
  "metadata": {
    "compressionRatio": 3.5,
    "originalSize": 60000,
    "compressedSize": 17143
  }
}
```

### EEG Mode Waveform (8-Channel)

```json
{
  // ============================================
  // DEVICE IDENTIFICATION (REQUIRED)
  // ============================================
  "deviceId": "fit-00001",
  "patientId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-21T10:00:00.000Z",
  "mode": "eeg",

  // ============================================
  // WAVEFORM PARAMETERS (REQUIRED)
  // ============================================
  "sampleRate": 250,                  // Hz
  "duration": 10,                     // seconds
  "compression": "delta",

  // ============================================
  // EEG WAVEFORM DATA (8 CHANNELS)
  // ============================================
  "eegWaveform": {
    // FRONTAL CHANNELS (REQUIRED - 4 channels)
    "frontal": {
      "Fp1": {
        "baseline": 8388608,          // 24-bit ADC midpoint
        "deltas": [120, -85, 45, ...]  // 2500 samples
      },
      "Fp2": {
        "baseline": 8388610,
        "deltas": [110, -90, 50, ...]
      },
      "F3": {
        "baseline": 8388605,
        "deltas": [95, -75, 40, ...]
      },
      "F4": {
        "baseline": 8388612,
        "deltas": [100, -80, 42, ...]
      }
    },

    // CENTRAL CHANNELS (REQUIRED - 2 channels)
    "central": {
      "C3": {
        "baseline": 8388600,
        "deltas": [85, -70, 38, ...]
      },
      "C4": {
        "baseline": 8388615,
        "deltas": [90, -72, 39, ...]
      }
    },

    // OCCIPITAL CHANNELS (REQUIRED - 2 channels)
    "occipital": {
      "O1": {
        "baseline": 8388608,
        "deltas": [105, -82, 44, ...]
      },
      "O2": {
        "baseline": 8388611,
        "deltas": [108, -84, 46, ...]
      }
    },

    // EEG ANALYSIS (OPTIONAL - Backend can also calculate this)
    "analysis": {
      "bandPowers": {
        "alpha": 25.5,
        "beta": 12.3,
        "theta": 18.7,
        "delta": 45.2,
        "gamma": 5.8
      },
      "dominantFrequency": 10.5,
      "asymmetry": 0.15,
      "seizureActivity": false
    }
  },

  // ============================================
  // SIGNAL QUALITY (OPTIONAL)
  // ============================================
  "quality": {
    "overall": 0.88,
    "leadOff": [false, false, false, false, false, false, false, false],
    "impedance": [2.1, 2.3, 1.9, 2.5, 2.0, 2.2, 2.4, 2.1]
  },

  // ============================================
  // METADATA (OPTIONAL)
  // ============================================
  "sequence": 123,
  "metadata": {
    "eyesOpen": false,
    "stimulusActive": false
  }
}
```

### Delta Encoding Explanation

**Why Delta Encoding?**
- Reduces bandwidth by 60-80%
- ECG/EEG waveforms have high sample-to-sample correlation
- Instead of sending absolute values, send differences

**Example:**
```
Original values: [512, 514, 513, 513, 516, 514, ...]
Delta encoded:
  baseline: 512
  deltas: [2, -1, 0, 3, -2, ...]
```

**Decompression (Backend):**
```python
def decompress(baseline, deltas):
    values = [baseline]
    for delta in deltas:
        values.append(values[-1] + delta)
    return values
```

---

## MESSAGE TYPE 3: NEURAL EVENTS (On-Demand)

**MQTT Topic:** `hospital/devices/{deviceId}/event`
**Frequency:** Only when arrhythmia or seizure detected
**Current ESP32 Status:** ❌ NOT IMPLEMENTED (requires waveform analysis)

### Neural Event Message

```json
{
  // ============================================
  // DEVICE IDENTIFICATION (REQUIRED)
  // ============================================
  "deviceId": "fit-00001",
  "patientId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-21T10:00:15.500Z",
  "mode": "ecg",

  // ============================================
  // EVENT DETAILS (REQUIRED)
  // ============================================
  "eventType": "bradycardia",         // ECG: "bradycardia", "tachycardia", "vfib", "asystole"
                                      // EEG: "seizure", "spike_wave", "burst_suppression"
  "severity": "high",                 // "low", "medium", "high", "critical"
  "confidence": 0.95,                 // 0.0-1.0 (detection confidence)

  // ============================================
  // CONTEXT (OPTIONAL)
  // ============================================
  "sampleRate": 250,
  "duration": 5,                      // seconds of event
  "context": {
    // Vitals at time of event
    "heartRate": 45,
    "respiratoryRate": 16,
    "oxygenSaturation": 95,
    "skinTemperature": 36.5
  },

  // ============================================
  // WAVEFORM SNIPPET (OPTIONAL)
  // ============================================
  "waveform": {
    // Small segment showing the event (5 seconds)
    "leadII": {
      "baseline": 512,
      "deltas": [/* 1250 samples - 5 sec * 250 Hz */]
    }
  },

  // ============================================
  // RECOMMENDED ACTIONS (OPTIONAL)
  // ============================================
  "actions": [
    "Check patient immediately",
    "Verify electrode placement",
    "Consider atropine if symptomatic"
  ],

  // ============================================
  // METADATA (OPTIONAL)
  // ============================================
  "metadata": {
    "algorithm": "pan_tompkins",
    "detectionLatency": 2.5          // seconds from event start to detection
  }
}
```

---

## CURRENT ESP32 IMPLEMENTATION STATUS

### ✅ IMPLEMENTED (Sending Now)

**Message Type:** Vitals (1 second interval)

**Fields Currently Sent:**
```json
{
  "timestamp": "2025-10-21T10:00:00.000Z",
  "mode": "ecg",                      // ✅ NOW GPIO-BASED (GPIO 4)
  "deviceId": "fit-00001",
  "patientId": "PAT0001",
  "heartRate": 0,                     // ❌ Zero (no sensor)
  "skinTemperature": -17.78,          // ❌ Zero converted to Celsius
  "oxygenSaturation": 0,              // ❌ Zero (no sensor)
  "respiratoryRate": 0,               // ❌ Zero (no sensor)
  "batteryLevel": 100,                // ✅ Hardcoded 100%
  "signalQuality": 0.0                // ❌ Zero (no sensor)
}
```

**Current Issues:**
- All vitals are zero (fake data removed)
- No real sensors integrated yet
- Backend triggers sensor malfunction alerts

### ❌ NOT IMPLEMENTED

**Message Type:** Waveforms (10 second interval)
- No `sendWaveform()` function exists
- Requires ADS1298 8-channel ADC hardware
- Backend is ready but receives nothing

**Message Type:** Neural Events (on-demand)
- No arrhythmia/seizure detection on ESP32
- Backend can detect these from waveform analysis
- ESP32 doesn't need to implement this (backend handles it)

---

## SENSOR REQUIREMENTS

### For Basic Vitals (Message Type 1)

| Vital Sign | Sensor | Interface | Notes |
|------------|--------|-----------|-------|
| Heart Rate | MAX30102 | I2C | PPG sensor |
| SpO2 | MAX30102 | I2C | Same sensor as HR |
| Skin Temperature | MLX90614 | I2C | Non-contact IR thermometer |
| Respiratory Rate | MAX30102 | I2C | Calculated from PPG waveform |
| Blood Pressure | ❌ Not planned | - | Requires cuff hardware |
| Battery Level | ESP32 ADC | ADC GPIO | Battery voltage divider |

### For ECG Waveforms (Message Type 2 - ECG Mode)

| Component | Part Number | Channels | Notes |
|-----------|-------------|----------|-------|
| **ADC** | ADS1298 | 8 channels | 24-bit, 250 Hz |
| **Electrodes** | 3M Red Dot | 10 electrodes | 12-lead ECG configuration |
| **Interface** | SPI | SCLK, MISO, MOSI, CS | High-speed data transfer |

**12-Lead ECG Electrode Placement:**
- **Limb Leads:** RA, LA, LL, RL (4 electrodes)
- **Precordial:** V1, V2, V3, V4, V5, V6 (6 electrodes)

### For EEG Waveforms (Message Type 2 - EEG Mode)

| Component | Part Number | Channels | Notes |
|-----------|-------------|----------|-------|
| **ADC** | ADS1298 | 8 channels | Same hardware as ECG |
| **Electrodes** | Gold cup EEG | 8 electrodes | 10-20 system placement |
| **Interface** | SPI | Same as ECG | - |

**8-Channel EEG Electrode Placement (10-20 System):**
- **Frontal:** Fp1, Fp2, F3, F4
- **Central:** C3, C4
- **Occipital:** O1, O2

---

## TIMESCALEDB STORAGE SCHEMA

### Table 1: `vitals_realtime` (Hypertable)

```sql
CREATE TABLE vitals_realtime (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50) NOT NULL,
    mode VARCHAR(10) NOT NULL,        -- 'ecg' or 'eeg'

    -- Basic vitals
    "heartRate" INTEGER,
    "respiratoryRate" INTEGER,
    "skinTemperature" DECIMAL(4,1),
    "oxygenSaturation" INTEGER,
    "batteryLevel" INTEGER,
    "signalQuality" DECIMAL(3,2),

    -- ECG analysis (mode='ecg')
    "rrInterval" INTEGER,
    "qrsDuration" INTEGER,
    "qtInterval" INTEGER,
    axis INTEGER,
    rhythm VARCHAR(50),
    "stSegment" VARCHAR(20),

    -- EEG analysis (mode='eeg')
    "alphaPower" DECIMAL(5,2),
    "betaPower" DECIMAL(5,2),
    "thetaPower" DECIMAL(5,2),
    "deltaPower" DECIMAL(5,2),
    "gammaPower" DECIMAL(5,2),
    "dominantFrequency" DECIMAL(5,2),
    "seizureActivity" BOOLEAN,

    -- Quality & metadata
    quality JSONB,
    sequence INTEGER,
    metadata JSONB
);
```

**Retention:** 90 days (compressed after 7 days)

### Table 2: `waveform_snapshots` (Hypertable)

```sql
CREATE TABLE waveform_snapshots (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50) NOT NULL,
    mode VARCHAR(10) NOT NULL,
    "sampleRate" INTEGER NOT NULL,
    duration INTEGER NOT NULL,

    -- ECG channels (JSONB for flexibility)
    "ecgLimbLeads" JSONB,
    "ecgPrecordialLeads" JSONB,
    "ecgDerivedLeads" JSONB,
    "ecgEvents" JSONB,

    -- EEG channels (JSONB for flexibility)
    "eegFrontalChannels" JSONB,
    "eegCentralChannels" JSONB,
    "eegOccipitalChannels" JSONB,
    "eegAnalysis" JSONB,

    -- Quality & metadata
    quality JSONB,
    sequence INTEGER,
    compression VARCHAR(20),
    metadata JSONB
);
```

**Retention:** 30 days (compressed after 1 day)
**Storage:** ~1.5 GB per patient per day (with delta compression)

### Table 3: `neural_events`

```sql
CREATE TABLE neural_events (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50) NOT NULL,
    "eventType" VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    mode VARCHAR(10) NOT NULL,

    -- Optional waveform context
    "sampleRate" INTEGER,
    duration INTEGER,
    context JSONB,
    waveform JSONB,
    actions JSONB,

    -- Workflow tracking
    acknowledged BOOLEAN DEFAULT FALSE,
    "acknowledgedBy" VARCHAR(100),
    "acknowledgedAt" TIMESTAMPTZ,
    resolved BOOLEAN DEFAULT FALSE,
    "resolvedAt" TIMESTAMPTZ,

    metadata JSONB
);
```

**Retention:** Permanent (important clinical events)

---

## BACKEND ANALYSIS CAPABILITIES

### ECG Analysis (Mode='ecg')

Backend automatically analyzes ECG waveforms for:

**Arrhythmia Detection:**
- Bradycardia (HR < 60 BPM)
- Tachycardia (HR > 100 BPM)
- Atrial Fibrillation (irregular R-R intervals)
- Ventricular Fibrillation (chaotic waveform)
- Premature Ventricular Contractions (PVCs)
- Asystole (flat line)

**Interval Analysis:**
- RR interval (heart rate variability)
- QRS duration (ventricular depolarization)
- QT interval (corrected QTc for long QT syndrome)
- PR interval (AV node conduction time)

**Morphology Analysis:**
- ST segment elevation/depression (ischemia)
- T wave inversion (ischemia)
- QRS axis deviation
- Bundle branch blocks

### EEG Analysis (Mode='eeg')

Backend automatically analyzes EEG waveforms for:

**Frequency Band Analysis:**
- Alpha (8-13 Hz) - Relaxed wakefulness
- Beta (13-30 Hz) - Active thinking
- Theta (4-8 Hz) - Drowsiness
- Delta (0.5-4 Hz) - Deep sleep
- Gamma (30-100 Hz) - Cognitive processing

**Seizure Detection:**
- Spike-wave patterns
- High-frequency oscillations
- Burst suppression
- Electrographic seizures

**Asymmetry Analysis:**
- Left-right hemispheric differences
- Focal abnormalities

---

## MQTT TOPICS SUMMARY

| Topic | Frequency | Size | Status |
|-------|-----------|------|--------|
| `hospital/devices/{deviceId}/vitals` | 1 sec | ~300 bytes | ✅ Active |
| `hospital/devices/{deviceId}/waveform` | 10 sec | ~15-60 KB | ⏳ Backend ready |
| `hospital/devices/{deviceId}/event` | On-demand | ~1-5 KB | ⏳ Backend ready |
| `hospital/devices/{deviceId}/heartbeat` | 30 sec | ~150 bytes | ✅ Active |
| `hospital/devices/{deviceId}/status` | On-change | ~200 bytes | ⏳ Backend ready |
| `hospital/devices/{deviceId}/alerts` | On-demand | ~500 bytes | ⏳ Backend ready |

---

## BANDWIDTH ANALYSIS

### Per Device (24/7 Monitoring)

**Vitals Only (Current):**
- 1 message/sec × 300 bytes = 300 bytes/sec
- **Daily:** 25.92 MB
- **Monthly:** 777.6 MB
- **100 Patients:** 77.76 GB/month

**Vitals + Waveforms (With Sensors):**
- Vitals: 300 bytes/sec
- Waveforms: 15 KB every 10 sec = 1.5 KB/sec
- **Total:** 1.8 KB/sec
- **Daily:** 155.52 MB
- **Monthly:** 4.67 GB
- **100 Patients:** 467 GB/month

**With Delta Compression:**
- Reduces waveform size by 60-80%
- **Total:** ~720 bytes/sec
- **Daily:** 62.21 MB
- **Monthly:** 1.87 GB
- **100 Patients:** 187 GB/month

---

## NEXT STEPS

### Immediate (No Hardware Required)
1. ✅ GPIO mode detection implemented
2. ⏳ Add realistic test vitals (random variations for testing)
3. ⏳ Test dynamic mode switching (ECG/EEG)

### Short-Term (Basic Sensors)
1. ⏳ Integrate MAX30102 for HR and SpO2
2. ⏳ Integrate MLX90614 for temperature
3. ⏳ Add battery voltage monitoring
4. ⏳ Calculate respiratory rate from PPG

### Long-Term (Full Waveform Capability)
1. ⏳ Integrate ADS1298 8-channel ADC
2. ⏳ Implement `sendWaveform()` function
3. ⏳ Add delta encoding compression
4. ⏳ Test ECG 12-lead configuration
5. ⏳ Test EEG 8-channel configuration
6. ⏳ Validate backend analysis accuracy

---

## SUMMARY

**Total Possible Data Fields:**

**Vitals Message:** 30+ fields
- 8 basic vitals (HR, RR, temp, SpO2, BP, battery, quality, mode)
- 12 ECG lead values (optional)
- 6 ECG analysis metrics (optional)
- 8 EEG channel values (optional)
- 5 EEG band powers (optional)
- Quality metrics (optional)

**Waveform Message:** 8-12 channels
- ECG: 3-12 leads (limb + precordial + derived)
- EEG: 8 channels (frontal + central + occipital)
- 250 Hz sampling = 2500 samples per channel per 10-second snapshot
- Delta encoding for bandwidth efficiency

**Event Message:** On-demand alerts
- Arrhythmia detection (ECG mode)
- Seizure detection (EEG mode)
- Context vitals + waveform snippet
- Recommended clinical actions

**Backend:** Fully ready for all message types. Waiting for ESP32 sensor integration.
