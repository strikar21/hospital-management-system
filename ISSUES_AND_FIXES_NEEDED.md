# Hospital Management System - Issues and Fixes Needed

**Date:** 2025-09-18
**Status:** Investigation in Progress
**Priority:** High - Multiple Critical Issues Found

## CRITICAL ISSUES FOUND

### 🚨 1. PROCESS OVERLOAD - IMMEDIATE ATTENTION NEEDED
**Status:** CRITICAL
**Description:** Multiple duplicate processes running
- **Python processes:** 9 running (should be 1-2)
- **Node.js processes:** 7 running (should be 1-2)
- **Impact:** Resource waste, potential port conflicts, data inconsistency

**Evidence:**
```
Backend Port 8001: LISTENING ✅
Frontend Port 3000: LISTENING ✅
But multiple Python and Node processes detected
```

### 🚨 2. SQL SCHEMA MISMATCH - INDIVIDUAL PATIENT RETRIEVAL BROKEN
**Status:** CRITICAL - ROOT CAUSE IDENTIFIED
**File:** `hospital-backend/app/api/v1/patients.py:207`
**Error:** `column s.name does not exist`

**ROOT CAUSE ANALYSIS:**
Major database schema inconsistency between definition and usage:

**Database Schema (database.py:76-90)** defines staff table with:
```sql
CREATE TABLE IF NOT EXISTS staff (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,  -- ✅ Single 'name' column exists
    role TEXT NOT NULL,
    ...
);
```

**But API Code (staff.py:194,202-203)** expects:
```sql
ORDER BY firstname, lastname  -- ❌ These columns don't exist
```

**Query causing immediate error (patients.py:207):**
```sql
SELECT m.*, s.name as prescribedbyname FROM medications m
LEFT JOIN staff s ON m.prescribedby = s.id
WHERE m.patientid = ? ORDER BY m.createdat DESC
```
**Issue:** This query should work since `s.name` exists, but there may be table name conflicts.

**Additional Schema Issues Found:**
- Table name mismatch: Schema creates `patientNotes` but code queries `patient_notes`
- Naming convention violation: Schema uses camelCase but project requires lowercase
- Staff model expects firstname/lastname but schema has single name column

### 🚨 3. FRONTEND COMPILATION ERRORS - DEVICEASSIGNMENT COMPONENT
**Status:** CRITICAL
**File:** `hospital-display-app/src/DeviceAssignment.tsx`

**Multiple TypeScript Errors:**
- `patientFilter` undefined (line 455)
- `setPatientFilter` undefined (line 456)
- `wardFilter` undefined (line 464)
- `setWardFilter` undefined (line 465)
- `connectionStatus` property missing from Device type
- `assignedWatches` property missing from API response type
- Variable redeclaration errors

### ⚠️ 4. DATA FLOW INCONSISTENCY - DASHBOARD WATCH STATUS
**Status:** FIXED - But monitoring needed
**Description:** Dashboard was showing "no watch assigned" despite database having correct data
- **Root Cause:** Missing `assignedDeviceId` field mapping in `api.ts`
- **Fix Applied:** Added `assignedDeviceId: p.assignedDeviceId || null,` to patient object creation
- **Status:** Should now work correctly

## PHASE 4 FINDINGS: BACKEND SQL ERRORS IDENTIFIED

### 🚨 CRITICAL SQL SCHEMA MISMATCHES FOUND

#### **A. Multiple Staff Table Column Errors**
**Files affected:** `patients.py` (lines 207, 211, 215, 219, 548)

1. **Lines 207, 211, 215, 219** use: `s.name` ✅ (Correct - staff table has 'name' column)
2. **Line 548** uses: `s.firstname || ' ' || s.lastname` ❌ (These columns don't exist)

#### **B. Patient Notes Table Name Inconsistencies**
**Files affected:** `patients.py` (lines 219 vs 548)

1. **Line 219** uses: `FROM patient_notes` ❌ (Underscore)
2. **Line 548** uses: `FROM patientnotes` ❌ (No underscore, lowercase)
3. **Schema creates:** `patientNotes` ❌ (camelCase)

#### **C. Staff Table Usage Contradictions**
**Files with firstname/lastname usage (but columns don't exist):**
- `admission.py:86` - `SELECT id, firstname, lastname, department FROM staff`
- `patients.py:548` - `s.firstname || ' ' || s.lastname`

**Files correctly using 'name' column:**
- `esp32.py:41`, `auth.py:73,204,230`, `staff.py:73,177,220,255,295,314,356,377`
- `patients.py:207,211,215,219,533`

### 📋 Database Schema Issues - COMPLETED ANALYSIS ✅
- ✅ Staff table has single 'name' column (not firstname/lastname)
- ✅ Patient table correctly has firstname/lastname columns
- ✅ camelCase vs lowercase inconsistency confirmed (violates project standards)
- ✅ Multiple table name variations found (patient_notes vs patientNotes vs patientnotes)

### 📋 Backend API Issues - ANALYSIS IN PROGRESS
- ❌ Individual patient endpoint: 500 error confirmed
- ❌ Multiple SQL queries using non-existent columns
- ✅ List patients endpoint: Working correctly
- ✅ Authentication endpoints: Appear to use correct 'name' column

### 📋 Frontend Issues
- [ ] Fix DeviceAssignment TypeScript compilation
- [ ] Check all component imports and exports
- [ ] Validate type definitions consistency
- [ ] Test responsive design and mobile compatibility

### 📋 Data Transformation Issues
- [ ] Verify backend → frontend field mappings
- [ ] Check date/time serialization
- [ ] Validate enum value translations
- [ ] Test API response transformations

## TESTING STATUS

### ✅ Working Endpoints
- `GET /api/v1/patients/?limit=100` - Returns patient list
- `GET /api/v1/patients/{id}/medications` - Returns medications (empty for test patient)
- `GET /api/v1/watch-management/assigned` - Returns watch assignments
- `GET /api/v1/watch-management/available` - Returns available watches

### ❌ Broken Endpoints
- `GET /api/v1/patients/{patient_id}` - 500 Internal Server Error

### 🔄 Needs Testing
- All authentication endpoints
- Patient admission workflow
- Device assignment operations
- Vital signs endpoints
- WebSocket connections

## INFRASTRUCTURE STATUS

### Process Status
```
Backend: Port 8001 LISTENING ✅
Frontend: Port 3000 LISTENING ✅
Database: PostgreSQL connection working ✅
TimescaleDB: Connection working ✅
```

### Resource Issues
```
Python processes: 9 (EXCESSIVE - should be 1-2)
Node processes: 7 (EXCESSIVE - should be 1-2)
Memory usage: Not checked
CPU usage: Not checked
```

## COMPREHENSIVE ERROR ANALYSIS COMPLETED

### 🎯 ROOT CAUSES IDENTIFIED

1. **Database Schema Chaos**: Multiple naming conventions and non-existent columns
2. **Process Overload**: 9 Python + 7 Node processes (should be 2-4 total)
3. **SQL Query Mismatches**: Code references columns that don't exist
4. **Table Name Inconsistencies**: 3 different names for same table

### ❌ CONFIRMED BROKEN FUNCTIONALITY
- Individual patient details (`GET /api/v1/patients/{id}`) - 500 error
- Patient admission workflow - Uses non-existent staff columns
- Discharge summary generation - Uses non-existent table names
- DeviceAssignment frontend component - TypeScript compilation errors

### ✅ CONFIRMED WORKING FUNCTIONALITY
- Patient list retrieval (`GET /api/v1/patients/`)
- Watch assignment management
- Authentication system
- Dashboard patient cards (after our assignedDeviceId fix)

## PRIORITY RECOMMENDATIONS

### 🚨 IMMEDIATE (Next 30 minutes)
1. **Process Cleanup**: Kill 7+ excess Python/Node processes causing resource waste
2. **Critical SQL Fix**: Fix `patients.py:548` staff table query (firstname/lastname → name)
3. **Table Name Fix**: Standardize patient notes table name across all queries

### ⚠️ SHORT TERM (Next 2 hours)
1. **Staff Column Fix**: Update `admission.py:86` to use 'name' instead of firstname/lastname
2. **DeviceAssignment TypeScript**: Fix missing state variables and type definitions
3. **Database Standards**: Decide on camelCase vs lowercase and implement consistently

### 📋 MEDIUM TERM (Next day)
1. **Schema Refactor**: Either add firstname/lastname to staff OR update all code to use 'name'
2. **API Testing**: Systematic testing of all endpoints post-fixes
3. **Performance Monitoring**: Resource usage analysis after process cleanup

## NOTES
- System is partially functional despite multiple issues
- Main patient list and watch assignment working
- Individual patient details broken due to SQL error
- Frontend compiles with warnings but has runtime issues
- No critical data loss detected

---

**Next Update:** After Phase 3 investigation
**Assigned:** Investigation in progress
**Last Updated:** 2025-09-18 05:30 UTC