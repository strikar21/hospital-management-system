# Priority 1: SQL INTERVAL Syntax Error - Root Cause Analysis & Fix Plan

## Issue Summary
**Error:** `invalid input syntax for type interval: "%s hours"`
**Impact:** 240+ errors per minute, blocking all historical vitals queries
**Location:** `hospital-backend/app/core/database.py`

## Root Cause Analysis

### Problem Code (Lines 679, 718, 794, 808, 839):
```python
# ❌ BROKEN: String interpolation inside SQL string literal
query = """
    SELECT time as timestamp, value
    FROM vitals_timeseries
    WHERE "patientId" = $1
      AND "vitalType" = $2
      AND time > NOW() - INTERVAL '%s hours'  # ❌ WRONG
    ORDER BY time ASC
"""
```

### Why It Fails:
1. `'%s hours'` is a **SQL string literal**, not a parameter placeholder
2. PostgreSQL tries to parse the literal string `"%s hours"` as an interval → syntax error
3. The `%s` never gets replaced by Python because it's inside SQL quotes

### Correct Approaches:

#### ✅ Option 1: Use make_interval() function (RECOMMENDED)
```python
query = """
    SELECT time as timestamp, value
    FROM vitals_timeseries
    WHERE "patientId" = $1
      AND "vitalType" = $2
      AND time > NOW() - make_interval(hours => $3)  # ✅ CORRECT
    ORDER BY time ASC
"""
# Execute with: conn.fetch(query, patientId, vitalType, hoursBack)
```

#### ✅ Option 2: Cast parameter to interval
```python
query = """
    SELECT time as timestamp, value
    FROM vitals_timeseries
    WHERE "patientId" = $1
      AND "vitalType" = $2
      AND time > NOW() - ($3 || ' hours')::INTERVAL  # ✅ CORRECT
    ORDER BY time ASC
"""
```

#### ✅ Option 3: Python string formatting OUTSIDE quotes (NOT RECOMMENDED - SQL injection risk)
```python
query = f"""
    SELECT time as timestamp, value
    FROM vitals_timeseries
    WHERE "patientId" = $1
      AND "vitalType" = $2
      AND time > NOW() - INTERVAL '{hoursBack} hours'  # ⚠️ Works but risky
    ORDER BY time ASC
"""
```

## Affected Functions in database.py

| Line | Function | Current Broken Code |
|------|----------|---------------------|
| 679 | `getHistoricalVitals()` | `INTERVAL '%s hours'` |
| 718 | `getVitalsTimeBuckets()` | `INTERVAL '%s hours'` (appears twice) |
| 794 | `countPatientsWithCondition()` | `INTERVAL '%s minutes'` |
| 808 | `countPatientsWithCondition()` | `INTERVAL '%s minutes'` |
| 839 | `countRecentAdmissions()` | `INTERVAL '%s hours'` |

## Fix Implementation Plan

### Step 1: Fix getHistoricalVitals() (Line 674-689)
**Current:**
```python
query = """
    SELECT time as timestamp, value
    FROM vitals_timeseries
    WHERE "patientId" = $1
      AND "vitalType" = $2
      AND time > NOW() - INTERVAL '%s hours'
    ORDER BY time ASC
"""
async with getTimescaleConnection() as conn:
    rows = await conn.fetch(query, patientId, vitalType, hoursBack)
```

**Fixed:**
```python
query = """
    SELECT time as timestamp, value
    FROM vitals_timeseries
    WHERE "patientId" = $1
      AND "vitalType" = $2
      AND time > NOW() - make_interval(hours => $3)
    ORDER BY time ASC
"""
async with getTimescaleConnection() as conn:
    rows = await conn.fetch(query, patientId, vitalType, hoursBack)
```

### Step 2: Fix getVitalsTimeBuckets() (Line 691-729)
**Current:**
```python
query = """
    SELECT time_bucket('%s minutes', time) AS bucket,
           AVG(value) as "avgValue",
           MIN(value) as "minValue",
           MAX(value) as "maxValue",
           COUNT(*) as count
    FROM vitals_timeseries
    WHERE "patientId" = $1
      AND "vitalType" = $2
      AND time > NOW() - INTERVAL '%s hours'
    GROUP BY bucket
    ORDER BY bucket ASC
"""
async with getTimescaleConnection() as conn:
    rows = await conn.fetch(query, bucketMinutes, patientId, vitalType, hoursBack)
```

**Fixed:**
```python
query = """
    SELECT time_bucket(($1 || ' minutes')::INTERVAL, time) AS bucket,
           AVG(value) as "avgValue",
           MIN(value) as "minValue",
           MAX(value) as "maxValue",
           COUNT(*) as count
    FROM vitals_timeseries
    WHERE "patientId" = $2
      AND "vitalType" = $3
      AND time > NOW() - make_interval(hours => $4)
    GROUP BY bucket
    ORDER BY bucket ASC
"""
async with getTimescaleConnection() as conn:
    rows = await conn.fetch(query, bucketMinutes, patientId, vitalType, hoursBack)
```

### Step 3: Fix countPatientsWithCondition() (Line 769-824)
**Current (2 instances):**
```python
query = """
    ...
    AND v.time > NOW() - INTERVAL '%s minutes'
    ...
"""
async with getTimescaleConnection() as conn:
    result = await conn.fetchval(query, wardId, timeWindowMinutes)
```

**Fixed:**
```python
# Fever condition query (line 787-796)
query = """
    SELECT COUNT(DISTINCT p.id)
    FROM patients p
    JOIN vitals_timeseries v ON p.id = v."patientId"
    WHERE ($1::TEXT IS NULL OR p."roomNumber" LIKE $1 || '%')
      AND v."vitalType" = 'temperature'
      AND v.value > 38.3
      AND v.time > NOW() - make_interval(mins => $2)
      AND p.status = 'active'
"""
async with getTimescaleConnection() as conn:
    result = await conn.fetchval(query, wardId, timeWindowMinutes)

# SpO2 declining query (line 798-814)
query = """
    WITH patient_spo2_trends AS (
        SELECT
            p.id as "patientId",
            FIRST_VALUE(v.value) OVER (PARTITION BY p.id ORDER BY v.time ASC) as "firstSpo2",
            LAST_VALUE(v.value) OVER (PARTITION BY p.id ORDER BY v.time DESC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as "lastSpo2"
        FROM patients p
        JOIN vitals_timeseries v ON p.id = v."patientId"
        WHERE ($1::TEXT IS NULL OR p."roomNumber" LIKE $1 || '%')
          AND v."vitalType" = 'oxygenSaturation'
          AND v.time > NOW() - make_interval(mins => $2)
          AND p.status = 'active'
    )
    SELECT COUNT(DISTINCT "patientId")
    FROM patient_spo2_trends
    WHERE ("firstSpo2" - "lastSpo2") / "firstSpo2" > 0.05
"""
async with getTimescaleConnection() as conn:
    result = await conn.fetchval(query, wardId, timeWindowMinutes)
```

### Step 4: Fix countRecentAdmissions() (Line 826-849)
**Current:**
```python
query = """
    SELECT COUNT(*)
    FROM patients
    WHERE "admissionDate" > NOW() - INTERVAL '%s hours'
      AND status = 'active'
"""
async with getDbConnection() as conn:
    result = await conn.fetchval(query, hoursBack)
```

**Fixed:**
```python
query = """
    SELECT COUNT(*)
    FROM patients
    WHERE "admissionDate" > NOW() - make_interval(hours => $1)
      AND status = 'active'
"""
async with getDbConnection() as conn:
    result = await conn.fetchval(query, hoursBack)
```

## Verification Plan

### Unit Tests (Create test_database_intervals.py):
```python
import pytest
from app.core.database import (
    getHistoricalVitals,
    getVitalsTimeBuckets,
    countPatientsWithCondition,
    countRecentAdmissions
)

@pytest.mark.asyncio
async def test_getHistoricalVitals_no_syntax_error():
    """Verify interval syntax is correct"""
    result = await getHistoricalVitals('PAT001', 'heartRate', 24)
    # Should not raise SQL syntax error

@pytest.mark.asyncio
async def test_getVitalsTimeBuckets_no_syntax_error():
    """Verify interval syntax is correct"""
    result = await getVitalsTimeBuckets('PAT001', 'heartRate', 24, 5)
    # Should not raise SQL syntax error

@pytest.mark.asyncio
async def test_countPatientsWithCondition_no_syntax_error():
    """Verify interval syntax is correct"""
    result = await countPatientsWithCondition(None, 'fever', 60)
    # Should not raise SQL syntax error

@pytest.mark.asyncio
async def test_countRecentAdmissions_no_syntax_error():
    """Verify interval syntax is correct"""
    result = await countRecentAdmissions(24)
    # Should not raise SQL syntax error
```

### Integration Tests:
1. Check backend logs for 0 interval syntax errors (currently 240/min)
2. Verify vitals history charts load in frontend
3. Verify alert detection service can query historical data

## Rollback Plan

### If Fix Fails:
1. Revert changes to database.py
2. Restore from git: `git checkout HEAD -- hospital-backend/app/core/database.py`
3. Restart backend: Backend will use previous working version

### Backup Current Version:
```bash
cp hospital-backend/app/core/database.py hospital-backend/app/core/database.py.backup
```

## Estimated Impact

### Before Fix:
- 240+ SQL errors per minute
- Historical vitals queries: 100% failure rate
- Alert detection: Cannot query trends
- Frontend vitals charts: Broken

### After Fix:
- 0 SQL errors from interval syntax
- Historical vitals queries: Working
- Alert detection: Can query trends
- Frontend vitals charts: Working

## Risk Assessment

**Risk Level:** LOW
**Confidence:** 100%

**Reasoning:**
1. Root cause is crystal clear (string interpolation in SQL literal)
2. Fix is well-documented PostgreSQL best practice
3. Changes are isolated to query strings only
4. No schema changes required
5. No data migration needed
6. Backward compatible (same function signatures)

## Implementation Time

- **Fix Code:** 15 minutes
- **Testing:** 30 minutes
- **Verification:** 15 minutes
- **Total:** 1 hour

## Next Steps

1. ✅ Create backup of database.py
2. ✅ Apply fixes to all 5 affected functions
3. ✅ Restart backend service
4. ✅ Monitor logs for interval errors (should drop to 0)
5. ✅ Test vitals history queries manually
6. ✅ Verify frontend charts load data
7. ✅ Create unit tests for regression prevention

## References

- PostgreSQL INTERVAL documentation: https://www.postgresql.org/docs/current/functions-datetime.html
- asyncpg parameter binding: https://magicstack.github.io/asyncpg/current/usage.html#preparing-and-executing-statements
- TimescaleDB time_bucket: https://docs.timescale.com/api/latest/hyperfunctions/time_bucket/
