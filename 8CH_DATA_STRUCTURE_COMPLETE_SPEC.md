# 8-Channel ECG/EEG Complete Data Structure Specification

**Version**: 1.0
**Date**: 2025-10-15
**Hardware**: ADS1298 (8-channel, 24-bit ADC)
**Purpose**: Future-proof data structure design for Phase 1-4 implementation

---

## Table of Contents
1. [ESP32 MQTT Message Format](#1-esp32-mqtt-message-format)
2. [Backend Python Data Models](#2-backend-python-data-models)
3. [TimescaleDB Schema](#3-timescaledb-schema)
4. [PostgreSQL Patient Vitals](#4-postgresql-patient-vitals)
5. [Frontend TypeScript Types](#5-frontend-typescript-types)
6. [Data Flow Summary](#6-data-flow-summary)

---

## 1. ESP32 MQTT Message Format

### 1.1 Topic Structure
```
hospital/devices/{deviceId}/vitals      # Real-time vitals (every 1 sec)
hospital/devices/{deviceId}/waveform    # Waveform snapshots (every 10 sec)
hospital/devices/{deviceId}/event       # Event-triggered (arrhythmia, seizure)
hospital/devices/{deviceId}/status      # Device status (battery, connection)
```

### 1.2 Real-Time Vitals Message (Every 1 Second)
**Topic**: `hospital/devices/{deviceId}/vitals`
**Payload Size**: ~500 bytes (compressed JSON)

```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd",
  "timestamp": "2025-10-15T10:30:00.123Z",
  "sequence": 12345,

  "mode": "ecg",
  "activeChannels": 8,
  "sampleRate": 250,

  "vitals": {
    "heartRate": 75,
    "respiratoryRate": 16,
    "skinTemperature": 98.6,
    "oxygenSaturation": 98,
    "batteryLevel": 85,
    "signalQuality": 0.95
  },

  "ecg": {
    "rrInterval": 800,
    "qrsDuration": 90,
    "qtInterval": 380,
    "axis": 60,
    "rhythm": "sinus",
    "stSegment": "normal"
  },

  "quality": {
    "overall": 0.95,
    "leadOff": [],
    "noise": {
      "50Hz": 0.02,
      "muscle": 0.01,
      "baseline": 0.01
    },
    "impedance": {
      "RA": 4.2,
      "LA": 3.8,
      "RL": 2.1,
      "LL": 4.0,
      "V1": 3.5,
      "V2": 3.7,
      "V3": 3.9,
      "V4": 4.1
    }
  }
}
```

### 1.3 Waveform Snapshot Message (Every 10 Seconds)
**Topic**: `hospital/devices/{deviceId}/waveform`
**Payload Size**: ~50 KB compressed (10 sec × 8 channels × 250 Hz)

```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd",
  "timestamp": "2025-10-15T10:30:00.000Z",
  "sequence": 123,

  "mode": "ecg",
  "sampleRate": 250,
  "duration": 10,
  "compression": "delta",

  "limb": {
    "leadI": {
      "baseline": 120,
      "deltas": [0, 2, 3, 5, 15, 30, 45, 55, 60, 55, ...]
    },
    "leadII": {
      "baseline": 150,
      "deltas": [0, 2, 5, 7, 20, 40, 60, 70, 75, 70, ...]
    },
    "leadIII": {
      "baseline": 30,
      "deltas": [0, 0, 2, 2, 5, 10, 15, 15, 15, 15, ...]
    }
  },

  "precordial": {
    "v1": {
      "baseline": 110,
      "deltas": [...]
    },
    "v2": {
      "baseline": 115,
      "deltas": [...]
    },
    "v3": {
      "baseline": 120,
      "deltas": [...]
    },
    "v4": {
      "baseline": 125,
      "deltas": [...]
    },
    "v5": {
      "baseline": 130,
      "deltas": [...]
    }
  },

  "derived": {
    "aVR": {
      "baseline": -135,
      "deltas": [...]
    },
    "aVL": {
      "baseline": 60,
      "deltas": [...]
    },
    "aVF": {
      "baseline": 90,
      "deltas": [...]
    },
    "v6": {
      "baseline": 132,
      "deltas": [...]
    }
  },

  "events": [
    {
      "timestamp": "2025-10-15T10:30:03.456Z",
      "type": "PVC",
      "confidence": 0.89,
      "location": "V3"
    }
  ]
}
```

**Delta Encoding Explanation**:
```
Original: [120, 122, 125, 130, 145, 160, ...]
Encoded:  baseline=120, deltas=[0, 2, 3, 5, 15, 15, ...]
Savings:  16-bit values → 8-bit deltas = 50% bandwidth reduction
```

### 1.4 EEG Waveform Message
**Topic**: `hospital/devices/{deviceId}/waveform`
**Mode**: `"mode": "eeg"`

```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd",
  "timestamp": "2025-10-15T10:30:00.000Z",

  "mode": "eeg",
  "sampleRate": 250,
  "duration": 10,
  "compression": "delta",

  "frontal": {
    "Fp1": {
      "baseline": 45,
      "deltas": [...]
    },
    "Fp2": {
      "baseline": 43,
      "deltas": [...]
    },
    "F3": {
      "baseline": 48,
      "deltas": [...]
    },
    "F4": {
      "baseline": 46,
      "deltas": [...]
    }
  },

  "central": {
    "C3": {
      "baseline": 42,
      "deltas": [...]
    },
    "C4": {
      "baseline": 41,
      "deltas": [...]
    }
  },

  "occipital": {
    "O1": {
      "baseline": 38,
      "deltas": [...]
    },
    "O2": {
      "baseline": 37,
      "deltas": [...]
    }
  },

  "analysis": {
    "bandPowers": {
      "delta": 14.2,
      "theta": 18.5,
      "alpha": 45.2,
      "beta": 22.1,
      "gamma": 8.3
    },
    "asymmetry": {
      "frontal": 0.05,
      "central": 0.02,
      "occipital": 0.03
    },
    "dominantFrequency": 10.2,
    "seizureActivity": false
  },

  "quality": {
    "overall": 0.92,
    "impedance": {
      "Fp1": 4.2,
      "Fp2": 3.8,
      "F3": 4.5,
      "F4": 4.1,
      "C3": 3.9,
      "C4": 4.0,
      "O1": 4.3,
      "O2": 4.2
    }
  }
}
```

### 1.5 Event-Triggered Message
**Topic**: `hospital/devices/{deviceId}/event`
**Trigger**: Arrhythmia, seizure, or critical vital

```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd",
  "timestamp": "2025-10-15T10:30:05.678Z",

  "eventType": "arrhythmia",
  "severity": "critical",
  "confidence": 0.94,

  "mode": "ecg",
  "sampleRate": 500,
  "duration": 30,

  "context": {
    "heartRate": 185,
    "rrInterval": 320,
    "irregularity": 0.78,
    "diagnosis": "ventricular_tachycardia"
  },

  "waveform": {
    "leadII": [150, 152, 155, ...],
    "v1": [110, 112, ...]
  },

  "actions": {
    "alertSent": true,
    "staffNotified": ["DOC0001", "NUR0001"],
    "priority": "immediate"
  }
}
```

---

## 2. Backend Python Data Models

### 2.1 Pydantic Models (app/models/vitals.py)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal
from datetime import datetime

# =====================================
# BASE VITALS MODEL
# =====================================
class VitalSigns(BaseModel):
    """Real-time vital signs - updated every 1 second"""
    heartRate: Optional[int] = Field(None, ge=20, le=300, description="BPM")
    respiratoryRate: Optional[int] = Field(None, ge=4, le=60, description="/min")
    skinTemperature: Optional[float] = Field(None, ge=90.0, le=110.0, description="°F")
    oxygenSaturation: Optional[int] = Field(None, ge=70, le=100, description="%")
    batteryLevel: int = Field(..., ge=0, le=100, description="%")
    signalQuality: float = Field(..., ge=0.0, le=1.0, description="0-1 scale")

class ECGAnalysis(BaseModel):
    """Derived ECG metrics"""
    rrInterval: Optional[int] = Field(None, ge=200, le=2000, description="ms")
    qrsDuration: Optional[int] = Field(None, ge=40, le=200, description="ms")
    qtInterval: Optional[int] = Field(None, ge=200, le=600, description="ms")
    axis: Optional[int] = Field(None, ge=-180, le=180, description="degrees")
    rhythm: Optional[str] = Field(None, description="sinus, afib, aflutter, etc")
    stSegment: Optional[Literal["normal", "elevated", "depressed"]] = None

class EEGAnalysis(BaseModel):
    """EEG band power analysis"""
    bandPowers: Dict[str, float] = Field(..., description="delta, theta, alpha, beta, gamma")
    asymmetry: Dict[str, float] = Field(..., description="frontal, central, occipital")
    dominantFrequency: Optional[float] = Field(None, ge=0.5, le=100.0, description="Hz")
    seizureActivity: bool = False

class SignalQuality(BaseModel):
    """Signal quality metrics"""
    overall: float = Field(..., ge=0.0, le=1.0)
    leadOff: List[str] = Field(default_factory=list)
    noise: Optional[Dict[str, float]] = None
    impedance: Optional[Dict[str, float]] = None

# =====================================
# REAL-TIME VITALS MESSAGE
# =====================================
class VitalsMessage(BaseModel):
    """MQTT vitals message (every 1 sec)"""
    deviceId: str
    patientId: str
    timestamp: datetime
    sequence: int

    mode: Literal["ecg", "eeg"]
    activeChannels: int = Field(..., ge=1, le=8)
    sampleRate: int = Field(..., description="Hz")

    vitals: VitalSigns
    ecg: Optional[ECGAnalysis] = None
    eeg: Optional[EEGAnalysis] = None
    quality: SignalQuality

# =====================================
# WAVEFORM DATA MODELS
# =====================================
class ChannelData(BaseModel):
    """Compressed channel data using delta encoding"""
    baseline: int = Field(..., description="First sample value")
    deltas: List[int] = Field(..., description="Delta-encoded samples")

class ECGWaveform(BaseModel):
    """12-lead ECG waveform data"""
    limb: Dict[str, ChannelData] = Field(..., description="leadI, leadII, leadIII")
    precordial: Dict[str, ChannelData] = Field(..., description="v1-v5")
    derived: Dict[str, ChannelData] = Field(..., description="aVR, aVL, aVF, v6")
    events: List[Dict] = Field(default_factory=list, description="Detected events")

class EEGWaveform(BaseModel):
    """8-channel EEG waveform data"""
    frontal: Dict[str, ChannelData] = Field(..., description="Fp1, Fp2, F3, F4")
    central: Dict[str, ChannelData] = Field(..., description="C3, C4")
    occipital: Dict[str, ChannelData] = Field(..., description="O1, O2")
    analysis: EEGAnalysis

class WaveformMessage(BaseModel):
    """MQTT waveform message (every 10 sec)"""
    deviceId: str
    patientId: str
    timestamp: datetime
    sequence: int

    mode: Literal["ecg", "eeg"]
    sampleRate: int
    duration: int = Field(..., description="seconds")
    compression: Literal["delta", "none"] = "delta"

    ecgWaveform: Optional[ECGWaveform] = None
    eegWaveform: Optional[EEGWaveform] = None
    quality: SignalQuality

# =====================================
# EVENT MESSAGE
# =====================================
class EventMessage(BaseModel):
    """Event-triggered high-priority message"""
    deviceId: str
    patientId: str
    timestamp: datetime

    eventType: Literal["arrhythmia", "seizure", "critical_vital"]
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float = Field(..., ge=0.0, le=1.0)

    mode: Literal["ecg", "eeg"]
    sampleRate: int
    duration: int

    context: Dict
    waveform: Dict[str, List[int]]
    actions: Dict
```

### 2.2 Database Models (app/db/models.py)

```python
# PostgreSQL patients table vitals column
vitals_column = {
    # Basic vitals
    "heartRate": int,
    "respiratoryRate": int,
    "skinTemperature": float,
    "oxygenSaturation": int,
    "systolicPressure": int,
    "diastolicPressure": int,

    # ECG/EEG mode
    "isEcgMode": bool,

    # ECG aggregates
    "ecgLeadI": int,
    "ecgLeadII": int,
    "ecgLeadIII": int,
    "ecgRRInterval": int,
    "ecgQRSDuration": int,
    "ecgQTInterval": int,
    "ecgAxis": int,
    "ecgRhythm": str,
    "ecgSTSegment": str,

    # EEG aggregates
    "eegFp1": int,
    "eegFp2": int,
    "eegF3": int,
    "eegF4": int,
    "eegC3": int,
    "eegC4": int,
    "eegO1": int,
    "eegO2": int,
    "eegAlphaPower": float,
    "eegBetaPower": float,
    "eegThetaPower": float,
    "eegDeltaPower": float,

    # Quality
    "dataQualityScore": float,
    "lastDataReceived": str
}
```

---

## 3. TimescaleDB Schema

### 3.1 Waveform Snapshots Table
```sql
CREATE TABLE IF NOT EXISTS public.waveform_snapshots (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50) NOT NULL,
    mode VARCHAR(10) NOT NULL,  -- 'ecg' or 'eeg'
    "sampleRate" INTEGER NOT NULL,
    duration INTEGER NOT NULL,

    -- ECG channels (12-lead)
    "ecgLimbLeads" JSONB,        -- {leadI: {baseline, deltas}, leadII, leadIII}
    "ecgPrecordialLeads" JSONB,  -- {v1: {baseline, deltas}, v2, v3, v4, v5}
    "ecgDerivedLeads" JSONB,     -- {aVR, aVL, aVF, v6}
    "ecgEvents" JSONB,           -- [{timestamp, type, confidence, location}]

    -- EEG channels (8-channel)
    "eegFrontalChannels" JSONB,  -- {Fp1, Fp2, F3, F4}
    "eegCentralChannels" JSONB,  -- {C3, C4}
    "eegOccipitalChannels" JSONB, -- {O1, O2}
    "eegAnalysis" JSONB,         -- {bandPowers, asymmetry, dominantFrequency}

    -- Quality metrics
    quality JSONB,               -- {overall, leadOff, noise, impedance}

    -- Metadata
    sequence INTEGER,
    compression VARCHAR(20),
    metadata JSONB
);

-- Convert to hypertable
SELECT create_hypertable('waveform_snapshots', 'time',
    chunk_time_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX idx_waveform_snapshots_patient_mode_time
    ON waveform_snapshots ("patientId", mode, time DESC);
CREATE INDEX idx_waveform_snapshots_device_time
    ON waveform_snapshots ("deviceId", time DESC);

-- Compression policy (compress after 24 hours)
SELECT add_compression_policy('waveform_snapshots', INTERVAL '24 hours', if_not_exists => true);

-- Retention policy (keep 7 years for HIPAA)
SELECT add_retention_policy('waveform_snapshots', INTERVAL '7 years', if_not_exists => true);
```

### 3.2 Real-Time Vitals Table
```sql
CREATE TABLE IF NOT EXISTS public.vitals_realtime (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50) NOT NULL,
    mode VARCHAR(10) NOT NULL,

    -- Basic vitals
    "heartRate" INTEGER,
    "respiratoryRate" INTEGER,
    "skinTemperature" DECIMAL(4,1),
    "oxygenSaturation" INTEGER,
    "batteryLevel" INTEGER,
    "signalQuality" DECIMAL(3,2),

    -- ECG analysis
    "rrInterval" INTEGER,
    "qrsDuration" INTEGER,
    "qtInterval" INTEGER,
    axis INTEGER,
    rhythm VARCHAR(50),
    "stSegment" VARCHAR(20),

    -- EEG analysis
    "alphaPower" DECIMAL(5,2),
    "betaPower" DECIMAL(5,2),
    "thetaPower" DECIMAL(5,2),
    "deltaPower" DECIMAL(5,2),
    "gammaPower" DECIMAL(5,2),
    "dominantFrequency" DECIMAL(5,2),
    "seizureActivity" BOOLEAN,

    -- Quality
    quality JSONB,

    -- Metadata
    sequence INTEGER,
    metadata JSONB
);

-- Convert to hypertable
SELECT create_hypertable('vitals_realtime', 'time',
    chunk_time_interval => INTERVAL '30 minutes',
    if_not_exists => TRUE
);

-- Continuous aggregate (1-minute averages)
CREATE MATERIALIZED VIEW IF NOT EXISTS vitals_1min
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    "patientId",
    "deviceId",
    mode,
    AVG("heartRate") as avg_heart_rate,
    AVG("respiratoryRate") as avg_respiratory_rate,
    AVG("skinTemperature") as avg_temperature,
    AVG("oxygenSaturation") as avg_oxygen_saturation,
    AVG("signalQuality") as avg_signal_quality,
    COUNT(*) as reading_count
FROM vitals_realtime
GROUP BY bucket, "patientId", "deviceId", mode;
```

### 3.3 Events Table
```sql
CREATE TABLE IF NOT EXISTS public.neural_events (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50) NOT NULL,

    "eventType" VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,

    mode VARCHAR(10) NOT NULL,
    "sampleRate" INTEGER,
    duration INTEGER,

    context JSONB,
    waveform JSONB,
    actions JSONB,

    acknowledged BOOLEAN DEFAULT FALSE,
    "acknowledgedBy" VARCHAR(100),
    "acknowledgedAt" TIMESTAMPTZ,

    resolved BOOLEAN DEFAULT FALSE,
    "resolvedAt" TIMESTAMPTZ,

    metadata JSONB
);

-- Convert to hypertable
SELECT create_hypertable('neural_events', 'time',
    chunk_time_interval => INTERVAL '24 hours',
    if_not_exists => TRUE
);
```

---

## 4. PostgreSQL Patient Vitals

### 4.1 Updated patients Table Column
```sql
ALTER TABLE patients ADD COLUMN IF NOT EXISTS vitals JSONB;

-- Example vitals JSONB structure:
{
  "heartRate": 75,
  "respiratoryRate": 16,
  "skinTemperature": 98.6,
  "oxygenSaturation": 98,
  "systolicPressure": 120,
  "diastolicPressure": 80,

  "isEcgMode": true,

  "ecg": {
    "leadI": 120,
    "leadII": 150,
    "leadIII": 30,
    "rrInterval": 800,
    "qrsDuration": 90,
    "qtInterval": 380,
    "axis": 60,
    "rhythm": "sinus",
    "stSegment": "normal"
  },

  "eeg": null,

  "dataQualityScore": 0.95,
  "lastDataReceived": "2025-10-15T10:30:00.123Z"
}
```

---

## 5. Frontend TypeScript Types

### 5.1 Updated PatientTypes.ts

```typescript
// =====================================
// VITALS INTERFACE (Updated)
// =====================================
export interface vitals {
  // Basic vitals
  heartRate: number;
  respiratoryRate: number;
  skinTemperature: number;
  oxygenSaturation: number;
  systolicPressure: number;
  diastolicPressure: number;

  // Mode tracking
  isEcgMode: boolean;

  // ECG data
  ecg?: {
    leadI: number;
    leadII: number;
    leadIII: number;
    aVR?: number;
    aVL?: number;
    aVF?: number;
    v1?: number;
    v2?: number;
    v3?: number;
    v4?: number;
    v5?: number;
    v6?: number;
    rrInterval: number;
    qrsDuration: number;
    qtInterval: number;
    axis: number;
    rhythm: string;
    stSegment: 'normal' | 'elevated' | 'depressed';
  };

  // EEG data
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
    gammaPower?: number;
    dominantFrequency: number;
    seizureActivity: boolean;
  };

  // Metadata
  dataQualityScore: number;
  lastDataReceived: string;

  // Legacy single-value fields (for backward compatibility)
  ecgReading?: number;
  eegReading?: number;
  bioelectricalImpedance?: number;
  tremorIntensity?: number;
  fallRisk?: 'low' | 'medium' | 'high';
}

// =====================================
// WAVEFORM INTERFACES
// =====================================
export interface channelData {
  baseline: number;
  deltas: number[];
}

export interface ecg12LeadWaveform {
  timestamp: string;
  sampleRate: number;
  duration: number;

  limb: {
    leadI: channelData;
    leadII: channelData;
    leadIII: channelData;
  };

  precordial: {
    v1: channelData;
    v2: channelData;
    v3: channelData;
    v4: channelData;
    v5: channelData;
  };

  derived: {
    aVR: channelData;
    aVL: channelData;
    aVF: channelData;
    v6: channelData;
  };

  events: Array<{
    timestamp: string;
    type: string;
    confidence: number;
    location: string;
  }>;

  quality: {
    overall: number;
    leadOff: string[];
    noise?: {
      [key: string]: number;
    };
    impedance?: {
      [key: string]: number;
    };
  };
}

export interface eeg8ChannelWaveform {
  timestamp: string;
  sampleRate: number;
  duration: number;

  frontal: {
    Fp1: channelData;
    Fp2: channelData;
    F3: channelData;
    F4: channelData;
  };

  central: {
    C3: channelData;
    C4: channelData;
  };

  occipital: {
    O1: channelData;
    O2: channelData;
  };

  analysis: {
    bandPowers: {
      delta: number;
      theta: number;
      alpha: number;
      beta: number;
      gamma: number;
    };
    asymmetry: {
      frontal: number;
      central: number;
      occipital: number;
    };
    dominantFrequency: number;
    seizureActivity: boolean;
  };

  quality: {
    overall: number;
    impedance: {
      [key: string]: number;
    };
  };
}

export type neuralWaveform = ecg12LeadWaveform | eeg8ChannelWaveform;
```

---

## 6. Data Flow Summary

### 6.1 Real-Time Flow (Every 1 Second)
```
ESP32 ADS1298 → MQTT (vitals topic) → Backend MQTT Handler
    ↓
Backend computes aggregates → Update PostgreSQL patients.vitals
    ↓
WebSocket broadcast → Frontend Dashboard
    ↓
Display updated vital signs
```

### 6.2 Waveform Flow (Every 10 Seconds)
```
ESP32 ADS1298 → MQTT (waveform topic) → Backend MQTT Handler
    ↓
Backend decompresses deltas → Store TimescaleDB waveform_snapshots
    ↓
Frontend requests waveform → Backend queries TimescaleDB
    ↓
Display ECG/EEG viewer charts
```

### 6.3 Event Flow (On Detection)
```
ESP32 detects arrhythmia/seizure → MQTT (event topic) → Backend MQTT Handler
    ↓
Backend creates alert → Store PostgreSQL alerts + TimescaleDB neural_events
    ↓
WebSocket broadcast critical alert → Frontend Dashboard
    ↓
Show critical alert notification + trigger alarms
```

---

## 7. Implementation Roadmap

### Phase 1: Single-Lead (1-Lead ECG)
- ESP32 sends: Lead II only
- Backend computes: HR, RR, basic rhythm
- Frontend displays: HR, temp, SpO2, RR
- Other fields: Show as `'--'`

### Phase 2: Three-Lead (3-Lead ECG)
- ESP32 sends: Lead I, II, III
- Backend computes: Axis, augmented leads
- Frontend displays: 3-lead ECG viewer

### Phase 3: Full 12-Lead (8-Channel ECG)
- ESP32 sends: All 8 channels
- Backend computes: Full 12-lead analysis
- Frontend displays: 12-lead ECG grid

### Phase 4: EEG Mode (8-Channel EEG)
- ESP32 switches to EEG mode
- Backend computes: Band powers, asymmetry
- Frontend displays: EEG montage viewer

---

## Next Steps

1. ✅ Data structure designed
2. ⏳ Implement Phase 1 ESP32 firmware
3. ⏳ Implement Phase 1 backend MQTT handler
4. ⏳ Test real-time data flow
5. ⏳ Progressively add channels (Phase 2-4)
