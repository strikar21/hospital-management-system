# Blood Pressure Data Missing - Root Cause Analysis

**Date**: 2025-11-05
**Investigation**: Complete data flow trace from ESP32 → MQTT → Backend → Database → Frontend
**Status**: ❌ CRITICAL - BP data completely absent from system

---

## Summary

Blood Pressure (BP) charts cannot work because BP data is **never transmitted** by ESP32 devices. While the PhysiologicalSimulator generates realistic BP values, the firmware never reads or sends them via MQTT.

---

## Complete Data Flow Analysis

### 1. ESP32 Firmware - ❌ DATA NOT SENT

**File**: [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:1913-1965](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1913-L1965)

**Current sendVitals() Payload**:
```cpp
doc["heartRate"] = (int)heartRate;
doc["skinTemperature"] = tempCelsius;
doc["oxygenSaturation"] = (int)oxygenSat;
doc["respiratoryRate"] = (int)respiratoryRate;
doc["batteryLevel"] = batteryLevel;
doc["signalQuality"] = quality / 100.0;
// ❌ MISSING: bloodPressureSystolic and bloodPressureDiastolic
```

**Simulator Has BP Functions** (but they're never called):
- `simulator.getBloodPressureSystolic()` - Returns 60-200 mmHg
- `simulator.getBloodPressureDiastolic()` - Returns 40-130 mmHg

**BP Values by Physiological State**:
- RESTING: 115/75 mmHg (±5/±3)
- LIGHT_ACTIVITY: 130/80 mmHg (±5/±3)
- EXERCISE: 155/85 mmHg (±10/±3)
- SLEEP: 105/65 mmHg (±3/±3)

**Finding**: ESP32 generates realistic BP data but never transmits it.

---

### 2. MQTT Broker - ⚠️ NOT APPLICABLE

MQTT broker would pass through BP data if ESP32 sent it, but since ESP32 doesn't send BP data, this stage is not relevant.

---

### 3. Backend MQTT Service - ✅ READY TO RECEIVE

**File**: [hospital-backend/app/services/mqtt_service.py:1224-1225](hospital-backend/app/services/mqtt_service.py#L1224-L1225)

**Code**:
```python
# Blood pressure - frontend field names
'systolicPressure': vitalsMsg.bloodPressureSystolic,
'diastolicPressure': vitalsMsg.bloodPressureDiastolic,
```

**Finding**: Backend IS expecting BP data and would map it correctly if received.

---

### 4. Pydantic Model - ✅ READY TO VALIDATE

**File**: [hospital-backend/app/models/neural_vitals.py:243-244](hospital-backend/app/models/neural_vitals.py#L243-L244)

**Schema**:
```python
bloodPressureSystolic: Optional[int] = Field(None, ge=60, le=200, description="Systolic blood pressure in mmHg")
bloodPressureDiastolic: Optional[int] = Field(None, ge=40, le=130, description="Diastolic blood pressure in mmHg")
```

**Validation Rules**:
- Systolic: 60-200 mmHg (matches ESP32 simulator range)
- Diastolic: 40-130 mmHg (matches ESP32 simulator range)
- Both fields: Optional (allows null values)

**Finding**: Backend model is correctly defined with proper validation.

---

### 5. TimescaleDB Schema - ❌ COLUMNS MISSING

**Database**: hospitaltimescale
**Table**: vitals_realtime

**Current Columns**:
```
time: timestamp with time zone
patientId: uuid
deviceId: character varying
mode: character varying
heartRate: integer
respiratoryRate: integer
skinTemperature: numeric
oxygenSaturation: integer
batteryLevel: integer
signalQuality: numeric
rrInterval: integer
qrsDuration: integer
qtInterval: integer
axis: integer
rhythm: character varying
stSegment: character varying
alphaPower: numeric
betaPower: numeric
thetaPower: numeric
deltaPower: numeric
gammaPower: numeric
dominantFrequency: numeric
seizureActivity: boolean
quality: jsonb
sequence: integer
metadata: jsonb
```

**Missing Columns**:
- ❌ systolicPressure
- ❌ diastolicPressure

**Finding**: Database schema does not have BP columns.

---

### 6. Frontend Charts - ⚠️ CONFIGURED BUT NO DATA

**File**: [hospital-display-app/src/components/EnhancedVitalChart/VitalChartContainer.tsx](hospital-display-app/src/components/EnhancedVitalChart/VitalChartContainer.tsx)

**Chart Configuration**:
```typescript
{
  type: 'bloodPressure',
  name: 'Blood Pressure',
  unit: 'mmHg',
  color: '#ef4444',
  normalRange: { min: 90, max: 120 } // Systolic
}
```

**Finding**: Frontend has BP chart component ready, but no data to display.

---

## Root Cause: ESP32 Firmware Missing BP Transmission

The PhysiologicalSimulator generates BP data, but the `sendVitals()` function in ESP32 firmware never calls the getter methods or includes BP fields in the MQTT payload.

**Code Location**: [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:1913](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1913)

---

## Impact Assessment

### P0 - Critical Issues
1. ❌ **BP charts completely non-functional** - No data to display
2. ❌ **BP alerts cannot trigger** - Backend has no BP data to analyze
3. ❌ **Incomplete patient monitoring** - Missing vital cardiovascular metric

### Clinical Impact
- **Hypertension/Hypotension undetected** - Cannot monitor blood pressure trends
- **Cardiovascular risk assessment incomplete** - BP is critical for cardiac patients
- **Emergency alerts delayed** - Cannot trigger BP-based alerts (hypertensive crisis, shock)

---

## Fix Plan

### Option A: Add BP to ESP32 Firmware (RECOMMENDED)
**Pros**:
- Hardware simulator already generates realistic BP data
- Backend and Pydantic models already support BP
- Frontend charts already configured
- Minimal backend changes needed

**Cons**:
- Requires ESP32 firmware update and re-flashing
- Need to add database migration for new columns

**Effort**: Medium (2-3 hours)

**Steps**:
1. ✅ Add BP fields to ESP32 `sendVitals()` function
2. ✅ Flash ESP32 with updated firmware
3. ✅ Create database migration to add systolicPressure and diastolicPressure columns
4. ✅ Update backend INSERT query to include BP fields
5. ✅ Test BP data flow end-to-end
6. ✅ Verify BP charts render correctly

---

### Option B: Remove BP Charts from Frontend
**Pros**:
- Quick fix (no hardware/backend changes)
- Aligns UI with actual capabilities

**Cons**:
- Removes important clinical feature
- Does not fix underlying data gap

**Effort**: Low (30 minutes)

**Not Recommended**: BP is a critical vital sign for hospital monitoring.

---

## Recommended Action

**Implement Option A**: Add BP transmission to ESP32 firmware

This is the proper fix that completes the monitoring system. The infrastructure is already 90% ready - we just need to connect the dots between ESP32 simulator and MQTT transmission.

---

## Technical Details for Implementation

### ESP32 Firmware Change Required

**File**: esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino
**Function**: sendVitals() at line 1913

**Add after line 1934**:
```cpp
// Blood Pressure (add after respiratoryRate)
doc["bloodPressureSystolic"] = simulator.getBloodPressureSystolic();
doc["bloodPressureDiastolic"] = simulator.getBloodPressureDiastolic();
```

### Database Migration Required

**Create**: hospital-backend/migrations/XXX_add_blood_pressure_columns.sql

```sql
-- Add blood pressure columns to vitals_realtime table
ALTER TABLE vitals_realtime
ADD COLUMN IF NOT EXISTS "systolicPressure" INTEGER,
ADD COLUMN IF NOT EXISTS "diastolicPressure" INTEGER;

-- Add constraints
ALTER TABLE vitals_realtime
ADD CONSTRAINT vitals_systolic_range CHECK ("systolicPressure" BETWEEN 60 AND 200),
ADD CONSTRAINT vitals_diastolic_range CHECK ("diastolicPressure" BETWEEN 40 AND 130);

-- Create index for BP queries
CREATE INDEX IF NOT EXISTS idx_vitals_blood_pressure
ON vitals_realtime ("patientId", "systolicPressure", "diastolicPressure");
```

### Backend INSERT Query Update

**File**: hospital-backend/app/services/mqtt_service.py
**Function**: handle_vitals_message

Current INSERT query needs to add systolicPressure and diastolicPressure to column list (backend code should automatically handle this via the Pydantic model mapping).

---

## Testing Checklist

After implementation:
1. ✅ Flash ESP32 with updated firmware
2. ✅ Verify MQTT payload includes bloodPressureSystolic and bloodPressureDiastolic
3. ✅ Check backend logs confirm BP data received
4. ✅ Query TimescaleDB to verify BP values stored
5. ✅ Open frontend BP chart and verify data displays
6. ✅ Test all 6 timeframes (1min, 5min, 15min, 30min, 1hr, 4hr)
7. ✅ Verify BP alerts trigger correctly for abnormal values
8. ✅ Test dual-line chart rendering (systolic + diastolic on same graph)

---

## Current Firmware Version

**ESP32**: v5.2.8 (currently flashed on device)
**Code Ready**: v5.2.13 (committed but not flashed)

BP feature can be added to v5.2.8 or v5.2.14 (next version).

---

## References

- ESP32 PhysiologicalSimulator: [esp32_hospital_watch_complete/PhysiologicalSimulator.cpp:728-734](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L728-L734)
- Backend MQTT Service: [hospital-backend/app/services/mqtt_service.py:1224-1225](hospital-backend/app/services/mqtt_service.py#L1224-L1225)
- Pydantic Model: [hospital-backend/app/models/neural_vitals.py:243-244](hospital-backend/app/models/neural_vitals.py#L243-L244)
- Frontend Chart: [hospital-display-app/src/components/EnhancedVitalChart/VitalChartContainer.tsx](hospital-display-app/src/components/EnhancedVitalChart/VitalChartContainer.tsx)
