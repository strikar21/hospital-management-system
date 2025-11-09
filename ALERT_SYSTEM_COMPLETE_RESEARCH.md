# Alert System - Complete Research and Status

## Current Situation Analysis

### Backend Status: ✅ WORKING CORRECTLY

1. **API Returns Alerts** - `/api/v2/patients/list` includes alerts array
2. **Alert Structure** - Alerts have `isAcknowledged` field for frontend filtering
3. **Acknowledgement Endpoint** - `POST /api/v2/atomic/patients/{id}/alerts/{id}/acknowledge` works
4. **Database Updates** - Alerts properly marked as `status='acknowledged'`

**Evidence from API Response:**
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

**7 total alerts:**
- 5 active (unacknowledged)
- 2 acknowledged

### Frontend Data Flow: ✅ APPEARS CORRECT

**Step 1:** API Response → `patient.alerts` array
```typescript
// hospital-display-app/src/hooks/usePatientData.ts:42
setPatients(patientData); // Includes patient.alerts
```

**Step 2:** PatientCardContainer receives patient data
```typescript
// hospital-display-app/src/components/PatientCard/PatientCardContainer.tsx:47
const { alerts: realtimeAlerts } = useRealtimeAlerts(patient.id, patient.alerts || []);
```

**Step 3:** useRealtimeAlerts hook processes alerts
```typescript
// hospital-display-app/src/hooks/useRealtimeAlerts.ts:28
const [alerts, setAlerts] = useState<alert[]>(initialAlerts || []);

// Lines 91-95
useEffect(() => {
  if (initialAlerts && initialAlerts.length > 0) {
    setAlerts(initialAlerts);
  }
}, [initialAlerts]);
```

**Potential Issue:** Conditional check `if (initialAlerts && initialAlerts.length > 0)` might not update properly when array reference changes.

**Step 4:** PatientCardContainer filters alerts
```typescript
// Lines 65, 75-77, 80-83
const displayedAlerts = realtimeAlerts;

const alertsWithFallRisk = useMemo(() => {
  return [...(displayedAlerts || [])];
}, [displayedAlerts]);

const unacknowledgedAlerts = useMemo(() =>
  alertsWithFallRisk.filter(alert => !alert.isAcknowledged),
  [alertsWithFallRisk]
);
```

**Step 5:** Alerts displayed in two components

### Alert Display Components

#### 1. PatientCardAlerts (Alert Banner)
**File:** `hospital-display-app/src/components/PatientCard/PatientCardAlerts.tsx`
**Location:** Top banner showing alert count and color
**Code:**
```typescript
// Lines 44-65
<div className={`absolute top-0 left-0 right-0 text-white text-xs px-2 py-1 rounded-t-xl flex items-center justify-between z-10 ${
  unacknowledgedAlerts.some(alert => alert.severity === 'critical')
    ? 'bg-red-600'
    : unacknowledgedAlerts.some(alert => alert.severity === 'high' || alert.severity === 'medium')
    ? 'bg-orange-500'
    : unacknowledgedAlerts.length > 0
    ? 'bg-yellow-500'
    : 'bg-green-600'
}`}>
  <div className="flex items-center space-x-1">
    <AlertTriangle className={`w-3 h-3 ${
      unacknowledgedAlerts.length > 0 ? 'animate-pulse' : ''
    }`} />
    <span className="font-medium">
      {unacknowledgedAlerts.length > 0 ? 'ALERTS PRESENT' : 'ALL NORMAL'}
    </span>
  </div>
  <div className="bg-black bg-opacity-20 px-1 rounded text-xs font-bold">
    {unacknowledgedAlerts.length}
  </div>
</div>
```

**Issue:** `handleAcknowledgeClick` defined but never used (Line 29 warning)

#### 2. PatientCardHeader (Alert List + Acknowledge Button)
**File:** `hospital-display-app/src/components/PatientCard/PatientCardHeader.tsx`
**Location:** Header section, shows top 2 alerts inline
**Code:**
```typescript
// Lines 84-124
{unacknowledgedAlerts.length > 0 && (
  <div className="flex items-center space-x-2 ml-2">
    <div className="flex flex-col space-y-1 max-w-[150px]">
      {unacknowledgedAlerts
        .slice(0, 2)
        .map((alert) => (
          <div key={alert.id} className={`text-xs px-2 py-1 rounded flex items-center overflow-hidden ${
            alert.severity === 'critical' ? 'text-red-700 bg-red-100' :
            alert.severity === 'high' ? 'text-orange-700 bg-orange-100' :
            'text-yellow-700 bg-yellow-100'
          }`}>
            <span className="flex-shrink-0">
              {alert.severity === 'critical' ? '🚨' : alert.severity === 'high' ? '⚠️' : '⚡'}
            </span>
            <span className="ml-1 truncate">{alert.message}</span>
          </div>
        ))}
    </div>

    {/* Acknowledge Button - Only the 2 visible alerts */}
    <button
      onClick={(e) => {
        e.stopPropagation();
        // Only acknowledge the top 2 displayed alerts
        unacknowledgedAlerts
          .slice(0, 2)
          .forEach(alert => {
            if (!alert.id.includes('fall-risk') &&
                !alert.id.includes('arrhythmia') &&
                !alert.id.includes('seizure')) {
              handleAcknowledgeClick(e, alert.id);
            }
          });
      }}
      className="w-6 h-6 bg-green-600 hover:bg-green-700 text-white rounded flex items-center justify-center flex-shrink-0"
      title="Acknowledge visible alerts"
    >
      <CheckCircle className="w-3 h-3" />
    </button>
  </div>
)}
```

### Acknowledgement Flow: ✅ WORKING CORRECTLY

**Step 1:** User clicks acknowledge button in PatientCardHeader
```typescript
// hospital-display-app/src/components/PatientCard/PatientCardHeader.tsx:110-116
unacknowledgedAlerts
  .slice(0, 2)
  .forEach(alert => {
    if (!alert.id.includes('fall-risk') &&
        !alert.id.includes('arrhythmia') &&
        !alert.id.includes('seizure')) {
      handleAcknowledgeClick(e, alert.id);
    }
  });
```

**Step 2:** handleAcknowledgeClick calls onAcknowledgeAlert prop
```typescript
// Lines 30-41
const handleAcknowledgeClick = (e: React.MouseEvent, alertId: string) => {
  e.stopPropagation();
  if (onAcknowledgeAlert) {
    onAcknowledgeAlert(patient, alertId);
    auditService.logPatientInteraction(
      'acknowledgeAlert',
      patient.id,
      `acknowledged alert ${alertId}`,
      { alertId: alertId }
    );
  }
};
```

**Step 3:** onAcknowledgeAlert traces back to useDashboard
```typescript
// hospital-display-app/src/hooks/useDashboard.ts:178-188
const handleAcknowledgeAlert = async (patient: patient, alertId: string) => {
  try {
    await PatientService.acknowledgeAlert(patient.id, alertId, currentUser.id);

    // Refetch fresh patient data from backend (single source of truth)
    loadPatients();

    const existingTimeout = alertTimeoutsRef.current.get(alertId);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
    }
```

**Step 4:** PatientService forwards to AlertService
```typescript
// hospital-display-app/src/services/patient/index.ts:86-88
static async acknowledgeAlert(patientId: string, alertId: string, userId: string) {
  return PatientCaseService.acknowledgeAlert(patientId, alertId, userId);
}

// hospital-display-app/src/services/patient/PatientCaseService.ts:89-95
static async acknowledgeAlert(patientId: string, alertId: string, userId: string): Promise<boolean> {
  return AlertService.acknowledgeAlert(patientId, alertId, userId);
}
```

**Step 5:** AlertService makes API call
```typescript
// hospital-display-app/src/services/AlertService.ts:66-89
static async acknowledgeAlert(patientId: string, alertId: string, userId: string): Promise<boolean> {
  try {
    await this.fetchFromBackend(
      `/atomic/patients/${patientId}/alerts/${alertId}/acknowledge`,
      {
        method: 'POST',
        body: JSON.stringify({
          acknowledgedBy: userId,
          alertId: alertId
        })
      }
    );

    return true;
  } catch (error) {
    console.error('Error acknowledging alert:', error);
    return false;
  }
}
```

**Step 6:** Backend updates database (✅ Working - confirmed in previous tests)

**Step 7:** loadPatients() refetches data
```typescript
// hospital-display-app/src/hooks/usePatientData.ts:25-51
const loadPatients = useCallback(async () => {
  setLoading(true);
  setError(null);

  try {
    let patientData: patient[];

    if (selectedWard === 'My Patients') {
      patientData = await PatientService.getPatients(undefined, undefined, true);
    } else if (showAllDepartments || selectedWard === 'All Departments') {
      patientData = await PatientService.getPatients(undefined, undefined, true);
    } else {
      patientData = await PatientService.getPatients(selectedWard, selectedWard, false);
    }

    setPatients(patientData); // ← Updates patients with new alert data
    setLastSync(new Date());
  } catch (error) {
    setError(error instanceof Error ? error.message : 'Failed to load patients');
  } finally {
    setLoading(false);
  }
}, [selectedWard, showAllDepartments]);
```

**Step 8:** New patient data flows back through PatientCardContainer → useRealtimeAlerts

### Potential Issues

#### Issue 1: useRealtimeAlerts Conditional Update
**Location:** `hospital-display-app/src/hooks/useRealtimeAlerts.ts:91-95`

```typescript
useEffect(() => {
  if (initialAlerts && initialAlerts.length > 0) { // ← Might not update properly
    setAlerts(initialAlerts);
  }
}, [initialAlerts]);
```

**Why This Could Be a Problem:**
- React's dependency array tracks object/array references
- If `initialAlerts` array reference doesn't change, effect won't run
- If condition isn't met, state won't update

**Potential Fix:**
```typescript
// Option 1: Always sync (simple)
useEffect(() => {
  setAlerts(initialAlerts || []);
}, [initialAlerts]);

// Option 2: Stringify for comparison (more robust)
useEffect(() => {
  setAlerts(initialAlerts || []);
}, [JSON.stringify(initialAlerts)]);

// Option 3: Deep comparison using useMemo
const alertIds = useMemo(() =>
  initialAlerts?.map(a => a.id).join(','),
  [initialAlerts]
);

useEffect(() => {
  setAlerts(initialAlerts || []);
}, [alertIds]);
```

#### Issue 2: handleAcknowledgeClick Not Used in PatientCardAlerts
**Location:** `hospital-display-app/src/components/PatientCard/PatientCardAlerts.tsx:29`

The component defines `handleAcknowledgeClick` but never uses it. The actual acknowledge button is in PatientCardHeader, not PatientCardAlerts.

**This is not a bug** - just unused code that should be cleaned up.

### Expected vs Actual Behavior

#### Expected Behavior:
1. Dashboard loads → Shows 5 unacknowledged alerts on patient card
2. Alert banner shows "ALERTS PRESENT" with count "5"
3. Patient header shows top 2 alerts inline with checkmark button
4. User clicks checkmark → Acknowledges top 2 alerts
5. API call succeeds → Backend updates database
6. loadPatients() refetches → New data has 3 unacknowledged, 4 acknowledged
7. useRealtimeAlerts updates → realtimeAlerts = [3 unacknowledged]
8. Frontend filters → unacknowledgedAlerts = [3 alerts]
9. UI updates → Banner shows "3", top 2 different alerts visible

#### Actual Behavior (User Reports):
- "no alert comes at all now?"
- Alerts not displaying despite being in API response

### Diagnostic Questions for User

1. **Do you see any alerts on the dashboard?**
   - Check alert banner (top of patient card - colored bar)
   - Check patient header (inline alerts with emoji icons)

2. **What do you see in browser console? (F12 → Console)**
   - Any errors?
   - Any warnings about "isAcknowledged"?
   - Any WebSocket connection messages?

3. **When you click acknowledge, what happens?**
   - Does button respond (visual feedback)?
   - Does network tab show API call?
   - Does anything change on screen?

4. **What browser are you using?**
   - Chrome/Edge (need hard refresh: Ctrl+Shift+R)
   - Firefox
   - Safari

### Next Steps Based on Research

#### If alerts ARE displaying but acknowledgement isn't working:
- Focus on useRealtimeAlerts sync issue
- Fix conditional check in useEffect

#### If alerts are NOT displaying at all:
- Check if WebSocket is overriding API data
- Check if frontend build is stale (need to rebuild)
- Check browser console for JavaScript errors
- Verify patient.alerts is populated (add console.log)

#### If everything looks correct but user still reports issues:
- Ask user to provide screenshot
- Ask user to check specific patient ID
- Ask user to provide browser console output

### Files Involved

**Backend (All Working ✅):**
1. `hospital-backend/app/repositories/patient_repository.py` - Queries with alerts
2. `hospital-backend/app/services/patient_service.py` - Adds isAcknowledged field
3. `hospital-backend/app/services/alert_manager_service.py` - Alert lifecycle
4. `hospital-backend/app/api/v2/atomic_medical.py` - Acknowledgement endpoint

**Frontend (Need to Verify):**
1. `hospital-display-app/src/hooks/useRealtimeAlerts.ts` - ⚠️ Conditional update issue
2. `hospital-display-app/src/hooks/usePatientData.ts` - ✅ Fetches patients
3. `hospital-display-app/src/hooks/useDashboard.ts` - ✅ Handles acknowledgement
4. `hospital-display-app/src/components/PatientCard/PatientCardContainer.tsx` - ✅ Filters alerts
5. `hospital-display-app/src/components/PatientCard/PatientCardAlerts.tsx` - ✅ Alert banner
6. `hospital-display-app/src/components/PatientCard/PatientCardHeader.tsx` - ✅ Alert list + button
7. `hospital-display-app/src/services/AlertService.ts` - ✅ API calls

### Recommendation

**Do NOT make changes yet.** First, ask user to:
1. Hard refresh browser (Ctrl+Shift+R)
2. Check browser console for errors
3. Confirm whether alerts are visible or not
4. Provide screenshot if possible

Once we know the exact symptom, we can apply the right fix.
