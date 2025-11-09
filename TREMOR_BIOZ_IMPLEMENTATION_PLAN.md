# Tremor and Bioimpedance Implementation Plan

**Date:** 2025-11-06
**Status:** Planning - Awaiting user approval

---

## Current State Analysis

### ✅ Already Exists:
1. **PhysiologicalSimulator** - Has getter methods:
   - `float getTremorIntensity()` - Returns 0.0-10.0 scale
   - `float getBioimpedance()` - Returns Ohms (200-1000 range)

2. **Backend Pydantic Model** - Already supports these fields:
   ```python
   # File: hospital-backend/app/models/neural_vitals.py (lines 249-250)
   bioimpedance: Optional[float] = Field(None, ge=200.0, le=1000.0, description="Bioelectrical impedance in Ohms")
   tremor: Optional[float] = Field(None, ge=0.0, le=10.0, description="Tremor intensity (0-10 scale)")
   ```

### ❌ Missing:
1. **ESP32 Firmware** - NOT reading or transmitting tremor/bioz data
2. **Database Schema** - NO columns for tremor/bioimpedance in vitals_realtime table
3. **Backend INSERT Query** - Does NOT include tremor/bioimpedance columns

---

## Implementation Steps

### Step 1: Database Schema Update ⏸️

**Add columns to TimescaleDB `vitals_realtime` table:**

```sql
-- Add tremor and bioimpedance columns
ALTER TABLE vitals_realtime
ADD COLUMN IF NOT EXISTS tremor NUMERIC(4,2),
ADD COLUMN IF NOT EXISTS bioimpedance NUMERIC(6,2);

-- Add constraints
ALTER TABLE vitals_realtime
ADD CONSTRAINT vitals_tremor_range CHECK (tremor BETWEEN 0.0 AND 10.0),
ADD CONSTRAINT vitals_bioimpedance_range CHECK (bioimpedance BETWEEN 200.0 AND 1000.0);

-- Add index for tremor queries (high tremor = fall risk)
CREATE INDEX IF NOT EXISTS idx_vitals_tremor
ON vitals_realtime ("patientId", tremor)
WHERE tremor > 5.0;

-- Add index for bioimpedance queries (fluid retention monitoring)
CREATE INDEX IF NOT EXISTS idx_vitals_bioimpedance
ON vitals_realtime ("patientId", bioimpedance);

-- Verify columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'vitals_realtime'
  AND column_name IN ('tremor', 'bioimpedance')
ORDER BY column_name;
```

**Expected Result:**
```
  column_name   | data_type | is_nullable
----------------+-----------+-------------
 bioimpedance   | numeric   | YES
 tremor         | numeric   | YES
```

---

### Step 2: ESP32 Firmware Updates ⏸️

**File:** `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`

**Change 1 - Add global variables (after line 216):**
```cpp
float tremor = 0;            // ✅ Read from simulator.getTremorIntensity()
float bioimpedance = 0;      // ✅ Read from simulator.getBioimpedance()
```

**Change 2 - Read from simulator in loop() (after line 1137):**
```cpp
bloodPressureSystolic = simulator.getBloodPressureSystolic();
bloodPressureDiastolic = simulator.getBloodPressureDiastolic();
tremor = simulator.getTremorIntensity();
bioimpedance = simulator.getBioimpedance();
```

**Change 3 - Transmit via MQTT in sendVitals() (after line 1941):**
```cpp
doc["bloodPressureSystolic"] = bloodPressureSystolic;
doc["bloodPressureDiastolic"] = bloodPressureDiastolic;
doc["tremor"] = tremor;
doc["bioimpedance"] = (int)bioimpedance;
```

**Change 4 - Update Serial debug output (optional, line ~1965):**
```cpp
Serial.println("📊 Vitals: Mode=" + String(isECGMode ? "ECG" : "EEG") +
               ", HR=" + String((int)heartRate) +
               ", BP=" + String(bloodPressureSystolic) + "/" + String(bloodPressureDiastolic) +
               ", Tremor=" + String(tremor, 1) +
               ", BioZ=" + String((int)bioimpedance) + "Ω" +
               ", Temp=" + String(tempCelsius, 1) + "°C" +
               ", SpO2=" + String(oxygenSat) + "%" +
               ", RR=" + String(respiratoryRate));
```

**Change 5 - Update version to v5.2.15:**
```cpp
// Line 3:
* Version: 5.2.15

// Add to features list (line ~35):
* - ✅ v5.2.15: FEATURE - Tremor and bioimpedance monitoring

// Add to detailed changelog (after v5.2.14 entries):
* ✅ v5.2.15: FEATURE - Tremor and bioimpedance monitoring
* ✅ v5.2.15: Added tremor and bioimpedance global variables
* ✅ v5.2.15: Read tremor/bioz from PhysiologicalSimulator every 1s
* ✅ v5.2.15: Transmit tremor/bioz via MQTT in vitals message
* ✅ v5.2.15: Updated serial debug output to show tremor and bioimpedance
* ✅ v5.2.15: Result: Backend receives and stores tremor/bioz data for fall risk and fluid monitoring
```

---

### Step 3: Backend MQTT Service Update ⏸️

**File:** `hospital-backend/app/services/mqtt_service.py`

**Update INSERT query in `_storeVitalsRealtime()` function (line 1162):**

**Current columns (line 1163-1171):**
```python
INSERT INTO vitals_realtime (
    time, "patientId", "deviceId", mode,
    "heartRate", "respiratoryRate", "skinTemperature",
    "oxygenSaturation", "batteryLevel", "signalQuality",
    "systolicPressure", "diastolicPressure",  # ← Added in v5.2.14
    "rrInterval", "qrsDuration", ...
```

**Updated columns (add tremor and bioimpedance after diastolicPressure):**
```python
INSERT INTO vitals_realtime (
    time, "patientId", "deviceId", mode,
    "heartRate", "respiratoryRate", "skinTemperature",
    "oxygenSaturation", "batteryLevel", "signalQuality",
    "systolicPressure", "diastolicPressure",
    tremor, bioimpedance,  # ← NEW: Add these columns
    "rrInterval", "qrsDuration", ...
) VALUES (
    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, ...  # ← Update parameter numbers
```

**Update parameter values (after line 1180):**
```python
vitalsMsg.timestamp, vitalsMsg.patientId, vitalsMsg.deviceId, vitalsMsg.mode,
vitalsMsg.heartRate, vitalsMsg.respiratoryRate, vitalsMsg.skinTemperature,
vitalsMsg.oxygenSaturation, vitalsMsg.batteryLevel, vitalsMsg.signalQuality,
vitalsMsg.bloodPressureSystolic, vitalsMsg.bloodPressureDiastolic,
vitalsMsg.tremor, vitalsMsg.bioimpedance,  # ← NEW: Add these parameters
vitalsMsg.ecgAnalysis.rrInterval if vitalsMsg.ecgAnalysis else None,
...
```

**Verify field mapping (should already exist around line 1224):**
```python
# Advanced vitals - frontend field names
'tremor': vitalsMsg.tremor,
'bioimpedance': vitalsMsg.bioimpedance,
```

---

### Step 4: Frontend Updates (Future) ⏸️

**Create charts/displays for:**
1. **Tremor Monitoring** - Line chart showing tremor intensity over time
   - Alert when tremor > 7.0 (high fall risk)
   - Useful for Parkinson's patients, post-stroke monitoring

2. **Bioimpedance Monitoring** - Line chart showing fluid retention
   - Alert when bioimpedance < 300 Ω (fluid overload)
   - Useful for heart failure patients, dialysis monitoring

**API Endpoints (should work automatically):**
```typescript
GET /api/v2/patients/{patientId}/vitals/timeseries?vitalType=tremor&timeRange=6h
GET /api/v2/patients/{patientId}/vitals/timeseries?vitalType=bioimpedance&timeRange=24h
```

---

## Expected Values by Physiological State

### Tremor Intensity (0-10 scale)

| Physiological State | Tremor Range | Clinical Significance |
|---------------------|--------------|----------------------|
| **Rest** | 0.0-1.0 | Normal, minimal tremor |
| **Light Activity** | 1.0-2.5 | Physiological tremor |
| **Exercise** | 2.0-4.0 | Exertion tremor (normal) |
| **Stress** | 3.0-5.0 | Elevated tremor |
| **Sleep** | 0.0-0.5 | Minimal to none |
| **Fever** | 2.0-4.0 | Elevated due to fever |
| **Hypoxia** | 4.0-7.0 | Significant tremor |
| **Seizure** | 7.0-10.0 | **CRITICAL** - Violent shaking |
| **Arrhythmia** | 1.5-3.0 | Slight elevation |

**Alert Thresholds:**
- **Medium Alert:** tremor > 5.0 (fall risk)
- **High Alert:** tremor > 7.0 (critical fall risk / seizure activity)

---

### Bioimpedance (Ohms)

| Physiological State | BioZ Range (Ω) | Clinical Significance |
|---------------------|----------------|----------------------|
| **Rest** | 500-600 | Normal hydration |
| **Light Activity** | 480-520 | Slight decrease (vasodilation) |
| **Exercise** | 450-500 | Decreased (increased blood flow) |
| **Stress** | 520-580 | Slight increase (vasoconstriction) |
| **Sleep** | 550-650 | Increased (reduced blood flow) |
| **Fever** | 480-520 | Decreased (vasodilation) |
| **Hypoxia** | 460-500 | Decreased (compensatory vasodilation) |
| **Seizure** | 400-450 | Significantly decreased |
| **Arrhythmia** | 480-550 | Variable |

**Special Cases:**
- **Fluid Overload (CHF):** < 400 Ω - **ALERT** (edema, need diuretics)
- **Dehydration:** > 700 Ω - **WARNING** (need IV fluids)

**Alert Thresholds:**
- **Medium Alert:** bioimpedance < 400 Ω (fluid overload)
- **High Alert:** bioimpedance > 700 Ω (severe dehydration)

---

## Clinical Use Cases

### 1. Fall Risk Assessment (Tremor)
- **Patient Type:** Elderly, Parkinson's, post-stroke
- **Monitoring:** Continuous tremor tracking
- **Alert:** Tremor > 5.0 → Notify nursing staff
- **Action:** Assist with ambulation, prevent falls

### 2. Fluid Management (Bioimpedance)
- **Patient Type:** Heart failure, kidney disease, post-surgery
- **Monitoring:** Bioimpedance trends over 24-48 hours
- **Alert:** BioZ < 400 Ω → Fluid overload
- **Action:** Adjust diuretic dosage, restrict fluid intake

### 3. Seizure Detection (Tremor)
- **Patient Type:** Epilepsy, post-head injury
- **Monitoring:** Sudden tremor spikes
- **Alert:** Tremor > 7.0 → Potential seizure
- **Action:** Immediate medical response, protect patient

### 4. Dehydration Monitoring (Bioimpedance)
- **Patient Type:** Post-surgery, gastroenteritis, elderly
- **Monitoring:** Increasing bioimpedance trend
- **Alert:** BioZ > 700 Ω → Dehydration
- **Action:** Increase fluid intake or IV fluids

---

## Testing Checklist

### Phase 1: Database Testing ⏸️
- [ ] Run ALTER TABLE commands to add tremor/bioimpedance columns
- [ ] Verify columns exist with correct data types (numeric)
- [ ] Verify constraints are in place (tremor: 0-10, bioz: 200-1000)
- [ ] Verify indexes created successfully

### Phase 2: ESP32 Firmware Testing ⏸️
- [ ] Update firmware code (4 changes + version bump)
- [ ] Flash updated firmware to ESP32 device
- [ ] Verify serial output shows tremor and bioimpedance values
- [ ] Verify MQTT message includes `tremor` and `bioimpedance` fields

### Phase 3: Backend Testing ⏸️
- [ ] Update backend MQTT INSERT query
- [ ] Restart backend service
- [ ] Monitor backend logs for tremor/bioz data reception
- [ ] Query database to verify tremor/bioz data is being stored:
  ```sql
  SELECT time, "patientId", tremor, bioimpedance
  FROM vitals_realtime
  WHERE tremor IS NOT NULL OR bioimpedance IS NOT NULL
  ORDER BY time DESC
  LIMIT 10;
  ```

### Phase 4: Frontend Testing ⏸️
- [ ] Create tremor chart component
- [ ] Create bioimpedance chart component
- [ ] Test API endpoints for tremor/bioz timeseries data
- [ ] Verify charts display correctly with real-time updates
- [ ] Test alert thresholds (tremor > 5.0, bioz < 400 or > 700)

---

## Data Flow

```
ESP32 PhysiologicalSimulator
  ↓ getTremorIntensity() / getBioimpedance()
ESP32 Firmware (every 1 second)
  ↓ MQTT publish: tremor, bioimpedance
MQTT Broker (mosquitto)
  ↓
Backend MQTT Service (mqtt_service.py)
  ↓ Pydantic validation (VitalsRealtimeMessage)
  ↓ INSERT with tremor, bioimpedance columns
TimescaleDB vitals_realtime table
  ↓
Backend API Endpoint
  ↓ GET /api/v2/patients/{id}/vitals/timeseries?vitalType=tremor
Frontend VitalService
  ↓ Chart rendering (tremor, bioimpedance)
User Interface
```

---

## File Locations

| Component | File Path |
|-----------|-----------|
| **ESP32 Firmware** | `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino` |
| **ESP32 Simulator** | `esp32_hospital_watch_complete/PhysiologicalSimulator.h` |
| **Backend MQTT Service** | `hospital-backend/app/services/mqtt_service.py` |
| **Backend Models** | `hospital-backend/app/models/neural_vitals.py` |
| **Database** | TimescaleDB `vitals_realtime` table |

---

## Summary

**Similar to BP implementation**, tremor and bioimpedance require:
1. ✅ Database schema update (2 new columns)
2. ✅ ESP32 firmware update (4 code changes)
3. ✅ Backend MQTT service update (INSERT query)
4. ⏸️ Frontend charts (future enhancement)

**Implementation Difficulty:** Low - Same pattern as blood pressure implementation

**Clinical Value:** High
- Tremor monitoring = Fall risk assessment + seizure detection
- Bioimpedance = Fluid management + dehydration/overload detection

**Estimated Time:** 15-20 minutes for database + backend + ESP32 firmware updates

---

## Next Steps

**Awaiting user approval to proceed with:**
1. Database schema update (SQL commands)
2. ESP32 firmware v5.2.15 (4 code changes + version bump)
3. Backend MQTT service update (INSERT query modification)

**User Decision Required:**
- Proceed with tremor + bioimpedance implementation? (yes/no)
- Implement now or defer to later?
- Any specific clinical requirements for tremor/bioz alerts?
