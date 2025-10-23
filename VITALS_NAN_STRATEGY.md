# Vitals NaN Strategy - 1-Lead to 8-Lead Progressive Implementation

## Executive Summary

Based on comprehensive frontend audit, **all vitals can safely show NaN** (displayed as `'--'`). Only waveform arrays need NaN filtering (currently flat line placeholders).

---

## Audit Key Findings

### ✅ **NaN-SAFE Displays (9 vitals)**
All use `|| '--'` or `?? 0` fallback patterns:

1. **heartRate** - Dashboard, detail view, charts
2. **oxygenSaturation** - Dashboard, detail view, charts
3. **respiratoryRate** - Dashboard, detail view
4. **systolicPressure / diastolicPressure** - Dashboard, detail view
5. **skinTemperature** - Dashboard, detail view, charts
6. **ecgReading** - Dashboard, detail view
7. **eegReading** - Dashboard, detail view
8. **bioelectricalImpedance** - Dashboard
9. **tremorIntensity** - Dashboard, detail view

**Display Pattern**:
```typescript
// Dashboard cards:
{patient.vitals?.heartRate || '--'}

// Patient detail:
{patient.vitals?.skinTemperature ? patient.vitals.skinTemperature.toFixed(1) : '--'}

// Bedside monitor:
Math.max(0, Math.min(300, patient.vitals?.heartRate ?? 0))  // Clamps NaN → 0
```

### ⚠️ **Needs NaN Filtering (waveforms only)**
```typescript
// ECG/EEG waveform rendering
const dataMin = Math.min(...recentData);  // ❌ Returns NaN if array contains NaN
const dataMax = Math.max(...recentData);  // ❌ Returns NaN if array contains NaN

// FIX:
const cleanData = recentData.filter(v => !isNaN(v) && isFinite(v));
const dataMin = Math.min(...cleanData);
```

**Current Status**: Waveforms are flat line placeholders - not reading real data yet.

### ❌ **Backend Rejects NaN**
```python
# Pydantic validators would reject NaN
heartRate: Optional[int] = Field(None, ge=20, le=300)  # NaN not in range

# TimescaleDB insert fails
float(value)  # Raises exception on NaN
```

---

## Progressive Implementation Strategy

### Phase 1: Single-Lead (1-Lead ECG/EEG)
**Goal**: Get basic vitals flowing from ESP32 to frontend

**ESP32 Sends**:
```json
{
  "mode": "ecg",
  "channels": {
    "leadII": [120, 122, 125, ...]  // 1 lead only
  },
  "aggregates": {
    "heartRate": 75,
    "respiratoryRate": 16,
    "temperature": 98.6,
    "oxygenSat": 98
  }
}
```

**Backend Computes**:
- ✅ Heart rate (from Lead II)
- ✅ Respiratory rate (from impedance/ECG modulation)
- ✅ Basic rhythm (regular/irregular)
- ❌ QRS morphology → **NaN** (needs 12-lead)
- ❌ ST segment analysis → **NaN** (needs 12-lead)
- ❌ Axis calculation → **NaN** (needs limb leads)

**Frontend Displays**:
```
Heart Rate: 75 BPM ✓
ECG Reading: 120 mV ✓
Respiratory Rate: 16 /min ✓
Temperature: 98.6°F ✓
Oxygen Sat: 98% ✓
Blood Pressure: --/-- (not available)
```

---

### Phase 2: Three-Lead (3-Lead ECG)
**Goal**: Add limb leads for axis and basic 12-lead derived calculations

**ESP32 Sends**:
```json
{
  "mode": "ecg",
  "channels": {
    "leadI": [120, 122, ...],
    "leadII": [150, 152, ...],
    "leadIII": [30, 32, ...]
  },
  "aggregates": {
    "heartRate": 75,
    "axis": 60,
    "rrInterval": 800
  }
}
```

**Backend Computes**:
- ✅ Heart rate
- ✅ Cardiac axis (from limb leads)
- ✅ Augmented leads (aVR, aVL, aVF - derived)
- ✅ Basic arrhythmia detection
- ⚠️ QRS morphology (partial - limited views)
- ❌ ST segment analysis → **NaN** (needs precordial leads)

---

### Phase 3: Full 12-Lead (8 Channels)
**Goal**: Professional diagnostic ECG

**ESP32 Sends**:
```json
{
  "mode": "ecg",
  "channels": {
    "leadI": [...],
    "leadII": [...],
    "leadIII": [...],
    "v1": [...],
    "v2": [...],
    "v3": [...],
    "v4": [...],
    "v5": [...]
  },
  "derived": {
    "aVR": [...],
    "aVL": [...],
    "aVF": [...],
    "v6": [...]
  },
  "analysis": {
    "heartRate": 75,
    "axis": 60,
    "qrsDuration": 90,
    "qtInterval": 380,
    "stSegment": "normal",
    "arrhythmia": {
      "detected": false
    }
  }
}
```

**Backend Computes**:
- ✅ All 12-lead calculations
- ✅ QRS morphology analysis
- ✅ ST segment analysis
- ✅ T-wave analysis
- ✅ Advanced arrhythmia classification
- ✅ Ischemia detection

---

### Phase 4: EEG Mode (8 Channels)
**Goal**: Brain monitoring with swappable connectors

**ESP32 Sends**:
```json
{
  "mode": "eeg",
  "channels": {
    "Fp1": [...],
    "Fp2": [...],
    "F3": [...],
    "F4": [...],
    "C3": [...],
    "C4": [...],
    "O1": [...],
    "O2": [...]
  },
  "analysis": {
    "alphaPower": 45.2,
    "betaPower": 22.1,
    "thetaPower": 18.5,
    "deltaPower": 14.2,
    "asymmetry": {
      "frontal": 0.05,
      "occipital": 0.03
    },
    "seizure": {
      "detected": false
    }
  }
}
```

**Backend Computes**:
- ✅ Band power analysis (delta, theta, alpha, beta, gamma)
- ✅ Hemispheric asymmetry
- ✅ Seizure detection
- ✅ Sleep stage analysis
- ✅ Abnormal pattern detection

---

## Data Quality Strategy

### Option A: NaN for Unavailable Metrics
```python
# Backend computation
vitals = {
    'heartRate': 75,
    'ecgReading': 120,
    'qrsDuration': float('nan'),  # ❌ Pydantic rejects
    'stSegment': None  # ✅ Use None instead
}
```

### Option B: Quality Flags (Recommended)
```python
vitals = {
    'heartRate': 75,
    'heartRateQuality': 'good',
    'ecgReading': 120,
    'ecgReadingQuality': 'good',
    'qrsDuration': None,  # Not available
    'qrsDurationQuality': 'unavailable',
    'stSegment': None,
    'stSegmentQuality': 'unavailable'
}
```

### Option C: Availability Matrix
```python
vitals = {
    'heartRate': 75,
    'ecgReading': 120,
    'availableMetrics': ['heartRate', 'ecgReading', 'respiratoryRate'],
    'unavailableMetrics': ['qrsDuration', 'stSegment', 'axis'],
    'dataQuality': 'limited-1-lead'
}
```

**Recommended**: **Option B** - explicit quality flags per metric

---

## Frontend Display Strategy

### Dashboard - Always Show Available Data
```typescript
// Current (already NaN-safe):
{patient.vitals?.heartRate || '--'}

// Enhanced with quality indicator:
<div className="flex items-center space-x-1">
  <span>{patient.vitals?.heartRate || '--'}</span>
  {patient.vitals?.heartRateQuality === 'degraded' && (
    <AlertTriangle className="w-3 h-3 text-yellow-500" />
  )}
</div>
```

### Patient Detail - Show All Fields with Quality
```typescript
// ECG Reading with quality badge
<div>
  <span className="font-bold">
    {patient.vitals?.ecgReading || '--'}
  </span>
  <span className={`ml-2 px-1 py-0.5 rounded text-xs ${
    patient.vitals?.ecgReadingQuality === 'good' ? 'bg-green-100 text-green-800' :
    patient.vitals?.ecgReadingQuality === 'degraded' ? 'bg-yellow-100 text-yellow-800' :
    'bg-gray-100 text-gray-600'
  }`}>
    {patient.vitals?.ecgReadingQuality || 'unknown'}
  </span>
</div>
```

### Bedside Monitor - Simple Display
```typescript
// No quality indicators - just numbers
// NaN → 0 → clamped (already safe)
const safeHeartRate = Math.max(0, Math.min(300, patient.vitals?.heartRate ?? 0));
```

---

## Implementation Checklist

### Phase 1 (1-Lead) - Immediate:
- [ ] Fix ESP32 vitals message structure (nest vitals, use camelCase)
- [ ] Fix backend MQTT handler to accept flat structure temporarily
- [ ] Add basic vital computation from single lead
- [ ] Test dashboard displays (should show HR, temp, SpO2)
- [ ] Verify '--' displays for unavailable metrics

### Phase 2 (3-Lead) - Next:
- [ ] Add 3-lead ECG support in ESP32 firmware
- [ ] Add axis calculation in backend
- [ ] Add augmented lead derivation
- [ ] Test limb lead waveform display

### Phase 3 (12-Lead) - Future:
- [ ] Add all 8 channels to ESP32 firmware
- [ ] Add full 12-lead analysis in backend
- [ ] Add ECG viewer with 12-lead grid layout
- [ ] Add ST segment tracking and alerts

### Phase 4 (EEG) - Future:
- [ ] Add EEG mode toggle in ESP32
- [ ] Add band power analysis in backend
- [ ] Add EEG montage viewer in frontend
- [ ] Add seizure detection alerts

---

## Conclusion

**Answer to Your Question**:
> "sometimes we could be using just 1 lead data, then others would be showing NaN?"

**Yes, exactly!** And it's totally safe:
- ✅ Frontend displays NaN as `'--'` automatically
- ✅ All vital displays have fallback handling
- ✅ Only waveform rendering needs NaN filtering (easy fix)
- ✅ Backend should use `None` instead of NaN (Pydantic compatible)
- ✅ Add quality flags so clinicians understand data limitations

**Recommended First Step**: Implement Phase 1 (1-lead) to get basic vitals flowing, then progressively add channels as needed.
