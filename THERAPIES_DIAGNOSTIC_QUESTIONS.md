# Therapies Diagnostic Questions

**User Report:** "notes work, therapies dont."

**Frontend Status:** ✅ Running without compilation errors

---

## Questions for User:

### 1. What specifically doesn't work with therapies?
- [ ] Cannot see therapies list?
- [ ] Cannot add new therapy (button doesn't work)?
- [ ] Can add but get error message?
- [ ] Therapies added but don't show in list?
- [ ] Cannot complete/cancel therapies?
- [ ] Cannot add therapy sessions?
- [ ] Other specific issue?

### 2. Error Messages?
- Do you see any error alerts/messages when using therapies?
- Do you see any console errors (F12 → Console tab)?

### 3. Backend Running?
- Is backend running on port 8001?
- Do other features work (medications, investigations)?

---

## Code Analysis Results:

### ✅ Architecture Looks Correct:

**PatientTherapiesContainer.tsx:**
- Properly uses `usePatientTherapies` hook ✅
- Passes all required props ✅
- Structure matches working Medications pattern ✅

**usePatientTherapies.ts:**
- Extends `usePatientMedicalRecords` base hook ✅
- Atomic operations configured ✅
- Service calls look correct ✅

**TherapyService.ts:**
- Extends `BaseMedicalRecordService<therapy>` ✅
- Has atomic operations: addTherapySessionAtomic, completeTherapyAtomic, cancelTherapyAtomic ✅
- Payload transformation present ✅

### 🔍 Potential Issues to Investigate:

1. **Backend Endpoint Mismatch?**
   - TherapyService uses: `/atomic/patients/${patientId}/therapies`
   - Does backend have this endpoint?

2. **Field Mapping Issues?**
   - transformAddPayload maps: `therapy.type` → `therapyType`
   - Backend expects: `therapyType` not `type`
   - Is this mapping correct for your backend?

3. **Status Enum Mismatch?**
   - Frontend uses: 'active', 'completed', 'cancelled'
   - Backend expects: 'scheduled', 'in-progress', 'completed', 'discontinued', 'on-hold'
   - Line 44: `status: 'scheduled'` vs line 79: `status: 'active'`

4. **Missing patientId prop?**
   - Hook uses `props.patient.id` - is patient object passed correctly?

---

## Next Steps:

**Please provide:**
1. Specific error message or behavior you're seeing
2. Browser console errors (if any)
3. Is backend running on port 8001?

**I can then:**
- Check backend API endpoints
- Verify field name alignment
- Fix any Phase 5 regression issues
- Test therapies with actual backend
