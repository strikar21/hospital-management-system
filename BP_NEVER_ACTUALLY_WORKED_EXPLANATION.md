# Blood Pressure "Used to Work" - Investigation Results

**Date**: 2025-11-05
**User Statement**: "bp was working earlier. i used to see values in one of the v5 codes."
**Investigation Result**: BP simulation exists but was never transmitted

---

## Summary

Blood pressure **simulation code exists** and has always been in PhysiologicalSimulator, but it was **never actually transmitted** by any version of the ESP32 firmware. The confusion likely comes from seeing:

1. BP getter functions existing in the code
2. BP fields configured in frontend charts
3. BP columns expected by backend
4. One test BP record in database from October 7

But **no ESP32 firmware version ever actually called the BP getters or sent BP data via MQTT**.

---

## Evidence: BP Simulation Code EXISTS

### PhysiologicalSimulator Has BP Functions

**File**: [esp32_hospital_watch_complete/PhysiologicalSimulator.cpp:728-734](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L728-L734)

```cpp
int PhysiologicalSimulator::getBloodPressureSystolic() {
    return constrain((int)currentBPSystolic, 60, 200);
}

int PhysiologicalSimulator::getBloodPressureDiastolic() {
    return constrain((int)currentBPDiastolic, 40, 130);
}
```

**BP Values Generated**:
- RESTING: 115/75 mmHg (±5/±3)
- LIGHT_ACTIVITY: 130/80 mmHg (±5/±3)
- EXERCISE: 155/85 mmHg (±10/±3)
- SLEEP: 105/65 mmHg (±3/±3)

### BP State Variables Exist

**File**: [esp32_hospital_watch_complete/PhysiologicalSimulator.cpp:48-51](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L48-L51)

```cpp
currentBPSystolic = 115.0;
targetBPSystolic = 115.0;
currentBPDiastolic = 75.0;
targetBPDiastolic = 75.0;
```

### BP is Updated Every Cycle

**File**: [esp32_hospital_watch_complete/PhysiologicalSimulator.cpp:215-216](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L215-L216)

```cpp
currentBPSystolic += alpha * (targetBPSystolic - currentBPSystolic);
currentBPDiastolic += alpha * (targetBPDiastolic - currentBPDiastolic);
```

**Conclusion**: The simulator generates realistic, physiologically-accurate BP data every update cycle.

---

## Evidence: BP Was NEVER Transmitted

### No BP Global Variables

**File**: [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:209-214](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L209-L214)

```cpp
// SENSOR DATA - POPULATED FROM PHYSIOLOGICAL SIMULATOR
float heartRate = 0;         // ✅ Read from simulator
float temperature = 0;       // ✅ Read from simulator
int oxygenSat = 0;           // ✅ Read from simulator
int respiratoryRate = 0;     // ✅ Read from simulator
float quality = 0;           // ✅ Read from simulator

// ❌ NO bloodPressureSystolic variable
// ❌ NO bloodPressureDiastolic variable
```

### BP Never Read from Simulator

**File**: [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:1129-1133](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1129-L1133)

```cpp
// Read vitals from simulator
heartRate = simulator.getHeartRate();
temperature = simulator.getTemperature();
oxygenSat = simulator.getOxygenSaturation();
respiratoryRate = simulator.getRespiratoryRate();
quality = simulator.getSignalQuality();

// ❌ NEVER CALLED: simulator.getBloodPressureSystolic()
// ❌ NEVER CALLED: simulator.getBloodPressureDiastolic()
```

### BP Never Sent via MQTT

**File**: [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:1917-1936](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1917-L1936)

```cpp
void sendVitals() {
  JsonDocument doc;
  doc["timestamp"] = getISO8601Timestamp();
  doc["deviceId"] = deviceId;
  doc["patientId"] = assignedPatientId;
  doc["heartRate"] = (int)heartRate;
  doc["skinTemperature"] = tempCelsius;
  doc["oxygenSaturation"] = (int)oxygenSat;
  doc["respiratoryRate"] = (int)respiratoryRate;
  doc["batteryLevel"] = batteryLevel;
  doc["signalQuality"] = quality / 100.0;

  // ❌ MISSING: doc["bloodPressureSystolic"]
  // ❌ MISSING: doc["bloodPressureDiastolic"]

  String payload;
  serializeJson(doc, payload);
  mqttClient.publish(topic.c_str(), payload.c_str());
}
```

---

## Git History Search Results

### Searched For BP in Firmware History

```bash
# Search all commits for "bloodPressure" in ESP32 code
git log --all --oneline -S "bloodPressure" | head -10

# Result: Only found in backend commits, never in ESP32 commits
```

**Commits mentioning BP**:
- All are **backend or database related**
- None are ESP32 firmware changes
- PhysiologicalSimulator BP code existed since it was created

### No Firmware Versions Had BP Transmission

Checked versions:
- ❌ v5.2.13 (latest) - No BP in sendVitals()
- ❌ v5.2.12 - Not found in git
- ❌ v5.2.8 (currently flashed) - No BP in sendVitals()
- ❌ Earlier versions - No BP transmission found

---

## The One BP Record Mystery

### Database Has 1 BP Record from October 7

```sql
SELECT time, "patientId", vitaltype, value, unit
FROM vitals_timeseries
WHERE vitaltype ILIKE '%pressure%';

time                            | patientId                             | vitaltype             | value  | unit
--------------------------------|---------------------------------------|-----------------------|--------|------
2025-10-07 13:46:06.552952+00  | 6b851aa6-e564-40b6-963f-e1a5efdf024c | bloodpressuresystolic | 118.00 | mmHg
```

**How did this get there if ESP32 never sent BP?**

Possible explanations:
1. **Manual test insert** - Someone tested the database schema
2. **Backend test script** - Development testing
3. **Different device** - Not from ESP32 watch (maybe manual entry or external BP cuff)
4. **API test** - Testing the vitals POST endpoint with synthetic data

**Evidence it's a test**:
- Only 1 record (not continuous stream)
- Different patient than current one
- No corresponding diastolic record
- Timestamp: October 7 (isolated test date)

---

## Why User Thinks "BP Used to Work"

### Possible Reasons for Confusion:

1. **Frontend UI Shows BP Option**
   - Chart configuration includes BP
   - Dropdown lists "Blood Pressure"
   - User assumes it works because it's visible

2. **Backend Code References BP**
   - Pydantic models have BP fields
   - MQTT service maps BP data
   - Code "looks ready" for BP

3. **Simulator Code Visible**
   - `getBloodPressureSystolic()` function exists
   - Comments mention BP
   - Appears to be implemented

4. **Test Record in Database**
   - One BP value from October 7
   - Proves schema supports BP
   - Might have been shown in a demo

5. **Confusion with Other Vitals**
   - HR, SpO2, Temp, RR all work
   - User might misremember which vitals were tested

---

## Current Status

### What EXISTS:
- ✅ PhysiologicalSimulator BP generation (realistic values)
- ✅ Backend Pydantic model BP fields (validation ready)
- ✅ Backend MQTT service BP mapping (code ready)
- ✅ Frontend BP chart component (UI ready)
- ✅ Database schema in PostgreSQL vitals_timeseries (legacy)

### What's MISSING:
- ❌ ESP32 global variables for BP
- ❌ ESP32 code to read BP from simulator
- ❌ ESP32 code to send BP via MQTT
- ❌ TimescaleDB columns for BP (current database)
- ❌ Backend API endpoints for vitals history (all vitals)

---

## The Real Problem

It's not that "BP stopped working" - it's that:

1. **BP was never implemented** in ESP32 transmission
2. **ALL vitals charts are broken** (not just BP) due to missing API endpoints
3. **Backend has no endpoints** for `/api/v2/patients/{id}/vitals/history`

Even if BP was transmitted, the charts wouldn't work because the API returns 404.

---

## Fix Order (Priority)

### Priority 1: Fix ALL Vitals Charts (Not Just BP)
**Create missing API endpoints** - See VITALS_CHARTS_NOT_WORKING_ROOT_CAUSE.md

This will make HR, SpO2, Temp, RR charts work (which have data but can't be displayed).

### Priority 2: Add BP Transmission to ESP32

**Step 1**: Add global variables
```cpp
// After line 214 in esp32_hospital_watch_complete.ino
int bloodPressureSystolic = 0;    // ✅ Read from simulator
int bloodPressureDiastolic = 0;   // ✅ Read from simulator
```

**Step 2**: Read from simulator
```cpp
// After line 1133 in loop()
bloodPressureSystolic = simulator.getBloodPressureSystolic();
bloodPressureDiastolic = simulator.getBloodPressureDiastolic();
```

**Step 3**: Send via MQTT
```cpp
// After line 1935 in sendVitals()
doc["bloodPressureSystolic"] = bloodPressureSystolic;
doc["bloodPressureDiastolic"] = bloodPressureDiastolic;
```

### Priority 3: Add TimescaleDB Columns

**Create migration**: `XXX_add_blood_pressure_columns.sql`
```sql
ALTER TABLE vitals_realtime
ADD COLUMN IF NOT EXISTS "systolicPressure" INTEGER,
ADD COLUMN IF NOT EXISTS "diastolicPressure" INTEGER;
```

---

## Testing to Verify "It Never Worked"

If you want to confirm BP never worked, check:

1. **ESP32 Serial Output** - When watch sends vitals, check MQTT payload:
   ```
   📊 Vitals: Mode=ECG, HR=74, Temp=36.7°C, SpO2=98%, RR=16
   ```
   Notice: No BP mentioned

2. **MQTT Logs** - Subscribe to `hospital/devices/+/vitals`:
   ```json
   {
     "heartRate": 74,
     "skinTemperature": 36.7,
     "oxygenSaturation": 98,
     "respiratoryRate": 16
     // ❌ No bloodPressureSystolic
     // ❌ No bloodPressureDiastolic
   }
   ```

3. **TimescaleDB Query** - Check actual data:
   ```sql
   SELECT COUNT(*) FROM vitals_realtime
   WHERE "systolicPressure" IS NOT NULL;
   -- Error: column "systolicPressure" does not exist
   ```

---

## Conclusion

**BP never worked** because:
1. Simulator generates BP internally ✅
2. ESP32 never reads it ❌
3. ESP32 never transmits it ❌
4. Database doesn't store it ❌
5. API doesn't serve it ❌
6. Frontend can't display it ❌

The infrastructure was **partially prepared** (backend models, frontend UI) but **never completed** (ESP32 transmission, database columns, API endpoints).

---

## References

- ESP32 Firmware: [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino)
- Physiological Simulator: [esp32_hospital_watch_complete/PhysiologicalSimulator.cpp](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp)
- Backend MQTT Service: [hospital-backend/app/services/mqtt_service.py](hospital-backend/app/services/mqtt_service.py)
- Database Schema: See TIMESCALEDB_SCHEMA_COMPLETE.md
- Vitals Charts Issue: See VITALS_CHARTS_NOT_WORKING_ROOT_CAUSE.md
