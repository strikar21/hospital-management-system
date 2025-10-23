# 8-Channel ECG/EEG Full Implementation Plan

**Date:** 2025-10-15
**Goal:** Complete end-to-end 8-12 channel ECG/EEG monitoring system
**Approach:** Backend-first, then frontend, then ESP32 firmware

---

## Pre-Implementation Checks

### Current State Verified
- ✅ Database tables exist (waveform_snapshots, vitals_realtime, neural_events)
- ✅ TimescaleDB hypertables configured
- ✅ Frontend device info display working
- ❌ No backend models for 8-channel data
- ❌ No MQTT handlers for vitals/waveform/events
- ❌ No frontend types for nested ECG/EEG
- ❌ No ECG/EEG viewer components

### Architecture Decisions
1. **Backend handles ALL medical logic** - No frontend calculations
2. **3 MQTT topics:** vitals (1 sec), waveform (10 sec), events (as needed)
3. **camelCase everywhere** - Database, backend, frontend
4. **Progressive implementation:** Start with basic vitals, add channels later
5. **NaN-safe frontend** - All displays use `|| '--'` fallback

---

## Phase 1: Backend Pydantic Models (30 minutes)

### File to Create: `hospital-backend/app/models/neural_vitals.py`

**Models needed:**
1. `SignalQuality` - overall, leadOff, noise, impedance
2. `ECGAnalysis` - rrInterval, qrsDuration, qtInterval, axis, rhythm, stSegment
3. `EEGBandPowers` - alpha, beta, theta, delta, gamma
4. `EEGAnalysis` - bandPowers, dominantFrequency, asymmetry, seizureActivity
5. `VitalsRealtimeMessage` - MQTT message for vitals (1 sec updates)
6. `ChannelData` - baseline + deltas for compression
7. `ECGWaveformData` - limb leads, precordial leads, derived leads
8. `EEGWaveformData` - frontal, central, occipital channels
9. `WaveformSnapshotMessage` - MQTT message for waveform (10 sec snapshots)
10. `NeuralEventMessage` - MQTT message for arrhythmia/seizure events

**Key Features:**
- All camelCase field names
- Optional fields for progressive implementation (can send 1 lead or 12 leads)
- Validation for medical ranges (HR: 30-250, SpO2: 0-100, etc.)
- Support for both ECG and EEG modes

---

## Phase 2: Backend MQTT Service Updates (45 minutes)

### File to Update: `hospital-backend/app/services/mqtt_service.py`

**Current State Check:**
- Read existing MQTT handlers
- Check how current ESP32 messages are processed
- Identify what needs to change

**New Handlers to Add:**
1. `handle_vitals_message()` - Process vitals topic
   - Parse VitalsRealtimeMessage
   - Update PostgreSQL patients.vitals (latest values only)
   - Insert into TimescaleDB vitals_realtime (time-series)
   - Broadcast via WebSocket to frontend

2. `handle_waveform_message()` - Process waveform topic
   - Parse WaveformSnapshotMessage
   - Decompress delta-encoded channels (if compressed)
   - Insert into TimescaleDB waveform_snapshots
   - Optional: Trigger waveform analysis

3. `handle_event_message()` - Process event topic
   - Parse NeuralEventMessage
   - Create alert in PostgreSQL alerts table
   - Insert into TimescaleDB neural_events
   - Broadcast critical alert via WebSocket

**MQTT Topic Structure:**
```
hospital/devices/{deviceId}/vitals     → handle_vitals_message()
hospital/devices/{deviceId}/waveform   → handle_waveform_message()
hospital/devices/{deviceId}/event      → handle_event_message()
```

**Error Handling:**
- Validate device exists and is assigned to patient
- Handle malformed JSON gracefully
- Log errors but don't crash service

---

## Phase 3: Backend API Endpoints (30 minutes)

### File to Create: `hospital-backend/app/api/v2/neural_vitals.py`

**Endpoints to Create:**
1. `GET /api/v2/patients/{patientId}/vitals/realtime`
   - Get latest vitals (last 60 seconds)
   - Returns: heartRate, SpO2, temp, ECG metrics, EEG metrics

2. `GET /api/v2/patients/{patientId}/vitals/timeseries`
   - Query params: startTime, endTime, aggregate ('1min'/'5min'/'1hour')
   - Returns: Time-series data for graphs

3. `GET /api/v2/patients/{patientId}/waveforms`
   - Query params: mode ('ecg'/'eeg'), startTime, endTime, limit
   - Returns: Array of waveform snapshots

4. `GET /api/v2/patients/{patientId}/neural-events`
   - Query params: eventType, severity, resolved, limit
   - Returns: Array of neural events (arrhythmias, seizures)

5. `POST /api/v2/neural-events/{eventId}/acknowledge`
   - Body: acknowledgedBy (staff member)
   - Marks event as acknowledged

6. `POST /api/v2/neural-events/{eventId}/resolve`
   - Body: resolvedBy, notes
   - Marks event as resolved

**Auth Required:** All endpoints require JWT token with patient access

---

## Phase 4: Frontend TypeScript Types (30 minutes)

### File to Update: `hospital-display-app/src/types/PatientTypes.ts`

**Current State Check:**
- Read existing vitals interface
- Check what fields already exist

**New Interfaces to Add:**

```typescript
// Nested ECG object in vitals
export interface ECGMetrics {
  // Lead values (optional - can have 1 lead or 12 leads)
  leadI?: number;
  leadII?: number;
  leadIII?: number;
  aVR?: number;
  aVL?: number;
  aVF?: number;
  v1?: number;
  v2?: number;
  v3?: number;
  v4?: number;
  v5?: number;
  v6?: number;

  // Computed metrics (backend calculates these)
  rrInterval: number;
  qrsDuration: number;
  qtInterval: number;
  axis: number;
  rhythm: string;
  stSegment: 'normal' | 'elevated' | 'depressed';
}

// Nested EEG object in vitals
export interface EEGMetrics {
  // Channel values (optional)
  Fp1?: number;
  Fp2?: number;
  F3?: number;
  F4?: number;
  C3?: number;
  C4?: number;
  O1?: number;
  O2?: number;

  // Band powers (backend calculates these)
  alphaPower: number;
  betaPower: number;
  thetaPower: number;
  deltaPower: number;
  gammaPower?: number;
  dominantFrequency: number;
  seizureActivity: boolean;
}

// Update vitals interface to include ecg/eeg
export interface vitals {
  // Existing fields...
  heartRate: number;
  respiratoryRate: number;
  skinTemperature: number;
  oxygenSaturation: number;

  // New nested objects
  ecg?: ECGMetrics;
  eeg?: EEGMetrics;

  // Mode flag
  isEcgMode: boolean;  // true = ECG mode, false = EEG mode
}

// Waveform data structures
export interface ChannelData {
  baseline: number;
  deltas: number[];
}

export interface ECGWaveform {
  timestamp: string;
  sampleRate: number;
  duration: number;
  limb: {
    leadI: ChannelData;
    leadII: ChannelData;
    leadIII: ChannelData;
  };
  precordial?: {
    v1?: ChannelData;
    v2?: ChannelData;
    v3?: ChannelData;
    v4?: ChannelData;
    v5?: ChannelData;
  };
  derived?: {
    aVR?: ChannelData;
    aVL?: ChannelData;
    aVF?: ChannelData;
    v6?: ChannelData;
  };
  quality: {
    overall: number;
    leadOff: boolean[];
    noise: number[];
  };
}

export interface EEGWaveform {
  timestamp: string;
  sampleRate: number;
  duration: number;
  frontal: {
    Fp1: ChannelData;
    Fp2: ChannelData;
    F3: ChannelData;
    F4: ChannelData;
  };
  central: {
    C3: ChannelData;
    C4: ChannelData;
  };
  occipital: {
    O1: ChannelData;
    O2: ChannelData;
  };
  quality: {
    overall: number;
    impedance: number[];
  };
}

// Neural events
export interface NeuralEvent {
  eventId: string;
  timestamp: string;
  eventType: string;  // 'bradycardia', 'tachycardia', 'seizure', etc.
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  mode: 'ecg' | 'eeg';
  acknowledged: boolean;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
  resolved: boolean;
  resolvedAt?: string;
  context?: any;
}
```

---

## Phase 5: Frontend PatientTransformer Updates (20 minutes)

### File to Update: `hospital-display-app/src/utils/transformers/PatientTransformer.ts`

**Changes Needed:**
1. Update `transformVitals()` to handle nested ecg/eeg objects
2. Ensure all fields use camelCase
3. Handle optional fields (can have ecg OR eeg, not both)
4. Preserve NaN-safe handling (`|| '--'` in display)

```typescript
private static transformVitals(data: any): vitals | null {
  if (!data) return null;

  return {
    // Basic vitals
    heartRate: data.heartRate,
    respiratoryRate: data.respiratoryRate,
    skinTemperature: data.skinTemperature,
    oxygenSaturation: data.oxygenSaturation,
    bloodPressureSystolic: data.bloodPressureSystolic,
    bloodPressureDiastolic: data.bloodPressureDiastolic,

    // Mode flag
    isEcgMode: data.isEcgMode ?? true,

    // ECG metrics (optional)
    ecg: data.ecg ? {
      leadI: data.ecg.leadI,
      leadII: data.ecg.leadII,
      leadIII: data.ecg.leadIII,
      aVR: data.ecg.aVR,
      aVL: data.ecg.aVL,
      aVF: data.ecg.aVF,
      v1: data.ecg.v1,
      v2: data.ecg.v2,
      v3: data.ecg.v3,
      v4: data.ecg.v4,
      v5: data.ecg.v5,
      v6: data.ecg.v6,
      rrInterval: data.ecg.rrInterval,
      qrsDuration: data.ecg.qrsDuration,
      qtInterval: data.ecg.qtInterval,
      axis: data.ecg.axis,
      rhythm: data.ecg.rhythm,
      stSegment: data.ecg.stSegment
    } : undefined,

    // EEG metrics (optional)
    eeg: data.eeg ? {
      Fp1: data.eeg.Fp1,
      Fp2: data.eeg.Fp2,
      F3: data.eeg.F3,
      F4: data.eeg.F4,
      C3: data.eeg.C3,
      C4: data.eeg.C4,
      O1: data.eeg.O1,
      O2: data.eeg.O2,
      alphaPower: data.eeg.alphaPower,
      betaPower: data.eeg.betaPower,
      thetaPower: data.eeg.thetaPower,
      deltaPower: data.eeg.deltaPower,
      gammaPower: data.eeg.gammaPower,
      dominantFrequency: data.eeg.dominantFrequency,
      seizureActivity: data.eeg.seizureActivity
    } : undefined
  };
}
```

---

## Phase 6: Frontend Components - ECG/EEG Viewers (2-3 hours)

### Component 1: `hospital-display-app/src/components/ECG12LeadViewer.tsx`

**Purpose:** Display 12-lead ECG in standard medical grid layout

**Layout:**
```
Standard 3x4 Grid:
┌────────┬────────┬────────┬────────┐
│ Lead I │ aVR    │ V1     │ V4     │
├────────┼────────┼────────┼────────┤
│ Lead II│ aVL    │ V2     │ V5     │
├────────┼────────┼────────┼────────┤
│ Lead III│ aVF   │ V3     │ V6     │
└────────┴────────┴────────┴────────┘
```

**Features:**
- Real-time waveform rendering (Canvas API)
- Auto-scaling based on signal amplitude
- Grid lines (0.1 mV / 0.04 sec)
- Event markers (PVCs, arrhythmias)
- Zoom/pan controls
- Print/export to PDF

### Component 2: `hospital-display-app/src/components/EEG8ChannelViewer.tsx`

**Purpose:** Display 8-channel EEG in montage view

**Layout:**
```
Stacked Montage:
Fp1 ─────────────────────────
Fp2 ─────────────────────────
F3  ─────────────────────────
F4  ─────────────────────────
C3  ─────────────────────────
C4  ─────────────────────────
O1  ─────────────────────────
O2  ─────────────────────────
    └── Time (seconds) ──→
```

**Features:**
- Synchronized time axis across all channels
- Amplitude scaling per channel
- Band power visualization (sidebar)
- Seizure event markers
- Frequency spectrum display

### Component 3: `hospital-display-app/src/components/NeuralEventsPanel.tsx`

**Purpose:** Display and manage neural events (arrhythmias, seizures)

**Features:**
- List of events sorted by timestamp
- Color-coded by severity (low=blue, medium=yellow, high=orange, critical=red)
- Filter by event type, severity, resolved status
- Acknowledge button (for staff)
- Resolve button (for staff)
- Click to view waveform snapshot

---

## Phase 7: ESP32 Firmware Updates (3-4 hours)

### File to Update: `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`

**Hardware Integration:**
1. Add ADS1298 library
2. Configure 8-channel ADC (SPI communication)
3. Set sample rate (250 Hz or 500 Hz)
4. Configure gain and filters

**Data Collection:**
1. Sample all 8 channels continuously
2. Buffer 10 seconds of data (2500 samples × 8 channels = 20,000 samples)
3. Apply delta encoding for compression (50% bandwidth savings)

**MQTT Publishing:**
1. **Vitals topic** (every 1 second):
   - Compute HR, RR, SpO2 from waveform
   - Send computed metrics only (no waveform)

2. **Waveform topic** (every 10 seconds):
   - Send full 8-channel waveform snapshot
   - Use delta encoding: {baseline, deltas}

3. **Event topic** (as needed):
   - Detect arrhythmias/seizures on device
   - Send event with confidence score

**Mode Switching:**
- Toggle between ECG and EEG modes
- Same hardware, different channel mapping
- Update MQTT messages with mode flag

---

## Phase 8: End-to-End Testing (1-2 hours)

### Test 1: Backend Unit Tests
- Test Pydantic model validation
- Test MQTT message parsing
- Test database insertion

### Test 2: API Endpoint Tests
- Test vitals retrieval
- Test waveform queries
- Test event management

### Test 3: Frontend Display Tests
- Test vitals display with nested ecg/eeg
- Test ECG viewer rendering
- Test EEG viewer rendering

### Test 4: ESP32 Integration Tests
- Test ESP32 → MQTT → Backend flow
- Test waveform compression/decompression
- Test event detection and alerting

### Test 5: Full System Test
- Assign watch to test patient
- Start ESP32 streaming
- Verify data appears in frontend
- Test all viewer components
- Test event acknowledgment workflow

---

## Implementation Order

### Day 1 (Morning):
1. ✅ Phase 1: Backend Pydantic Models (30 min)
2. ✅ Phase 2: Backend MQTT Service (45 min)
3. ✅ Phase 3: Backend API Endpoints (30 min)

### Day 1 (Afternoon):
4. ✅ Phase 4: Frontend TypeScript Types (30 min)
5. ✅ Phase 5: Frontend PatientTransformer (20 min)
6. ⏳ Phase 6: Frontend Components (2-3 hours)

### Day 2:
7. ⏳ Phase 7: ESP32 Firmware (3-4 hours)
8. ⏳ Phase 8: End-to-End Testing (1-2 hours)

---

## Files to Create/Modify

### Backend (Python)
- `hospital-backend/app/models/neural_vitals.py` (NEW)
- `hospital-backend/app/services/mqtt_service.py` (UPDATE)
- `hospital-backend/app/api/v2/neural_vitals.py` (NEW)

### Frontend (TypeScript/React)
- `hospital-display-app/src/types/PatientTypes.ts` (UPDATE)
- `hospital-display-app/src/utils/transformers/PatientTransformer.ts` (UPDATE)
- `hospital-display-app/src/components/ECG12LeadViewer.tsx` (NEW)
- `hospital-display-app/src/components/EEG8ChannelViewer.tsx` (NEW)
- `hospital-display-app/src/components/NeuralEventsPanel.tsx` (NEW)

### ESP32 (C++)
- `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino` (UPDATE)
- May need new file: `ads1298_driver.cpp` (ADS1298 hardware interface)

---

## Success Criteria

✅ **Backend:**
- Pydantic models validate all 8-channel data
- MQTT service processes all 3 topics correctly
- Data correctly stored in TimescaleDB
- API endpoints return data in camelCase

✅ **Frontend:**
- All vitals display with nested ecg/eeg
- ECG viewer shows 12-lead grid
- EEG viewer shows 8-channel montage
- Neural events panel shows alerts
- All displays handle NaN gracefully

✅ **ESP32:**
- Samples 8 channels at 250+ Hz
- Publishes to 3 MQTT topics
- Delta encoding works correctly
- Mode switching works

✅ **Integration:**
- End-to-end data flow works
- Latency < 2 seconds from device to display
- No data loss
- All medical calculations on backend only

---

## Questions Before Starting

1. **Backend first or frontend first?**
   - Recommendation: Backend first (models → MQTT → API)
   - Reason: Can test with MQTT simulator before ESP32 ready

2. **Do you have ADS1298 hardware ready?**
   - If yes: Can integrate firmware in parallel
   - If no: Can simulate with mock data

3. **Priority: Basic vitals or full waveforms?**
   - Recommendation: Start with vitals (Phase 1-5), add waveforms later (Phase 6-7)
   - Reason: Gets graphs working faster

4. **Do you want to test each phase or do all at once?**
   - Recommendation: Test after Phase 3 (backend complete)
   - Reason: Catch issues early before frontend work

---

## Ready to Start?

**I recommend starting with:**
1. Phase 1: Backend Pydantic Models
2. Phase 2: Backend MQTT Service
3. Phase 3: Backend API Endpoints
4. Then test backend with MQTT simulator

**Do you approve this plan?** Any changes needed?
