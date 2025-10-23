# Vitals Data Flow - Complete Analysis

## Summary: ESP32 → Backend → Frontend Data Flow

### Current Status: ❌ BROKEN - Field Name Mismatches

---

## Data Flow Chain

```
ESP32 Watch → MQTT → Backend MQTT Service → TimescaleDB + WebSocket → Frontend
```

---

## ESP32 Firmware (esp32_hospital_watch_complete.ino:843-851)

### What ESP32 Sends via MQTT:
```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "patient-uuid",
  "timestamp": 12345678,
  "heartRate": 75,
  "temperature": 98.6,
  "oxygenSat": 98,
  "batteryLevel": 85,
  "quality": 95
}
```

**Fields Sent**: 3 vitals only
- ✅ `heartRate` (BPM)
- ✅ `temperature` (Fahrenheit)
- ✅ `oxygenSat` (percentage)

**Issues**:
- ❌ Sends flat structure, NOT nested under `vitals` key
- ❌ Uses `oxygenSat` instead of `oxygenSaturation`
- ❌ Uses `temperature` instead of `skinTemperature`
- ❌ `timestamp` is millis(), not ISO format
- ❌ `quality` is 0-100 scale, not 0-1

---

## Backend MQTT Service (mqtt_service.py:229-271)

### What Backend Expects (line 254):
```python
vitalsData = payload.get('vitals', {})
```

**❌ CRITICAL BUG**: Backend expects vitals under **nested `vitals` key**, but ESP32 sends **flat structure**!

### Field Mappings (lines 321-331):
```python
vitalMappings = {
    'heartrate': ('heartrate', 'bpm'),
    'temperature': ('temperature', 'F'),
    'oxygensat': ('oxygensaturation', '%'),
    'respiratoryrate': ('respiratoryrate', '/min'),
    'bloodpressurevalue': ('bloodpressuresystolic', 'mmHg'),
    'ecg': ('ecg', 'mV'),
    'eeg': ('eeg', 'μV'),
    'bioimpedance': ('bioimpedance', 'Ω'),
    'tremor': ('tremor', 'scale')
}
```

**Backend Expects**:
- `heartrate` (lowercase, no camelCase!)
- `oxygensat` (lowercase, no camelCase!)
- `temperature` (lowercase)

### Conversion to Frontend Format (lines 344-359):
```python
def _convertMqttToFrontendFormat(self, mqttVitals: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'heartrate': mqttVitals.get('heartrate'),
        'oxygensat': mqttVitals.get('oxygensat'),
        'temperature': mqttVitals.get('temperature'),
        # ... other fields ...
    }
```

**Still lowercase!** Not matching frontend expectations!

---

## Frontend Requirements (PatientTypes.ts:45-71)

### What Frontend Expects:
```typescript
vitals: {
  heartRate: number;  // camelCase!
  oxygenSaturation: number;  // Full name, camelCase!
  skinTemperature: number;  // "skin" prefix!
  systolicPressure: number;
  diastolicPressure: number;
  respiratoryRate: number;
  ecgReading: number;
  eegReading: number;
  isEcgMode: boolean;
  bioelectricalImpedance: number;
  tremorIntensity: number;
  fallRisk: 'low' | 'medium' | 'high';
  lastDataReceived: string;
  dataQualityScore: number;
}
```

---

## Field Name Mapping Table

| ESP32 Sends | Backend Expects | Backend Converts To | Frontend Expects | Status |
|-------------|-----------------|---------------------|------------------|--------|
| `heartRate` | `heartrate` | `heartrate` | `heartRate` | ❌ Case mismatch |
| `temperature` | `temperature` | `temperature` | `skinTemperature` | ❌ Name mismatch |
| `oxygenSat` | `oxygensat` | `oxygensat` | `oxygenSaturation` | ❌ Both wrong |
| `quality` | N/A | N/A | `dataQualityScore` (0-1) | ❌ Wrong scale |
| `timestamp` (millis) | N/A | N/A | `lastDataReceived` (ISO) | ❌ Wrong format |

---

## Critical Issues Identified

### Issue #1: Nested vs Flat Structure
**ESP32 sends**:
```json
{
  "deviceId": "...",
  "heartRate": 75,
  "temperature": 98.6
}
```

**Backend expects**:
```json
{
  "deviceId": "...",
  "vitals": {
    "heartrate": 75,
    "temperature": 98.6
  }
}
```

### Issue #2: camelCase vs lowercase
- ESP32: `heartRate` (camelCase)
- Backend: `heartrate` (lowercase)
- Frontend: `heartRate` (camelCase)

### Issue #3: Field Name Mismatches
- ESP32: `temperature` → Frontend: `skinTemperature`
- ESP32: `oxygenSat` → Backend: `oxygensat` → Frontend: `oxygenSaturation`

### Issue #4: Missing 9 Vital Signs
ESP32 only sends 3 vitals. Frontend expects 12:
- ❌ Blood pressure (systolic/diastolic)
- ❌ Respiratory rate
- ❌ ECG/EEG readings
- ❌ Bioelectrical impedance
- ❌ Tremor intensity
- ❌ Fall risk

---

## Root Cause

**The entire vitals data flow is broken due to**:
1. Backend expects nested structure, ESP32 sends flat
2. Backend uses lowercase field names, frontend/ESP32 use camelCase
3. Field name mismatches (temperature vs skinTemperature)
4. ESP32 only sends 3 of 12 required vitals

**Result**: Vitals are NOT being stored in TimescaleDB or displayed on frontend!

---

## Fix Options

### Option A: Fix ESP32 to Match Backend (Recommended)
**Change ESP32 firmware to send**:
```json
{
  "deviceId": "ESP32_WATCH_003",
  "patientId": "patient-uuid",
  "timestamp": "2025-10-15T04:30:00Z",
  "vitals": {
    "heartrate": 75,
    "temperature": 98.6,
    "oxygensat": 98
  },
  "batteryLevel": 85,
  "quality": 0.95
}
```

### Option B: Fix Backend to Match ESP32
**Change backend MQTT service** to:
1. Accept flat structure (lines 254)
2. Convert camelCase to lowercase
3. Map field names properly

### Option C: Add Backend Middleware
Create a **field mapper middleware** to transform ESP32 data format to backend format.

---

## Recommended Solution

**Hybrid Approach**:

1. **ESP32 Changes** (minimal):
   - Keep camelCase (easier to read)
   - Wrap vitals in nested object
   - Add missing vital signs (blood pressure, respiratory rate, etc.)
   - Use ISO timestamp

2. **Backend Changes** (add middleware):
   - Create `esp32_vitals_transformer.py` to convert camelCase → database format
   - Handle both flat and nested structures for backward compatibility
   - Map `temperature` → `skinTemperature`, `oxygenSat` → `oxygenSaturation`

3. **Frontend** (no changes needed):
   - Already has correct field names and types

---

## Next Steps

1. **Verify current state** - Test if ANY vitals are reaching the backend
2. **Check TimescaleDB** - Query `vitals_timeseries` table to see if data exists
3. **Check frontend** - Are vitals displaying at all on dashboard?
4. **Implement fix** - Based on findings, apply Option A, B, or C

**DO NOT modify anything until we verify the current state!**
