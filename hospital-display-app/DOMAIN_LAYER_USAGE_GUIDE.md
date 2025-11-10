# Domain Layer Usage Guide

**Last Updated**: 2025-11-10
**Version**: 1.0
**For**: Hospital Management System Frontend

---

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Domain Layer Classes](#domain-layer-classes)
4. [Usage Examples](#usage-examples)
5. [Common Patterns](#common-patterns)
6. [Anti-Patterns](#anti-patterns)
7. [Testing Guidelines](#testing-guidelines)
8. [Migration Guide](#migration-guide)

---

## Introduction

This guide explains how to use the domain layer classes in the hospital management system frontend. The domain layer provides reusable business logic for:

- **Alert processing** (formatting, prioritization, grouping)
- **Vitals validation** (range checks, staleness detection)
- **Vitals formatting** (units, color coding, temperature conversion)

### Benefits

✅ **Single Source of Truth**: All formatting logic in one place
✅ **Consistency**: Same display across all components
✅ **Maintainability**: Update once, apply everywhere
✅ **Testability**: Pure functions, easy to test
✅ **Type Safety**: TypeScript interfaces ensure correctness

---

## Architecture Overview

### Directory Structure

```
src/
├── domain/                    # Domain layer (business logic)
│   ├── alerts/
│   │   └── AlertProcessor.ts  # Alert display logic
│   └── vitals/
│       ├── VitalsValidator.ts # Validation rules
│       └── VitalsFormatter.ts # Display formatting
├── services/                  # API services
├── components/                # React components
└── hooks/                     # React hooks
```

### Data Flow

```
Backend API → Services → Components → Domain Layer → Display
                             ↓
                       (Uses Domain Classes)
                             ↓
                    AlertProcessor
                    VitalsValidator
                    VitalsFormatter
```

### Principles

1. **Domain layer is pure**: No side effects, deterministic output
2. **Components delegate to domain layer**: No inline formatting logic
3. **Services fetch data only**: Domain layer processes data for display
4. **Backward compatible**: Supports both new and legacy data formats

---

## Domain Layer Classes

### 1. AlertProcessor

**Location**: `src/domain/alerts/AlertProcessor.ts`

**Purpose**: Process alerts for display (formatting, sorting, grouping, filtering)

**Key Methods**:

| Method | Purpose | Returns |
|--------|---------|---------|
| `formatAlertForDisplay()` | Format single alert with display properties | `DisplayAlert` |
| `formatAlertsForDisplay()` | Format multiple alerts (batch) | `DisplayAlert[]` |
| `getSeverityClass()` | Get Tailwind CSS classes for severity | `string` |
| `getSeverityIcon()` | Get emoji icon for severity | `string` (🚨 ⚠️ ⚡ ℹ️) |
| `calculatePriority()` | Calculate numeric priority for sorting | `number` |
| `sortAlertsByPriority()` | Sort alerts by priority (highest first) | `AlertData[]` |
| `groupAlertsByPatient()` | Group alerts by patient ID | `Map<string, AlertData[]>` |
| `filterByStatus()` | Filter by active/acknowledged/resolved | `AlertData[]` |
| `filterBySeverity()` | Filter by minimum severity level | `AlertData[]` |
| `formatTimestamp()` | Format as relative time ("2 mins ago") | `string` |

---

### 2. VitalsValidator

**Location**: `src/domain/vitals/VitalsValidator.ts`

**Purpose**: Validate vitals data before display

**Key Methods**:

| Method | Purpose | Returns |
|--------|---------|---------|
| `validate()` | Complete validation with errors/warnings | `ValidationResult` |
| `hasRequiredFields()` | Check for required fields (patientId, timestamp, HR, SpO2) | `boolean` |
| `checkDisplayRanges()` | Check if vitals are within display ranges | `string[]` (errors) |
| `checkDataQuality()` | Check data quality (signal, battery, completeness) | `string[]` (warnings) |
| `isStale()` | Check if vitals are older than threshold | `boolean` |
| `hasMinimumData()` | Check if at least one vital is present | `boolean` |
| `getAvailableVitals()` | Get list of available (non-null) vitals | `string[]` |
| `calculateCompleteness()` | Calculate % of vitals present | `number` (0-1) |

---

### 3. VitalsFormatter

**Location**: `src/domain/vitals/VitalsFormatter.ts`

**Purpose**: Format vitals for display with units and colors

**Key Methods**:

| Method | Purpose | Returns |
|--------|---------|---------|
| `formatAllVitals()` | Format all vitals at once (batch) | `FormattedVitals` |
| `formatHeartRate()` | Format with "bpm" unit | `string` |
| `formatOxygenSaturation()` | Format with "%" unit | `string` |
| `formatTemperature()` | Format with "°C" or "°F" (with conversion) | `string` |
| `formatBloodPressure()` | Format as "120/80 mmHg" | `string` |
| `formatRespiratoryRate()` | Format with "/min" unit | `string` |
| `formatBioimpedance()` | Format with "Ω" unit | `string` |
| `formatTremor()` | Format with "/10" scale | `string` |
| `formatPerfusionIndex()` | Format with "%" unit | `string` |
| `getHeartRateColor()` | Get color for HR (red/yellow/green/gray) | `string` |
| `getTemperatureColor()` | Get color for temperature | `string` |
| `getBloodPressureColor()` | Get color for BP | `string` |

---

## Usage Examples

### Example 1: Format Alerts for Display

```typescript
import { AlertProcessor } from '@/domain/alerts/AlertProcessor';

// Component receiving alerts from API
function AlertsComponent({ alerts }: { alerts: AlertData[] }) {
  // Format alerts with display properties
  const displayAlerts = AlertProcessor.formatAlertsForDisplay(alerts);

  return (
    <div>
      {displayAlerts.map(alert => (
        <div key={alert.id} className={alert.severityClass}>
          <span>{alert.severityIcon}</span>
          <span>{alert.message}</span>
          <span>{alert.formattedTimestamp}</span>
        </div>
      ))}
    </div>
  );
}
```

**Benefits**:
- ✅ Consistent severity icons across all alert displays
- ✅ Consistent Tailwind CSS classes
- ✅ Human-readable timestamps ("2 mins ago")
- ✅ Easy to test (mock AlertProcessor)

---

### Example 2: Format Vitals with Temperature Conversion

```typescript
import { VitalsFormatter } from '@/domain/vitals/VitalsFormatter';
import { VitalsData } from '@/domain/vitals/VitalsValidator';

// Component displaying patient vitals
function VitalsDisplay({ patient }: { patient: patient }) {
  // Create vitals data structure
  const vitalsData: VitalsData = useMemo(() => ({
    patientId: patient.id,
    timestamp: new Date().toISOString(),
    heartRate: patient.vitals?.heartRate,
    oxygenSaturation: patient.vitals?.oxygenSaturation,
    temperature: patient.vitals?.skinTemperature, // Celsius from backend
    bloodPressureSystolic: patient.vitals?.systolicPressure,
    bloodPressureDiastolic: patient.vitals?.diastolicPressure,
    respiratoryRate: patient.vitals?.respiratoryRate
  }), [patient]);

  // Format all vitals with Fahrenheit temperature
  const formattedVitals = useMemo(() =>
    VitalsFormatter.formatAllVitals(vitalsData, 'F'),
    [vitalsData]
  );

  return (
    <div>
      <div>HR: {formattedVitals.heartRate.value}</div>
      <div>SpO2: {formattedVitals.oxygenSaturation.value}</div>
      <div>Temp: {formattedVitals.temperature.value}</div> {/* Displays in °F */}
      <div>BP: {formattedVitals.bloodPressure.value}</div>
    </div>
  );
}
```

**Benefits**:
- ✅ Automatic temperature conversion (Celsius → Fahrenheit)
- ✅ Consistent units across all displays
- ✅ Easy to change temperature unit globally (just change 'F' to 'C')
- ✅ Memoized for performance

---

### Example 3: Validate Vitals Before Display

```typescript
import { VitalsValidator } from '@/domain/vitals/VitalsValidator';

function VitalsQualityIndicator({ vitals }: { vitals: VitalsData }) {
  // Validate vitals
  const validation = VitalsValidator.validate(vitals);

  if (!validation.isValid) {
    return (
      <div className="bg-red-100 p-2">
        <h3>Data Quality Issues</h3>
        <ul>
          {validation.errors.map(error => (
            <li key={error} className="text-red-600">{error}</li>
          ))}
        </ul>
      </div>
    );
  }

  if (validation.warnings.length > 0) {
    return (
      <div className="bg-yellow-100 p-2">
        <h3>Data Quality Warnings</h3>
        <ul>
          {validation.warnings.map(warning => (
            <li key={warning} className="text-yellow-600">{warning}</li>
          ))}
        </ul>
      </div>
    );
  }

  return <div className="text-green-600">✓ Good data quality</div>;
}
```

**Benefits**:
- ✅ Centralized validation rules
- ✅ Clear error vs warning distinction
- ✅ Informative error messages
- ✅ Easy to add new validation rules

---

### Example 4: Sort and Filter Alerts

```typescript
import { AlertProcessor } from '@/domain/alerts/AlertProcessor';

function FilteredAlertsList({ alerts }: { alerts: AlertData[] }) {
  // Filter only active alerts
  const activeAlerts = AlertProcessor.filterByStatus(alerts, 'active');

  // Filter only high and critical severity
  const urgentAlerts = AlertProcessor.filterBySeverity(activeAlerts, 'high');

  // Sort by priority
  const sortedAlerts = AlertProcessor.sortAlertsByPriority(urgentAlerts);

  return (
    <div>
      <h2>Urgent Active Alerts ({sortedAlerts.length})</h2>
      {sortedAlerts.map(alert => (
        <AlertCard key={alert.id} alert={alert} />
      ))}
    </div>
  );
}
```

**Benefits**:
- ✅ Declarative filtering and sorting
- ✅ Consistent priority calculation
- ✅ Easy to chain operations
- ✅ No mutation of original array

---

### Example 5: Group Alerts by Patient

```typescript
import { AlertProcessor } from '@/domain/alerts/AlertProcessor';

function PatientAlertSummary({ alerts }: { alerts: AlertData[] }) {
  // Group alerts by patient
  const groupedAlerts = AlertProcessor.groupAlertsByPatient(alerts);

  return (
    <div>
      {Array.from(groupedAlerts.entries()).map(([patientId, patientAlerts]) => (
        <div key={patientId}>
          <h3>Patient {patientId}</h3>
          <p>{patientAlerts.length} alerts</p>
          <ul>
            {patientAlerts.map(alert => (
              <li key={alert.id}>{alert.message}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
```

**Benefits**:
- ✅ Automatic grouping and sorting within groups
- ✅ Handles missing patientId gracefully
- ✅ Consistent across all components
- ✅ Easy to aggregate patient-level statistics

---

## Common Patterns

### Pattern 1: Memoized Domain Layer Calls

**Problem**: Domain layer methods called on every render

**Solution**: Use `useMemo` to memoize expensive computations

```typescript
// ✅ GOOD: Memoized
const formattedVitals = useMemo(() =>
  VitalsFormatter.formatAllVitals(vitalsData, 'F'),
  [vitalsData] // Only recompute when vitalsData changes
);

// ❌ BAD: Called on every render
const formattedVitals = VitalsFormatter.formatAllVitals(vitalsData, 'F');
```

---

### Pattern 2: Batch Operations

**Problem**: Calling domain layer methods in a loop

**Solution**: Use batch methods when available

```typescript
// ✅ GOOD: Batch operation
const displayAlerts = AlertProcessor.formatAlertsForDisplay(alerts);

// ❌ BAD: Loop with individual calls
const displayAlerts = alerts.map(alert =>
  AlertProcessor.formatAlertForDisplay(alert)
); // Less efficient, but works
```

---

### Pattern 3: Separate Value and Unit Display

**Problem**: Domain layer returns "98.6°F" but need separate value and unit

**Solution**: Use `.replace()` to split value and unit

```typescript
const formattedVitals = VitalsFormatter.formatAllVitals(vitalsData, 'F');

// Split value and unit for separate display
<span className="text-2xl">{formattedVitals.temperature.value.replace('°F', '')}</span>
<span className="text-sm">{formattedVitals.temperature.unit}</span>
```

**Result**:
```
98.6  ← Large font
°F    ← Small font
```

---

### Pattern 4: Conditional Formatting Based on Color

**Problem**: Need to apply CSS classes based on vital status

**Solution**: Use color methods from VitalsFormatter

```typescript
const hrColor = VitalsFormatter.getHeartRateColor(patient.vitals.heartRate);

// Map colors to Tailwind classes
const colorClasses = {
  red: 'bg-red-100 text-red-600',
  yellow: 'bg-yellow-100 text-yellow-600',
  green: 'bg-green-100 text-green-600',
  gray: 'bg-gray-100 text-gray-600'
};

<div className={colorClasses[hrColor]}>
  HR: {patient.vitals.heartRate} bpm
</div>
```

---

### Pattern 5: Default Values for Missing Vitals

**Problem**: Vitals may be undefined

**Solution**: Domain layer handles undefined with `--` placeholder

```typescript
// Domain layer automatically handles undefined
const formattedVitals = VitalsFormatter.formatAllVitals(vitalsData, 'F');

// vitalsData.heartRate = undefined
// formattedVitals.heartRate.value = "--"
// formattedVitals.heartRate.unit = ""

<div>HR: {formattedVitals.heartRate.value} {formattedVitals.heartRate.unit}</div>
// Displays: "HR: --" (no unit when value is missing)
```

---

## Anti-Patterns

### ❌ Anti-Pattern 1: Inline Formatting Logic

```typescript
// ❌ BAD: Inline formatting
<div>{patient.vitals.skinTemperature.toFixed(1)}°F</div>

// ✅ GOOD: Use domain layer
const formattedVitals = VitalsFormatter.formatAllVitals(vitalsData, 'F');
<div>{formattedVitals.temperature.value}</div>
```

**Why Bad**: Duplicate logic, no temperature conversion, inconsistent formatting

---

### ❌ Anti-Pattern 2: Manual Temperature Conversion

```typescript
// ❌ BAD: Manual conversion
const tempF = (patient.vitals.skinTemperature * 9/5) + 32;
<div>{tempF.toFixed(1)}°F</div>

// ✅ GOOD: Use domain layer
const formattedVitals = VitalsFormatter.formatAllVitals(vitalsData, 'F');
<div>{formattedVitals.temperature.value}</div>
```

**Why Bad**: Formula duplication, formatting inconsistency, harder to maintain

---

### ❌ Anti-Pattern 3: Hardcoded Severity Icons

```typescript
// ❌ BAD: Hardcoded icons
const icon = alert.severity === 'critical' ? '🚨' :
             alert.severity === 'high' ? '⚠️' :
             alert.severity === 'medium' ? '⚡' : 'ℹ️';

// ✅ GOOD: Use domain layer
const icon = AlertProcessor.getSeverityIcon(alert.severity);
```

**Why Bad**: Duplicate logic, ternary chains hard to read, inconsistent icons

---

### ❌ Anti-Pattern 4: Inline Validation

```typescript
// ❌ BAD: Inline validation
const isValid = patient.vitals?.heartRate &&
                patient.vitals?.heartRate > 0 &&
                patient.vitals?.heartRate < 300 &&
                patient.vitals?.oxygenSaturation &&
                patient.vitals?.oxygenSaturation > 0 &&
                patient.vitals?.oxygenSaturation <= 100;

// ✅ GOOD: Use domain layer
const validation = VitalsValidator.validate(vitalsData);
const isValid = validation.isValid;
```

**Why Bad**: Verbose, error-prone, no error messages, duplicate validation rules

---

### ❌ Anti-Pattern 5: Mutating Domain Layer Results

```typescript
// ❌ BAD: Mutating sorted alerts
const sortedAlerts = AlertProcessor.sortAlertsByPriority(alerts);
sortedAlerts.reverse(); // MUTATION!

// ✅ GOOD: Create new array
const sortedAlerts = AlertProcessor.sortAlertsByPriority(alerts);
const reversedAlerts = [...sortedAlerts].reverse();
```

**Why Bad**: Domain layer returns new arrays, but mutating breaks immutability

---

## Testing Guidelines

### Unit Testing Domain Layer

```typescript
import { VitalsFormatter } from '@/domain/vitals/VitalsFormatter';

describe('VitalsFormatter', () => {
  it('should format heart rate with bpm unit', () => {
    expect(VitalsFormatter.formatHeartRate(75)).toBe('75 bpm');
  });

  it('should convert Celsius to Fahrenheit', () => {
    const result = VitalsFormatter.formatTemperature(37, 'F');
    expect(result).toContain('98.6'); // 37°C = 98.6°F
    expect(result).toContain('°F');
  });

  it('should handle undefined heart rate', () => {
    expect(VitalsFormatter.formatHeartRate(undefined)).toBe('--');
  });
});
```

---

### Integration Testing Components with Domain Layer

```typescript
import { render, screen } from '@testing-library/react';
import { PatientOverview } from './PatientOverview';

it('should display temperature with domain layer unit', () => {
  const patient = createMockPatient({
    vitals: { skinTemperature: 37.0 } // Celsius
  });

  render(<PatientOverview patient={patient} />);

  // Domain layer converts to Fahrenheit
  expect(screen.getByText('°F')).toBeInTheDocument();
});
```

---

### Mocking Domain Layer in Tests

```typescript
import { VitalsFormatter } from '@/domain/vitals/VitalsFormatter';

jest.mock('@/domain/vitals/VitalsFormatter');

const mockVitalsFormatter = VitalsFormatter as jest.Mocked<typeof VitalsFormatter>;

it('should use domain layer for formatting', () => {
  mockVitalsFormatter.formatHeartRate.mockReturnValue('75 bpm');

  render(<MyComponent />);

  expect(mockVitalsFormatter.formatHeartRate).toHaveBeenCalledWith(75);
});
```

---

## Migration Guide

### Migrating from Inline Formatting to Domain Layer

#### Step 1: Identify Inline Formatting

Search for patterns like:
- `.toFixed()`
- Manual unit strings (`"bpm"`, `"mmHg"`, `"°F"`)
- Manual temperature conversion formulas
- Inline ternary chains for severity/status

#### Step 2: Add Domain Layer Imports

```typescript
import { VitalsFormatter } from '@/domain/vitals/VitalsFormatter';
import { VitalsData } from '@/domain/vitals/VitalsValidator';
```

#### Step 3: Create VitalsData Structure

```typescript
const vitalsData: VitalsData = useMemo(() => ({
  patientId: patient.id,
  timestamp: new Date().toISOString(),
  heartRate: patient.vitals?.heartRate,
  oxygenSaturation: patient.vitals?.oxygenSaturation,
  temperature: patient.vitals?.skinTemperature,
  bloodPressureSystolic: patient.vitals?.systolicPressure,
  bloodPressureDiastolic: patient.vitals?.diastolicPressure,
  respiratoryRate: patient.vitals?.respiratoryRate
}), [patient.id, patient.vitals]);
```

#### Step 4: Format with Domain Layer

```typescript
const formattedVitals = useMemo(() =>
  VitalsFormatter.formatAllVitals(vitalsData, 'F'),
  [vitalsData]
);
```

#### Step 5: Replace Inline Formatting

**Before**:
```typescript
<span>{patient.vitals.skinTemperature.toFixed(1)}°F</span>
```

**After**:
```typescript
<span>{formattedVitals.temperature.value}</span>
```

#### Step 6: Test and Verify

- Run TypeScript compiler: `npx tsc --noEmit`
- Run tests: `npm test`
- Verify display in browser

---

### Migration Checklist

- [ ] Identified all inline formatting in component
- [ ] Added domain layer imports
- [ ] Created VitalsData/AlertData structure
- [ ] Replaced inline formatting with domain layer methods
- [ ] Removed manual temperature conversion
- [ ] Removed hardcoded units
- [ ] Removed inline ternary chains
- [ ] Added useMemo for performance
- [ ] TypeScript compiles without errors
- [ ] All tests passing
- [ ] Verified display in browser
- [ ] Committed changes with descriptive message

---

## Best Practices Summary

### DO ✅

- Use `formatAllVitals()` for batch formatting
- Memoize domain layer calls with `useMemo`
- Use domain layer for ALL formatting (no exceptions)
- Handle undefined values (domain layer returns `--`)
- Use TypeScript interfaces (VitalsData, AlertData)
- Test domain layer methods (pure functions, easy to test)
- Split value and unit for custom styling

### DON'T ❌

- Don't use inline `.toFixed()` for vitals
- Don't manually convert temperatures
- Don't hardcode units (`"bpm"`, `"°F"`, etc.)
- Don't use inline ternary chains for severity/status
- Don't mutate domain layer results
- Don't call domain layer in loops (use batch methods)
- Don't skip `useMemo` for expensive computations

---

## Reference

### Type Definitions

```typescript
// VitalsData (input to VitalsFormatter)
interface VitalsData {
  patientId: string;
  timestamp: string;
  heartRate?: number;
  oxygenSaturation?: number;
  temperature?: number;
  bloodPressureSystolic?: number;
  bloodPressureDiastolic?: number;
  respiratoryRate?: number;
}

// FormattedVitals (output from VitalsFormatter)
interface FormattedVitals {
  heartRate: FormattedVital;
  oxygenSaturation: FormattedVital;
  temperature: FormattedVital;
  bloodPressure: FormattedVital;
  respiratoryRate: FormattedVital;
  // ... additional vitals
}

// FormattedVital (individual vital)
interface FormattedVital {
  value: string;        // "75 bpm" or "--"
  unit: string;         // "bpm" or ""
  color: string;        // "red" | "yellow" | "green" | "gray"
  isNormal: boolean;    // true if within normal range
}

// AlertData (input to AlertProcessor)
interface AlertData {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  timestamp: string;
  patientId?: string;
  status?: 'active' | 'acknowledged' | 'resolved';
  isAcknowledged?: boolean; // Legacy field
}

// DisplayAlert (output from AlertProcessor)
interface DisplayAlert extends AlertData {
  severityClass: string;        // Tailwind CSS classes
  severityIcon: string;         // "🚨" | "⚠️" | "⚡" | "ℹ️"
  formattedTimestamp: string;   // "2 mins ago"
  priorityScore: number;        // For sorting
}
```

---

## Conclusion

The domain layer provides a clean, consistent, and maintainable way to handle business logic in the frontend. By following this guide, you can:

- ✅ Eliminate duplicate formatting code
- ✅ Ensure consistent display across all components
- ✅ Make changes in one place, apply everywhere
- ✅ Improve testability with pure functions
- ✅ Leverage TypeScript for type safety

**For questions or suggestions, please refer to the source code or create an issue.**

---

**Domain Layer Usage Guide v1.0**
**Hospital Management System Frontend**
**Last Updated**: 2025-11-10
