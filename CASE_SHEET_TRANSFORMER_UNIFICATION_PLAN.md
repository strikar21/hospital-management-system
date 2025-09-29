# 🔧 Case Sheet Transformer Unification Plan

## 🎯 Objective
Align Case Sheet with existing PatientTransformer system used by other tabs (Medications, Notes, Investigations, Therapy) for consistent data transformation and staff name resolution.

## 📊 Current System Analysis

### ✅ Other Tabs (Working)
- **Service**: PatientCRUDService
- **Transformer**: PatientTransformer + BaseTransformer
- **Data Flow**: Backend → PatientCRUDService → PatientTransformer → Standardized Data → UI
- **Staff Names**: Handled by BaseTransformer.addResolvedNames()
- **Field Names**: Consistent camelCase (`type`, `performedByName`)

### ❌ Case Sheet (Broken)
- **Service**: PatientCaseService (different from others)
- **Transformer**: Inline transformation (lines 35-42)
- **Data Flow**: Backend → PatientCaseService → Inline Transform (FAILS) → Raw Data → UI
- **Staff Names**: Backend does resolution (lines 438-444 in patient_repository.py)
- **Field Names**: Mixed (`entryType` vs `type`, both `performedBy` and `performedByName`)

### 🔍 Root Problem
1. **PatientCaseService import errors** → transformation fails
2. **Raw backend data** (`entryType`) reaches CaseSheetBook
3. **CaseSheetBook expects `type`** → no match found
4. **Result**: "UNKNOWN" badges, "by Unknown" attribution

## 🎯 Proposed Solution: Unified Architecture

### Phase 1: PatientTransformer Enhancement
**File**: `src/utils/transformers/PatientTransformer.ts`

**Add Method**:
```typescript
/**
 * Transform case sheet entries with medical compliance
 */
static transformCaseEntries(data: any[], staffMapping?: { [key: string]: string }): any[] {
  if (!Array.isArray(data)) return [];

  return data.map(entry => {
    // Handle both backend field name variants
    const entryType = entry.entryType || entry.type;

    const transformed = {
      ...entry,
      type: entryType, // Standardize to 'type'
      canEdit: PatientTransformer.canEditMedicalRecord(entry.timestamp || entry.createdAt),
      timestamp: entry.timestamp || entry.createdAt || new Date().toISOString()
    };

    // Apply staff name resolution
    return BaseTransformer.addResolvedNames(transformed, staffMapping);
  });
}
```

### Phase 2: Backend Standardization
**File**: `hospital-backend/app/repositories/patient_repository.py`

**Changes**:
1. **Remove Case-Specific Staff Mapping** (lines 438-444)
   - Delete backend staff name resolution for case entries
   - Let frontend handle staff mapping consistently

2. **Standardize Field Names**:
   ```python
   # Instead of mixed field names, use consistent 'type'
   timeline_entries.append({
       'id': f"alert_{alert['id']}",
       'timestamp': alert['timestamp'],
       'type': 'vitalAlert',  # Use 'type' not 'entryType'
       'description': f"Alert: {alert['message']}",
       'performedBy': 'SYSTEM',  # Only performedBy, no performedByName
       'canEdit': False
   })
   ```

### Phase 3: PatientCaseService Refactor
**File**: `src/services/patient/PatientCaseService.ts`

**Changes**:
1. **Add Missing Import**:
   ```typescript
   import { PatientTransformer } from '../../utils/transformers/PatientTransformer';
   ```

2. **Replace Inline Transformation**:
   ```typescript
   // REMOVE lines 35-42 (inline transformation)
   // REPLACE with:
   const transformedEntries = PatientTransformer.transformCaseEntries(caseEntries, staffMapping);
   ```

3. **Add Staff Mapping Support**:
   ```typescript
   static async getCaseEntries(patientId: string): Promise<any[]> {
     try {
       const [response, staffMapping] = await Promise.all([
         this.fetchFromBackend(`/patients/${patientId}/case-entries`),
         this.getStaffMapping() // Add this method
       ]);

       const caseEntries = response?.caseEntries || [];
       return PatientTransformer.transformCaseEntries(caseEntries, staffMapping);
     } catch (error) {
       console.error('❌ Error fetching case entries:', error);
       return [];
     }
   }
   ```

### Phase 4: Staff Mapping Method
**File**: `src/services/BaseService.ts` or `PatientCaseService.ts`

**Add Method**:
```typescript
/**
 * Get staff ID to name mapping for transformation
 */
protected static async getStaffMapping(): Promise<{ [key: string]: string }> {
  try {
    const response = await this.fetchFromBackend('/staff/mapping');
    return response || {};
  } catch (error) {
    console.warn('⚠️ Staff mapping unavailable:', error);
    return {};
  }
}
```

## 📈 Expected Results

### ✅ After Implementation
1. **Consistent Architecture**: Case sheet uses same transformation as other tabs
2. **Proper Type Badges**: `type` field correctly mapped in CaseSheetBook
3. **Staff Names**: `performedByName` resolved by PatientTransformer
4. **Single Source of Truth**: PatientTransformer handles all medical data transformation
5. **No Duplication**: Remove backend-specific case sheet logic

### 🔧 Data Flow (Unified)
```
Backend (Raw Data)
    ↓
PatientCaseService.getCaseEntries()
    ↓
PatientTransformer.transformCaseEntries()
    ↓
BaseTransformer.addResolvedNames()
    ↓
Standardized Data (type, performedByName)
    ↓
CaseSheetBook (Proper Display)
```

## 🚀 Implementation Order

1. **Add transformCaseEntries() to PatientTransformer**
2. **Add getStaffMapping() to PatientCaseService**
3. **Remove inline transformation from PatientCaseService**
4. **Update PatientCaseService.getCaseEntries() to use PatientTransformer**
5. **Remove backend staff mapping logic for case entries**
6. **Test case sheet display shows proper badges and staff names**

## 📝 Files to Modify

### Frontend
- `src/utils/transformers/PatientTransformer.ts` - Add transformCaseEntries()
- `src/services/patient/PatientCaseService.ts` - Use PatientTransformer
- `src/services/BaseService.ts` - Add getStaffMapping() (if needed)

### Backend
- `hospital-backend/app/repositories/patient_repository.py` - Remove case-specific staff mapping
- `hospital-backend/app/api/v2/patients.py` - Verify consistent field names

## 🎯 Success Criteria
- ✅ Case sheet shows proper type badges instead of "UNKNOWN"
- ✅ Staff names display instead of "by Unknown"
- ✅ Case sheet uses same transformation architecture as other tabs
- ✅ No duplicate staff mapping logic between frontend and backend
- ✅ Consistent camelCase field names throughout system

---

**Status**: Ready for Implementation
**Priority**: High - Fixes core case sheet functionality
**Risk**: Low - Aligns with existing working architecture