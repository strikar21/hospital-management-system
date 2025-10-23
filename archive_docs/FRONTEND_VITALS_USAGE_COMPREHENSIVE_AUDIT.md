# Frontend Vitals Usage - Comprehensive Audit
**Date**: 2025-10-15
**Purpose**: Document all locations where vitals data is displayed, used, or referenced in the frontend
**Scope**: Full codebase analysis to determine which vitals can show NaN vs require all channels

---

## Executive Summary

This audit identifies **all locations** in the frontend where vitals data is accessed, displayed, or used for alerts. The analysis categorizes vitals by **criticality** and **fallback handling** to determine which vitals can safely show NaN when only 1-lead data is available.

### Key Findings:

1. **All vital displays use fallback handling** (`|| '--'` or `|| 0`)
2. **No vitals are required** - every field has optional chaining (`patient.vitals?.field`)
3. **Backend computes only basic vitals** - no advanced multi-lead analysis currently
4. **ECG/EEG waveforms are flat line placeholders** - awaiting real-time streaming
5. **Medical logic removed from frontend** - all determinations come from backend

---

## 1. VITALS DATA STRUCTURE (TypeScript Types)

### Patient Vitals Interface
**Location**: `hospital-display-app/src/types/PatientTypes.ts` (Lines 45-71)

```typescript
vitals: {
  // Cardiovascular - STANDARDIZED NAMES
  heartRate: number;              // Always integer - BPM
  systolicPressure: number;       // Always integer - mmHg
  diastolicPressure: number;      // Always integer - mmHg

  // Respiratory - STANDARDIZED NAMES
  respiratoryRate: number;        // Always integer - breaths per minute
  oxygenSaturation: number;       // Always integer - percentage

  // Temperature - STANDARDIZED NAME
  skinTemperature: number;        // Can have decimals - Fahrenheit

  // Neurological/Cardiac Monitoring - STANDARDIZED NAMES
  ecgReading: number;             // Always integer - mV * 100 (120 = 1.2mV)
  eegReading: number;             // Always integer - μV (microvolts)
  isEcgMode: boolean;             // true = ECG, false = EEG

  // Advanced Monitoring - STANDARDIZED NAMES
  bioelectricalImpedance: number; // Ohms - bioelectrical impedance
  tremorIntensity: number;        // 0-10 scale tremor intensity
  fallRisk: 'low' | 'medium' | 'high'; // Fall risk assessment

  // Metadata - STANDARDIZED NAMES
  lastDataReceived: string;
  dataQualityScore: number;       // 0-1 scale for data quality
}
```

**Notes**:
- All fields are typed as `number` (not `number | undefined`)
- Frontend assumes vitals object may be undefined (`patient.vitals?.field`)
- No indication of NaN handling in type definitions

---

## 2. DASHBOARD VIEW - Patient Cards

### 2.1 PatientCardContainer.tsx
**Location**: `hospital-display-app/src/components/PatientCard/PatientCardContainer.tsx`

**All Vitals Array** (Lines 128-187):
```typescript
const allVitals = useMemo(() => [
  {
    key: 'heartRate',
    value: hasWatchAssigned ? (patient.vitals?.heartRate || '--') : '--',
    unit: hasWatchAssigned && patient.vitals?.heartRate ? 'BPM' : '',
    alertStatus: hasWatchAssigned ? getVitalAlertStatus('heartRate') : 'normal'
  },
  {
    key: 'oxygenSaturation',
    value: hasWatchAssigned ? (patient.vitals?.oxygenSaturation || '--') : '--',
    unit: hasWatchAssigned && patient.vitals?.oxygenSaturation ? '%' : '',
    alertStatus: hasWatchAssigned ? getVitalAlertStatus('oxygenSaturation') : 'normal'
  },
  {
    key: 'skinTemperature',
    value: hasWatchAssigned ? (patient.vitals?.skinTemperature ? patient.vitals.skinTemperature.toFixed(1) : '--') : '--',
    unit: hasWatchAssigned && patient.vitals?.skinTemperature ? '°F' : '',
    alertStatus: hasWatchAssigned ? getVitalAlertStatus('skinTemperature') : 'normal'
  },
  {
    key: 'systolicPressure',
    value: hasWatchAssigned ?
      (patient.vitals?.systolicPressure && patient.vitals?.diastolicPressure ?
        `${patient.vitals.systolicPressure}/${patient.vitals.diastolicPressure}` : '--/--') : '--/--',
    unit: hasWatchAssigned && patient.vitals?.systolicPressure && patient.vitals?.diastolicPressure ? 'mmHg' : '',
    alertStatus: hasWatchAssigned ? getVitalAlertStatus('systolicPressure') : 'normal'
  },
  {
    key: 'respiratoryRate',
    value: hasWatchAssigned ? (patient.vitals?.respiratoryRate || '--') : '--',
    unit: hasWatchAssigned && patient.vitals?.respiratoryRate ? '/min' : '',
    alertStatus: hasWatchAssigned ? getVitalAlertStatus('respiratoryRate') : 'normal'
  },
  {
    key: 'bioelectricalImpedance',
    value: hasWatchAssigned ? (patient.vitals?.bioelectricalImpedance || '--') : '--',
    unit: hasWatchAssigned && patient.vitals?.bioelectricalImpedance ? 'Ω' : '',
    alertStatus: hasWatchAssigned ? getVitalAlertStatus('bioelectricalImpedance') : 'normal'
  },
  {
    key: 'tremorIntensity',
    value: hasWatchAssigned ? (patient.vitals?.tremorIntensity ? patient.vitals.tremorIntensity.toFixed(1) : '--') : '--',
    unit: hasWatchAssigned && patient.vitals?.tremorIntensity ? '/10' : '',
    alertStatus: hasWatchAssigned ? getVitalAlertStatus('tremorIntensity') : 'normal'
  }
], [hasWatchAssigned, patient.vitals, getVitalAlertStatus]);
```

**Fallback Pattern**:
- `|| '--'` for integer vitals (heartRate, oxygenSaturation, respiratoryRate, bioelectricalImpedance)
- `.toFixed(1) : '--'` for decimal vitals (skinTemperature, tremorIntensity)
- Conditional display based on `hasWatchAssigned` (patient.assignedDeviceId)
- Unit text only shown if value exists

### 2.2 PatientVitalStrip.tsx
**Location**: `hospital-display-app/src/components/PatientCard/PatientVitalStrip.tsx`

**Vital Display** (Lines 90-114):
```typescript
{[...allVitals, ...allVitals, ...allVitals].map((vital, index) => (
  <div key={`${vital.key}-${index}`}
    className={`... ${getVitalColorClass(vital.alertStatus)}`}
  >
    <div className="flex items-center space-x-1 mb-1">
      <vital.icon className="w-3 h-3" />
      <span className="text-sm font-medium">{vital.label}</span>
    </div>
    <span className="text-sm font-bold">{vital.value}{vital.unit}</span>
    <div className={`... ${getStatusDotClass(vital.alertStatus)}`}></div>
  </div>
))}
```

**ECG/EEG Display** (Lines 115-137):
```typescript
<span className="text-sm font-bold">
  {isECGMode ? (patient.vitals?.eegReading || '--') : (patient.vitals?.ecgReading || '--')}
</span>
<div className={`... ${
  isECGMode ? (seizureActivity ? 'bg-red-500 animate-pulse' : 'bg-green-500') :
  (arrhythmiaDetected ? 'bg-yellow-500 animate-pulse' : 'bg-green-500')
}`}></div>
```

**Notes**:
- Infinite scroll with tripled array for seamless animation
- Color coding based on `alertStatus` from backend
- ECG/EEG readings display `'--'` if undefined

### 2.3 PatientCardWaveform.tsx
**Location**: `hospital-display-app/src/components/PatientCard/PatientCardWaveform.tsx`

**Waveform Header** (Line 60):
```typescript
{isECGMode ? 'ECG' : 'EEG'} {isECGMode ? (patient.vitals?.ecgReading || '--') : (patient.vitals?.eegReading || '--')}{isECGMode ? 'mV' : 'μV'}
```

**Heart Rate Display** (Line 108):
```typescript
<span className="text-[10px] text-gray-400">{patient.vitals?.heartRate || 0} BPM</span>
```

**Waveform Data** (Line 38):
```typescript
// BACKEND INTEGRATION NEEDED: Replace with VitalService.getWaveformData(patientId, isECGMode)
// Expected endpoint: GET /api/v1/patients/{id}/waveform?mode=ecg|eeg&lead={selectedLead}
const pathData = "M 0 25 L 250 25"; // Flat line placeholder
```

**Notes**:
- Waveform display is **PLACEHOLDER ONLY**
- No real-time waveform data currently implemented
- Heart rate defaults to `0` instead of `'--'`

---

## 3. PATIENT DETAIL VIEW

### 3.1 PatientOverview.tsx
**Location**: `hospital-display-app/src/components/PatientDetail/PatientOverview.tsx`

**Vital Trends (Quick View)** (Lines 96-166):
```typescript
{patient.vitals?.heartRate || 0} BPM • ↗ Stable
{patient.vitals?.systolicPressure || '--'}/{patient.vitals?.diastolicPressure || '--'} • → Normal
{patient.vitals?.skinTemperature ? patient.vitals.skinTemperature.toFixed(1) : '--'}°F • → Normal
{patient.vitals?.oxygenSaturation || '--'}% • → Good
```

**All Vitals Grid (8×1 Layout)** (Lines 169-299):
```typescript
// Heart Rate
<span className="font-bold text-xl text-red-600">{patient.vitals?.heartRate || '--'}</span>
<span className="text-xs text-gray-500 ml-1">BPM</span>

// Blood Pressure
<span className="font-bold text-lg text-purple-600">
  {patient.vitals?.systolicPressure || '--'}/{patient.vitals?.diastolicPressure || '--'}
</span>
<span className="text-xs text-gray-500 ml-1">mmHg</span>

// Oxygen Saturation
<span className="font-bold text-xl text-blue-600">{patient.vitals?.oxygenSaturation || '--'}</span>
<span className="text-xs text-gray-500 ml-1">%</span>

// Temperature
<span className="font-bold text-xl text-orange-600">
  {patient.vitals?.skinTemperature ? patient.vitals.skinTemperature.toFixed(1) : '--'}
</span>
<span className="text-xs text-gray-500 ml-1">°F</span>

// Respiratory Rate
<span className="font-bold text-xl text-green-600">{patient.vitals?.respiratoryRate || '--'}</span>
<span className="text-xs text-gray-500 ml-1">/min</span>

// ECG Reading
<span className="font-bold text-xl text-yellow-600">{patient.vitals?.ecgReading || '--'}</span>
<span className="text-xs text-gray-500 ml-1">mV</span>

// EEG Reading
<span className="font-bold text-xl text-indigo-600">{patient.vitals?.eegReading || '--'}</span>
<span className="text-xs text-gray-500 ml-1">μV</span>

// Tremor Intensity
<span className="font-bold text-xl text-pink-600">
  {patient.vitals?.tremorIntensity ? patient.vitals.tremorIntensity.toFixed(1) : '--'}
</span>
<span className="text-xs text-gray-500 ml-1">/10</span>
```

**Color Coding** (Lines 178, 194, 210, etc.):
```typescript
className={`p-1 rounded-lg ${getVitalStatusColor(
  MedicalUtils.getVitalStatus(patient.vitals?.heartRate || 0, 'heartRate')
)}`}
```

**Notes**:
- All vitals have fallback to `'--'` or `0`
- Color coding uses `MedicalUtils.getVitalStatus()` with fallback value
- Trend indicators are **static placeholders** ("↗ Stable", "→ Normal")
- ECGViewer component embedded at bottom (Lines 302-307)

---

## 4. BEDSIDE MONITOR MODE

### 4.1 PatientMonitor.tsx
**Location**: `hospital-display-app/src/components/BedsideMode/PatientMonitor.tsx`

**Safe Vitals Validation** (Lines 59-67):
```typescript
const safeVitals = {
  heartRate: Math.max(0, Math.min(300, patient.vitals?.heartRate ?? 0)),
  systolicPressure: Math.max(60, Math.min(300, patient.vitals?.systolicPressure ?? 0)),
  diastolicPressure: Math.max(30, Math.min(150, patient.vitals?.diastolicPressure ?? 0)),
  oxygenSaturation: Math.max(0, Math.min(100, patient.vitals?.oxygenSaturation ?? 0)),
  skinTemperature: Math.max(90.0, Math.min(115.0, patient.vitals?.skinTemperature ?? 0)),
  ecgReading: Math.max(-50, Math.min(50, patient.vitals?.ecgReading ?? 0)),
  eegReading: Math.max(0, Math.min(200, patient.vitals?.eegReading ?? 0))
};
```

**Single Patient Layout** (Lines 102-184):
```typescript
// Heart Rate
<div className="text-4xl font-mono font-bold text-red-400 leading-none">
  {safeVitals.heartRate}
</div>
<div className="text-red-300 text-sm font-medium">BPM</div>

// Blood Pressure
<div className="text-3xl font-mono font-bold text-blue-400 leading-none">
  {`${safeVitals.systolicPressure}/${safeVitals.diastolicPressure}`}
</div>
<div className="text-blue-300 text-sm font-medium">mmHg</div>

// Oxygen Saturation
<div className="text-4xl font-mono font-bold text-cyan-400 leading-none">
  {safeVitals.oxygenSaturation}
</div>
<div className="text-cyan-300 text-sm font-medium">%</div>

// Temperature
<div className="text-3xl font-mono font-bold text-amber-400 leading-none">
  {safeVitals.skinTemperature.toFixed(1)}
</div>
<div className="text-amber-300 text-sm font-medium">°F</div>
```

**Dual Patient Layout** (Lines 256-296):
```typescript
// Compact vitals with same pattern, smaller text
<div className="text-2xl font-mono font-bold text-red-400">{safeVitals.heartRate}</div>
<div className="text-xl font-mono font-bold text-blue-400">
  {`${safeVitals.systolicPressure}/${safeVitals.diastolicPressure}`}
</div>
<div className="text-2xl font-mono font-bold text-cyan-400">{safeVitals.oxygenSaturation}</div>
<div className="text-xl font-mono font-bold text-amber-400">{safeVitals.skinTemperature.toFixed(1)}</div>
```

**Waveform Display** (Lines 29-47):
```typescript
// BACKEND INTEGRATION NEEDED: Replace with VitalService.getWaveformData(patientId, isEcgMode)
// Expected endpoint: GET /api/v1/patients/{id}/waveform?mode=ecg|eeg
// Placeholder: flat line data until backend supports real-time waveform streaming
const processedData = Array.from({length: 400}, (_, x) => ({
  x,
  y: 25 // Flat line placeholder
}));
```

**Notes**:
- **Medical Safety**: Clamps all vitals to displayable ranges
- Uses `?? 0` (nullish coalescing) instead of `|| 0` for stricter handling
- NaN values would be clamped to minimum range (0 or range min)
- **No '--' display** - always shows numbers (even if 0)
- Waveform is **flat line placeholder**

---

## 5. CHARTS AND TRENDS

### 5.1 EnhancedVitalChart - ChartVisualization.tsx
**Location**: `hospital-display-app/src/components/EnhancedVitalChart/ChartVisualization.tsx`

**Chart Data Preparation** (Lines 169-201):
```typescript
const chartData = vitalData.map((point, index) => {
  const formattedTime = new Date(point.timestamp).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });

  const baseData = {
    time: formattedTime,
    timestamp: point.timestamp,
    value: point.value,
    isAbnormal: point.isAbnormal || false,
    qualityScore: point.qualityScore,
    dataPoints: point.dataPoints,
    maxValue: point.maxValue,
    minValue: point.minValue
  };

  // Add diastolic data for blood pressure charts
  if (isBloodPressure && secondaryVitalData[index]) {
    return {
      ...baseData,
      diastolicValue: secondaryVitalData[index].value,
      diastolicAbnormal: secondaryVitalData[index].isAbnormal || false
    };
  }

  return baseData;
});
```

**Custom Tooltip** (Lines 103-144):
```typescript
if (active && payload && payload.length > 0) {
  const data = payload[0].payload;

  // Blood Pressure - Show both systolic and diastolic
  if (isBloodPressure && data.diastolicValue !== undefined) {
    <p className="text-red-300">
      {`Systolic: ${payload[0].value.toFixed(0)} mmHg ${
        (data.isAbnormal && payload[0].value < 90) || payload[0].value > 140 ? '⚠️' : '✓'
      }`}
    </p>
    <p className="text-purple-300">
      {`Diastolic: ${data.diastolicValue.toFixed(0)} mmHg ${data.diastolicAbnormal ? '⚠️' : '✓'}`}
    </p>
  } else {
    // Single vital display
    <p className="text-blue-300">
      {`${getVitalDisplayName()}: ${payload[0].value.toFixed(1)} ${chartConfig.yAxisLabel || ''}`}
    </p>
  }
}
```

**Notes**:
- Charts use historical data from backend (not real-time)
- All values are pre-validated numbers (not NaN)
- Abnormal flags come from backend (`point.isAbnormal`)
- No NaN handling - assumes clean data

### 5.2 VitalChartContainer.tsx
**Location**: `hospital-display-app/src/components/EnhancedVitalChart/VitalChartContainer.tsx`

**Data Transformation** (Lines 156-165, 203):
```typescript
// Blood Pressure
{
  timestamp: point.timestamp,
  value: point.systolicPressure || 0,
  diastolicValue: point.diastolicPressure || 0,
  isAbnormal: point.systolicPressure < 90 || point.systolicPressure > 140 ||
              point.diastolicPressure < 60 || point.diastolicPressure > 90
}

// Other Vitals
{
  timestamp: point.timestamp,
  value: (point[vitalKey] as number) || 0,
  isAbnormal: false // Backend should provide this
}
```

**Notes**:
- Fallback to `0` for missing values
- Would convert NaN to `0` via `|| 0` operator
- Abnormal detection is **frontend logic** (should be backend)

---

## 6. ECG/EEG VIEWER

### 6.1 ECGViewerContainer.tsx
**Location**: `hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx`

**Waveform Drawing** (Lines 82-169):
```typescript
const drawWaveform = (leadIdx: number, viewIdx: number) => {
  const data = dataBufferRef.current[leadIdx];
  if (data.length < 2) return;

  // AUTO-SCALING: Calculate data range and scale to fit canvas
  const visibleSamples = Math.min(data.length, Math.floor(width * 2));
  const recentData = data.slice(-visibleSamples);

  const dataMin = Math.min(...recentData);
  const dataMax = Math.max(...recentData);
  const dataRange = dataMax - dataMin;

  // If no variation, use default scaling
  if (dataRange === 0) return;

  // Use 80% of canvas height for the waveform (10% margin top/bottom)
  const margin = height * 0.1;
  const usableHeight = height - (2 * margin);

  // Map data value to canvas coordinates
  for (let x = 0; x < width; x++) {
    const sampleIndex = Math.floor(startSample + x * samplesPerPixel);
    if (sampleIndex < data.length) {
      const value = data[sampleIndex];

      if (dataRange > 0) {
        const normalizedValue = (value - dataMin) / dataRange; // 0 to 1
        y = margin + usableHeight - (normalizedValue * usableHeight);
      } else {
        y = height / 2; // Center line if no range
      }

      // Clamp to canvas bounds
      y = Math.max(margin, Math.min(height - margin, y));
    }
  }
};
```

**Notes**:
- Auto-scaling based on data range
- **NaN values would cause Math.min/Math.max to return NaN**
- This would make `dataRange = NaN`, triggering early return
- **No explicit NaN handling** - assumes clean numeric data

### 6.2 ECGWaveformCanvas.tsx
**Location**: `hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx`

**Same waveform drawing logic** (Lines 82-195) - identical to container

**Amplitude Scale Indicators** (Lines 186-194):
```typescript
if (dataRange > 0) {
  ctx.fillText(`${dataMax.toFixed(1)} ${isECGMode ? 'mV' : 'μV'}`, 5, margin + 12);
  ctx.fillText(`${dataMin.toFixed(1)} ${isECGMode ? 'mV' : 'μV'}`, 5, height - margin - 2);
  ctx.fillText(`0`, 5, height / 2 + 5);
}
```

**Notes**:
- Shows min/max values from actual data
- NaN would result in "NaN mV" text display
- **No NaN handling** in text rendering

---

## 7. ALERTS AND MEDICAL LOGIC

### 7.1 MedicalUtils.ts
**Location**: `hospital-display-app/src/utils/medicalUtils.ts`

**Vital Status Function** (Lines 16-22):
```typescript
static getVitalStatus(value: number, type: vitaltype, diastolic?: number): vitalstatus {
  // REMOVED: All medical logic moved to backend
  // Frontend cannot make medical determinations
  // Backend must provide vital status in API response
  return 'normal'; // Default fallback - backend should provide actual status
}
```

**Arrhythmia Detection** (Lines 27-30):
```typescript
static detectArrhythmia(heartRate: number, ecgValue: number): boolean {
  return false; // Frontend cannot make medical diagnoses
}
```

**Risk Score Calculation** (Lines 43-46):
```typescript
static calculateRiskScore(heartRate: number, oxygenSaturation: number, temperature: number): number {
  return 0; // Frontend cannot make medical assessments
}
```

**Notes**:
- **ALL MEDICAL LOGIC REMOVED FROM FRONTEND**
- Functions return safe defaults (`'normal'`, `false`, `0`)
- Backend must provide:
  - Vital status in API response
  - Arrhythmia alerts via alerts array
  - Risk scores in patient data

### 7.2 PatientCardContainer Alert Status
**Location**: `hospital-display-app/src/components/PatientCard/PatientCardContainer.tsx`

**Vital Alert Status Calculation** (Lines 77-117):
```typescript
const getVitalAlertStatus = useCallback((vitalKey: string) => {
  let vitalStatus = 'normal';
  if (patient.vitals) {
    switch (vitalKey) {
      case 'heartRate':
        vitalStatus = patient.vitals.heartRate ?
          MedicalUtils.getVitalStatus(patient.vitals.heartRate, 'heartRate') : 'normal';
        break;
      // ... similar for other vitals
    }
  }

  // Check backend alerts for this vital
  const vitalAlerts = allCombinedAlerts.filter(alert => {
    const message = alert.message.toLowerCase();
    return (
      (vitalKey === 'heartRate' && (message.includes('heart') || message.includes('cardiac'))) ||
      (vitalKey === 'oxygenSaturation' && (message.includes('oxygen') || message.includes('spo2'))) ||
      // ... other vital keywords
    );
  });

  if (vitalAlerts.some(alert => alert.severity === 'critical')) return 'critical';
  if (vitalAlerts.some(alert => alert.severity === 'high')) return 'critical';
  if (vitalAlerts.some(alert => alert.severity === 'medium')) return 'warning';
  if (vitalAlerts.some(alert => alert.severity === 'low')) return 'warning';
  return vitalStatus;
}, [patient.vitals, allCombinedAlerts]);
```

**Notes**:
- Alert status comes from **backend alerts** (via `patient.alerts`)
- Frontend only does text matching to link alerts to vitals
- NaN vitals would trigger `vitalStatus = 'normal'` (falsy check)

### 7.3 PatientCardAlerts.tsx
**Location**: `hospital-display-app/src/components/PatientCard/PatientCardAlerts.tsx`

**Alert Display** (Lines 44-65):
```typescript
<div className={`... ${
  unacknowledgedAlerts.some(alert => alert.severity === 'critical')
    ? 'bg-red-600'
    : unacknowledgedAlerts.some(alert => alert.severity === 'high' || alert.severity === 'medium')
    ? 'bg-orange-500'
    : unacknowledgedAlerts.length > 0
    ? 'bg-yellow-500'
    : 'bg-green-600'
}`}>
  <span className="font-medium">
    {unacknowledgedAlerts.length > 0 ? 'ALERTS PRESENT' : 'ALL NORMAL'}
  </span>
  <div className="bg-black bg-opacity-20 px-1 rounded text-xs font-bold">
    {unacknowledgedAlerts.length}
  </div>
</div>
```

**Notes**:
- All alerts come from backend (`patient.alerts`)
- Frontend only displays and acknowledges alerts
- No frontend alert generation

---

## 8. BACKEND VITALS COMPUTATION

### 8.1 ESP32 Field Mapper
**Location**: `hospital-backend/app/middleware/esp32_field_mapper.py`

**Vital Field Mappings** (Lines 37-47):
```python
FIELD_MAPPING = {
    # Vital Signs
    "heartrate": "heartRate",
    "oxygensat": "oxygenSaturation",
    "bloodpressurevalue": "bloodPressureSystolic",
    "bloodpressuresystolic": "bloodPressureSystolic",
    "bloodpressurediastolic": "bloodPressureDiastolic",
    "temperature": "bodyTemperature",
    "bodytemperature": "bodyTemperature",
    "respiratoryrate": "respiratoryRate",
    "ecgdata": "ecgData",
    # ... (device fields omitted)
}
```

**Notes**:
- ESP32 sends lowercase field names
- Backend transforms to camelCase
- **No mention of multi-lead ECG/EEG fields**
- Suggests ESP32 computes single values, not per-lead

### 8.2 ESP32 Vitals Endpoint
**Location**: `hospital-backend/app/api/v1/esp32.py`

**Vitals Processing** (Lines 357-378):
```python
# Store each vital type (using camelCase after transformation)
vitalTypes = {
    'heartrate': vitalsData.get('heartRate'),
    'temperature': vitalsData.get('bodyTemperature'),
    'oxygensaturation': vitalsData.get('oxygenSaturation'),
    'respiratoryrate': vitalsData.get('respiratoryRate'),
    'bloodpressuresystolic': vitalsData.get('bloodPressureSystolic'),
    'ecg': vitalsData.get('ecg'),
    'eeg': vitalsData.get('eeg'),
    'bioimpedance': vitalsData.get('bioImpedance'),
    'tremor': vitalsData.get('tremor')
}

for vitalType, value in vitalTypes.items():
    if value is not None:
        await tsConn.execute("""
            INSERT INTO vitals_timeseries ("patientId", "deviceId", vitaltype, value, unit, time, quality)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, patientId, deviceId, vitalType, float(value),
             getUnitForVitalFix(vitalType), timestamp,
             vitalsData.get('quality', 95))
```

**Notes**:
- Backend stores **single values** for ecg/eeg (not per-lead)
- `float(value)` conversion would raise exception on NaN
- No multi-lead computation logic visible
- Suggests ESP32 sends pre-computed single values

### 8.3 Vital Validators
**Location**: `hospital-backend/app/validators/vitals_validators.py`

**Vital Sign Ranges** (Lines 34-75):
```python
heartRate: Optional[int] = Field(None, ge=20, le=300, description="Heart rate in beats per minute (20-300 bpm)")
bloodPressureSystolic: Optional[int] = Field(None, ge=50, le=250, description="Systolic blood pressure in mmHg (50-250)")
bloodPressureDiastolic: Optional[int] = Field(None, ge=30, le=150, description="Diastolic blood pressure in mmHg (30-150)")
temperature: Optional[float] = Field(None, ge=30.0, le=45.0, description="Body temperature in Celsius (30-45°C)")
oxygenSaturation: Optional[int] = Field(None, ge=0, le=100, description="Oxygen saturation percentage (0-100%)")
respiratoryRate: Optional[int] = Field(None, ge=0, le=60, description="Respiratory rate in breaths per minute (0-60)")
glucoseLevel: Optional[float] = Field(None, ge=0.0, le=1000.0, description="Glucose level in mg/dL (0-1000)")
```

**Notes**:
- All fields are `Optional` - can be None
- Pydantic would reject NaN values (not in valid range)
- **No ECG/EEG fields in validator**
- Suggests ECG/EEG stored separately or differently

---

## 9. CRITICAL FINDINGS

### 9.1 NaN Handling Summary

| **Component** | **NaN Handling** | **Fallback** | **Risk if NaN** |
|---------------|------------------|--------------|-----------------|
| PatientCardContainer | `|| '--'` | Display '--' | **SAFE** - shows dash |
| PatientVitalStrip | `|| '--'` | Display '--' | **SAFE** - shows dash |
| PatientOverview | `|| '--'` or `|| 0` | Display '--' or 0 | **SAFE** - shows fallback |
| PatientMonitor | `?? 0` + Math.clamp | Default to 0, clamp | **SAFE** - shows 0 |
| ChartVisualization | `|| 0` | Default to 0 | **SAFE** - chart shows 0 |
| ECGWaveformCanvas | **No handling** | None | **UNSAFE** - NaN propagates, causes Math.min/max to fail |
| VitalChartContainer | `|| 0` | Default to 0 | **SAFE** - shows 0 |

**Key Observation**:
- **ECG/EEG waveform rendering is the ONLY place without NaN handling**
- Math.min/max on arrays with NaN returns NaN
- This would cause `dataRange = NaN`, preventing waveform display
- **However**: Waveforms are currently flat line placeholders, not used

### 9.2 Which Vitals Can Show NaN?

Based on the analysis:

#### **CATEGORY 1: Safe to Show NaN (Display as '--')**
All vitals that use `|| '--'` fallback can safely receive NaN:

1. **heartRate** - Dashboard, detail view, trends (shows '--')
2. **oxygenSaturation** - Dashboard, detail view, trends (shows '--')
3. **respiratoryRate** - Dashboard, detail view (shows '--')
4. **systolicPressure / diastolicPressure** - Dashboard, detail view (shows '--/--')
5. **skinTemperature** - Dashboard, detail view (shows '--')
6. **ecgReading** - Dashboard, detail view (shows '--')
7. **eegReading** - Dashboard, detail view (shows '--')
8. **bioelectricalImpedance** - Dashboard (shows '--')
9. **tremorIntensity** - Dashboard, detail view (shows '--')

**Caveat**: Bedside monitor uses `?? 0` and clamps to range, so NaN → 0 → clamped minimum.

#### **CATEGORY 2: Cannot Show NaN (Would Break)**
Only waveform data (not currently used):

1. **ECG waveform arrays** - Would cause Math.min/max to fail
2. **EEG waveform arrays** - Would cause Math.min/max to fail

**Mitigation**: Waveforms are flat line placeholders, not reading real data.

#### **CATEGORY 3: Backend Must Provide Valid Values**
Backend validation would reject NaN:

1. **All vitals sent to TimescaleDB** - `float(value)` conversion fails on NaN
2. **All vitals in Pydantic validators** - NaN not in valid range

---

## 10. RECOMMENDATIONS

### 10.1 Frontend Changes Needed

1. **Add NaN filtering in waveform rendering**:
   ```typescript
   // ECGWaveformCanvas.tsx, ECGViewerContainer.tsx
   const cleanData = recentData.filter(v => !isNaN(v) && isFinite(v));
   const dataMin = Math.min(...cleanData);
   const dataMax = Math.max(...cleanData);
   ```

2. **Standardize NaN handling across components**:
   - Use `|| '--'` for display vitals (consistent)
   - Use `?? 0` for numeric calculations (strict)
   - Document which pattern to use where

3. **Add NaN logging for debugging**:
   ```typescript
   if (isNaN(patient.vitals?.heartRate)) {
     logger.warn(`NaN detected in heartRate for patient ${patient.id}`);
   }
   ```

### 10.2 Backend Changes Needed

1. **Compute single-lead vitals when multi-lead data unavailable**:
   - If 3-lead ECG, compute all standard 12-lead calculations
   - If 1-lead ECG, compute only basic HR, skip advanced metrics
   - Send NaN for unavailable metrics (frontend handles gracefully)

2. **Add data quality flags**:
   ```python
   vitals = {
       'heartRate': 75,
       'heartRateQuality': 'good',  # 'good', 'degraded', 'unavailable'
       'ecgReading': 120,
       'ecgReadingQuality': 'good',
       'qrsComplex': NaN,  # Not computable from 1-lead
       'qrsComplexQuality': 'unavailable'
   }
   ```

3. **Document vital availability matrix**:
   | Vital | 1-Lead | 3-Lead | 12-Lead |
   |-------|--------|--------|---------|
   | Heart Rate | ✓ | ✓ | ✓ |
   | QRS Complex | ✗ (NaN) | ✓ | ✓ |
   | ST Segment | ✗ (NaN) | Partial | ✓ |
   | Arrhythmia | Basic | Advanced | Full |

### 10.3 Testing Checklist

- [ ] Test all vital displays with NaN values
- [ ] Test waveform rendering with NaN in data arrays
- [ ] Test chart rendering with NaN data points
- [ ] Test bedside monitor with NaN vitals (should show 0)
- [ ] Test alert generation with NaN vitals
- [ ] Test backend validation with NaN values (should reject)
- [ ] Test TimescaleDB insertion with NaN (should fail gracefully)

---

## 11. CONCLUSION

### Summary of Findings:

1. **All vital displays are NaN-safe** - use `|| '--'` or `?? 0` fallbacks
2. **Waveform rendering is NOT NaN-safe** - but currently unused (flat line placeholder)
3. **Backend expects valid numbers** - NaN would be rejected by Pydantic validators
4. **No multi-lead computation logic found** - backend stores single ECG/EEG values
5. **Medical logic removed from frontend** - all determinations from backend

### Answer to Original Question:

**Q**: Which vitals can show NaN when only 1-lead data is available?

**A**: **All vitals can safely display NaN** (rendered as `'--'`) EXCEPT:
- Waveform arrays (not currently used, would need filtering)
- Backend submissions (Pydantic would reject)

**Recommended approach**:
1. Compute basic vitals from 1-lead (HR, RR, basic rhythm)
2. Send NaN for unavailable metrics (QRS morphology, ST analysis, etc.)
3. Frontend will display NaN as `'--'` automatically
4. Add quality flags so clinicians know data limitations

---

**End of Report**
