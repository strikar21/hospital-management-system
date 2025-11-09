# Alert System Root Cause - Database Connection Failure

## Executive Summary

**Problem:** User reports "no alert comes at all now?" despite previous fixes showing API responses with alerts.

**Root Cause:** PostgreSQL/TimescaleDB database connection failure. Backend cannot query database, resulting in 500 Internal Server Error for all API calls.

**Impact:**
- ❌ All API endpoints return 500 errors
- ❌ No patient data can be fetched
- ❌ No alerts can be displayed (even though backend is detecting them)
- ❌ Frontend shows empty/no data
- ✅ Backend IS running and detecting alerts from ESP32 watches
- ✅ Alert detection logic working correctly

## Evidence

### 1. Database Connection Error
```
ConnectionResetError: [WinError 64] The specified network name is no longer available
```

When trying to connect to PostgreSQL:
```python
conn = await asyncpg.connect(
    host='localhost',
    port=5432,
    user='hospital_admin',
    password='hospital_secure_2024',
    database='hospital_management'
)
# Results in: ConnectionResetError
```

### 2. API Returns 500 Errors
```bash
$ curl -k "https://localhost:8001/api/v2/patients/list?showAllDepts=true" -H "Authorization: Bearer NUR0001"

{
    "success": false,
    "errorCode": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred. Please try again later.",
    "timestamp": "2025-11-08T05:20:41.525544Z",
    "path": "/api/v2/patients/list",
    "statusCode": 500
}
```

### 3. Backend Logs Show Continuous Errors
```
INFO:     127.0.0.1:64266 - "GET /api/v2/patients/list?showAllDepts=true HTTP/1.1" 500 Internal Server Error
INFO:     127.0.0.1:63333 - "POST /api/v1/auth/login HTTP/1.1" 500 Internal Server Error
INFO:     127.0.0.1:58542 - "POST /api/v1/audit/log HTTP/1.1" 500 Internal Server Error
```

### 4. Backend IS Detecting Alerts (From ESP32)
```
2025-11-08 00:51:54,314 - app.services.alert_detection_service - WARNING - 🚨 Detected 2 alert(s) for patient 081a5294-da91-4c74-bb8a-e5062f5851dd: {'medium': 1, 'high': 1}
2025-11-08 00:51:54,314 - app.services.alert_detection_service - WARNING -    → [MEDIUM] tachycardia: TACHYCARDIA - HR 142 BPM
2025-11-08 00:51:54,314 - app.services.alert_detection_service - WARNING -    → [HIGH] earlyWarningScoreMedium: NEWS2 Score elevated: 5 (threshold: 5)
```

**This proves:**
- ✅ ESP32 watch is sending vitals
- ✅ Backend is receiving MQTT messages
- ✅ Alert detection logic is working
- ✅ Alerts are being created (or attempted to be created)
- ❌ Database write may be failing (cannot confirm without DB connection)
- ❌ API cannot read alerts from database (connection failure)

## Technical Analysis

### What's Working
1. **Backend Service** - Running on port 8001 (PID 110016)
2. **MQTT Service** - Receiving ESP32 watch data
3. **Alert Detection** - Identifying tachycardia and NEWS2 score elevation
4. **WebSocket** - Service initialized

### What's Broken
1. **PostgreSQL Connection** - Cannot connect to database
2. **API Queries** - All endpoints return 500 errors
3. **Data Persistence** - Unknown if alerts are being saved (cannot verify)
4. **Frontend Data** - Cannot fetch patient list or alerts

### Database Configuration
**Backend expects:**
- Host: localhost
- Port: 5432
- User: hospital_admin
- Password: hospital_secure_2024
- Database: hospital_management

**Alternate configuration found in code:**
- User: hospital_user
- Password: hospital123
- Database: hospitaldb

**Issue:** Multiple database configurations exist, possible mismatch.

## Diagnosis Steps Taken

### Step 1: Attempted Direct Database Query
```python
import asyncpg
conn = await asyncpg.connect(
    host='localhost',
    port=5432,
    user='hospital_admin',
    password='hospital_secure_2024',
    database='hospital_management'
)
```
**Result:** ConnectionResetError - Network connection lost

### Step 2: Attempted API Query
```bash
curl -k "https://localhost:8001/api/v2/patients/list?showAllDepts=true"
```
**Result:** 500 Internal Server Error

### Step 3: Checked Backend Logs
**Result:** Backend running, detecting alerts, but database queries failing

## Root Cause: Database Not Running or Wrong Configuration

### Possible Causes:
1. **PostgreSQL service not running**
2. **Wrong database credentials** (hospital_admin vs hospital_user)
3. **Wrong database name** (hospital_management vs hospitaldb)
4. **Network connectivity issue** (firewall, port conflict)
5. **Database crashed** (needs restart)

## Previous Context (From Summary)

The user previously provided an API response showing 7 alerts:
```json
"alerts":[
  {"id":"05ffa0c5-...","type":"patientWettingElectrodes","status":"active","isAcknowledged":false},
  {"id":"51d0ac6f-...","type":"earlyWarningScoreHigh","status":"active","isAcknowledged":false},
  ...
]
```

**This was working before.** Something changed that broke the database connection.

## Fix Plan

### Option 1: Restart PostgreSQL Service (Most Likely Fix)
```bash
# Windows
net stop postgresql-x64-14  # or whichever version
net start postgresql-x64-14

# Or using services.msc
# Find "postgresql" service and restart it
```

### Option 2: Fix Database Configuration Mismatch
Check which database actually exists and update backend config:
```python
# File: hospital-backend/app/core/database.py
# Current multiple configs:
DATABASE_URL = "postgresql://hospital_admin:hospital_secure_2024@localhost:5432/hospital_management"
DATABASE_URL = "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb"

# Need to use ONE consistent configuration
```

### Option 3: Restart Backend with Correct Config
If database is running but backend has wrong config, restart backend with correct credentials.

### Option 4: Check PostgreSQL is Listening on Port 5432
```bash
netstat -ano | findstr :5432
```

If nothing shows up, PostgreSQL isn't running.

## Action Required

**User needs to:**
1. **Check if PostgreSQL service is running**
   - Open Services (services.msc)
   - Find "postgresql" service
   - Check if it's running
   - If not, start it

2. **Verify database configuration**
   - What is the actual database name? (hospital_management or hospitaldb?)
   - What are the actual credentials? (hospital_admin or hospital_user?)

3. **Restart backend after database is running**

## Why Alert System "Appeared" to Work Before

Looking at the conversation summary, the user provided an API JSON response showing 7 alerts. This means:
- At that point in time, the database WAS working
- API WAS returning alert data
- Something happened SINCE THEN that broke the database connection

**Possible trigger:**
- System restart
- PostgreSQL service stopped
- Network configuration changed
- Too many database connections (connection pool exhausted)

## Next Steps

1. **STOP** all code changes - this is NOT a code issue
2. **FIX** database connection first
3. **TEST** API endpoint returns 200 OK
4. **VERIFY** alerts are in the response
5. **THEN** check frontend display

## Testing After Database Fix

Once database is back online, verify with:

```bash
# Test 1: API returns patient list
curl -k "https://localhost:8001/api/v2/patients/list?showAllDepts=true" \
  -H "Authorization: Bearer NUR0001"

# Expected: 200 OK with JSON response

# Test 2: Check if alerts are in response
# Look for "alerts" array in each patient object

# Test 3: Frontend should display alerts
# Hard refresh browser (Ctrl+Shift+R)
# Login as NUR0001
# Check if alert banners show on patient cards
```

## Conclusion

**Alert acknowledgement code is NOT the problem.**

The issue is infrastructure:
- PostgreSQL database connection is broken
- Backend cannot query any data
- API returns 500 errors for all endpoints
- Frontend receives no data (not even patient list)

**User reported "no alert comes at all now"** - this is because NO DATA comes at all now. The entire system is down due to database connectivity failure.

**Fix the database connection first, then test if alerts display.**
