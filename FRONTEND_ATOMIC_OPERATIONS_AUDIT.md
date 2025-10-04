# Frontend Atomic Operations Audit & Plan

## Current State Issues

### ❌ CRITICAL: Multiple Sources of Truth

**Frontend violates single source of truth principle:**

1. **Medications Data**: Frontend maintains local state AND manually updates it
2. **Duplicate Logic**: Both `PatientMedications.tsx` AND `usePatientMedications.ts` have identical atomic operations
3. **Manual State Updates**: Frontend updates medication status locally instead of refetching from backend
4. **Frontend Data Generation**: Creating medication history, IDs, timestamps on frontend

### ❌ Specific Violations Found

#### PatientMedications.tsx (Lines 68-83):
```typescript
// WRONG: Manual frontend state update after atomic operation
setMedications(prev => prev.map(med =>
  med.id === medicationId ? {
    ...med,
    status,
    modifiedBy: currentUser.staffId,
    updatedat: new Date().toISOString(),  // Frontend generating timestamps
    canEdit: PatientService.canEditItem(...),
    history: [...(med.history || []), {    // Frontend creating history
      id: 'hist_' + Date.now(),           // Frontend generating IDs
      action: status === 'active' ? 'resumed' : status,
      timestamp: new Date().toISOString(),
      performedBy: currentUser.staffId
    }]
  } : med
));
```

#### usePatientMedications.ts (Lines 64-78):
```typescript
// SAME VIOLATION: Identical manual state update
setMedications(prev => prev.map(med => /* ... same logic ... */));
```

#### usePatientMedications.ts (Lines 134-144):
```typescript
// WRONG: Frontend creating medication data
const medicationWithHistory: medication = {
  ...result.medical_record,
  history: [{                            // Frontend creating history
    id: 'hist_' + Date.now(),           // Frontend generating IDs
    action: 'prescribed' as const,
    timestamp,                          // Frontend timestamp
    performedBy: currentUser.staffId
  }]
};
```

## ✅ Correct Atomic Operations Architecture

### Single Source of Truth Principle:
1. **Backend**: Only source of medication data, IDs, timestamps, history
2. **Frontend**: Display layer only, refetches data after operations
3. **No Manual Updates**: Frontend never modifies data locally

### Correct Flow:
```typescript
// CORRECT: Atomic operation + refetch
const response = await atomicOperation();
if (response.success) {
  // Refetch fresh data from backend (single source of truth)
  await refreshMedicationsFromBackend();
}
```

## 🔧 Required Frontend Changes

### 1. Create RefreshData Function
```typescript
const refreshMedications = async () => {
  const response = await fetch(`/api/v2/patients/${patient.id}/medications`);
  const medications = await response.json();
  setMedications(medications);
};
```

### 2. Replace Manual Updates with Refetch
**BEFORE (Wrong):**
```typescript
setMedications(prev => prev.map(med => ...)); // Manual update
```

**AFTER (Correct):**
```typescript
const response = await atomicOperation();
if (response.success) {
  await refreshMedications(); // Single source of truth
}
```

### 3. Remove Duplicate Logic
- Keep logic in `usePatientMedications.ts` only
- Remove atomic operations from `PatientMedications.tsx`
- Use hook in component

### 4. Backend-Only Data Generation
- Remove frontend ID generation (`'hist_' + Date.now()`)
- Remove frontend timestamp generation
- Remove frontend history creation
- Let backend handle all data creation

## 📋 Implementation Plan

### Phase 1: Data Fetching Layer
1. Create `refreshMedications()` function
2. Create `refreshCaseEntries()` function
3. Create `refreshPatientData()` function

### Phase 2: Replace Manual Updates
1. Fix medication status changes to use refetch
2. Fix medication addition to use refetch
3. Fix medication administration to use refetch

### Phase 3: Consolidate Logic
1. Remove atomic operations from `PatientMedications.tsx`
2. Use only `usePatientMedications.ts` hook
3. Remove duplicate imports and logic

### Phase 4: Clean Frontend Data Generation
1. Remove all frontend ID generation
2. Remove all frontend timestamp generation
3. Remove all frontend history creation
4. Trust backend as single source

## 🎯 Expected Benefits

### Single Source of Truth:
- ✅ Backend controls all medical data
- ✅ Frontend displays fresh data always
- ✅ No data inconsistencies
- ✅ No stale state issues

### Simplified Frontend:
- ✅ No complex state management
- ✅ No duplicate logic
- ✅ Clear separation of concerns
- ✅ Easier debugging

### Medical Safety:
- ✅ All medication data from database
- ✅ No frontend-generated medical records
- ✅ Atomic operations guaranteed
- ✅ Audit trail integrity

## 🚨 Current Risk Assessment

**HIGH RISK**: Frontend generating medical data (IDs, timestamps, history)
**MEDIUM RISK**: Manual state updates creating data inconsistencies
**LOW RISK**: Duplicate logic maintenance overhead

## Next Steps

1. Implement data refresh functions
2. Replace all manual state updates with refetch calls
3. Remove frontend data generation
4. Test atomic operations end-to-end
5. Verify single source of truth compliance