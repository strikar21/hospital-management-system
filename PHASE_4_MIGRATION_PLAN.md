# Phase 4 Migration Plan

**Date:** 2025-11-10
**Status:** Ready to begin
**Test Coverage:** 95/95 tests passing (100%)

---

## Strategy: Incremental Migration

### Approach
1. ✅ **Test suite complete** - Safety net in place
2. 🔄 **Migrate one module at a time**
3. ✅ **Run tests after each change**
4. ✅ **Delete old code only when tests pass**
5. ✅ **Commit after each successful migration**

---

## Migration Order

### Module 1: Datetime Utils (READY)
**Old Code:** `app/common/datetime_utils.py` (209 lines)
**New Code:** `app/common/datetime/` (3 files, ~110 lines)
**Test Coverage:** 20/20 tests passing ✅

**Migration Steps:**
1. Find all imports of `from app.common.datetime_utils import ...`
2. Replace with `from app.common.datetime import ...`
3. Update function name mappings:
   - `to_utc_now()` → `now_utc()`
   - `format_iso8601()` → `to_iso8601()`
   - Keep `parse_iso8601()` (same name)
4. Run tests to verify
5. Delete old `datetime_utils.py`
6. Run tests again
7. Commit

**Files Using datetime_utils.py:** 28 files (from grep)

---

### Module 2: Waveform Processing (READY)
**Old Code:** Duplicated in `mqtt_service.py` and `websocket_manager.py`
**New Code:** `app/common/waveform/` (3 files)
**Test Coverage:** 18/18 tests passing ✅

**Migration Steps:**
1. Identify waveform processing code in mqtt_service.py
2. Replace with imports from `app/common/waveform`
3. Verify with tests
4. Repeat for websocket_manager.py
5. Delete duplicated code
6. Commit

---

### Module 3: Alert Thresholds (READY)
**Old Code:** Hardcoded in `mqtt_service.py` (~130 lines)
**New Code:** `app/domain/alerts/rules/` (3 files)
**Test Coverage:** 29/29 tests passing ✅

**Migration Steps:**
1. Find hardcoded threshold checks
2. Replace with `check_vital_threshold()` from rules module
3. Update threshold constants to use `VITAL_THRESHOLDS`
4. Verify with tests
5. Delete old threshold code
6. Commit

---

### Module 4: Alert Generation (READY)
**Old Code:** Duplicated alert generation logic
**New Code:** `app/domain/alerts/generators/` (vital.py)
**Test Coverage:** 19/19 tests passing ✅

**Migration Steps:**
1. Find alert generation code
2. Replace with `generate_vital_alert()`
3. Verify alert format matches
4. Run tests
5. Delete old alert code
6. Commit

---

### Module 5: Patient Queries (READY)
**Old Code:** Direct SQL queries in API endpoints
**New Code:** `app/common/queries/patient.py`
**Test Coverage:** 9/9 tests passing ✅

**Migration Steps:**
1. Find direct patient queries in API routes
2. Replace with `get_patient_by_id()`, `get_patients_by_status()`
3. Verify camelCase fields
4. Run tests
5. Delete duplicate queries
6. Commit

---

## Detailed Migration: Module 1 (Datetime)

### Function Name Mapping

| Old (datetime_utils.py) | New (datetime/) | Notes |
|-------------------------|-----------------|-------|
| `parse_iso8601()` | `parse_iso8601()` | ✅ Same name |
| `to_utc_now()` | `now_utc()` | ⚠️ NAME CHANGE |
| `format_iso8601()` | `to_iso8601()` | ⚠️ NAME CHANGE |
| `parse_date_only()` | ❌ Not in new modules | Keep in utils or add |
| `calculate_age()` | ❌ Not in new modules | Keep in utils or add |
| `is_within_window()` | `is_recent()` | ⚠️ Different params |
| `get_hours_difference()` | `seconds_since()` | ⚠️ Different units |

### Decision: Hybrid Approach
**Keep domain-specific functions** (`calculate_age`, `parse_date_only`) in `datetime_utils.py`
**Migrate core functions** to new datetime modules
**Update imports** to use new modules for core functions

### Updated Migration for Module 1

**Step 1:** Update `datetime_utils.py` to import from new modules
```python
# OLD:
from datetime import datetime, timezone

def to_utc_now() -> datetime:
    return datetime.now(timezone.utc)

# NEW:
from app.common.datetime import now_utc

def to_utc_now() -> datetime:
    """Backward compatibility wrapper."""
    return now_utc()
```

**Step 2:** Gradually replace old imports in all files
```python
# OLD:
from app.common.datetime_utils import to_utc_now, parse_iso8601

# NEW:
from app.common.datetime import now_utc, parse_iso8601
```

**Step 3:** Once all files migrated, remove wrapper functions

---

## Test Strategy

### After Each Migration Step
```bash
# Run full test suite
cd hospital-backend
pytest tests/test_phase*.py -v

# Expected: 95/95 passing
```

### Before Deleting Old Code
```bash
# Search for any remaining imports
grep -r "from app.common.datetime_utils" app/

# Should return: no matches
```

### After Deleting Old Code
```bash
# Run tests again
pytest tests/test_phase*.py -v

# Expected: Still 95/95 passing
```

---

## Risk Mitigation

### Low Risk (Green Light)
- ✅ 100% test coverage for new modules
- ✅ All tests passing
- ✅ Incremental approach
- ✅ Git commits after each step
- ✅ Easy rollback if needed

### Medium Risk (Caution)
- ⚠️ 28 files use datetime_utils
- ⚠️ Function name changes require search/replace
- ⚠️ Some functions not in new modules

### Mitigation
1. **Use backward compatibility wrappers** initially
2. **Migrate in small batches** (5-10 files at a time)
3. **Run tests frequently**
4. **Commit after each successful batch**

---

## Success Criteria

### Module Migrated Successfully When:
1. ✅ All imports updated to new module
2. ✅ All tests still passing (95/95)
3. ✅ Old code deleted
4. ✅ No compiler/import errors
5. ✅ Committed to git

### Overall Migration Complete When:
1. ✅ All 5 modules migrated
2. ✅ All duplicate code removed
3. ✅ All tests passing
4. ✅ Code size reduced (~1,470 LOC deleted)
5. ✅ Documentation updated

---

## Timeline Estimate

### Per Module
- **Module 1 (Datetime):** 1-2 hours (28 files to update)
- **Module 2 (Waveform):** 30 minutes (2 files)
- **Module 3 (Alert Rules):** 45 minutes (mqtt_service.py)
- **Module 4 (Alert Gen):** 30 minutes (alert pipeline)
- **Module 5 (Queries):** 45 minutes (API routes)

**Total:** ~4 hours of focused work

---

## Current Status

### Ready to Migrate
✅ **Module 1:** Datetime (20 tests)
✅ **Module 2:** Waveform (18 tests)
✅ **Module 3:** Alert Rules (29 tests)
✅ **Module 4:** Alert Generation (19 tests)
✅ **Module 5:** Patient Queries (9 tests)

### Test Coverage
✅ **95/95 tests passing**

### Documentation
✅ Migration plan complete
✅ Risk mitigation defined
✅ Success criteria clear

---

## Next Action

**Start with Module 1: Datetime Migration**

Command to begin:
```bash
# Step 1: Create backward compatibility wrappers in datetime_utils.py
# Step 2: Update 5 files as a test batch
# Step 3: Run tests
# Step 4: If passing, continue with next batch
```

**Ready to proceed!** 🚀

---

**Status:** ✅ Plan complete, ready for execution
**Test Safety Net:** ✅ 95/95 tests passing
**Risk Level:** 🟢 Low (incremental approach with tests)
