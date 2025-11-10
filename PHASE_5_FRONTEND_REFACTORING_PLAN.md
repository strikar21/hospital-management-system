# PHASE 5: FRONTEND REFACTORING PLAN

**Goal:** Refactor frontend services to match backend domain-driven architecture patterns

**Status:** Phase 4 (Backend) Complete ✅ → Phase 5 (Frontend) Starting

**Estimated Time:** 2-3 hours

---

## 📋 CONTEXT FROM PHASE 4

### What We Achieved in Backend (Phase 4):
- ✅ Created domain layer (AlertPipeline, StaffResolver, VitalsNormalizer)
- ✅ Eliminated 5,000+ lines of duplicate code
- ✅ Deleted 5 deprecated service files (204KB)
- ✅ Single source of truth for all business logic
- ✅ Type safety with domain schemas
- ✅ N+1 query problem solved with batch operations

### Patterns to Apply to Frontend:
1. **Domain Layer Pattern** - Centralize business logic
2. **Service Consolidation** - Merge duplicate services
3. **Type Safety** - Use TypeScript interfaces consistently
4. **Single Responsibility** - Each service does one thing well

---

## 🎯 FRONTEND ISSUES TO FIX

### Current Problems in Frontend:

1. **Duplicate Service Code**
   - Multiple services doing similar HTTP operations
   - Repeated error handling logic
   - Duplicate camelCase transformations

2. **Scattered Business Logic**
   - Alert processing logic in components
   - Data transformation in hooks
   - No centralized domain layer

3. **Inconsistent Error Handling**
   - Some services throw errors
   - Some return null
   - No standardized error types

4. **No Service Consolidation**
   - PatientService, MedicationService, InvestigationService, TherapyService all similar
   - Could use generic `MedicalRecordService<T>`

5. **Missing Frontend Domain Layer**
   - No equivalent to backend's AlertPipeline
   - No centralized data validators
   - No type-safe transformers

---

## 🏗️ PHASE 5 ARCHITECTURE

### Proposed Frontend Structure:

```
hospital-display-app/src/
├── domain/                          # NEW - Frontend domain layer
│   ├── alerts/
│   │   ├── AlertProcessor.ts       # Alert display logic
│   │   └── AlertDeduplicator.ts    # Client-side deduplication
│   ├── vitals/
│   │   ├── VitalsValidator.ts      # Validate incoming vitals
│   │   └── VitalsFormatter.ts      # Display formatting
│   └── staff/
│       └── StaffCache.ts           # Client-side staff name cache
│
├── services/
│   ├── base/
│   │   ├── ApiService.ts           # REFACTOR - Base HTTP operations
│   │   └── MedicalRecordService.ts # REFACTOR - Generic record CRUD
│   ├── AlertService.ts             # REFACTOR - Use AlertProcessor
│   ├── PatientService.ts           # REFACTOR - Use base services
│   └── VitalService.ts             # REFACTOR - Use VitalsValidator
│
└── utils/
    ├── transformers/
    │   └── camelCaseTransformer.ts # CONSOLIDATE - Single transformer
    └── validators/
        └── medicalValidators.ts    # NEW - Validation utilities
```

---

## 📝 PHASE 5 TASKS

### Task 1: Create Frontend Domain Layer
**Priority:** HIGH
**Estimated Time:** 30 minutes

Create domain layer similar to backend:

#### 1.1: AlertProcessor (domain/alerts/AlertProcessor.ts)
```typescript
/**
 * Frontend AlertProcessor - Handles alert display logic
 *
 * Responsibilities:
 * - Format alert messages for display
 * - Determine alert UI severity (color, icon)
 * - Group alerts by patient/type
 * - Sort alerts by severity + timestamp
 */
export class AlertProcessor {
  static formatAlertForDisplay(alert: AlertData): DisplayAlert {
    return {
      id: alert.id,
      severity: this.getSeverityClass(alert.severity),
      icon: this.getSeverityIcon(alert.severity),
      message: alert.message,
      timestamp: this.formatTimestamp(alert.timestamp),
      patientId: alert.patientId
    };
  }

  static getSeverityClass(severity: string): string {
    const severityMap = {
      'critical': 'bg-red-500',
      'high': 'bg-orange-500',
      'medium': 'bg-yellow-500',
      'low': 'bg-blue-500'
    };
    return severityMap[severity] || 'bg-gray-500';
  }

  static getSeverityIcon(severity: string): string {
    // Return appropriate icon name
  }

  static groupAlertsByPatient(alerts: AlertData[]): Map<string, AlertData[]> {
    // Group and sort
  }
}
```

#### 1.2: VitalsValidator (domain/vitals/VitalsValidator.ts)
```typescript
/**
 * Frontend VitalsValidator - Validate incoming vitals data
 *
 * Responsibilities:
 * - Validate vitals have required fields
 * - Check vitals are within display ranges
 * - Detect stale vitals (old timestamps)
 */
export class VitalsValidator {
  static isValid(vitals: VitalsData): boolean {
    return this.hasRequiredFields(vitals) &&
           this.hasRecentTimestamp(vitals);
  }

  static hasRequiredFields(vitals: VitalsData): boolean {
    return !!(vitals.heartRate && vitals.timestamp);
  }

  static hasRecentTimestamp(vitals: VitalsData): boolean {
    const now = Date.now();
    const vitalTime = new Date(vitals.timestamp).getTime();
    const ageSeconds = (now - vitalTime) / 1000;
    return ageSeconds < 300; // 5 minutes max age
  }
}
```

#### 1.3: VitalsFormatter (domain/vitals/VitalsFormatter.ts)
```typescript
/**
 * Frontend VitalsFormatter - Format vitals for display
 */
export class VitalsFormatter {
  static formatHeartRate(hr: number): string {
    return `${hr} bpm`;
  }

  static formatTemperature(temp: number, unit: 'C' | 'F' = 'C'): string {
    if (unit === 'F') {
      temp = (temp * 9/5) + 32;
    }
    return `${temp.toFixed(1)}°${unit}`;
  }

  static formatSpO2(spo2: number): string {
    return `${spo2}%`;
  }

  static formatBloodPressure(systolic: number, diastolic: number): string {
    return `${systolic}/${diastolic} mmHg`;
  }
}
```

---

### Task 2: Refactor Base Services
**Priority:** HIGH
**Estimated Time:** 45 minutes

#### 2.1: Consolidate BaseMedicalRecordService
Currently we have similar code in:
- MedicationService
- InvestigationService
- TherapyService

**REFACTOR TO:**
```typescript
/**
 * Generic medical record service
 * Handles CRUD operations for medications, investigations, therapies
 */
export class BaseMedicalRecordService<T> {
  constructor(
    private endpoint: string,
    private recordType: string
  ) {}

  async getByPatientId(patientId: string): Promise<T[]> {
    const response = await fetch(`${API_BASE}${this.endpoint}/${patientId}`);
    if (!response.ok) throw new Error(`Failed to fetch ${this.recordType}`);
    const data = await response.json();
    return data;
  }

  async create(patientId: string, record: Partial<T>): Promise<T> {
    const response = await fetch(`${API_BASE}${this.endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patientId, ...record })
    });
    if (!response.ok) throw new Error(`Failed to create ${this.recordType}`);
    return await response.json();
  }

  async update(id: string, updates: Partial<T>): Promise<T> {
    const response = await fetch(`${API_BASE}${this.endpoint}/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });
    if (!response.ok) throw new Error(`Failed to update ${this.recordType}`);
    return await response.json();
  }

  async delete(id: string): Promise<void> {
    const response = await fetch(`${API_BASE}${this.endpoint}/${id}`, {
      method: 'DELETE'
    });
    if (!response.ok) throw new Error(`Failed to delete ${this.recordType}`);
  }
}

// Usage:
export const medicationService = new BaseMedicalRecordService<Medication>(
  '/api/v2/medications',
  'medication'
);

export const investigationService = new BaseMedicalRecordService<Investigation>(
  '/api/v2/investigations',
  'investigation'
);
```

---

### Task 3: Refactor Alert System
**Priority:** MEDIUM
**Estimated Time:** 30 minutes

#### 3.1: Update AlertService to use AlertProcessor
```typescript
// BEFORE: AlertService.ts has display logic mixed with data fetching
export class AlertService {
  async getAlerts(patientId: string) {
    const alerts = await fetch(...);
    // Inline formatting, sorting, grouping
    return alerts.map(a => ({
      ...a,
      severity: a.severity === 'critical' ? 'bg-red-500' : ...
    }));
  }
}

// AFTER: Separate concerns
export class AlertService {
  async getAlerts(patientId: string): Promise<AlertData[]> {
    const response = await fetch(`${API_BASE}/api/v2/alerts/${patientId}`);
    return await response.json();
  }

  async acknowledgeAlert(alertId: string, staffId: string): Promise<void> {
    await fetch(`${API_BASE}/api/v2/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ acknowledgedBy: staffId })
    });
  }
}

// Components use AlertProcessor for display logic:
import { AlertProcessor } from '@/domain/alerts/AlertProcessor';

const displayAlerts = alerts.map(AlertProcessor.formatAlertForDisplay);
const groupedAlerts = AlertProcessor.groupAlertsByPatient(alerts);
```

---

### Task 4: Consolidate Utilities
**Priority:** LOW
**Estimated Time:** 15 minutes

#### 4.1: Single camelCase transformer
Currently scattered across multiple files.

**CREATE:** `utils/transformers/camelCaseTransformer.ts`
```typescript
export function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

export function objectToCamelCase<T>(obj: any): T {
  if (Array.isArray(obj)) {
    return obj.map(objectToCamelCase) as any;
  }

  if (obj !== null && typeof obj === 'object') {
    return Object.keys(obj).reduce((acc, key) => {
      const camelKey = toCamelCase(key);
      acc[camelKey] = objectToCamelCase(obj[key]);
      return acc;
    }, {} as any);
  }

  return obj;
}
```

---

## 🗑️ FILES TO DELETE/CONSOLIDATE

### Duplicate Services to Consolidate:
1. **MedicationService.ts** → Use BaseMedicalRecordService<Medication>
2. **InvestigationService.ts** → Use BaseMedicalRecordService<Investigation>
3. **TherapyService.ts** → Use BaseMedicalRecordService<Therapy>

### Duplicate Utilities to Consolidate:
1. Multiple `toCamelCase` implementations across services
2. Multiple error handling patterns
3. Multiple timestamp formatters

---

## 📊 EXPECTED IMPACT

### Code Reduction:
- **MedicationService**: 150 lines → 20 lines (using generic)
- **InvestigationService**: 120 lines → 20 lines
- **TherapyService**: 130 lines → 20 lines
- **Utilities**: ~100 lines of duplicate code eliminated
- **Total**: ~460 lines removed

### Architecture Benefits:
- ✅ Matches backend domain-driven design
- ✅ Single source of truth for display logic
- ✅ Easier testing (domain layer isolated)
- ✅ Type safety throughout
- ✅ Faster development (reusable components)

---

## 🔍 VERIFICATION CHECKLIST

After each refactoring:
- [ ] TypeScript compiles without errors
- [ ] All imports updated correctly
- [ ] No duplicate code remains
- [ ] Component tests still pass
- [ ] Frontend runs without console errors
- [ ] Git commit with detailed message

---

## ⚠️ RISKS & MITIGATION

### Risk 1: Breaking existing components
**Mitigation:**
- Refactor incrementally (one service at a time)
- Test each change before moving forward
- Keep old code commented out temporarily

### Risk 2: Type mismatches
**Mitigation:**
- Use strict TypeScript checking
- Create comprehensive type definitions
- Test with real backend data

---

## 🎯 EXECUTION ORDER

### Session 1: Domain Layer (30 min)
1. Create `domain/alerts/AlertProcessor.ts`
2. Create `domain/vitals/VitalsValidator.ts`
3. Create `domain/vitals/VitalsFormatter.ts`
4. Git commit

### Session 2: Base Services (45 min)
1. Refactor `BaseMedicalRecordService` to be generic
2. Update MedicationService to use generic
3. Update InvestigationService to use generic
4. Update TherapyService to use generic
5. Git commit

### Session 3: Alert System (30 min)
1. Update AlertService to use AlertProcessor
2. Update components to use domain layer
3. Git commit

### Session 4: Cleanup (15 min)
1. Consolidate camelCase transformers
2. Remove duplicate utilities
3. Final git commit
4. Update documentation

---

## 🚀 NEXT STEPS

**Immediate:** Ask user which task to start with, or proceed with Task 1 (Domain Layer) as it's foundational.

**After Phase 5:** System will have consistent architecture across frontend and backend, ready for production deployment.

---

**Status:** ⏳ Ready to begin Phase 5
**Recommended Start:** Task 1 - Create Frontend Domain Layer
