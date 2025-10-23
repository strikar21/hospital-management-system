# ADS1298 8-Channel Implementation Specification

## Hardware: TI ADS1298 (Professional Medical-Grade ADC)

### Specifications:
- **Channels**: 8 differential inputs
- **Resolution**: 24-bit ADC
- **Sample Rate**: Up to 32 kSPS (typically 250-500 Hz for ECG/EEG)
- **Input Range**: ±2.4V differential
- **Noise**: 0.19 μVpp (very low - clinical grade)
- **Built-in Features**:
  - Right-leg drive (RLD) for noise reduction
  - Lead-off detection
  - Built-in respiration measurement
  - Wilson Central Terminal (WCT) for 12-lead ECG

**This is the SAME chip used in professional Holter monitors and clinical EEG systems!**

---

## ECG Mode: Full 12-Lead Capability

### Standard 12-Lead ECG Configuration

With 8 channels, you can capture **full 12-lead ECG**:

#### Physical Leads (10 electrodes):
```
Limb Electrodes (4):
- RA (Right Arm)
- LA (Left Arm)
- RL (Right Leg) - Reference/ground
- LL (Left Leg)

Precordial Electrodes (6):
- V1: 4th intercostal space, right sternal border
- V2: 4th intercostal space, left sternal border
- V3: Midway between V2 and V4
- V4: 5th intercostal space, mid-clavicular line
- V5: Same level as V4, anterior axillary line
- V6: Same level as V4, mid-axillary line
```

#### 8 ADC Channels Map To:
```
Channel 1: Lead I   (LA - RA)
Channel 2: Lead II  (LL - RA)
Channel 3: Lead III (LL - LA)  [Can also be derived]
Channel 4: V1
Channel 5: V2
Channel 6: V3
Channel 7: V4
Channel 8: V5 (V6 can be derived or use 8th channel)
```

#### Augmented Leads (Derived):
```
aVR = RA - (LA + LL)/2
aVL = LA - (RA + LL)/2
aVF = LL - (RA + LA)/2
```

**Total: 12 leads (8 direct + 3 augmented + 1 derived)**

---

## EEG Mode: 8-Channel EEG (10-20 System)

### Clinical 8-Channel EEG Setup

```
Channel 1: Fp1 (Left frontal pole)
Channel 2: Fp2 (Right frontal pole)
Channel 3: F3  (Left frontal)
Channel 4: F4  (Right frontal)
Channel 5: C3  (Left central)
Channel 6: C4  (Right central)
Channel 7: O1  (Left occipital)
Channel 8: O2  (Right occipital)

Reference: Cz (vertex) or linked mastoids (A1-A2)
```

**Coverage**: Full anterior-posterior brain monitoring
- Frontal lobe (Fp1, Fp2, F3, F4)
- Central lobe (C3, C4)
- Occipital lobe (O1, O2)

---

## Data Structure Design

### ESP32 → MQTT Message Format

#### ECG Mode (12-Lead, 250 Hz):
```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "patient-uuid",
  "timestamp": "2025-10-15T10:30:00.000Z",
  "mode": "ecg",
  "sampleRate": 250,
  "duration": 1,

  "aggregates": {
    "heartRate": 75,
    "rrInterval": 800,
    "qrsDuration": 90,
    "qtInterval": 380,
    "temperature": 98.6,
    "oxygenSat": 98
  },

  "channels": {
    "leadI": [120, 122, 125, ...],      // 250 samples
    "leadII": [150, 152, 155, ...],     // 250 samples
    "leadIII": [30, 30, 30, ...],       // 250 samples
    "v1": [110, 112, 115, ...],         // 250 samples
    "v2": [115, 117, 120, ...],         // 250 samples
    "v3": [120, 122, 125, ...],         // 250 samples
    "v4": [125, 127, 130, ...],         // 250 samples
    "v5": [130, 132, 135, ...]          // 250 samples
  },

  "derived": {
    "aVR": [-135, -137, -140, ...],     // Calculated
    "aVL": [60, 62, 65, ...],           // Calculated
    "aVF": [90, 92, 95, ...]            // Calculated
  },

  "quality": {
    "overall": 0.95,
    "leadOff": [],
    "noise": 0.05
  },

  "batteryLevel": 85
}
```

**Payload Size**: ~20 KB/sec (12 channels × 250 Hz × 2 bytes + JSON overhead)

#### EEG Mode (8-Channel, 250 Hz):
```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "patient-uuid",
  "timestamp": "2025-10-15T10:30:00.000Z",
  "mode": "eeg",
  "sampleRate": 250,
  "duration": 1,

  "aggregates": {
    "alphaPower": 45.2,
    "betaPower": 22.1,
    "thetaPower": 18.5,
    "deltaPower": 14.2,
    "dominantFrequency": 10.2
  },

  "channels": {
    "Fp1": [45, 47, 46, ...],  // 250 samples
    "Fp2": [43, 44, 46, ...],  // 250 samples
    "F3": [48, 50, 49, ...],   // 250 samples
    "F4": [46, 47, 48, ...],   // 250 samples
    "C3": [42, 43, 44, ...],   // 250 samples
    "C4": [41, 42, 43, ...],   // 250 samples
    "O1": [38, 39, 40, ...],   // 250 samples
    "O2": [37, 38, 39, ...]    // 250 samples
  },

  "quality": {
    "overall": 0.92,
    "impedance": {
      "Fp1": 4.2,  // kΩ
      "Fp2": 3.8,
      "F3": 4.5,
      "F4": 4.1,
      "C3": 3.9,
      "C4": 4.0,
      "O1": 4.3,
      "O2": 4.2
    }
  },

  "batteryLevel": 85
}
```

**Payload Size**: ~16 KB/sec (8 channels × 250 Hz × 2 bytes + JSON overhead)

---

## Bandwidth Optimization Strategies

### Issue: 16-20 KB/sec continuous streaming is heavy for MQTT

### Strategy 1: Compression
```cpp
// Use zlib/gzip compression
compressedData = compress(channelData);
// Reduces payload by ~70% = 5-6 KB/sec
```

### Strategy 2: Differential Encoding
```cpp
// Send first sample + deltas
channels["leadI"][0] = 120;  // First value
channels["leadI"][1] = 2;    // Delta (+2)
channels["leadI"][2] = 3;    // Delta (+3)
// Reduces from 16-bit to 8-bit values = 50% savings
```

### Strategy 3: Tiered Transmission
```cpp
// Every 1 second: Aggregates only (< 1 KB)
sendAggregates();

// Every 10 seconds: Full waveform (16 KB)
sendFullWaveform();

// On-demand: High-resolution recording
if (arrhythmiaDetected || seizureDetected) {
  sendHighResWaveform();  // 500 Hz for 30 seconds
}
```

### Recommended: Hybrid Approach
```json
// Real-time (every 1 sec): Dashboard vitals
{
  "aggregates": {
    "heartRate": 75,
    "temperature": 98.6,
    "oxygenSat": 98
  },
  "quality": 0.95
}
// Payload: ~200 bytes

// Periodic (every 10 sec): Waveform snapshot
{
  "mode": "ecg",
  "channels": { ... },  // 10 seconds of data
  "derived": { ... }
}
// Payload: ~160 KB (compressed to ~50 KB)

// Event-triggered: High-res capture
{
  "event": "arrhythmia_detected",
  "highResWaveform": { ... },  // 30 seconds @ 500 Hz
  "analysis": { ... }
}
// Payload: ~2.4 MB (compressed to ~800 KB)
```

---

## Frontend TypeScript Types (8-Channel)

### Updated Vitals Interface:
```typescript
vitals: {
  // Basic vitals
  heartRate: number;
  skinTemperature: number;
  oxygenSaturation: number;
  respiratoryRate: number;
  systolicPressure: number;  // Can derive from ECG
  diastolicPressure: number;

  // Mode tracking
  isEcgMode: boolean;

  // ECG 12-Lead (when isEcgMode = true)
  ecg?: {
    leadI: number;
    leadII: number;
    leadIII: number;
    aVR: number;
    aVL: number;
    aVF: number;
    v1: number;
    v2: number;
    v3: number;
    v4: number;
    v5: number;
    v6: number;
    heartRate: number;
    rrInterval: number;
    qrsDuration: number;
    qtInterval: number;
  };

  // EEG 8-Channel (when isEcgMode = false)
  eeg?: {
    Fp1: number;
    Fp2: number;
    F3: number;
    F4: number;
    C3: number;
    C4: number;
    O1: number;
    O2: number;
    alphaPower: number;
    betaPower: number;
    thetaPower: number;
    deltaPower: number;
  };

  // Quality metrics
  lastDataReceived: string;
  dataQualityScore: number;
}
```

### Waveform Interfaces:
```typescript
export interface ecg12LeadWaveform {
  timestamp: string;
  duration: number;
  sampleRate: number;
  mode: 'ecg';

  limb: {
    leadI: number[];
    leadII: number[];
    leadIII: number[];
  };

  augmented: {
    aVR: number[];
    aVL: number[];
    aVF: number[];
  };

  precordial: {
    v1: number[];
    v2: number[];
    v3: number[];
    v4: number[];
    v5: number[];
    v6: number[];
  };

  analysis?: {
    heartRate: number;
    rrIntervals: number[];
    qrsDuration: number;
    qtInterval: number;
    stSegment: 'normal' | 'elevated' | 'depressed';
    arrhythmia?: {
      detected: boolean;
      type: string;
      confidence: number;
    };
  };

  quality: number;
}

export interface eeg8ChannelWaveform {
  timestamp: string;
  duration: number;
  sampleRate: number;
  mode: 'eeg';

  frontal: {
    Fp1: number[];
    Fp2: number[];
    F3: number[];
    F4: number[];
  };

  central: {
    C3: number[];
    C4: number[];
  };

  occipital: {
    O1: number[];
    O2: number[];
  };

  analysis?: {
    bandPowers: {
      delta: number;   // 0.5-4 Hz
      theta: number;   // 4-8 Hz
      alpha: number;   // 8-13 Hz
      beta: number;    // 13-30 Hz
      gamma: number;   // 30-100 Hz
    };
    asymmetry: {
      frontal: number;   // (F4-F3) / (F4+F3)
      occipital: number; // (O2-O1) / (O2+O1)
    };
    seizure?: {
      detected: boolean;
      location: string[];
      confidence: number;
    };
  };

  quality: number;
  impedance: {
    Fp1: number;
    Fp2: number;
    F3: number;
    F4: number;
    C3: number;
    C4: number;
    O1: number;
    O2: number;
  };
}
```

---

## TimescaleDB Schema (8-Channel)

### Waveform Snapshots Table:
```sql
CREATE TABLE IF NOT EXISTS public.neural_waveforms (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50),
    mode VARCHAR(10) NOT NULL,  -- 'ecg' or 'eeg'
    "sampleRate" INTEGER NOT NULL,
    duration INTEGER NOT NULL,

    -- ECG channels (NULL if EEG mode)
    "leadI" JSONB,
    "leadII" JSONB,
    "leadIII" JSONB,
    "aVR" JSONB,
    "aVL" JSONB,
    "aVF" JSONB,
    "v1" JSONB,
    "v2" JSONB,
    "v3" JSONB,
    "v4" JSONB,
    "v5" JSONB,
    "v6" JSONB,

    -- EEG channels (NULL if ECG mode)
    "Fp1" JSONB,
    "Fp2" JSONB,
    "F3" JSONB,
    "F4" JSONB,
    "C3" JSONB,
    "C4" JSONB,
    "O1" JSONB,
    "O2" JSONB,

    -- Analysis results
    analysis JSONB,

    -- Quality metrics
    quality DECIMAL(3,2),
    "qualityMetrics" JSONB,

    metadata JSONB
);

-- Convert to hypertable
SELECT create_hypertable('neural_waveforms', 'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX idx_neural_waveforms_patient_mode_time
    ON neural_waveforms ("patientId", mode, time DESC);
```

---

## Implementation Priority

### Phase 1: Basic ECG (3-Lead)
Start with simplified 3-lead ECG to get data flowing:
- Channel 1: Lead I
- Channel 2: Lead II
- Derived: Lead III

### Phase 2: Full 12-Lead ECG
Expand to full 12-lead diagnostic capability:
- All 8 physical channels
- 3 augmented leads (derived)
- 1 additional derived lead

### Phase 3: EEG Mode
Add brain monitoring:
- 8-channel EEG configuration
- Mode switching (ECG ↔ EEG)
- Seizure detection

### Phase 4: Advanced Features
- Real-time arrhythmia detection
- EEG band power analysis
- Automated interpretation
- Event-triggered high-res recording

---

## Next Steps

1. **Confirm electrode configuration**: Which leads are you prioritizing first?
2. **Waveform transmission**: Every 1 sec? 5 sec? 10 sec?
3. **Storage duration**: How long to keep waveforms? (HIPAA = 7 years)
4. **Frontend display**: Need full 12-lead ECG viewer? EEG montage viewer?
5. **Analysis features**: Real-time arrhythmia detection? Seizure alerts?

**Ready to implement once you confirm priorities!**
