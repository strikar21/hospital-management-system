# Timezone Standardization Plan

**Goal:** Store ALL timestamps in UTC (timezone-aware), display locally in frontend
**Date:** 2025-11-10

---

## Current Problem

**Mixed timestamp approaches:**
1. ❌ `datetime.now()` - Returns LOCAL timezone (varies by server)
2. ❌ `datetime.utcnow()` - Returns UTC but timezone-NAIVE
3. ✅ `now_utc()` - Returns UTC timezone-AWARE (correct!)

**Why this is bad:**
- Can't compare naive and aware datetimes
- Inconsistent storage (some UTC, some local)
- Confusion about what timezone a timestamp represents

---

## Correct Architecture

### Backend (Python/PostgreSQL)
**Storage:** ALL timestamps in UTC with timezone info
**Creation:** Use `now_utc()` from `app.common.datetime`
**Database:** Use `TIMESTAMP WITH TIME ZONE` columns

### Frontend (React/JavaScript)
**Display:** Convert UTC to user's local timezone
**Input:** Convert user's local timezone to UTC before sending
**Library:** Use `date-fns` or native JS `Intl` for conversion

---

## Implementation Plan

### Phase 1: Replace datetime.now() and datetime.utcnow()

**Files to fix (20+ files):**
```
app/services/arrhythmia_detection_service.py
app/services/audit.py
app/services/base_service.py
app/services/calibration_service.py
app/services/certificate_service.py
app/services/device_health_service.py
app/services/maintenance_service.py
... (more)
```

**Change:**
```python
# ❌ OLD (wrong)
timestamp = datetime.now()
timestamp = datetime.utcnow()

# ✅ NEW (correct)
from app.common.datetime import now_utc
timestamp = now_utc()
```

### Phase 2: Database Schema Verification

**Check all timestamp columns:**
```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE data_type LIKE '%timestamp%';
```

**Ensure all are:**
- `TIMESTAMP WITH TIME ZONE` (correct)
- NOT `TIMESTAMP WITHOUT TIME ZONE` (wrong)

### Phase 3: Frontend Timezone Conversion

**Example implementation:**
```typescript
// utils/timezone.ts
export function formatLocalDateTime(utcTimestamp: string): string {
  const date = new Date(utcTimestamp);
  return date.toLocaleString(); // Automatic local conversion
}

export function formatLocalDate(utcTimestamp: string): string {
  const date = new Date(utcTimestamp);
  return date.toLocaleDateString();
}

export function formatLocalTime(utcTimestamp: string): string {
  const date = new Date(utcTimestamp);
  return date.toLocaleTimeString();
}
```

**Usage in components:**
```tsx
import { formatLocalDateTime } from './utils/timezone';

function MedicationItem({ medication }) {
  return (
    <div>
      <p>Prescribed: {formatLocalDateTime(medication.createdAt)}</p>
    </div>
  );
}
```

---

## Quick Win: Replace All datetime.utcnow()

This is the most critical fix since `datetime.utcnow()` returns **naive** datetimes.

### Files with datetime.utcnow() (7 files):
1. `app/services/base_service.py` - 2 occurrences
2. `app/services/certificate_service.py` - 2 occurrences

### Replacement Pattern:
```python
# Add import at top of file
from app.common.datetime import now_utc

# Replace throughout file
- datetime.utcnow()
+ now_utc()
```

---

## Timeline Comparison Fix (Already Done)

**What we fixed:** `patient_repository.py` - Added `safe_timestamp()` helper
**Why it helps:** Handles mixed naive/aware datetimes during sorting
**Status:** ✅ Complete (commit 3f5d100)

This is a **temporary workaround**. Once all timestamps are timezone-aware, we won't need it.

---

## Testing Strategy

### Backend Tests:
```python
def test_all_timestamps_are_timezone_aware():
    # Create a record
    result = await create_medication(patient_id, medication_data)

    # Verify timestamp has timezone
    assert result['createdAt'].tzinfo is not None
    assert result['createdAt'].tzinfo == timezone.utc
```

### Frontend Tests:
```typescript
test('displays timestamp in local timezone', () => {
  const utcTimestamp = '2025-11-10T14:30:00Z';
  const formatted = formatLocalDateTime(utcTimestamp);

  // Should NOT show UTC time
  expect(formatted).not.toContain('14:30');

  // Should show local time (varies by test machine timezone)
  // Just verify it's a valid date string
  expect(Date.parse(formatted)).not.toBeNaN();
});
```

---

## Database Migration (If Needed)

If any columns are `TIMESTAMP WITHOUT TIME ZONE`, migrate them:

```sql
-- Check current column type
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'medications'
  AND column_name = 'createdAt';

-- Migrate to timezone-aware (if needed)
ALTER TABLE medications
  ALTER COLUMN "createdAt" TYPE TIMESTAMP WITH TIME ZONE
  USING "createdAt" AT TIME ZONE 'UTC';

-- Repeat for all timestamp columns in all tables
```

---

## Benefits After Standardization

1. **No More Comparison Errors:** All timestamps comparable
2. **Correct Time Display:** Users see their local time
3. **Audit Trail Accuracy:** Know exactly when actions occurred (UTC)
4. **International Support:** Works for users in any timezone
5. **Daylight Saving:** No issues with DST changes

---

## Recommended Immediate Action

**Option 1: Quick Fix (30 minutes)**
- Replace all `datetime.utcnow()` calls with `now_utc()` (7 files)
- Keeps `safe_timestamp()` workaround for now
- Prevents future comparison errors

**Option 2: Comprehensive Fix (2-3 hours)**
- Replace ALL `datetime.now()` and `datetime.utcnow()` (20+ files)
- Remove `safe_timestamp()` workaround (no longer needed)
- Complete timezone standardization

**Option 3: Do Nothing**
- Keep `safe_timestamp()` workaround
- Accept mixed timezone approach
- Risk of future comparison errors

---

## Decision

**Recommended:** Option 1 (Quick Fix)

Replace `datetime.utcnow()` now, address `datetime.now()` gradually as we encounter issues.

**Reasoning:**
- `datetime.utcnow()` is most problematic (naive UTC)
- Quick fix prevents immediate errors
- Can do comprehensive fix later as separate task

---

**Status:** Planning complete
**Next:** Replace datetime.utcnow() calls (7 files)
