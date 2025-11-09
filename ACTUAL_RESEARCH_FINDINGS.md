# Actual Research Findings - Vitals Charts Issue

**Date**: 2025-11-05
**Research Method**: File searching, code reading, database queries, log analysis
**Status**: ✅ RESEARCH COMPLETE - Ready for proper fix plan

---

## What I Actually Found (Not Assumptions)

### 1. Missing API Endpoints - CONFIRMED ✅

**Evidence**:
```bash
# Searched all API files
find app/api -name "*.py"
# Result: 20 API files found

# Searched for vitals endpoints
grep -r "def.*vitals\|@router.*vitals" app/api --include="*.py"
# Result: Only found POST endpoints (write), NO GET endpoints (read)
```

**Confirmed Endpoints**:
- ❌ `GET /api/v2/patients/{id}/vitals/history` - Does NOT exist
- ❌ `GET /api/v2/patients/{id}/vitals/timeseries` - Does NOT exist
- ✅ `POST /api/v1/esp32/{deviceId}/vitals/{patientId}` - EXISTS (write vitals)
- ✅ `POST /api/v1/websocket/broadcast/vitals/{patientId}` - EXISTS (broadcast)

**File**: [hospital-backend/app/api/v2/patients.py:1-521](hospital-backend/app/api/v2/patients.py)
- Contains 521 lines
- Has endpoints for: list, search, status, notes, discharge, alerts, case-entries
- **NO vitals endpoints**

**Backend Logs Evidence**:
```
INFO: 127.0.0.1:56092 - "GET /api/v2/patients/081a5294.../vitals/history?timeRange=6h HTTP/1.1" 404 Not Found
```

**Conclusion**: Frontend calls `/vitals/history` but endpoint doesn't exist. This is not an assumption - I searched the code and confirmed.

---

### 2. Broken SQL Query - CONFIRMED ✅

**File**: [hospital-backend/app/core/database.py:658-689](hospital-backend/app/core/database.py#L658-L689)

**Function**: `getHistoricalVitals()`

**The Bug** (Line 679):
```python
query = """
    SELECT time as timestamp, value
    FROM vitals_timeseries
    WHERE "patientId" = $1
      AND "vitalType" = $2
      AND time > NOW() - INTERVAL '%s hours'  # ❌ BUG HERE
    ORDER BY time ASC
"""

async with getTimescaleConnection() as conn:
    rows = await conn.fetch(query, patientId, vitalType, hoursBack)  # Passes 3 params but query only has $1, $2
```

**Why it's broken**:
1. Uses `'%s hours'` (Python string formatting) instead of SQL parameter placeholder
2. PostgreSQL doesn't evaluate `%s` - treats it literally as the string "%s"
3. Error: `invalid input syntax for type interval: "%s hours"`
4. Query has only 2 placeholders (`$1`, `$2`) but function passes 3 parameters

**Backend Log Evidence**:
```
❌ Failed to get historical vitals for 081a5294.../heartRate: invalid input syntax for type interval: "%s hours"
```

**Conclusion**: This function exists but has a SQL syntax bug. Not an assumption - I read the code and saw the error in logs.

---

### 3. Wrong Database Table - CONFIRMED ✅

**The Problem**:
```python
# Function queries PostgreSQL vitals_timeseries
async with getTimescaleConnection() as conn:  # ✅ Connects to TimescaleDB
    rows = await conn.fetch("""
        SELECT time as timestamp, value
        FROM vitals_timeseries  # ❌ But queries PostgreSQL table!
        WHERE ...
    """)
```

**Database Research**:
```sql
-- PostgreSQL (hospitaldb) vitals_timeseries:
SELECT COUNT(*) FROM vitals_timeseries
WHERE "patientId" = '081a5294-da91-4c74-bb8a-e5062f5851dd';
-- Result: 0 rows (empty for current patient)

-- TimescaleDB (hospitaltimescale) vitals_realtime:
SELECT COUNT(*) FROM vitals_realtime
WHERE "patientId" = '081a5294-da91-4c74-bb8a-e5062f5851dd';
-- Result: 12,729 rows (data exists!)
```

**Schema Differences**:

**PostgreSQL `vitals_timeseries`** (narrow schema - legacy):
```
time, patientId, deviceId, vitalType, value, unit, quality, rawData, metadata
```
- One row per vital type per timestamp
- Nearly empty (only test data from October 7)

**TimescaleDB `vitals_realtime`** (wide schema - current):
```
time, patientId, deviceId, mode, heartRate, respiratoryRate, skinTemperature,
oxygenSaturation, batteryLevel, signalQuality, rrInterval, qrsDuration, etc.
```
- One row per timestamp with all vitals
- 12,729+ rows of actual data flowing from ESP32

**Conclusion**: Function exists but queries wrong table. Real data is in `vitals_realtime`, not `vitals_timeseries`. Not an assumption - I queried both databases and confirmed.

---

### 4. BP Never Transmitted - CONFIRMED ✅

**ESP32 Firmware Analysis**:

**Simulator HAS BP** ([PhysiologicalSimulator.cpp:728-734]()):
```cpp
int PhysiologicalSimulator::getBloodPressureSystolic() {
    return constrain((int)currentBPSystolic, 60, 200);
}
```

**ESP32 NEVER calls it** ([esp32_hospital_watch_complete.ino:1129-1133]()):
```cpp
// Read vitals from simulator (line 1129-1133)
heartRate = simulator.getHeartRate();
temperature = simulator.getTemperature();
oxygenSat = simulator.getOxygenSaturation();
respiratoryRate = simulator.getRespiratoryRate();
quality = simulator.getSignalQuality();

// ❌ NEVER CALLED:
// bloodPressureSystolic = simulator.getBloodPressureSystolic();
// bloodPressureDiastolic = simulator.getBloodPressureDiastolic();
```

**ESP32 NEVER sends it** ([esp32_hospital_watch_complete.ino:1917-1936]()):
```cpp
void sendVitals() {
  doc["heartRate"] = (int)heartRate;
  doc["skinTemperature"] = tempCelsius;
  doc["oxygenSaturation"] = (int)oxygenSat;
  doc["respiratoryRate"] = (int)respiratoryRate;
  doc["batteryLevel"] = batteryLevel;
  doc["signalQuality"] = quality / 100.0;

  // ❌ MISSING:
  // doc["bloodPressureSystolic"] = bloodPressureSystolic;
  // doc["bloodPressureDiastolic"] = bloodPressureDiastolic;
}
```

**No Global Variables** ([esp32_hospital_watch_complete.ino:209-214]()):
```cpp
float heartRate = 0;         // ✅ EXISTS
float temperature = 0;       // ✅ EXISTS
int oxygenSat = 0;           // ✅ EXISTS
int respiratoryRate = 0;     // ✅ EXISTS
// ❌ NO: int bloodPressureSystolic = 0;
// ❌ NO: int bloodPressureDiastolic = 0;
```

**Git History Search**:
```bash
git log --all -S "bloodPressureSystolic" -- esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino
# Result: No commits found (never added to firmware)
```

**Conclusion**: BP simulation code exists but firmware never uses it. Not an assumption - I searched the code, checked git history, and confirmed.

---

### 5. TimescaleDB Missing BP Columns - CONFIRMED ✅

**Schema Query**:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'vitals_realtime' AND table_schema = 'public'
ORDER BY ordinal_position;

-- Result (26 columns total):
time, patientId, deviceId, mode,
heartRate, respiratoryRate, skinTemperature, oxygenSaturation,
batteryLevel, signalQuality, rrInterval, qrsDuration, qtInterval,
axis, rhythm, stSegment, alphaPower, betaPower, thetaPower,
deltaPower, gammaPower, dominantFrequency, seizureActivity,
quality, sequence, metadata

-- ❌ MISSING: systolicPressure, diastolicPressure
```

**Conclusion**: Database schema doesn't have BP columns. Not an assumption - I queried the schema and confirmed.

---

## Summary: What's Actually Broken

### Issue #1: Missing API Endpoints (P0 - Critical)
- **Status**: Confirmed via file search
- **Impact**: ALL vitals charts broken (not just BP)
- **Evidence**: 404 errors in logs, no endpoint found in code
- **Files Checked**: All 20 API files in `app/api/`

### Issue #2: SQL Syntax Bug in database.py (P1 - High)
- **Status**: Confirmed by reading code
- **Location**: Line 679 in database.py
- **Error**: `invalid input syntax for type interval: "%s hours"`
- **Evidence**: Error logs + source code inspection

### Issue #3: Wrong Database Table (P1 - High)
- **Status**: Confirmed via database queries
- **Problem**: Queries empty `vitals_timeseries` instead of `vitals_realtime`
- **Evidence**: Counted rows in both tables

### Issue #4: BP Not Transmitted (P2 - Medium)
- **Status**: Confirmed via code search
- **Problem**: ESP32 never calls BP getters or sends BP via MQTT
- **Evidence**: Read firmware code, searched git history

### Issue #5: Missing DB Columns for BP (P2 - Medium)
- **Status**: Confirmed via schema query
- **Problem**: vitals_realtime table has no systolicPressure/diastolicPressure
- **Evidence**: Queried information_schema

---

## What I Did NOT Assume

❌ Did NOT assume endpoints don't exist - I searched all 20 API files
❌ Did NOT assume SQL is broken - I read the actual code at line 679
❌ Did NOT assume wrong table - I queried both databases
❌ Did NOT assume BP never worked - I checked git history and firmware code
❌ Did NOT assume columns missing - I queried the schema

---

## Questions for Proper Fix Plan

Before creating a fix plan, I need to verify:

1. **Should we create new endpoints** or fix/use existing ones?
   - Need to check if there's a repository pattern service I missed

2. **Which database table should we use** for vitals history?
   - PostgreSQL `vitals_timeseries` (legacy, empty)
   - TimescaleDB `vitals_realtime` (current, has data)

3. **What timeRange formats** does frontend expect?
   - "1h", "6h", "24h", "7d" - Need to verify

4. **Do we want BP support** in this fix?
   - Or focus on making existing vitals (HR, SpO2, Temp, RR) work first?

5. **Are there existing services** I should use?
   - Found `patient_service.py` but no vitals methods
   - Should I add methods there or create new vitals service?

---

## Next Steps (Need User Confirmation)

1. ✅ **Create API endpoints** for `/api/v2/patients/{id}/vitals/history` and `/vitals/timeseries`
2. ✅ **Fix SQL bug** in database.py line 679
3. ✅ **Switch to correct table** (vitals_realtime instead of vitals_timeseries)
4. ⏸️ **Add BP support** (defer to Phase 2?)

**Should I proceed with creating a detailed fix plan now that research is complete?**
