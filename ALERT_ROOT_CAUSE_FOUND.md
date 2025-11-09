# Alert Acknowledgement Bug - ROOT CAUSE FOUND

## The Problem
**User Report:** "it shows alert" (alerts display) but "doesn't get updated" (after acknowledge, alert doesn't disappear)

## Root Cause Identified ✅

### Backend Returns
```javascript
alert: {
  id: "...",
  status: "acknowledged",  // String: 'active', 'acknowledged', or 'resolved'
  type: "tachycardia",
  severity: "high",
  message: "...",
  acknowledgedBy: "NUR0001",
  acknowledgedAt: "2025-11-07..."
}
```

### Frontend Expects
```javascript
alert: {
  id: "...",
  isAcknowledged: false,  // Boolean!
  type: "tachycardia",
  severity: "high",
  message: "..."
}
```

### Frontend Filtering Code
**File:** `hospital-display-app/src/components/PatientCard/PatientCardContainer.tsx:81`
```typescript
const unacknowledgedAlerts = useMemo(() =>
  alertsWithFallRisk.filter(alert => !alert.isAcknowledged),  // ❌ WRONG FIELD!
  [alertsWithFallRisk]
);
```

**PROBLEM:** Frontend filters by `!alert.isAcknowledged` but backend provides `alert.status === 'active' | 'acknowledged' | 'resolved'`

## Why It Fails
1. User clicks "Acknowledge" button
2. Backend correctly updates `status` to `'acknowledged'` in database ✅
3. Frontend calls `loadPatients()` to refresh ✅
4. Backend returns alert with `status: 'acknowledged'` ✅
5. **Frontend filter checks `!alert.isAcknowledged`** ❌
6. **`alert.isAcknowledged` is `undefined` (not a field)** ❌
7. **`!undefined` evaluates to `true`** ❌
8. **Alert is NOT filtered out, still shows!** ❌

## The Fix

### Option 1: Backend Adds `isAcknowledged` Field (Recommended)
Add computed property in `patient_service.py` when processing alerts:
```python
for alert in alerts_data:
    alert_camel = self.patient_repository.transform_to_camel_case(alert)
    # Add isAcknowledged boolean for frontend compatibility
    alert_camel['isAcknowledged'] = alert['status'] == 'acknowledged'
    processed_alerts.append(alert_camel)
```

### Option 2: Frontend Uses `status` Field
Change frontend filter to:
```typescript
const unacknowledgedAlerts = useMemo(() =>
  alertsWithFallRisk.filter(alert => alert.status === 'active'),
  [alertsWithFallRisk]
);
```

**Recommendation:** Option 1 is better - maintain backward compatibility and cleaner frontend code.

## Files to Fix

### Backend
**File:** `hospital-backend/app/services/patient_service.py`
- **Method:** `get_all()` (lines 415-434)
- **Method:** `get_complete_patient_data()` (lines 57-85)
- **Change:** Add `isAcknowledged` boolean when processing alerts

### No Frontend Changes Needed!
Frontend code is correct - it just expects the backend to provide the `isAcknowledged` field.

## Test Plan
1. Restart backend with fix
2. Open frontend dashboard
3. Click acknowledge on any alert
4. **Expected:** Alert disappears immediately
5. **Expected:** Alert count badge decreases
6. **Expected:** Other alerts move up to be visible
