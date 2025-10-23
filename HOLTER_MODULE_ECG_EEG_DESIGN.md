# Holter Module ECG/EEG Design - Hardware & Data Structure

## Hardware Configuration

### Holter ECG Module (Typical Specs)
**Common Holter modules for ESP32/Arduino**:
- AD8232 (single-lead ECG)
- MAX30003 (single-lead ECG with R-R detection)
- **ADS1292R** (2-channel, 24-bit ADC) ⭐ Most likely
- **ADS1298** (8-channel, 24-bit ADC) ⭐ Professional grade

### Your Setup: "planning to use same leads for eeg. just swap the connectors"

**Interpretation**:
- Physical electrodes are swappable between ECG (chest) and EEG (scalp)
- Same ADC hardware reads both signals
- Software determines interpretation (ECG mode vs EEG mode)
- `isEcgMode: boolean` flag switches between modes ✅

---

## Actual Hardware: ADS1298 (8-Channel Professional Grade)

### ADS1298 Specifications:
- **Channels**: 8 differential inputs (using 7-8 channels)
- **Resolution**: 24-bit ADC
- **Sample Rate**: Up to 32 kSPS (typically 250-500 Hz for ECG/EEG)
- **Use Cases**:
  - ECG: Full 12-lead ECG capability (8 direct + derived leads)
  - EEG: 8-channel clinical EEG (10-20 system)

### ECG Configuration (7-8 Channels):
```
Channel 1: Lead I   (LA - RA)
Channel 2: Lead II  (LL - RA)
Channel 3: Lead III (LL - LA)
Channel 4: V1 (precordial)
Channel 5: V2 (precordial)
Channel 6: V3 (precordial)
Channel 7: V4 (precordial)
Channel 8: V5 (precordial) or Reference

Derived:
- aVR = RA - (LA + LL)/2
- aVL = LA - (RA + LL)/2
- aVF = LL - (RA + LA)/2
- V6 can be derived or use 8th channel
```

**Result**: Full 12-lead ECG ✅

### EEG Configuration (8-Channel):
```
Channel 1: Fp1 (frontal pole left)
Channel 2: Fp2 (frontal pole right)
Channel 3: F3  (frontal left)
Channel 4: F4  (frontal right)
Channel 5: C3  (central left)
Channel 6: C4  (central right)
Channel 7: O1  (occipital left)
Channel 8: O2  (occipital right)
Reference: Cz or linked mastoids
```

**Result**: 8-channel clinical EEG ✅

---

## Data Structure Design

### Real-Time Streaming Format (High-Frequency)

#### ECG Mode - 8 Channels @ 250 Hz (Full 12-Lead):
```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "patient-uuid",
  "timestamp": "2025-10-15T10:30:00.000Z",
  "mode": "ecg",
  "sampleRate": 250,
  "channels": {
    "leadI": [120, 122, 125, ...],    // 250 samples
    "leadII": [150, 152, 155, ...],   // 250 samples
    "leadIII": [30, 32, 35, ...],     // 250 samples
    "v1": [110, 112, 115, ...],       // 250 samples
    "v2": [115, 117, 120, ...],       // 250 samples
    "v3": [120, 122, 125, ...],       // 250 samples
    "v4": [125, 127, 130, ...],       // 250 samples
    "v5": [130, 132, 135, ...]        // 250 samples
  },
  "derived": {
    "aVR": [-135, -137, -140, ...],   // Calculated
    "aVL": [60, 62, 65, ...],         // Calculated
    "aVF": [90, 92, 95, ...],         // Calculated
    "v6": [132, 134, 137, ...]        // Calculated or 8th channel
  },
  "aggregates": {
    "heartRate": 75,
    "rrInterval": 800
  },
  "batteryLevel": 85,
  "quality": 0.95
}
```

**Payload Size**: ~16 KB/sec (8 channels × 250 Hz × 2 bytes + JSON overhead)

#### EEG Mode - 8 Channels @ 250 Hz:
```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "patient-uuid",
  "timestamp": "2025-10-15T10:30:00.000Z",
  "mode": "eeg",
  "sampleRate": 250,
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
  "aggregates": {
    "alphaPower": 45.2,
    "betaPower": 22.1
  },
  "batteryLevel": 85,
  "quality": 0.92
}
```

**Payload Size**: ~16 KB/sec (8 channels × 250 Hz × 2 bytes + JSON overhead)

---

## Optimized Data Structure (Bandwidth Reduction)

### Option A: Aggregate + Waveform Snippet
**Send every 5 seconds**:
```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "patient-uuid",
  "timestamp": "2025-10-15T10:30:00.000Z",
  "mode": "ecg",
  "sampleRate": 250,

  // Aggregate values for dashboard (every 5 sec)
  "aggregates": {
    "heartRate": 75,  // Calculated from R-R intervals
    "avgLeadI": 120,
    "avgLeadII": 150
  },

  // 10-second waveform snippet (for charts)
  "waveform": {
    "duration": 10,  // seconds
    "leadI": [120, 122, ...],  // 2500 samples (10 sec × 250 Hz)
    "leadII": [150, 152, ...]  // 2500 samples
  },

  "batteryLevel": 85,
  "quality": 0.95
}
```

### Option B: Real-Time + Compressed Storage
**Real-time**: Send aggregates every 1 second
**Batch upload**: Send full waveform every 60 seconds for storage

---

## Database Schema Redesign

### PostgreSQL Patients Table - Latest Vitals (Dashboard)

```typescript
vitals: {
  // Basic vitals
  heartRate: number;  // Derived from ECG
  skinTemperature: number;
  oxygenSaturation: number;

  // ECG/EEG mode tracking
  isEcgMode: boolean;  // true = ECG mode, false = EEG mode

  // ECG aggregates (when isEcgMode = true)
  ecgLeadI: number;  // Average Lead I value (mV × 100)
  ecgLeadII: number;  // Average Lead II value (mV × 100)
  ecgLeadIII: number;  // Derived: Lead II - Lead I

  // EEG aggregates (when isEcgMode = false)
  eegF3: number;  // Average F3 channel (μV)
  eegF4: number;  // Average F4 channel (μV)

  // Metadata
  lastDataReceived: string;
  dataQualityScore: number;  // 0-1 scale
}
```

### TimescaleDB vitals_timeseries - Time-Series Data

#### Option A: Separate Row Per Channel
```sql
CREATE TABLE IF NOT EXISTS public.vitals_timeseries (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50),
    mode VARCHAR(10) NOT NULL,  -- 'ecg' or 'eeg'
    channel VARCHAR(20) NOT NULL,  -- 'Lead_I', 'Lead_II', 'F3', 'F4'
    value DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20),
    quality INTEGER DEFAULT 95,
    metadata JSONB
);

-- Example data:
time                    | patientId | mode | channel  | value | unit
------------------------|-----------|------|----------|-------|------
2025-10-15 10:30:00.000 | uuid      | ecg  | Lead_I   | 120   | mV
2025-10-15 10:30:00.000 | uuid      | ecg  | Lead_II  | 150   | mV
2025-10-15 10:30:00.004 | uuid      | ecg  | Lead_I   | 122   | mV
2025-10-15 10:30:00.004 | uuid      | ecg  | Lead_II  | 152   | mV
```

**Pros**: Simple queries, easy to filter by channel
**Cons**: High row count (2 channels × 250 Hz = 500 rows/sec)

#### Option B: Waveform Snapshots (JSONB)
```sql
CREATE TABLE IF NOT EXISTS public.ecg_waveforms (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50),
    mode VARCHAR(10) NOT NULL,  -- 'ecg' or 'eeg'
    "sampleRate" INTEGER NOT NULL,
    duration INTEGER NOT NULL,  -- seconds
    channels JSONB NOT NULL,  -- {"Lead_I": [120,122,...], "Lead_II": [150,152,...]}
    quality DECIMAL(3,2),
    metadata JSONB
);

-- Example data:
time                    | mode | sampleRate | duration | channels (JSONB)
------------------------|------|------------|----------|------------------
2025-10-15 10:30:00.000 | ecg  | 250        | 10       | {"Lead_I": [120,122,...], "Lead_II": [150,152,...]}
2025-10-15 10:30:10.000 | ecg  | 250        | 10       | {"Lead_I": [121,123,...], "Lead_II": [151,153,...]}
```

**Pros**: Fewer rows, full waveform context
**Cons**: JSONB queries harder, larger row size

---

## Frontend TypeScript Types (Updated)

### Updated Vitals Interface:
```typescript
vitals: {
  // Cardiovascular
  heartRate: number;
  systolicPressure: number;
  diastolicPressure: number;

  // Respiratory
  respiratoryRate: number;
  oxygenSaturation: number;

  // Temperature
  skinTemperature: number;

  // ECG/EEG Mode
  isEcgMode: boolean;  // true = ECG, false = EEG

  // ECG Channels (when isEcgMode = true)
  ecgLeadI?: number;  // mV × 100
  ecgLeadII?: number;  // mV × 100
  ecgLeadIII?: number;  // Derived: Lead II - Lead I

  // EEG Channels (when isEcgMode = false)
  eegF3?: number;  // μV
  eegF4?: number;  // μV

  // Advanced Monitoring
  bioelectricalImpedance: number;
  tremorIntensity: number;
  fallRisk: 'low' | 'medium' | 'high';

  // Metadata
  lastDataReceived: string;
  dataQualityScore: number;
}
```

### Waveform Interfaces (Updated):
```typescript
export interface ecgWaveform {
  timestamp: string;
  duration: number;  // seconds
  sampleRate: number;  // Hz
  mode: 'ecg';
  channels: {
    leadI: number[];  // Array of samples
    leadII: number[];  // Array of samples
    leadIII?: number[];  // Derived (optional)
  };
  interpretation?: string;
  arrhythmiaDetected?: boolean;
  arrhythmiaType?: string;
  quality: number;  // 0-1 scale
}

export interface eegWaveform {
  timestamp: string;
  duration: number;  // seconds
  sampleRate: number;  // Hz
  mode: 'eeg';
  channels: {
    F3: number[];  // Frontal left
    F4: number[];  // Frontal right
  };
  interpretation?: string;
  seizureActivity?: boolean;
  abnormalPatterns?: string[];
  quality: number;  // 0-1 scale
}

export type neuralWaveform = ecgWaveform | eegWaveform;
```

---

## ESP32 Firmware Changes Needed

### Current (Broken):
```cpp
// Flat structure, no channels
doc["heartRate"] = heartRate;
doc["temperature"] = temperature;
doc["oxygenSat"] = oxygenSat;
```

### Proposed (Multi-Channel):
```cpp
// Mode tracking
bool isEcgMode = true;  // true = ECG, false = EEG

// Sample buffers (2 channels × 250 samples for 1 second)
int16_t channel1Buffer[250];
int16_t channel2Buffer[250];

void sendWaveformData() {
  JsonDocument doc;
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["timestamp"] = getISOTimestamp();  // ISO 8601
  doc["mode"] = isEcgMode ? "ecg" : "eeg";
  doc["sampleRate"] = 250;
  doc["duration"] = 1;  // 1 second of data

  // Aggregate vitals for dashboard
  JsonObject aggregates = doc.createNestedObject("aggregates");
  aggregates["heartRate"] = calculateHeartRate();  // From R-R intervals
  aggregates["temperature"] = temperature;
  aggregates["oxygenSat"] = oxygenSat;

  // Channel data
  JsonObject channels = doc.createNestedObject("channels");

  if (isEcgMode) {
    // ECG mode
    JsonArray leadI = channels.createNestedArray("leadI");
    JsonArray leadII = channels.createNestedArray("leadII");

    for (int i = 0; i < 250; i++) {
      leadI.add(channel1Buffer[i]);
      leadII.add(channel2Buffer[i]);
    }
  } else {
    // EEG mode
    JsonArray F3 = channels.createNestedArray("F3");
    JsonArray F4 = channels.createNestedArray("F4");

    for (int i = 0; i < 250; i++) {
      F3.add(channel1Buffer[i]);
      F4.add(channel2Buffer[i]);
    }
  }

  doc["batteryLevel"] = batteryLevel;
  doc["quality"] = calculateSignalQuality();

  // Publish via MQTT
  mqttClient.publish(topic, doc.as<String>().c_str());
}
```

---

## Backend MQTT Handler Changes Needed

### Current (Broken):
```python
vitalsData = payload.get('vitals', {})  # ❌ Expects nested vitals
```

### Proposed (Multi-Channel):
```python
async def _handleVitalsMessage(self, payload: Dict[str, Any]):
    """Handle multi-channel ECG/EEG vitals from ESP32"""
    deviceId = payload.get('deviceId')
    patientId = payload.get('patientId')
    timestamp = payload.get('timestamp')  # ISO 8601
    mode = payload.get('mode')  # 'ecg' or 'eeg'
    sampleRate = payload.get('sampleRate', 250)

    # Extract aggregate vitals for real-time display
    aggregates = payload.get('aggregates', {})
    heartRate = aggregates.get('heartRate')
    temperature = aggregates.get('temperature')
    oxygenSat = aggregates.get('oxygenSat')

    # Extract waveform channels
    channels = payload.get('channels', {})

    # Update patient latest vitals (PostgreSQL)
    if mode == 'ecg':
        await self._updatePatientVitals(patientId, {
            'heartRate': heartRate,
            'skinTemperature': temperature,
            'oxygenSaturation': oxygenSat,
            'isEcgMode': True,
            'ecgLeadI': self._calculateAverage(channels.get('leadI', [])),
            'ecgLeadII': self._calculateAverage(channels.get('leadII', [])),
            'lastDataReceived': timestamp
        })
    elif mode == 'eeg':
        await self._updatePatientVitals(patientId, {
            'isEcgMode': False,
            'eegF3': self._calculateAverage(channels.get('F3', [])),
            'eegF4': self._calculateAverage(channels.get('F4', [])),
            'lastDataReceived': timestamp
        })

    # Store waveform snapshot in TimescaleDB
    await self._storeWaveformSnapshot(
        patientId=patientId,
        deviceId=deviceId,
        timestamp=timestamp,
        mode=mode,
        sampleRate=sampleRate,
        channels=channels,
        quality=payload.get('quality', 0.95)
    )
```

---

## Summary & Next Steps

### Hardware Confirmation:
- ✅ Holter module = 2-channel ECG/EEG capability
- ✅ Swappable connectors for ECG (chest) vs EEG (scalp)
- ✅ `isEcgMode` boolean switches between interpretations

### Data Model:
- **2 ECG Leads**: Lead I, Lead II (+ derived Lead III)
- **2 EEG Channels**: F3, F4 (frontal hemispheres)
- **Sample Rate**: 250 Hz typical for both
- **Real-time aggregates** + **periodic waveform snapshots**

### Implementation Plan:
1. ✅ Update frontend TypeScript types (add channel-specific fields)
2. ✅ Update TimescaleDB schema (add waveform table)
3. ✅ Update ESP32 firmware (send multi-channel data)
4. ✅ Update backend MQTT handler (process multi-channel data)
5. ✅ Add frontend waveform viewer component (ECG/EEG charts)

### Questions:
1. **Which Holter module exactly?** ADS1292R (2-ch) or ADS1298 (8-ch)?
2. **Waveform transmission frequency?** Every 1 sec? 5 sec? 10 sec?
3. **Storage duration?** How long to keep waveform data? (7 years per HIPAA?)
4. **Frontend display?** Real-time waveform or just aggregates on dashboard?

**Ready to implement once you confirm the exact hardware model and transmission frequency!**
