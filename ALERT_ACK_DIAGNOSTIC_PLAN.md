# Alert Acknowledgement Diagnostic Plan

## Problem Statement
User reports: "it shows alert" (alerts ARE displaying) but "doesn't get updated" (alerts don't disappear after clicking acknowledge)

## What We Know Works ✅
1. **Backend Query** - SQL query returns alerts with json_agg (verified with direct database test)
2. **Backend Service** - patient_service.py processes alerts array (logs show "Retrieved 5 patients with alerts and vitals merged")
3. **Backend Acknowledgement** - Alert status changes to 'acknowledged' in database (verified)
4. **Frontend Logic** - useDashboard.ts calls `loadPatients()` after acknowledgement

## What Might Be Broken ❌

### Hypothesis 1: JSON Serialization Issue
**Theory:** Alerts JSON isn't being properly serialized in API response
**Test:** Add debug logging to see actual API response structure

### Hypothesis 2: Frontend Filtering Issue
**Theory:** Frontend filters out acknowledged alerts, but alert count still shows them
**Test:** Check PatientCardContainer.tsx to see how alerts are filtered

### Hypothesis 3: WebSocket Race Condition
**Theory:** Backend sends stale vitals via WebSocket immediately after acknowledge, overwriting fresh data
**Test:** Check if WebSocket vitals messages include alerts field

### Hypothesis 4: Frontend Caching Issue
**Theory:** usePatientData hook has caching that prevents update
**Test:** Check usePatientData implementation

## Investigation Steps

###Step 1: Add Debug Logging to Backend API Response
**File:** `hospital-backend/app/api/v2/patient_api.py`
**Add:** Logging to see actual alerts being returned in patient list

### Step 2: Check Frontend Alert Filtering
**File:** `hospital-display-app/src/components/PatientCard/PatientCardContainer.tsx`
**Check:** How `patient.alerts` is filtered for display

### Step 3: Check WebSocket Vitals Messages
**File:** `hospital-backend/app/services/websocket_manager.py`
**Check:** If vitals updates include alerts

### Step 4: Check usePatientData Hook
**File:** `hospital-display-app/src/hooks/usePatientData.ts`
**Check:** If there's caching preventing updates

## Next Action
Let's start with Step 1 - check what's actually being returned in the API response.
