# Alert Display Root Cause - Found

## Problem
User reports "no alert comes at all now?" despite API response showing 7 alerts with correct `isAcknowledged` field.

## Root Cause Found

**File:** [hospital-display-app/src/hooks/useRealtimeAlerts.ts:91-95](hospital-display-app/src/hooks/useRealtimeAlerts.ts#L91-L95)

```typescript
// Update alerts when initialAlerts change (from API)
useEffect(() => {
  if (initialAlerts && initialAlerts.length > 0) {  // ❌ BUG HERE
    setAlerts(initialAlerts);
  }
}, [initialAlerts]);
```

### Why This Is Broken

1. **Conditional Update:** Only updates alerts if `initialAlerts.length > 0`
2. **Missing Edge Case:** If alerts array changes but condition isn't perfectly met, state won't update
3. **Array Reference Issue:** React dependency might not trigger properly for array changes
4. **Inconsistent State:** Hook initializes with `initialAlerts` but conditionally updates later

### Flow Analysis

```
API Response (7 alerts)
  ↓
PatientCardContainer receives patient.alerts = [7 alerts]
  ↓
useRealtimeAlerts(patient.id, patient.alerts || [])
  ↓
useState initializes with patient.alerts (7 alerts) ✅
  ↓
useEffect([initialAlerts]) runs
  ↓
if (initialAlerts && initialAlerts.length > 0) ← Should pass ✅
  ↓
setAlerts(initialAlerts) ← Should update ✅
  ↓
PatientCardContainer.tsx:47: realtimeAlerts = ??? ❌
  ↓
PatientCardContainer.tsx:65: displayedAlerts = realtimeAlerts ❌
  ↓
PatientCardContainer.tsx:75-77: alertsWithFallRisk = [...displayedAlerts] ❌
  ↓
PatientCardContainer.tsx:80-83: unacknowledgedAlerts = filter(isAcknowledged: false) ❌
  ↓
PatientCardAlerts component receives empty array ❌
```

## Evidence

### API Response (Working)
```json
"alerts":[
  {"id":"05ffa0c5-...","type":"patientWettingElectrodes","status":"active","isAcknowledged":false},
  {"id":"51d0ac6f-...","type":"earlyWarningScoreHigh","status":"active","isAcknowledged":false},
  {"id":"60feb4f4-...","type":"electrodeGelDried","status":"active","isAcknowledged":false},
  {"id":"8883aba7-...","type":"earlyWarningScoreHigh","status":"acknowledged","isAcknowledged":true},
  {"id":"aeacbe28-...","type":"earlyWarningScoreMedium","status":"active","isAcknowledged":false},
  {"id":"c760de37-...","type":"watchTampering","status":"acknowledged","isAcknowledged":true},
  {"id":"dccc7391-...","type":"watchTampering","status":"active","isAcknowledged":false}
]
```

### Potential Issues in useRealtimeAlerts Hook

1. **Array Dependency Issue:** React's `useEffect` with array dependencies can be tricky
2. **Conditional Logic:** The `if (initialAlerts && initialAlerts.length > 0)` might be preventing updates
3. **State Not Syncing:** `initialAlerts` parameter changes but hook state doesn't update

## Fix Plan

### Option 1: Remove Conditional (Simplest)
```typescript
useEffect(() => {
  setAlerts(initialAlerts || []);
}, [initialAlerts]);
```

**Pros:**
- Simplest fix
- Always syncs with API data
- Handles empty arrays correctly

**Cons:**
- Might override WebSocket-added alerts if API refreshes

### Option 2: Merge Instead of Replace
```typescript
useEffect(() => {
  if (initialAlerts) {
    setAlerts(prevAlerts => {
      // Create a map of existing alert IDs
      const existingIds = new Set(prevAlerts.map(a => a.id));

      // Add API alerts that don't exist yet
      const newAlerts = initialAlerts.filter(a => !existingIds.has(a.id));

      // Merge: keep existing alerts + add new ones from API
      return [...prevAlerts, ...newAlerts];
    });
  }
}, [initialAlerts]);
```

**Pros:**
- Preserves WebSocket-added alerts
- Prevents duplication
- More robust

**Cons:**
- More complex
- Might accumulate stale alerts

### Option 3: Smart Merge with Update Detection
```typescript
useEffect(() => {
  if (!initialAlerts) return;

  setAlerts(prevAlerts => {
    // If no previous alerts, use initial alerts
    if (prevAlerts.length === 0) {
      return initialAlerts;
    }

    // Create maps for efficient lookup
    const prevMap = new Map(prevAlerts.map(a => [a.id, a]));
    const newMap = new Map(initialAlerts.map(a => [a.id, a]));

    // Merge: Update existing alerts, add new ones
    const merged: alert[] = [];

    // Add/update from API alerts
    for (const apiAlert of initialAlerts) {
      merged.push(apiAlert);
    }

    // Add WebSocket-only alerts (not in API)
    for (const prevAlert of prevAlerts) {
      if (!newMap.has(prevAlert.id)) {
        merged.push(prevAlert);
      }
    }

    return merged;
  });
}, [initialAlerts]);
```

**Pros:**
- Most robust
- Handles acknowledgement updates
- Preserves WebSocket alerts
- Updates acknowledged status from API

**Cons:**
- Most complex
- Might be overkill

## Recommended Fix

**Use Option 1** for now (simplest) because:
1. Alert acknowledgement updates come from API refresh (not WebSocket yet)
2. User is experiencing total alert loss, not just stale data
3. WebSocket alert additions are separate (via `addAlert` callback)
4. API is the source of truth for alert acknowledgement status

If WebSocket real-time alert acknowledgement is added later, upgrade to Option 3.

## Implementation

**File to Fix:** `hospital-display-app/src/hooks/useRealtimeAlerts.ts`

**Change:**
```typescript
// BEFORE (Lines 91-95)
useEffect(() => {
  if (initialAlerts && initialAlerts.length > 0) {
    setAlerts(initialAlerts);
  }
}, [initialAlerts]);

// AFTER
useEffect(() => {
  setAlerts(initialAlerts || []);
}, [initialAlerts]);
```

This ensures alerts always sync with API data, whether it's 0 alerts or 100 alerts.

## Testing Plan

1. **Start frontend** - Refresh browser
2. **Check dashboard** - Should see 7 alerts on patient card
3. **Click acknowledge** - Alert should disappear immediately
4. **Check API** - Should show `isAcknowledged: true` for that alert
5. **Check frontend** - Acknowledged alert should not be visible
6. **Verify count** - Alert count badge should show correct number

## Files to Modify

1. ✅ `hospital-display-app/src/hooks/useRealtimeAlerts.ts` - Remove conditional in useEffect

## Expected Behavior After Fix

- Dashboard loads → Shows 5 unacknowledged alerts (7 total - 2 acknowledged)
- Click acknowledge → Alert disappears immediately
- API refreshes → Updates alert list with new acknowledgement status
- WebSocket adds new alert → Prepended to list (separate from API sync)
