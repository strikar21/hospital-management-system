# Watch Display Issue - Diagnosis

**Problem**: Watch details not visible in Patient Detail view or modal

---

## Root Cause Analysis

### Issue #1: Patient Object Not Updated

The `PatientDetailContainer` component:
- Receives initial `patient` prop
- Fetches fresh data in `loadComprehensivePatientData()`
- Updates individual states (medications, notes, etc.)
- **BUT**: Never updates the main `patient` object itself!
- Device fields are on `patient` object, so they're stale/missing

**Location**: [PatientDetailContainer.tsx:62-97](hospital-display-app/src/components/PatientDetail/PatientDetailContainer.tsx#L62-L97)

```typescript
// Fresh data is fetched:
const patientResponse = await PatientCRUDService.getPatientComplete(patient.id);

// But individual states are updated, not patient itself:
if (patientResponse.medications) setMedications(patientResponse.medications);
// ...etc

// The patient prop passed to PatientOverview is still the ORIGINAL prop:
<PatientOverview
  patient={patient}  // ← This is the ORIGINAL patient prop, not fresh data!
  onVitalClick={onVitalClick}
/>
```

### Issue #2: Dashboard Modal Same Problem

The modal receives the patient object from the dashboard patient card, which may or may not have the device fields depending on when the dashboard list was fetched.

---

## Solutions

### Option A: Update Patient State (Recommended)

Add patient state to PatientDetailContainer:

```typescript
const [patientData, setPatientData] = useState(patient);

// In loadComprehensivePatientData:
if (patientResponse) {
  setPatientData(patientResponse);  // Update entire patient object
  if (patientResponse.medications) setMedications(patientResponse.medications);
  // ...
}

// Pass updated patient to Overview:
<PatientOverview
  patient={patientData}  // ← Now has fresh device fields!
  onVitalClick={onVitalClick}
/>
```

### Option B: Pass Device Fields Separately

Extract device fields and pass them as separate props to PatientOverview.

---

## Quick Test

To verify the backend IS returning device data, check browser DevTools:

1. Open DevTools (F12)
2. Go to Network tab
3. Click on Thomas Brown patient card
4. Look for `/api/v2/patients/[id]` request
5. Check Response - should contain:
   - `assignedDeviceId`
   - `deviceSerialNumber`
   - `deviceMacAddress`
   - `deviceFirmwareVersion`
   - `deviceBatteryLevel`
   - `deviceLastSeen`
   - `deviceStatus`

If these fields are present in the response, the issue is confirmed to be the frontend not using the fresh data.

---

## Files to Fix

1. **PatientDetailContainer.tsx**
   - Add `patientData` state
   - Update state when fresh data is fetched
   - Pass `patientData` instead of `patient` to child components

---

## Next Steps

1. Confirm device fields are in API response (check browser DevTools)
2. If yes, implement Option A (update patient state)
3. Test that watch details appear in Overview tab
4. Test that modal shows all device fields
