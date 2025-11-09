# ECG/EEG Metrics Tooltip - "No ECG metrics available" Issue

## Problem
When hovering over the ECG/EEG title in PatientCard, the tooltip shows "No ECG metrics available" or "No EEG metrics available" instead of displaying the advanced metrics.

## Research Findings

### 1. **Frontend Type Definitions** ✅ CORRECT
**File:** `hospital-display-app/src/types/PatientTypes.ts` (lines 73-90)

The types ARE defined correctly:
```typescript
ecg?: {
  rrInterval?: number;
  qrsDuration?: number;
  qtInterval?: number;
  axis?: number;
  rhythm?: string;
  stSegment?: 'normal' | 'elevated' | 'depressed';
};
eeg?: {
  alphaPower?: number;
  betaPower?: number;
  thetaPower?: number;
  deltaPower?: number;
  gammaPower?: number;
  dominantFrequency?: number;
  seizureActivity?: boolean;
};
```

### 2. **Backend Database Query** ✅ CORRECT
**File:** `hospital-backend/app/repositories/patient_repository.py` (lines 738-743)

The backend IS querying these fields from TimescaleDB:
```sql
SELECT DISTINCT ON ("patientId")
    "patientId", time, "deviceId", mode,
    "heartRate", "respiratoryRate", "skinTemperature",
    "oxygenSaturation", "batteryLevel", "signalQuality",
    "rrInterval", "qrsDuration", "qtInterval", axis, rhythm, "stSegment",
    "alphaPower", "betaPower", "thetaPower", "deltaPower", "gammaPower",
    "dominantFrequency", "seizureActivity"
FROM vitals_realtime
WHERE "patientId" = ANY($1)
```

### 3. **Backend Response Construction** ✅ CORRECT
**File:** `hospital-backend/app/services/patient_service.py` (lines 120-138, 318-336)

The backend IS creating nested ECG/EEG objects:

```python
# Add nested ECG/EEG objects if present
if vitals_row.get('mode') == 'ecg':
    camel_result['vitals']['ecg'] = {
        'rrInterval': vitals_row.get('rrInterval'),
        'qrsDuration': vitals_row.get('qrsDuration'),
        'qtInterval': vitals_row.get('qtInterval'),
        'axis': vitals_row.get('axis'),
        'rhythm': vitals_row.get('rhythm'),
        'stSegment': vitals_row.get('stSegment')
    }
elif vitals_row.get('mode') == 'eeg':
    camel_result['vitals']['eeg'] = {
        'alphaPower': vitals_row.get('alphaPower'),
        'betaPower': vitals_row.get('betaPower'),
        'thetaPower': vitals_row.get('thetaPower'),
        'deltaPower': vitals_row.get('deltaPower'),
        'gammaPower': vitals_row.get('gammaPower'),
        'dominantFrequency': vitals_row.get('dominantFrequency'),
        'seizureActivity': vitals_row.get('seizureActivity')
    }
```

### 4. **Frontend Tooltip Logic**
**File:** `hospital-display-app/src/components/PatientCard/PatientCardWaveform.tsx` (lines 91-114)

The tooltip checks:
```typescript
{isECGMode ? (
  patient.vitals?.ecg ? (
    // Show ECG metrics
  ) : (
    <div>No ECG metrics available</div>
  )
) : (
  patient.vitals?.eeg ? (
    // Show EEG metrics
  ) : (
    <div>No EEG metrics available</div>
  )
)}
```

## Root Cause

The tooltip is showing "No ECG metrics available" because **one of these is true**:

1. **`patient.vitals?.ecg` is undefined/null** - The backend is creating the object, but ALL fields are NULL
2. **The database fields are empty** - vitals_realtime table has NULL values for rrInterval, qrsDuration, etc.
3. **ESP32 is not sending these metrics** - The watch firmware isn't calculating/sending these values

## The REAL Issue: ESP32 Firmware

Looking at the data flow, the issue is that **the ESP32 firmware is NOT calculating or sending ECG/EEG advanced metrics**.

The firmware sends:
- ✅ Raw waveform samples (12 channels ECG or 8 channels EEG)
- ✅ Basic vitals (HR, RR, SpO2, temp)
- ❌ Advanced ECG metrics (RR interval, QRS duration, QT interval, rhythm, axis, ST segment)
- ❌ Advanced EEG metrics (band powers, dominant frequency, seizure detection)

## Where These Metrics SHOULD Be Calculated

There are two options:

### Option 1: Backend Calculation (RECOMMENDED)
**Pros:**
- Medical-grade algorithms on powerful hardware
- Can be updated without ESP32 firmware changes
- Better for regulatory compliance
- More processing power available

**Cons:**
- Requires implementing ECG/EEG analysis services

**Status:** Backend services exist but may not be fully integrated:
- `hospital-backend/app/services/ecg_analysis_service.py` (exists)
- `hospital-backend/app/services/eeg_analysis_service.py` (exists)

### Option 2: ESP32 Calculation
**Pros:**
- Lower latency
- Reduces backend load

**Cons:**
- Limited CPU/memory on ESP32
- Harder to update/improve algorithms
- Less accurate than backend analysis

## Solution Options

### Quick Fix: Remove the Tooltip
Since the metrics aren't being calculated/sent, remove the misleading tooltip that shows "No ECG metrics available".

**File:** `hospital-display-app/src/components/PatientCard/PatientCardWaveform.tsx`
**Action:** Remove the entire tooltip div (lines 91-114)

### Proper Fix: Implement Backend Analysis
1. Integrate existing ECG/EEG analysis services
2. Process incoming waveform data through analysis
3. Store calculated metrics in vitals_realtime table
4. Metrics will then automatically appear in tooltip

## Recommendation

**For now:** Remove the tooltip since it's showing "No metrics available" which looks broken.

**For future:** Implement backend ECG/EEG analysis to populate these metrics. The infrastructure is already in place - just needs integration.

## Current Status

- ✅ Database schema supports ECG/EEG metrics
- ✅ Backend queries these fields
- ✅ Backend creates nested objects
- ✅ Frontend types defined correctly
- ✅ Tooltip code is correct
- ❌ **Metrics are NOT being calculated/populated**
- ❌ **Tooltip shows "No metrics available"**

## User's Question: "why does it say no ecg metrics?"

**Answer:** The tooltip says "No ECG metrics available" because:
1. The backend IS querying and sending the data structure correctly
2. BUT the actual metric VALUES are NULL/undefined in the database
3. Because the ECG analysis backend service hasn't been integrated to calculate these metrics from the raw waveform data
4. The ESP32 only sends raw waveform samples, not the calculated metrics (RR interval, QRS, etc.)

The code is working correctly - it's just that there's no data to display yet!
