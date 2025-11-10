# PHASE 6: CONTINUED DOMAIN LAYER ADOPTION + INTEGRATION TESTS

**Date**: 2025-11-10
**Branch**: feat/staff-resolution-standardization
**Status**: 📝 PLANNING
**Prerequisites**: Phase 5 Complete ✅

---

## Executive Summary

Phase 5 successfully created the frontend domain layer (AlertProcessor, VitalsValidator, VitalsFormatter) and applied it to select components. Phase 6 will:

1. **Extend domain layer adoption** to remaining components
2. **Add comprehensive integration tests** for all refactored components
3. **Consolidate remaining duplicate code** across the codebase
4. **Prepare for production deployment** with test coverage

**Estimated Timeline**: 2-3 days

---

## Context from Previous Phases

### Phase 5 Achievements ✅
- Created domain layer classes (697 lines of reusable logic)
- Refactored PatientAlerts.tsx to use AlertProcessor
- Refactored PatientMonitor.tsx to use VitalsFormatter
- Enhanced BaseMedicalRecordService with utilities
- Eliminated 125+ lines of duplicate code
- Created integration tests for PatientMonitor (31 tests passing)

### Remaining Work from Phase 5 "Future Work" Section

From PHASE_5_COMPLETE.md lines 461-484:

**1. Extend Domain Layer** (Low Priority → Now HIGH Priority for Phase 6)
- Create `StaffResolver` domain class for staff name resolution
- Create `PermissionChecker` domain class for role-based permissions
- Move more business logic out of services into domain layer

**2. Add Unit Tests** (Medium Priority → Now HIGH Priority for Phase 6)
- Test AlertProcessor methods
- Test VitalsValidator validation rules
- Test VitalsFormatter formatting logic
- Test BaseMedicalRecordService utilities

**3. Component Refactoring** (Low Priority → Now HIGH Priority for Phase 6)
- Apply domain layer pattern to other components
- Use VitalsFormatter in vitals display components
- Use AlertProcessor in dashboard components

**4. Performance Optimization** (Low Priority → Defer to Phase 7)
- Memoize domain layer computations
- Cache formatted alerts to avoid re-formatting
- Tree-shake unused utility functions

---

## Phase 6 Goals

### Primary Goals:
1. ✅ **Apply domain layer to 5+ additional components**
2. ✅ **Add integration tests for all refactored components**
3. ✅ **Create unit tests for domain layer classes**
4. ✅ **Eliminate remaining duplicate vitals formatting code**

### Secondary Goals:
- Document domain layer usage patterns
- Create developer guide for domain layer
- Improve type safety across domain layer

---

## Task Breakdown

### Task 1: Identify Components for Domain Layer Adoption
**Priority**: HIGH
**Estimated Time**: 30 minutes
**Status**: ✅ COMPLETE (DOMAIN_LAYER_ADOPTION_PLAN.md already created)

From DOMAIN_LAYER_ADOPTION_PLAN.md, remaining high-priority candidates:

**HIGH PRIORITY:**
1. ~~PatientMonitor.tsx~~ ✅ COMPLETE
2. PatientCard/PatientVitalStrip.tsx - Lines 31-92 (vitals display)
3. Dashboard/PatientGrid.tsx - Alert display logic
4. PatientDetail/PatientOverview.tsx - Vitals formatting

**MEDIUM PRIORITY:**
5. BedsideMode/BedsideModeContainer.tsx - Vital status logic
6. ECGViewer/ECGViewerHeader.tsx - Waveform metrics formatting

**Result**: Task 1 already done in previous session.

---

### Task 2: Apply Domain Layer to PatientVitalStrip
**Priority**: HIGH
**Estimated Time**: 45 minutes
**Status**: ⏳ PENDING

**Current Issues** (from DOMAIN_LAYER_ADOPTION_PLAN.md):
- Manual inline formatting (line 91: `${vital.value}${vital.unit}`)
- Vitals formatted in PatientCardContainer.tsx (parent)
- Should use VitalsFormatter for consistency

**Refactoring Plan**:

**Before:**
```typescript
// PatientCardContainer.tsx - parent prepares vitals array
const allVitals = [
  { label: 'HR', value: patient.vitals.heartRate || '--', unit: 'bpm', ... },
  { label: 'SpO2', value: patient.vitals.oxygenSaturation || '--', unit: '%', ... }
];
```

**After:**
```typescript
import { VitalsFormatter } from '@/domain/vitals/VitalsFormatter';

// Use domain layer for formatting
const vitalsData: VitalsData = {
  patientId: patient.id,
  timestamp: new Date().toISOString(),
  heartRate: patient.vitals?.heartRate,
  oxygenSaturation: patient.vitals?.oxygenSaturation,
  temperature: patient.vitals?.skinTemperature,
  // ... rest of vitals
};

const formattedVitals = VitalsFormatter.formatAllVitals(vitalsData, 'C');

const allVitals = [
  {
    label: 'HR',
    value: formattedVitals.heartRate.value.replace(' bpm', ''),
    unit: formattedVitals.heartRate.unit,
    alertStatus: formattedVitals.heartRate.isNormal ? 'normal' : 'warning'
  },
  // ... rest
];
```

**Files to Modify**:
1. `PatientCard/PatientCardContainer.tsx` - Use VitalsFormatter
2. `PatientCard/PatientVitalStrip.tsx` - Remove inline formatting

**Verification**:
- [ ] Vitals display correctly with units
- [ ] Alert status colors match domain layer logic
- [ ] No TypeScript errors
- [ ] Component renders without crashes

---

### Task 3: Apply Domain Layer to PatientGrid (Dashboard)
**Priority**: HIGH
**Estimated Time**: 30 minutes
**Status**: ⏳ PENDING

**Current Issues**:
- Alert severity display uses inline logic
- Should use AlertProcessor.formatAlertForDisplay()

**Refactoring Plan**:

**Before:**
```typescript
// Inline severity logic scattered
<div className={alert.severity === 'critical' ? 'bg-red-500' : ...}>
```

**After:**
```typescript
import { AlertProcessor } from '@/domain/alerts/AlertProcessor';

// Use domain layer
const displayAlerts = alerts.map(AlertProcessor.formatAlertForDisplay);

{displayAlerts.map(alert => (
  <div className={alert.severityClass}>
    <span>{alert.severityIcon}</span>
    <span>{alert.message}</span>
  </div>
))}
```

**Files to Modify**:
1. `Dashboard/PatientGrid.tsx` - Use AlertProcessor

**Verification**:
- [ ] Alert icons display correctly
- [ ] Severity colors match PatientAlerts component
- [ ] No duplicate alert display logic

---

### Task 4: Apply Domain Layer to PatientOverview
**Priority**: MEDIUM
**Estimated Time**: 30 minutes
**Status**: ⏳ PENDING

**Current Issues**:
- Vitals formatted inline in component
- No temperature conversion
- Inconsistent with PatientMonitor

**Refactoring Plan**:

**Before:**
```typescript
<div>{patient.vitals.heartRate} bpm</div>
<div>{patient.vitals.skinTemperature}°C</div>
```

**After:**
```typescript
import { VitalsFormatter } from '@/domain/vitals/VitalsFormatter';

const vitalsData = { /* ... */ };
const formattedVitals = VitalsFormatter.formatAllVitals(vitalsData, 'C');

<div>{formattedVitals.heartRate.value}</div>
<div>{formattedVitals.temperature.value}</div>
```

**Files to Modify**:
1. `PatientDetail/PatientOverview.tsx` - Use VitalsFormatter

**Verification**:
- [ ] Vitals display consistently with PatientMonitor
- [ ] Temperature unit matches system preference
- [ ] Component styling unchanged

---

### Task 5: Create Unit Tests for Domain Layer
**Priority**: HIGH
**Estimated Time**: 2 hours
**Status**: ⏳ PENDING

**Test Files to Create**:

#### 5.1: AlertProcessor.test.ts
**Location**: `domain/alerts/__tests__/AlertProcessor.test.ts`
**Test Count**: ~15 tests

**Test Categories**:
```typescript
describe('AlertProcessor', () => {
  describe('formatAlertForDisplay', () => {
    it('should format critical alert with icon and class');
    it('should handle missing timestamp with fallback');
    it('should include relative timestamp');
  });

  describe('getSeverityIcon', () => {
    it('should return 🚨 for critical');
    it('should return ⚠️ for high');
    it('should return ⚡ for medium');
    it('should return ℹ️ for low');
  });

  describe('groupAlertsByPatient', () => {
    it('should group alerts by patientId');
    it('should handle alerts without patientId');
    it('should sort alerts within groups');
  });

  describe('filterByStatus', () => {
    it('should filter active alerts');
    it('should filter acknowledged alerts');
    it('should support legacy isAcknowledged field');
  });
});
```

**Expected Coverage**: 90%+

#### 5.2: VitalsValidator.test.ts
**Location**: `domain/vitals/__tests__/VitalsValidator.test.ts`
**Test Count**: ~12 tests

**Test Categories**:
```typescript
describe('VitalsValidator', () => {
  describe('validate', () => {
    it('should validate complete vitals data');
    it('should reject missing required fields');
    it('should detect stale timestamp (> 5 minutes)');
    it('should warn about low data quality');
  });

  describe('isWithinDisplayRange', () => {
    it('should validate heart rate 0-300');
    it('should validate SpO2 0-100');
    it('should validate temperature -10 to 60');
  });

  describe('calculateCompleteness', () => {
    it('should return 100% for complete data');
    it('should return 50% for half-missing data');
  });
});
```

**Expected Coverage**: 95%+

#### 5.3: VitalsFormatter.test.ts
**Location**: `domain/vitals/__tests__/VitalsFormatter.test.ts`
**Test Count**: ~20 tests

**Test Categories**:
```typescript
describe('VitalsFormatter', () => {
  describe('formatHeartRate', () => {
    it('should format with bpm unit');
    it('should handle undefined with --');
    it('should round fractional values');
  });

  describe('formatTemperature', () => {
    it('should format Celsius with °C');
    it('should convert Celsius to Fahrenheit');
    it('should handle undefined with --');
  });

  describe('formatBloodPressure', () => {
    it('should format systolic/diastolic');
    it('should handle missing diastolic');
    it('should return --/-- for both missing');
  });

  describe('getHeartRateColor', () => {
    it('should return green for normal (60-90)');
    it('should return yellow for warning (50-100)');
    it('should return red for abnormal (< 50 or > 100)');
  });

  describe('formatAllVitals', () => {
    it('should format all vitals with units');
    it('should include isNormal flags');
    it('should handle partial vitals data');
  });
});
```

**Expected Coverage**: 95%+

#### 5.4: BaseMedicalRecordService.test.ts (already exists)
**Location**: `services/base/__tests__/BaseMedicalRecordService.test.ts`
**Status**: ✅ EXISTS (from Phase 5)

**Expected Coverage**: Already at 90%+

---

### Task 6: Create Integration Tests for Refactored Components
**Priority**: HIGH
**Estimated Time**: 3 hours
**Status**: ⏳ PENDING

**Test Files to Create**:

#### 6.1: PatientVitalStrip.integration.test.tsx
**Location**: `PatientCard/__tests__/PatientVitalStrip.integration.test.tsx`
**Test Count**: ~15 tests

**Test Categories**:
- Vitals formatting with domain layer
- Alert status colors from domain layer
- Infinite scroll rendering
- Click handlers for vital charts
- Edge cases (missing vitals, undefined values)

#### 6.2: PatientGrid.integration.test.tsx
**Location**: `Dashboard/__tests__/PatientGrid.integration.test.tsx`
**Test Count**: ~10 tests

**Test Categories**:
- Alert display with AlertProcessor
- Patient card rendering
- Alert severity icons
- Grid layout (single, dual, quad)

#### 6.3: PatientOverview.integration.test.tsx
**Location**: `PatientDetail/__tests__/PatientOverview.integration.test.tsx`
**Test Count**: ~12 tests

**Test Categories**:
- Vitals display with VitalsFormatter
- Patient metadata display
- Temperature unit conversion
- Edge cases (missing data)

**Total Integration Tests**: ~37 new tests (plus 31 existing = 68 total)

---

### Task 7: Documentation and Developer Guide
**Priority**: MEDIUM
**Estimated Time**: 1 hour
**Status**: ⏳ PENDING

**Documents to Create**:

#### 7.1: DOMAIN_LAYER_USAGE_GUIDE.md
**Content**:
- When to use domain layer classes
- Code examples for each class
- Common patterns and anti-patterns
- Testing guidelines

#### 7.2: Update PHASE_5_COMPLETE.md
**Content**:
- Add "Phase 5 Extension" section
- Document additional components refactored
- Update test coverage metrics

---

## Success Metrics

### Code Quality Metrics:
- ✅ **Domain Layer Adoption**: 8+ components using domain layer (up from 3)
- ✅ **Test Coverage**: 85%+ overall (up from ~40%)
- ✅ **Duplicate Code**: < 10 lines of duplicate formatting logic
- ✅ **TypeScript Errors**: 0 compilation errors

### Test Coverage Metrics:
- ✅ **Unit Tests**: 47+ tests (AlertProcessor, VitalsValidator, VitalsFormatter)
- ✅ **Integration Tests**: 68+ tests (all refactored components)
- ✅ **Test Execution Time**: < 30 seconds for full suite
- ✅ **Test Success Rate**: 100% passing

### Architecture Metrics:
- ✅ **Consistency**: All components use same domain layer
- ✅ **Maintainability**: Single source of truth for formatting
- ✅ **Reusability**: Domain layer used in 8+ components
- ✅ **Documentation**: Developer guide complete

---

## Execution Order

### Week 1, Day 1 (Today): Component Refactoring
1. ✅ Task 1: Already complete (DOMAIN_LAYER_ADOPTION_PLAN.md)
2. ⏳ Task 2: PatientVitalStrip refactoring (45 min)
3. ⏳ Task 3: PatientGrid refactoring (30 min)
4. ⏳ Task 4: PatientOverview refactoring (30 min)
5. Git commit: "refactor: Apply domain layer to remaining components"

**Estimated Time**: 2 hours

### Week 1, Day 2: Unit Testing
1. ⏳ Task 5.1: AlertProcessor unit tests (45 min)
2. ⏳ Task 5.2: VitalsValidator unit tests (30 min)
3. ⏳ Task 5.3: VitalsFormatter unit tests (45 min)
4. Git commit: "test: Add comprehensive unit tests for domain layer"

**Estimated Time**: 2 hours

### Week 1, Day 3: Integration Testing
1. ⏳ Task 6.1: PatientVitalStrip integration tests (1 hour)
2. ⏳ Task 6.2: PatientGrid integration tests (45 min)
3. ⏳ Task 6.3: PatientOverview integration tests (45 min)
4. Git commit: "test: Add integration tests for refactored components"

**Estimated Time**: 2.5 hours

### Week 1, Day 4: Documentation
1. ⏳ Task 7.1: Create DOMAIN_LAYER_USAGE_GUIDE.md (45 min)
2. ⏳ Task 7.2: Update PHASE_5_COMPLETE.md (15 min)
3. Git commit: "docs: Add domain layer usage guide and Phase 6 summary"

**Estimated Time**: 1 hour

**Total Estimated Time**: 7.5 hours (spread across 2-3 days)

---

## Risks and Mitigation

### Risk 1: Breaking Existing Components
**Mitigation**:
- Test each component after refactoring
- Use TypeScript strict checks
- Run full test suite before committing
- Keep old code commented out temporarily

### Risk 2: Test Failures Due to Component Changes
**Mitigation**:
- Update tests to match new domain layer usage
- Use flexible test assertions (check for presence, not exact matches)
- Mock domain layer in component tests if needed

### Risk 3: Time Overruns
**Mitigation**:
- Break tasks into smaller sub-tasks
- Commit after each completed task
- Prioritize HIGH over MEDIUM tasks
- Defer LOW priority work to Phase 7

---

## Verification Checklist

After each task:
- [ ] TypeScript compiles without errors
- [ ] All tests passing (npm test)
- [ ] Components render correctly
- [ ] No console errors in browser
- [ ] Git commit with descriptive message

After Phase 6 completion:
- [ ] 85%+ test coverage achieved
- [ ] All domain layer classes tested
- [ ] All refactored components tested
- [ ] Documentation complete
- [ ] No duplicate formatting logic remains
- [ ] Developer guide published

---

## Dependencies

**From Phase 5**:
- ✅ Domain layer classes exist (AlertProcessor, VitalsValidator, VitalsFormatter)
- ✅ BaseMedicalRecordService utilities exist
- ✅ PatientAlerts.tsx refactored
- ✅ PatientMonitor.tsx refactored
- ✅ PatientMonitor integration tests complete

**External Dependencies**:
- Jest + @testing-library/react (already installed)
- TypeScript strict mode (already enabled)
- Git (for commits)

---

## Next Steps (Phase 7 Preview)

After Phase 6 completion, Phase 7 will focus on:

1. **Performance Optimization**
   - Memoization for domain layer computations
   - Alert caching to reduce re-formatting
   - Tree-shaking unused utilities

2. **Production Readiness**
   - Security audit (from COMPREHENSIVE_SYSTEM_AUDIT)
   - Compliance validation (DPDP Act 2023)
   - Load testing (100+ concurrent users)

3. **Monitoring and Observability**
   - Health check endpoint
   - Metrics collection (Prometheus)
   - Error tracking (Sentry)

---

## Conclusion

**Phase 6 Status**: 📝 PLANNING COMPLETE, READY TO EXECUTE

Phase 6 will complete the domain layer adoption across the frontend, add comprehensive test coverage, and prepare the codebase for production deployment. By the end of Phase 6:

- ✅ 8+ components using domain layer (vs 3 currently)
- ✅ 85%+ test coverage (vs ~40% currently)
- ✅ 68+ integration tests (vs 31 currently)
- ✅ 47+ unit tests for domain layer (vs 0 currently)
- ✅ Developer guide for domain layer patterns
- ✅ Zero duplicate formatting logic

**Recommendation**: Proceed with Task 2 (PatientVitalStrip refactoring) as the first step.

---

**Phase 6 Plan Complete** 📋
**Date**: 2025-11-10
**Branch**: feat/staff-resolution-standardization
**Ready to Execute**: ✅ YES
