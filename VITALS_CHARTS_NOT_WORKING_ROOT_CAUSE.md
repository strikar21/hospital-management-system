# Vitals Charts Not Working - ACTUAL Root Cause

**Date**: 2025-11-05
**Investigation**: Complete analysis of vitals chart system
**Status**: ❌ **CRITICAL** - ALL vitals charts broken, not just BP

---

## Summary

Vitals charts appear to have "worked earlier" but actually **the API endpoints don't exist**. Frontend gets 404 errors when requesting vitals history data.

---

## Root Cause: Missing Backend API Endpoints

### Frontend Calls (that fail with 404):

1. **`GET /api/v2/patients/{patientId}/vitals/history?timeRange={range}`**
   - Called by: [hospital-display-app/src/services/VitalService.ts:101](hospital-display-app/src/services/VitalService.ts#L101)
   - Status: **404 Not Found**
   - Evidence from backend logs:
   ```
   INFO: 127.0.0.1:56092 - "GET /api/v2/patients/081a5294-da91-4c74-bb8a-e5062f5851dd/vitals/history?timeRange=6h HTTP/1.1" 404 Not Found
   INFO: 127.0.0.1:56092 - "GET /api/v2/patients/081a5294-da91-4c74-bb8a-e5062f5851dd/vitals/history?timeRange=7d HTTP/1.1" 404 Not Found
   INFO: 127.0.0.1:56092 - "GET /api/v2/patients/081a5294-da91-4c74-bb8a-e5062f5851dd/vitals/history?timeRange=24h HTTP/1.1" 404 Not Found
   ```

2. **`GET /api/v2/patients/{patientId}/vitals/timeseries?vitalType={type}&timeRange={range}&limit={limit}`**
   - Called by: [hospital-display-app/src/services/VitalService.ts:62-64](hospital-display-app/src/services/VitalService.ts#L62-L64)
   - Status: **Endpoint doesn't exist** (searched entire backend, not found)

---

## What About Blood Pressure?

BP charts can't work because:
1. ❌ **API endpoints don't exist** (404 errors)
2. ❌ **ESP32 doesn't send BP data** (never calls `getBloodPressureSystolic/Diastolic()`)
3. ❌ **TimescaleDB missing BP columns** (`systolicPressure`, `diastolicPressure`)

But even if ESP32 sent BP data and database had columns, **charts still wouldn't work** because the API endpoints return 404.

---

## Database Evidence

### PostgreSQL `vitals_timeseries` Table

This table exists and HAS blood pressure data (1 record from October 7):

```sql
SELECT vitaltype, COUNT(*)
FROM vitals_timeseries
GROUP BY vitaltype;

vitaltype              | count
-----------------------|------
bloodpressuresystolic  |     1
heartrate              |    98
oxygensaturation       |    86
temperature            |    70
respiratoryrate        |    16
ecg                    |     1
```

**However**:
- This data is from **October 7, 2025** (old)
- Current patient (081a5294-da91-4c74-bb8a-e5062f5851dd) has **NO data** in this table
- Data is for a different patient (6b851aa6-e564-40b6-963f-e1a5efdf024c)

### TimescaleDB `vitals_realtime` Table

This is where **current data flows** (12,729+ records for patient):
- ✅ heartRate, oxygenSaturation, skinTemperature, respiratoryRate
- ❌ systolicPressure, diastolicPressure (columns don't exist)

---

## Backend Errors

Additional errors in backend logs reveal broken queries:

```
❌ Failed to get historical vitals for 081a5294.../heartRate:
   invalid input syntax for type interval: "%s hours"
```

This suggests there IS code trying to query vitals_timeseries, but it has a **SQL syntax bug** (`"%s hours"` is Python string formatting, not SQL parameter).

---

## Why User Thinks "BP Used to Work Earlier"

**Hypothesis**: User saw the BP chart OPTION in the frontend UI, but clicking it never actually worked (always returned empty data or 404).

**Evidence**:
1. Frontend has BP chart component configured: [hospital-display-app/src/components/EnhancedVitalChart/VitalChartContainer.tsx](hospital-display-app/src/components/EnhancedVitalChart/VitalChartContainer.tsx)
2. Only 1 BP record ever existed (October 7, different patient)
3. Current patient never had BP data
4. API endpoints don't exist (404)

---

## Complete Issues List

### P0 - Critical (All Vitals Charts Broken)

1. ❌ **Missing API endpoint**: `/api/v2/patients/{patientId}/vitals/history`
   - Returns: 404 Not Found
   - Impact: ALL vitals charts fail to load data

2. ❌ **Missing API endpoint**: `/api/v2/patients/{patientId}/vitals/timeseries`
   - Returns: 404 (endpoint never created)
   - Impact: Individual vital type charts fail

3. ❌ **SQL syntax bug in backend**:
   - Error: `invalid input syntax for type interval: "%s hours"`
   - Location: Likely in database.py `get_historical_vitals()` function
   - Impact: Even if endpoints existed, queries would fail

4. ❌ **ESP32 doesn't send BP data**:
   - File: [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:1913-1965](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1913-L1965)
   - Missing: `doc["bloodPressureSystolic"]` and `doc["bloodPressureDiastolic"]`
   - Impact: No BP data flowing from devices

5. ❌ **TimescaleDB missing BP columns**:
   - Table: `vitals_realtime`
   - Missing: `systolicPressure`, `diastolicPressure`
   - Impact: Can't store BP data even if ESP32 sent it

### P3 - Low Priority

6. ⚠️ **PostgreSQL vitals_timeseries appears unused**:
   - Only 1 BP record from October 7 (old test data)
   - Current patient has NO records in this table
   - May be legacy or alternative schema

---

## Fix Plan

### Phase 1: Create Missing API Endpoints ⭐ HIGHEST PRIORITY

**File**: Create `hospital-backend/app/api/v2/vitals.py` or add to existing patient API

**Endpoints Needed**:

```python
@router.get("/patients/{patient_id}/vitals/history")
async def get_vitals_history(
    patient_id: UUID,
    timeRange: str = "24h"  # "1h", "6h", "24h", "7d"
):
    """
    Get comprehensive vitals history for all vital types.
    Query TimescaleDB vitals_realtime table.
    """
    pass

@router.get("/patients/{patient_id}/vitals/timeseries")
async def get_vital_timeseries(
    patient_id: UUID,
    vitalType: str,  # "heartRate", "oxygenSaturation", etc.
    timeRange: str = "24h",
    limit: int = 1000
):
    """
    Get time-series data for a specific vital type.
    Query TimescaleDB vitals_realtime table.
    """
    pass
```

**Implementation Details**:
- Query TimescaleDB `vitals_realtime` table (NOT PostgreSQL vitals_timeseries)
- Parse timeRange to PostgreSQL intervals:
  - "1h" → `INTERVAL '1 hour'`
  - "6h" → `INTERVAL '6 hours'`
  - "24h" → `INTERVAL '24 hours'`
  - "7d" → `INTERVAL '7 days'`
- Return camelCase JSON matching frontend expectations
- Handle missing data gracefully (empty array, not 404)

---

### Phase 2: Fix SQL Syntax Bug

**File**: [hospital-backend/app/core/database.py](hospital-backend/app/core/database.py)

**Find and fix**:
```python
# ❌ WRONG
query = f"WHERE time > NOW() - INTERVAL '%s hours'"

# ✅ CORRECT
query = f"WHERE time > NOW() - INTERVAL '{hours} hours'"
# OR use SQL parameter:
query = "WHERE time > NOW() - INTERVAL $1"
```

---

### Phase 3: Add Blood Pressure Support (Optional - After Phase 1 & 2 work)

**Step 3a: Update ESP32 Firmware**
- File: [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:1913](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1913)
- Add after line 1934:
  ```cpp
  doc["bloodPressureSystolic"] = simulator.getBloodPressureSystolic();
  doc["bloodPressureDiastolic"] = simulator.getBloodPressureDiastolic();
  ```

**Step 3b: Add Database Columns**
- Create migration: `hospital-backend/migrations/XXX_add_blood_pressure_columns.sql`
- Add to TimescaleDB `vitals_realtime` table:
  ```sql
  ALTER TABLE vitals_realtime
  ADD COLUMN IF NOT EXISTS "systolicPressure" INTEGER,
  ADD COLUMN IF NOT EXISTS "diastolicPressure" INTEGER;
  ```

**Step 3c: Update Backend MQTT Service**
- File: [hospital-backend/app/services/mqtt_service.py:1224-1225](hospital-backend/app/services/mqtt_service.py#L1224-L1225)
- Already maps BP fields (no changes needed)

---

## Testing Checklist

### After Phase 1 (API Endpoints):
1. ✅ Start backend, verify no startup errors
2. ✅ Open browser console, check for 404 errors → Should be gone
3. ✅ Click on "Heart Rate" vital name → Chart modal opens with data
4. ✅ Try all timeframes (1h, 6h, 24h, 7d) → Data loads
5. ✅ Test SpO2, Temp, RR charts → All work
6. ✅ BP charts show "No data available" (expected - Phase 3 adds BP)

### After Phase 2 (SQL Fix):
1. ✅ Check backend logs for SQL errors → Should be gone
2. ✅ Vitals charts load faster (no query retries)

### After Phase 3 (BP Support):
1. ✅ Flash ESP32 with updated firmware
2. ✅ Verify MQTT payload includes BP fields
3. ✅ Check TimescaleDB for BP values
4. ✅ Open BP chart → Displays systolic and diastolic lines

---

## Data Flow (How It Should Work)

```
┌──────────────────────────────────────────────────────────────────────┐
│ ESP32 Watch (fit-00001)                                              │
│ - PhysiologicalSimulator generates vitals every 1 second             │
│ - sendVitals() publishes to MQTT: hospital/devices/fit-00001/vitals │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ MQTT Broker (Mosquitto:8883)                                         │
│ - Receives QoS 1 message                                             │
│ - Forwards to subscribed backend                                     │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Backend MQTT Service (mqtt_service.py)                               │
│ - handle_vitals_message() processes payload                          │
│ - Maps fields to camelCase                                           │
│ - INSERT INTO vitals_realtime (TimescaleDB)                          │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ TimescaleDB (vitals_realtime table)                                  │
│ - Stores: heartRate, oxygenSaturation, skinTemperature, etc.         │
│ - Partitioned by time (hypertable)                                   │
│ - 12,729+ records for patient                                        │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ REST API Endpoints (MISSING - NEEDS TO BE CREATED)                   │
│ - GET /api/v2/patients/{id}/vitals/history                           │
│ - GET /api/v2/patients/{id}/vitals/timeseries                        │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Frontend (React)                                                     │
│ - VitalService.getVitalTimeSeries() fetches data                     │
│ - EnhancedVitalChart displays Recharts graphs                        │
│ - User clicks vital name → Chart modal opens                         │
└──────────────────────────────────────────────────────────────────────┘
```

**Current Issue**: The REST API endpoints (in red box) **don't exist**, so frontend gets 404 errors and charts show no data.

---

## Why This Matters Clinically

Without working vitals charts, clinical staff cannot:
- ❌ View vital sign trends over time
- ❌ Identify gradual deterioration (e.g., slowly declining SpO2)
- ❌ Correlate medication administration with vital changes
- ❌ Review historical data during handoffs or rounds
- ❌ Make data-driven treatment decisions

Real-time vitals (current values) work fine, but **trending analysis is completely broken**.

---

## References

- Frontend VitalService: [hospital-display-app/src/services/VitalService.ts](hospital-display-app/src/services/VitalService.ts)
- Frontend Chart Component: [hospital-display-app/src/components/EnhancedVitalChart/VitalChartContainer.tsx](hospital-display-app/src/components/EnhancedVitalChart/VitalChartContainer.tsx)
- Backend MQTT Service: [hospital-backend/app/services/mqtt_service.py](hospital-backend/app/services/mqtt_service.py)
- TimescaleDB Schema: See TIMESCALEDB_SCHEMA_COMPLETE.md
- BP Root Cause: See BP_DATA_MISSING_ROOT_CAUSE_ANALYSIS.md
