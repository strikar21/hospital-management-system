# ECG/EEG Multi-Lead Analysis - Thorough Investigation

## Your Question: "check how many leads we have in eeg/ecg. you are collecting only one field?"

**Answer: YES, currently collecting only ONE aggregate value, NOT multi-lead data!**

---

## Current Implementation Analysis

### 1. Frontend TypeScript Definitions

#### Simple Vitals (PatientTypes.ts:59-60)
```typescript
vitals: {
  ecgReading: number;  // Single value - mV * 100
  eegReading: number;  // Single value - μV
  isEcgMode: boolean;  // Toggle between ECG vs EEG
}
```
**Status**: ❌ Only stores ONE aggregate ECG value and ONE aggregate EEG value

#### Detailed ECG Reading Interface (PatientTypes.ts:162-171)
```typescript
export interface ecgreading {
  timestamp: string;
  duration: number;
  samplerate: number;
  data: number[];  // ✅ Array of readings (time series)
  interpretation: string;
  performedBy: string;
  arrhythmiadetected?: boolean;
  arrhythmiatype?: string;
}
```
**Status**: ✅ CAN store multi-point time series, BUT no lead/channel info!

#### Detailed EEG Reading Interface (PatientTypes.ts:173-183)
```typescript
export interface eegreading {
  timestamp: string;
  duration: number;
  samplerate: number;
  data: number[];  // ⚠️ Flat array - how are channels separated?
  channels: string[];  // ✅ ['F3', 'F4', 'C3', 'C4'] etc
  interpretation: string;
  performedBy: string;
  seizureactivity?: boolean;
  abnormalpatterns?: string[];
}
```
**Status**: ⚠️ HAS channel names but unclear how `data` array maps to channels

---

### 2. TimescaleDB Schema

#### Schema 1: vital_signs table (02-init-timescale-database.sql:34-49)
```sql
CREATE TABLE IF NOT EXISTS public.vital_signs (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50),
    "heartRate" INTEGER,
    "bloodPressureSystolic" INTEGER,
    "bloodPressureDiastolic" INTEGER,
    "oxygenSaturation" DECIMAL(5,2),
    "bodyTemperature" DECIMAL(4,1),
    "respiratoryRate" INTEGER,
    "bloodGlucose" DECIMAL(5,1),
    "ecgData" JSONB,  -- ⚠️ ECG stored as JSONB blob
    "alertLevel" VARCHAR(20) DEFAULT 'normal',
    "dataQuality" VARCHAR(20) DEFAULT 'good',
    metadata JSONB
);
```
**Status**: ⚠️ `ecgData` is JSONB - can store multi-lead, but structure undefined

#### Schema 2: vitals_timeseries table (03-create-vitals-timeseries.sql:9-18)
```sql
CREATE TABLE IF NOT EXISTS public.vitals_timeseries (
    time TIMESTAMPTZ NOT NULL,
    "patientId" UUID NOT NULL,
    "deviceId" VARCHAR(50),
    vitaltype VARCHAR(50) NOT NULL,  -- 'ecg', 'eeg', 'heartrate', etc.
    value DECIMAL(10,2) NOT NULL,  -- ❌ Single value only!
    unit VARCHAR(20),
    quality INTEGER DEFAULT 95,
    metadata JSONB  -- ⚠️ Could store lead info here
);
```
**Status**: ❌ Only ONE value per row - for multi-lead, would need multiple rows or JSONB metadata

---

### 3. ESP32 Current Implementation

#### ESP32 sends (esp32_hospital_watch_complete.ino:843-851)
```cpp
doc["heartRate"] = heartRate;
doc["temperature"] = temperature;
doc["oxygenSat"] = oxygenSat;
doc["batteryLevel"] = batteryLevel;
```
**Status**: ❌ NO ECG/EEG data being sent at all!

---

## Medical Standard: How Many Leads?

### ECG Leads (Standard Medical Practice)

#### 12-Lead ECG (Clinical Standard):
- **Limb Leads** (6):
  - Lead I, II, III (bipolar)
  - aVR, aVL, aVF (augmented unipolar)
- **Precordial Leads** (6):
  - V1, V2, V3, V4, V5, V6

**Total: 12 leads for complete cardiac assessment**

#### Simplified ECG (Emergency/Watch):
- **3-Lead**: I, II, III (basic cardiac monitoring)
- **5-Lead**: I, II, III, V1, V5 (emergency/ICU)
- **Single-Lead**: Lead II or Lead I (wearables like Apple Watch)

### EEG Channels (Standard Medical Practice)

#### 10-20 System (Clinical Standard):
**Frontal**: Fp1, Fp2, F3, F4, F7, F8, Fz
**Central**: C3, C4, Cz
**Parietal**: P3, P4, Pz
**Temporal**: T3, T4, T5, T6
**Occipital**: O1, O2

**Total: 19-21 electrodes for full brain mapping**

#### Simplified EEG:
- **4-Channel**: F3, F4, O1, O2 (basic brain activity)
- **2-Channel**: F3-O1, F4-O2 (seizure detection)
- **Single-Channel**: Fz-Oz (consumer wearables)

---

## What We Should Be Collecting

### For ESP32 Watch (Realistic Wearable Capability)

#### Option A: Single-Lead ECG (Minimal)
```json
{
  "ecgReading": 120,  // Single aggregate mV value
  "ecgLead": "Lead II"  // Which lead
}
```

#### Option B: 3-Lead ECG (Better)
```json
{
  "ecg": {
    "leadI": 120,
    "leadII": 150,
    "leadIII": 30,
    "sampleRate": 250
  }
}
```

#### Option C: Time-Series ECG (Best for Analysis)
```json
{
  "ecg": {
    "lead": "Lead II",
    "sampleRate": 250,
    "samples": [120, 122, 125, 130, 145, 160, ...],  // 250 samples/sec
    "duration": 10  // seconds
  }
}
```

### For EEG (If Implemented)

#### Option A: 2-Channel EEG (Minimal Seizure Detection)
```json
{
  "eeg": {
    "channels": ["F3", "F4"],
    "sampleRate": 250,
    "data": {
      "F3": [45, 47, 46, 48, ...],
      "F4": [43, 44, 46, 45, ...]
    }
  }
}
```

---

## Current Data Structure Issues

### Issue #1: Frontend Vitals Store Single Values
```typescript
ecgReading: number;  // ❌ Only ONE value, no lead info
eegReading: number;  // ❌ Only ONE value, no channel info
```

**Problem**: Cannot differentiate between leads or detect regional issues

### Issue #2: Detailed Reading Interfaces Are Unclear
```typescript
export interface ecgreading {
  data: number[];  // ❌ Is this Lead I? Lead II? All leads combined?
}

export interface eegreading {
  data: number[];  // ❌ How do channels map to this array?
  channels: string[];  // ✅ Has channel names BUT...
}
```

**Problem**: `data` array structure is ambiguous
- Is it: `[lead1_sample1, lead1_sample2, ...]`?
- Or: `[lead1_s1, lead2_s1, lead3_s1, lead1_s2, ...]` (interleaved)?
- Or: `[...lead1_samples, ...lead2_samples]` (concatenated)?

### Issue #3: Database Can't Store Multi-Lead Efficiently
```sql
-- Current:
vitaltype VARCHAR(50) NOT NULL,  -- 'ecg'
value DECIMAL(10,2) NOT NULL,  -- 120 (which lead?)

-- Would need:
vitaltype VARCHAR(50),  -- 'ecg_lead_II' or 'eeg_F3'
value DECIMAL(10,2),
```

**Problem**: Either need multiple rows per timestamp OR redesign schema

---

## Recommended Data Model

### For Real-Time Vitals (Dashboard Display)

#### PostgreSQL patients table - Latest vitals:
```typescript
vitals: {
  // Single aggregate values for quick dashboard display
  heartRate: number;  // Derived from ECG Lead II
  ecgLeadII: number;  // Primary monitoring lead
  eegF3: number;  // Frontal left hemisphere
  eegF4: number;  // Frontal right hemisphere
  // ... other vitals
}
```

### For Time-Series Analysis (Charts/History)

#### TimescaleDB vitals_timeseries - Detailed data:
```sql
-- Option A: One row per lead per timestamp
time | patientId | vitalType  | leadName | value | quality
-----|-----------|------------|----------|-------|--------
t1   | patient1  | ecg        | Lead_I   | 120   | 95
t1   | patient1  | ecg        | Lead_II  | 150   | 95
t1   | patient1  | ecg        | Lead_III | 30    | 95
t1   | patient1  | eeg        | F3       | 45    | 92
t1   | patient1  | eeg        | F4       | 43    | 94

-- Option B: JSONB for waveform data
time | patientId | vitalType | waveform (JSONB)
-----|-----------|-----------|------------------
t1   | patient1  | ecg       | {"leads": {"I": [120,122,...], "II": [150,152,...]}}
t1   | patient1  | eeg       | {"channels": {"F3": [45,47,...], "F4": [43,44,...]}}
```

---

## Questions to Answer Before Implementation

1. **ESP32 Hardware Capability**:
   - How many ECG electrodes does the watch have? (2, 3, or more?)
   - Can it actually capture multi-lead ECG or just single-lead?
   - Is EEG even possible with a wrist device? (Usually needs skull electrodes)

2. **Clinical Requirements**:
   - Do doctors need 12-lead ECG or is single-lead sufficient?
   - Is EEG actually required or just ECG?
   - What's the minimum data needed for arrhythmia detection?

3. **Performance Constraints**:
   - Can MQTT handle 250 Hz x N leads? (e.g., 3 leads x 250 samples/sec = 750 values/sec)
   - Does TimescaleDB need optimization for high-frequency multi-channel data?
   - Should we compress/aggregate data before storing?

4. **Display Requirements**:
   - Does frontend need to show all leads or just one primary lead?
   - Should dashboard show waveforms or just aggregate values?
   - Do we need ECG viewer component for detailed analysis?

---

## Conclusion

**Current State**:
- ✅ Database CAN store multi-lead data (via JSONB or multiple rows)
- ✅ Frontend HAS interfaces for detailed ECG/EEG readings
- ❌ ESP32 is NOT sending ANY ECG/EEG data
- ❌ Frontend vitals only store SINGLE aggregate ECG/EEG values
- ❌ Data structure for multi-lead is UNDEFINED/AMBIGUOUS

**Recommendation**:
1. **Research first**: Check ESP32 hardware - how many ECG leads does it actually have?
2. **Define requirements**: Single-lead or multi-lead? EEG needed?
3. **Design data model**: Clear structure for multi-channel waveform data
4. **Implement incrementally**: Start with single-lead, expand to multi-lead if needed

**DO NOT implement until we know the hardware capabilities and clinical requirements!**
