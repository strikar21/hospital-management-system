# Atomic Operations Implementation Plan
**Single Source of Truth Architecture**

## Summary

The frontend currently violates atomic operation principles by manually updating state instead of refetching from the backend (single source of truth). This creates data inconsistencies and medical safety risks.

## ❌ Current Issues

### Frontend State Management Violations:
1. **Manual state updates** after atomic operations
2. **Frontend data generation** (IDs, timestamps, history)
3. **Duplicate logic** in component and hook
4. **Multiple sources of truth** (frontend state + backend database)

### Medical Safety Risks:
- Frontend creating medical record IDs
- Frontend generating timestamps for medical actions
- Potential data inconsistencies between frontend and database

## ✅ Atomic Operations Architecture

### Core Principle: **Backend = Single Source of Truth**

```typescript
// CORRECT FLOW:
1. Frontend sends atomic operation request
2. Backend processes atomically (medication + case entry + audit)
3. Frontend refetches fresh data from backend
4. UI updates with authoritative backend data
```

### Key Rules:
- ✅ Backend generates ALL medical data (IDs, timestamps, history)
- ✅ Frontend NEVER modifies medication state locally
- ✅ Frontend ALWAYS refetches after operations
- ✅ Single atomic endpoint per medical action

## 🔧 Implementation Plan

### Phase 1: Create Data Refresh Layer

**File: `hospital-display-app/src/hooks/useDataRefresh.ts`**
```typescript
export const useDataRefresh = (patientId: string) => {
  const refreshMedications = async () => {
    const response = await fetch(`/api/v2/patients/${patientId}/medications`);
    return await response.json();
  };

  const refreshCaseEntries = async () => {
    const response = await fetch(`/api/v2/patients/${patientId}/case-entries`);
    return await response.json();
  };

  const refreshPatientData = async () => {
    const response = await fetch(`/api/v2/patients/${patientId}`);
    return await response.json();
  };

  return { refreshMedications, refreshCaseEntries, refreshPatientData };
};
```

### Phase 2: Fix Medication Status Changes

**Replace manual state updates with refetch:**

**BEFORE (Wrong):**
```typescript
// PatientMedications.tsx:68-83 & usePatientMedications.ts:64-78
setMedications(prev => prev.map(med =>
  med.id === medicationId ? { ...med, status, /* manual updates */ } : med
));
```

**AFTER (Correct):**
```typescript
const response = await atomicStatusChange(medicationId, status);
if (response.success) {
  const freshMedications = await refreshMedications();
  setMedications(freshMedications);

  const freshCaseEntries = await refreshCaseEntries();
  setCaseEntries(freshCaseEntries);
}
```

### Phase 3: Fix Medication Addition

**Replace frontend data generation:**

**BEFORE (Wrong):**
```typescript
// usePatientMedications.ts:134-144
const medicationWithHistory: medication = {
  ...result.medical_record,
  history: [{
    id: 'hist_' + Date.now(),           // Frontend generating ID
    action: 'prescribed' as const,
    timestamp,                          // Frontend timestamp
    performedBy: currentUser.staffId
  }]
};
setMedications(prev => [...prev, medicationWithHistory]);
```

**AFTER (Correct):**
```typescript
const response = await atomicAddMedication(medicationData);
if (response.success) {
  const freshMedications = await refreshMedications();
  setMedications(freshMedications);

  const freshCaseEntries = await refreshCaseEntries();
  setCaseEntries(freshCaseEntries);
}
```

### Phase 4: Consolidate Logic

**Remove duplicate atomic operations:**
1. Keep logic ONLY in `usePatientMedications.ts`
2. Remove atomic operations from `PatientMedications.tsx`
3. Component uses hook functions only

**File: `hospital-display-app/src/hooks/usePatientMedications.ts`**
```typescript
export const usePatientMedications = (patientId: string) => {
  const { refreshMedications, refreshCaseEntries } = useDataRefresh(patientId);

  const handleStatusChange = async (medicationId: string, status: string) => {
    const response = await atomicStatusChange(medicationId, status);
    if (response.success) {
      await refreshMedications();
      await refreshCaseEntries();
    }
  };

  const handleAddMedication = async (medicationData: any) => {
    const response = await atomicAddMedication(medicationData);
    if (response.success) {
      await refreshMedications();
      await refreshCaseEntries();
    }
  };

  return { handleStatusChange, handleAddMedication };
};
```

### Phase 5: Backend Data Authority

**Backend must provide complete medical records:**
- ✅ Backend generates medication IDs
- ✅ Backend generates all timestamps
- ✅ Backend creates medication history
- ✅ Backend handles audit trails
- ✅ Backend returns complete updated records

## 🎯 Expected Outcomes

### Medical Safety:
- ✅ All medical data from authoritative backend
- ✅ No frontend-generated medical records
- ✅ Consistent medication status across UI
- ✅ Complete audit trail integrity

### Data Consistency:
- ✅ Single source of truth (backend database)
- ✅ No stale state in frontend
- ✅ Real-time data accuracy
- ✅ Eliminated data race conditions

### Code Quality:
- ✅ No duplicate atomic operations
- ✅ Clear separation of concerns
- ✅ Simplified state management
- ✅ Easier testing and debugging

## 📋 Implementation Steps

### Step 1: Create Data Refresh Functions
- [ ] Create `useDataRefresh.ts` hook
- [ ] Add medication refresh endpoint
- [ ] Add case entries refresh endpoint

### Step 2: Replace Manual State Updates
- [ ] Fix `usePatientMedications.ts` status change
- [ ] Fix `usePatientMedications.ts` medication addition
- [ ] Remove manual state updates

### Step 3: Remove Duplicate Logic
- [ ] Remove atomic operations from `PatientMedications.tsx`
- [ ] Use only `usePatientMedications.ts` hook
- [ ] Clean up imports

### Step 4: Test Atomic Operations
- [ ] Test medication status changes
- [ ] Test medication addition
- [ ] Verify data consistency
- [ ] Test error handling

### Step 5: Verify Medical Safety
- [ ] Confirm backend generates all medical data
- [ ] Verify audit trail completeness
- [ ] Test data persistence
- [ ] Validate single source of truth

## 🚨 Risk Mitigation

**High Priority**: Fix database function `create_atomic_case_entry` first
**Medium Priority**: Implement proper error handling for failed refreshes
**Low Priority**: Add loading states during refresh operations

## Success Criteria

✅ **No frontend data generation** for medical records
✅ **No manual state updates** after atomic operations
✅ **Single atomic endpoint** per medical action
✅ **Backend authority** for all medical data
✅ **Data consistency** between frontend and database