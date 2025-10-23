# Decimal Serialization Error - Root Cause Analysis & Detailed Fix Plan

## Date: 2025-10-13
## Issue: Test failing with "Object of type Decimal is not JSON serializable"

---

## ROOT CAUSE ANALYSIS

### The Problem
PostgreSQL's `EXTRACT(EPOCH FROM timestamp)` function returns **NUMERIC** type, which becomes Python **Decimal** when fetched via asyncpg. FastAPI's JSONResponse uses Python's `json.dumps()` which **cannot serialize Decimal objects**.

### Affected Locations (3 total)
1. **hospital-backend/app/api/v1/device_management.py:288**
   - Endpoint: `GET /{deviceId}` (getDevice)
   - Query: `EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 as minutesSinceLastSeen`
   - Status: **NOT TESTED - Has latent bug**

2. **hospital-backend/app/api/v1/watch_management.py:274**
   - Endpoint: `GET /connection-status` (getWatchConnectionStatus)
   - Query: `EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 as "minutesSinceLastSeen"`
   - Status: **FAILING TEST**

3. **hospital-backend/app/api/v1/watch_management.py:345**
   - Endpoint: `GET /alerts` (getWatchAlerts)
   - Query: `EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 as minutesSinceLastSeen`
   - Status: **WORKS - Uses round() to convert Decimal to int before returning**

### Why getWatchAlerts() Works
Line 370 in watch_management.py:
```python
"minutesSinceLastSeen": round(deviceDict['minutesSinceLastSeen']),
```
The `round()` function converts Decimal to int, preventing serialization error.

### Why Current Fixes Don't Work
Attempted fixes in watch_management.py (lines 23-34, 288-293, 315-327):
- Added convertDecimalAndDatetime() helper function
- Added Decimal import
- Added conversion loop
- Added debug logging

**Problem**: The changes are in the file but the serialization error persists, indicating either:
1. The conversion is not being applied correctly
2. JSONResponse has its own serialization that bypasses the conversion
3. There's a caching/reload issue

---

## SOLUTION OPTIONS ANALYSIS

### Option 1: Python-Side Conversion (CURRENT ATTEMPT - FAILED)
**Approach**: Convert Decimal to float after fetching from database
**Problems**:
- Requires manual conversion in every endpoint
- Easy to miss locations
- Already attempted, not working reliably

### Option 2: SQL CAST (RECOMMENDED)
**Approach**: Use CAST() in SQL to convert EXTRACT result to DOUBLE PRECISION
**Advantages**:
- ✅ Fixes problem at the source
- ✅ No Python-side conversion needed
- ✅ Most reliable and performant
- ✅ Consistent with SQL best practices
- ✅ Type-safe from query to response

**SQL Change**:
```sql
-- BEFORE (returns NUMERIC/Decimal):
EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 as minutesSinceLastSeen

-- AFTER (returns DOUBLE PRECISION/float):
CAST(EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 AS DOUBLE PRECISION) as minutesSinceLastSeen
```

### Option 3: FastAPI Return Type (ALTERNATIVE)
**Approach**: Return plain dict instead of JSONResponse, let FastAPI serialize
**Advantages**:
- FastAPI has better type handling
**Disadvantages**:
- Requires changing return patterns across codebase
- More invasive change

### Option 4: Custom JSON Encoder (OVERKILL)
**Approach**: Configure FastAPI app-wide JSON encoder to handle Decimal
**Disadvantages**:
- Global change affecting all endpoints
- Unnecessary complexity

### Option 5: Always Use round()/int() (INCONSISTENT)
**Approach**: Call round() on every EXTRACT result like getWatchAlerts() does
**Disadvantages**:
- Loses decimal precision
- Easy to forget
- Not semantically correct for time calculations

---

## RECOMMENDED SOLUTION: SQL CAST

### Changes Required (3 locations)

#### Location 1: device_management.py:288
**File**: `hospital-backend/app/api/v1/device_management.py`
**Function**: `getDevice(deviceId: str)`
**Line**: 288

**BEFORE**:
```python
query = """
    SELECT d.*,
           CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                ELSE 'offline' END as connectionStatus,
           EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 as minutesSinceLastSeen
    FROM devices d
    WHERE d.id = $1
"""
```

**AFTER**:
```python
query = """
    SELECT d.*,
           CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                ELSE 'offline' END as connectionStatus,
           CAST(EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 AS DOUBLE PRECISION) as minutesSinceLastSeen
    FROM devices d
    WHERE d.id = $1
"""
```

#### Location 2: watch_management.py:274
**File**: `hospital-backend/app/api/v1/watch_management.py`
**Function**: `getWatchConnectionStatus()`
**Line**: 274

**BEFORE**:
```python
query = """
    SELECT d.*, da."patientId", p."firstName", p."lastName",
           CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                ELSE 'offline' END as "connectionStatus",
           EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 as "minutesSinceLastSeen"
    FROM devices d
    LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
    LEFT JOIN patients p ON da."patientId" = p.id
    WHERE d."deviceType" = 'watch'
    ORDER BY d.status, d."lastSeen" DESC
"""
```

**AFTER**:
```python
query = """
    SELECT d.*, da."patientId", p."firstName", p."lastName",
           CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                ELSE 'offline' END as "connectionStatus",
           CAST(EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 AS DOUBLE PRECISION) as "minutesSinceLastSeen"
    FROM devices d
    LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
    LEFT JOIN patients p ON da."patientId" = p.id
    WHERE d."deviceType" = 'watch'
    ORDER BY d.status, d."lastSeen" DESC
"""
```

#### Location 3: watch_management.py:345
**File**: `hospital-backend/app/api/v1/watch_management.py`
**Function**: `getWatchAlerts()`
**Line**: 345

**BEFORE**:
```python
query = """
    SELECT d.*, da."patientId", p."firstName", p."lastName", p."roomNumber", p."bedNumber",
           CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                ELSE 'offline' END as connectionStatus,
           EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 as minutesSinceLastSeen
    FROM devices d
    JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
    JOIN patients p ON da."patientId" = p.id
    WHERE d."deviceType" = 'watch' AND p.status = 'active'
"""
```

**AFTER**:
```python
query = """
    SELECT d.*, da."patientId", p."firstName", p."lastName", p."roomNumber", p."bedNumber",
           CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
                WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
                ELSE 'offline' END as connectionStatus,
           CAST(EXTRACT(EPOCH FROM (NOW() - d."lastSeen"))/60 AS DOUBLE PRECISION) as minutesSinceLastSeen
    FROM devices d
    JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
    JOIN patients p ON da."patientId" = p.id
    WHERE d."deviceType" = 'watch' AND p.status = 'active'
"""
```

### Cleanup Required

**File**: `hospital-backend/app/api/v1/watch_management.py`

**Remove Failed Attempt Code**:
1. Line 13: Remove `import json` (unused)
2. Lines 23-34: Remove `convertDecimalAndDatetime()` function (unused)
3. Lines 288-293: Remove Decimal conversion loop (unnecessary with SQL CAST)
4. Lines 307-311: Remove DEBUG logging loop (debugging code)
5. Lines 315-327: Simplify to direct JSONResponse return (no conversion needed)
6. Lines 330-332: Remove traceback logging (debugging code)

**Simplified Return** (lines 315-327):
```python
# BEFORE (overly complex):
# Convert all Decimal and datetime objects before returning
response_data = {
    "success": True,
    "watchStatus": watchStatus,
    "summary": {
        "total": len(watchStatus),
        "connected": connected,
        "recentlySeen": recentlySeen,
        "offline": offline
    }
}

return JSONResponse(content=convertDecimalAndDatetime(response_data))

# AFTER (clean):
return JSONResponse(content={
    "success": True,
    "watchStatus": watchStatus,
    "summary": {
        "total": len(watchStatus),
        "connected": connected,
        "recentlySeen": recentlySeen,
        "offline": offline
    }
})
```

---

## TESTING PLAN

### Test 1: Verify SQL CAST Works
```bash
cd hospital-backend
python -c "import asyncio; import asyncpg; asyncio.run((lambda: asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb').then(lambda c: c.fetch('SELECT CAST(EXTRACT(EPOCH FROM NOW())/60 AS DOUBLE PRECISION) as test').then(lambda r: print(type(r[0]['test'])))))())"
```
Expected: `<class 'float'>`

### Test 2: Run Device Pool Tests
```bash
cd hospital-backend
python test_device_pool.py
```
Expected: **8/8 tests passing** (currently 7/8)

### Test 3: Manual Endpoint Test
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8001/api/v1/watchmanagement/connection-status
```
Expected: Valid JSON response, no Decimal error

---

## ALTERNATIVES CONSIDERED

### Why Not Fix in Python?
- Less reliable (current attempt failed)
- Requires changes in multiple places
- Error-prone (easy to miss locations)
- Performance overhead

### Why Not Use FastAPI's JSONable Encoder?
- Would require importing and using `jsonable_encoder()` everywhere
- Still wouldn't handle Decimal without custom encoder
- More invasive than SQL fix

### Why Not Custom JSON Encoder?
- Global change affecting entire application
- Unnecessary complexity for 3 locations
- Would mask similar issues in future

---

## SUCCESS CRITERIA

✅ All 3 SQL queries use CAST() to return DOUBLE PRECISION
✅ Remove all failed attempt code from watch_management.py
✅ Device pool tests show 8/8 passing
✅ No "Decimal is not JSON serializable" errors
✅ Code is clean and maintainable

---

## RISK ANALYSIS

### Low Risk
- SQL CAST is standard PostgreSQL operation
- DOUBLE PRECISION is appropriate for time calculations
- Change is localized to 3 query strings
- Reversible if needed

### No Breaking Changes
- API response format unchanged (still returns numbers)
- Clients won't notice difference (float vs Decimal)
- Existing datetime conversion logic untouched

---

## IMPLEMENTATION ORDER

1. **First**: Fix watch_management.py:274 (failing test)
2. **Second**: Fix device_management.py:288 (latent bug)
3. **Third**: Fix watch_management.py:345 (already works, make consistent)
4. **Fourth**: Clean up failed attempt code
5. **Fifth**: Run tests and verify
6. **Sixth**: Document in completion report

---

## LESSONS LEARNED

1. **PostgreSQL type system**: EXTRACT() returns NUMERIC, not FLOAT
2. **Always check SQL return types** when working with numeric calculations
3. **Fix at the source** (SQL) is better than fixing downstream (Python)
4. **Test early**: device_management.py bug would have been caught with proper testing
5. **Don't over-engineer**: Simple SQL CAST is better than complex Python conversion
