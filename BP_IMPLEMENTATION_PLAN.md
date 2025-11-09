# Blood Pressure Implementation Plan

**Date**: 2025-11-06
**Goal**: Add systolic and diastolic blood pressure support
**Status**: Ready to implement

---

## Current Situation

### ✅ What Already Exists

1. **ESP32 Simulator** - Generates realistic BP values
   - `PhysiologicalSimulator::getBloodPressureSystolic()` - Returns 60-200 mmHg
   - `PhysiologicalSimulator::getBloodPressureDiastolic()` - Returns 40-130 mmHg
   - Values vary by physiological state (RESTING: 115/75, EXERCISE: 155/85, etc.)

2. **Backend Pydantic Model** - Ready to validate BP
   - `bloodPressureSystolic: Optional[int] = Field(None, ge=60, le=200)`
   - `bloodPressureDiastolic: Optional[int] = Field(None, ge=40, le=130)`

3. **Backend MQTT Service** - Ready to map BP fields
   - Lines 1224-1225: Maps `bloodPressureSystolic` and `bloodPressureDiastolic`

4. **Frontend Chart Component** - Has BP chart configured
   - Chart type: 'bloodPressure' with dual lines (systolic + diastolic)

### ❌ What's Missing

1. **ESP32 firmware** - Doesn't read or transmit BP
2. **TimescaleDB columns** - vitals_realtime table missing BP columns
3. **Backend INSERT query** - Doesn't include BP in database write

---

## Implementation Steps

### Step 1: Add BP Columns to TimescaleDB ✅ READY

**File**: Create migration script
**Database**: hospitaltimescale.vitals_realtime

**SQL**:
```sql
ALTER TABLE vitals_realtime
ADD COLUMN IF NOT EXISTS "systolicPressure" INTEGER,
ADD COLUMN IF NOT EXISTS "diastolicPressure" INTEGER;

-- Add constraints for valid BP ranges
ALTER TABLE vitals_realtime
ADD CONSTRAINT vitals_systolic_range CHECK ("systolicPressure" BETWEEN 60 AND 200),
ADD CONSTRAINT vitals_diastolic_range CHECK ("diastolicPressure" BETWEEN 40 AND 130);

-- Create index for BP queries (optional but recommended)
CREATE INDEX IF NOT EXISTS idx_vitals_bp
ON vitals_realtime ("patientId", "systolicPressure", "diastolicPressure")
WHERE "systolicPressure" IS NOT NULL;
```

**Verification**:
```sql
-- Check columns added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'vitals_realtime'
AND column_name ILIKE '%pressure%';

-- Should return:
-- systolicPressure  | integer
-- diastolicPressure | integer
```

---

### Step 2: Update ESP32 Firmware ✅ READY

#### 2a. Add Global Variables

**File**: esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino
**Location**: After line 214

**Add**:
```cpp
// SENSOR DATA - POPULATED FROM PHYSIOLOGICAL SIMULATOR
// ... existing variables ...
int respiratoryRate = 0;     // ✅ Read from simulator.getRespiratoryRate()
float quality = 0;           // ✅ Read from simulator.getSignalQuality()

// ADD THESE TWO LINES:
int bloodPressureSystolic = 0;    // ✅ Read from simulator.getBloodPressureSystolic()
int bloodPressureDiastolic = 0;   // ✅ Read from simulator.getBloodPressureDiastolic()
```

#### 2b. Read BP from Simulator

**File**: esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino
**Location**: After line 1133 in `loop()` function

**Add**:
```cpp
// Read vitals from simulator (existing code)
heartRate = simulator.getHeartRate();
temperature = simulator.getTemperature();
oxygenSat = simulator.getOxygenSaturation();
respiratoryRate = simulator.getRespiratoryRate();
quality = simulator.getSignalQuality();

// ADD THESE TWO LINES:
bloodPressureSystolic = simulator.getBloodPressureSystolic();
bloodPressureDiastolic = simulator.getBloodPressureDiastolic();
```

#### 2c. Transmit BP via MQTT

**File**: esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino
**Location**: After line 1935 in `sendVitals()` function

**Add**:
```cpp
void sendVitals() {
  // ... existing code ...
  doc["oxygenSaturation"] = (int)oxygenSat;
  doc["signalQuality"] = quality / 100.0;
  doc["respiratoryRate"] = (int)respiratoryRate;
  doc["batteryLevel"] = batteryLevel;

  // ADD THESE TWO LINES:
  doc["bloodPressureSystolic"] = bloodPressureSystolic;
  doc["bloodPressureDiastolic"] = bloodPressureDiastolic;

  String payload;
  serializeJson(doc, payload);
  // ... rest of function ...
}
```

#### 2d. Update Serial Debug Output (Optional)

**File**: esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino
**Location**: Line 1955-1959 in `sendVitals()` function

**Update**:
```cpp
Serial.println("📊 Vitals: Mode=" + String(isECGMode ? "ECG" : "EEG") +
               ", HR=" + String((int)heartRate) +
               ", Temp=" + String(tempCelsius, 1) + "°C" +
               ", SpO2=" + String(oxygenSat) + "%" +
               ", RR=" + String(respiratoryRate) +
               ", BP=" + String(bloodPressureSystolic) + "/" + String(bloodPressureDiastolic));  // ADD THIS
```

---

### Step 3: Verify Backend MQTT Service ✅ ALREADY READY

**File**: hospital-backend/app/services/mqtt_service.py
**Location**: Lines 1224-1225

**Current Code** (already correct):
```python
# Blood pressure - frontend field names
'systolicPressure': vitalsMsg.bloodPressureSystolic,
'diastolicPressure': vitalsMsg.bloodPressureDiastolic,
```

**No changes needed** - backend already maps BP fields correctly.

---

### Step 4: Update Backend INSERT Query

**File**: hospital-backend/app/services/mqtt_service.py
**Location**: Around line 1250-1300 (INSERT INTO vitals_realtime)

**Current INSERT** (need to verify):
```python
INSERT INTO vitals_realtime (
    time, "patientId", "deviceId", mode,
    "heartRate", "respiratoryRate", "skinTemperature", "oxygenSaturation",
    "batteryLevel", "signalQuality",
    -- ECG/EEG fields...
)
```

**Need to add**:
```python
INSERT INTO vitals_realtime (
    time, "patientId", "deviceId", mode,
    "heartRate", "respiratoryRate", "skinTemperature", "oxygenSaturation",
    "batteryLevel", "signalQuality",
    "systolicPressure", "diastolicPressure",  -- ADD THESE
    -- ECG/EEG fields...
)
VALUES (
    $1, $2, $3, $4,
    $5, $6, $7, $8,
    $9, $10,
    $11, $12,  -- ADD THESE PLACEHOLDERS
    -- More placeholders...
)
```

---

## Testing Plan

### Test 1: Database Migration
```bash
cd hospital-backend
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://hospital_user:hospital123@localhost:5433/hospitaltimescale')
cur = conn.cursor()

# Run migration
cur.execute('''
ALTER TABLE vitals_realtime
ADD COLUMN IF NOT EXISTS \"systolicPressure\" INTEGER,
ADD COLUMN IF NOT EXISTS \"diastolicPressure\" INTEGER
''')
conn.commit()

# Verify columns added
cur.execute('''
SELECT column_name FROM information_schema.columns
WHERE table_name = 'vitals_realtime' AND column_name ILIKE '%pressure%'
''')
print('BP columns:', [row[0] for row in cur.fetchall()])
cur.close()
conn.close()
"
```

**Expected**: `['systolicPressure', 'diastolicPressure']`

---

### Test 2: ESP32 Firmware Changes
1. Make the 3 code changes above
2. Compile firmware (verify no errors)
3. Flash to ESP32
4. Monitor serial output

**Expected Serial Output**:
```
📊 Vitals: Mode=ECG, HR=74, Temp=36.7°C, SpO2=98%, RR=16, BP=118/76
```

---

### Test 3: MQTT Payload Verification
```bash
# Subscribe to MQTT topic
mosquitto_sub -h 127.0.0.1 -p 8883 \
  --cafile mosquitto/certs/hospital_ca.crt \
  --cert mosquitto/certs/backend_client.crt \
  --key mosquitto/certs/backend_client.key \
  -t "hospital/devices/fit-00001/vitals" -v
```

**Expected MQTT Message**:
```json
{
  "timestamp": "2025-11-06T01:23:45.678Z",
  "deviceId": "fit-00001",
  "patientId": "081a5294-da91-4c74-bb8a-e5062f5851dd",
  "heartRate": 74,
  "skinTemperature": 36.7,
  "oxygenSaturation": 98,
  "respiratoryRate": 16,
  "batteryLevel": 100,
  "signalQuality": 0.95,
  "bloodPressureSystolic": 118,
  "bloodPressureDiastolic": 76,
  "mode": "ecg"
}
```

---

### Test 4: Backend Processing
Check backend logs for BP data processing:

**Expected Log Output**:
```
INFO: 📊 8CH Vitals processed for patient 081a5294... from device fit-00001 (mode: ecg)
      systolicPressure: 118, diastolicPressure: 76
```

---

### Test 5: Database Storage
```bash
cd hospital-backend
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://hospital_user:hospital123@localhost:5433/hospitaltimescale')
cur = conn.cursor()

# Query latest BP values
cur.execute('''
SELECT time, \"heartRate\", \"systolicPressure\", \"diastolicPressure\"
FROM vitals_realtime
WHERE \"patientId\" = '081a5294-da91-4c74-bb8a-e5062f5851dd'
AND \"systolicPressure\" IS NOT NULL
ORDER BY time DESC
LIMIT 5
''')

print('Latest BP readings:')
for row in cur.fetchall():
    print(f'  {row[0]} | HR={row[1]} BP={row[2]}/{row[3]}')

cur.close()
conn.close()
"
```

**Expected Output**:
```
Latest BP readings:
  2025-11-06 01:23:45+00 | HR=74 BP=118/76
  2025-11-06 01:23:44+00 | HR=73 BP=117/75
  2025-11-06 01:23:43+00 | HR=75 BP=119/77
```

---

### Test 6: Frontend Charts (After API endpoints created)
1. Open patient detail page
2. Click on "Blood Pressure" vital name
3. Chart modal should open
4. Should show dual-line chart (systolic in red, diastolic in blue)
5. Test all timeframes (1min, 5min, 15min, 30min, 1hr, 4hr)

---

## Rollback Plan

If anything goes wrong:

### Rollback Database Migration
```sql
ALTER TABLE vitals_realtime
DROP COLUMN IF EXISTS "systolicPressure",
DROP COLUMN IF EXISTS "diastolicPressure";
```

### Rollback ESP32 Firmware
Flash previous firmware version (v5.2.8 or v5.2.13)

### No Backend Changes Needed
Backend already handles missing BP fields gracefully (Optional fields in Pydantic model)

---

## Expected BP Values

### By Physiological State
- **RESTING**: 115/75 mmHg (±5/±3)
- **LIGHT_ACTIVITY**: 130/80 mmHg (±5/±3)
- **EXERCISE**: 155/85 mmHg (±10/±3)
- **SLEEP**: 105/65 mmHg (±3/±3)

### Medical Ranges
- **Normal**: Systolic 90-120, Diastolic 60-80
- **Elevated**: Systolic 120-129, Diastolic <80
- **Hypertension Stage 1**: Systolic 130-139 or Diastolic 80-89
- **Hypertension Stage 2**: Systolic ≥140 or Diastolic ≥90
- **Hypotension**: Systolic <90 or Diastolic <60

---

## Estimated Time

- **Step 1** (Database): 5 minutes
- **Step 2** (ESP32 firmware): 15 minutes (edit + compile + flash)
- **Step 3** (Backend verification): 2 minutes
- **Step 4** (Backend INSERT update): 10 minutes
- **Testing**: 15 minutes

**Total**: ~45 minutes

---

## Ready to Execute?

All code changes are identified and ready. Shall I proceed with:
1. ✅ Database migration (add BP columns)
2. ✅ ESP32 firmware updates (3 changes)
3. ✅ Backend INSERT query update
4. ✅ Testing and verification
