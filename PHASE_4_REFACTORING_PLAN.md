# PHASE 4: SERVICE REFACTORING PLAN

**Goal:** Update existing services to use new shared modules (VitalsNormalizer, AlertPipeline, StaffResolver, common utilities)

**Estimated Time:** 3-4 hours

---

## 📋 REFACTORING STRATEGY

### Approach:
1. **Incremental refactoring** - One service at a time
2. **Git commit after each service** - For safety and rollback capability
3. **Preserve functionality** - Only change internal implementation, not external API
4. **Add type hints** - Use domain schemas for type safety

---

## 🎯 FILES TO REFACTOR

### 1. **mqtt_service.py** - HIGHEST PRIORITY
**Lines:** 1475 (very large file)
**Current Issues:**
- Line 426-454: Inline vitals range validation → Replace with `VitalsNormalizer.validate_vitals()`
- Line 456-670: `_handleVitalsMessageNew()` - Inline vitals processing → Use `VitalsNormalizer.normalize_mqtt_payload()`
- Line 622-661: Inline alert generation → Replace with `AlertPipeline.generate_vital_alert()`
- Uses deprecated `alert_detection_service` (line 33) and `alert_manager_service` (line 34)

**Refactoring Plan:**
```python
# Add imports at top
from app.domain import VitalsNormalizer, AlertPipeline

class MQTTService:
    def __init__(self):
        # ... existing code ...
        self.vitalsNormalizer = VitalsNormalizer()
        # AlertPipeline needs db pool, initialize in start()
        self.alertPipeline = None

    async def start(self, config):
        # ... existing code ...
        # Initialize AlertPipeline with db pool
        from app.core.database import getDbConnectionPool
        self.alertPipeline = AlertPipeline(pool=getDbConnectionPool())

    def _validateVitalsRanges(self, payload):
        """Replace inline validation with VitalsNormalizer"""
        try:
            vitals = self.vitalsNormalizer.normalize_mqtt_payload(payload)
            is_valid, error = self.vitalsNormalizer.validate_vitals(vitals)
            return is_valid
        except Exception as e:
            logger.error(f"Vitals validation error: {e}")
            return False

    async def _handleVitalsMessageNew(self, deviceId, payload):
        """Refactor to use VitalsNormalizer and AlertPipeline"""
        # 1. Normalize vitals
        vitals = self.vitalsNormalizer.normalize_mqtt_payload(payload)

        # 2. Validate vitals
        is_valid, error = self.vitalsNormalizer.validate_vitals(vitals)
        if not is_valid:
            logger.warning(f"Invalid vitals: {error}")
            return

        # 3. Generate alerts using AlertPipeline
        if vitals.get('heartRate'):
            alert = await self.alertPipeline.generate_vital_alert(
                patient_id=vitals['patientId'],
                vital_type='heartrate',
                vital_value=vitals['heartRate'],
                device_id=deviceId
            )
            if alert:
                alert_id = await self.alertPipeline.process_alert(alert)
                # Broadcast to WebSocket...

        # ... rest of method
```

**Lines to Remove:**
- Line 33-34: Remove imports of deprecated alert services
- Line 426-454: Replace `_validateVitalsRanges()` body with VitalsNormalizer call
- Line 622-661: Replace inline alert detection with AlertPipeline

---

### 2. **patient_service.py** - HIGH PRIORITY
**Current Issues:**
- Multiple instances of inline staff resolution (10+ places)
- Inline camelCase transformation
- Inline datetime parsing

**Refactoring Plan:**
```python
# Add imports
from app.domain import StaffResolver, PatientRecord
from app.common import dict_to_camel_case, parse_iso8601

class PatientService:
    def __init__(self, pool):
        self.pool = pool
        self.staffResolver = StaffResolver(pool)

    async def get_patient_details(self, patient_id):
        # ... fetch patient from DB ...

        # OLD: Inline staff resolution
        # if row['attendingPhysician']:
        #     physician = await conn.fetchrow(...)
        #     patient['attendingPhysicianName'] = f"{physician['firstName']} ..."

        # NEW: Use StaffResolver
        patient = dict(row)
        patient = await self.staffResolver.enrich_record_with_staff(
            patient,
            {
                'attendingPhysician': 'attendingPhysicianName',
                'admittedBy': 'admittedByName'
            }
        )

        # OLD: Inline camelCase
        # for key, value in patient.items():
        #     camel_key = self._to_camel_case(key)
        #     result[camel_key] = value

        # NEW: Use common utility
        return dict_to_camel_case(patient)

    async def get_medications(self, patient_id):
        # ... fetch medications ...

        # NEW: Batch staff resolution
        medications = [dict(row) for row in rows]
        medications = await self.staffResolver.enrich_records_batch(
            medications,
            {'prescribedBy': 'prescribedByName'}
        )

        return [dict_to_camel_case(med) for med in medications]
```

**Files/Functions to Update:**
- `get_patient_details()` - Staff resolution for attendingPhysician, admittedBy
- `get_medications()` - Staff resolution for prescribedBy
- `get_investigations()` - Staff resolution for orderedBy
- `get_therapies()` - Staff resolution for prescribedBy
- `get_patient_notes()` - Staff resolution for createdBy, updatedBy

---

### 3. **medication_service.py** - MEDIUM PRIORITY
**Refactoring Plan:**
```python
from app.domain import StaffResolver, MedicationRecord
from app.common import dict_to_camel_case, to_utc_now

class MedicationService:
    def __init__(self, pool):
        self.pool = pool
        self.staffResolver = StaffResolver(pool)

    async def add_medication(self, patient_id, medication_data, prescribed_by):
        # Use common datetime utility
        created_at = to_utc_now()

        # ... insert medication ...

        # Enrich with staff name
        medication = dict(row)
        medication = await self.staffResolver.enrich_record_with_staff(
            medication,
            {'prescribedBy': 'prescribedByName'}
        )

        return dict_to_camel_case(medication)
```

---

### 4. **investigation_service.py** - MEDIUM PRIORITY
Similar pattern to medication_service:
- Replace inline staff resolution with StaffResolver
- Replace inline camelCase with common utilities

---

### 5. **therapy_service.py** - MEDIUM PRIORITY
Similar pattern to medication_service:
- Replace inline staff resolution with StaffResolver
- Replace inline camelCase with common utilities

---

## 🗑️ FILES TO DELETE

### Deprecated Alert Services (After refactoring mqtt_service.py):

1. **vital_alert_service.py** - DEPRECATED
   - Replaced by `AlertPipeline.generate_vital_alert()`
   - 10,172 bytes

2. **alert_manager_service.py** - DEPRECATED
   - Replaced by `AlertPipeline + AlertDeduplicator`
   - 13,943 bytes

3. **alert_detection_service_old_backup.py** - OLD BACKUP
   - Can be deleted
   - 12,407 bytes

4. **alert_detection_service_complete.py** - DUPLICATE
   - Check if still used, likely can be deleted
   - 60,695 bytes

**IMPORTANT:** Before deleting, grep codebase to ensure no imports remain:
```bash
grep -r "vital_alert_service" --include="*.py"
grep -r "alert_manager_service" --include="*.py"
```

---

## 🔍 VERIFICATION CHECKLIST

After refactoring each service:

- [ ] All imports updated to use `app.domain` and `app.common`
- [ ] No inline staff resolution (search for `fetchrow.*staff.*firstName`)
- [ ] No inline camelCase transformation (search for `to_camel_case.*=.*lambda`)
- [ ] No inline timestamp parsing (search for `fromisoformat.*replace.*Z`)
- [ ] Type hints use domain schemas (VitalsRecord, AlertRecord, etc.)
- [ ] Git commit with detailed message
- [ ] Run basic smoke test (start backend, check logs)

---

## 📊 IMPACT ANALYSIS

### Code Reduction Expected:
- **mqtt_service.py:** ~100 lines removed (validation + alert logic)
- **patient_service.py:** ~150 lines removed (staff resolution + serialization)
- **medication_service.py:** ~50 lines removed
- **investigation_service.py:** ~50 lines removed
- **therapy_service.py:** ~50 lines removed
- **Deleted services:** ~400 lines removed

**Total:** ~800 lines of duplicate code eliminated

### Maintainability Improvements:
- **Single source of truth** for vitals validation, alert generation, staff resolution
- **Type safety** with domain schemas
- **Easier testing** - can test VitalsNormalizer independently
- **Faster debugging** - all vitals logic in one place

---

## ⚠️ RISKS & MITIGATION

### Risk 1: Breaking existing MQTT flow
**Mitigation:**
- Test with actual ESP32 watch after refactoring
- Keep old code commented out temporarily
- Roll back if issues detected

### Risk 2: Performance degradation
**Mitigation:**
- StaffResolver has caching built-in
- AlertDeduplicator uses indexed queries
- Monitor logs for performance issues

### Risk 3: Missing edge cases
**Mitigation:**
- Carefully review current logic before replacing
- Add unit tests for new shared modules
- Test with real patient data

---

## 🎯 EXECUTION ORDER

1. **Day 1: Core Services**
   - ✅ Phase 3 complete (domain logic created)
   - ⏳ Refactor `patient_service.py` (most critical, used everywhere)
   - ⏳ Git commit
   - ⏳ Refactor `mqtt_service.py` (complex, needs careful testing)
   - ⏳ Git commit

2. **Day 2: Supporting Services**
   - ⏳ Refactor `medication_service.py`
   - ⏳ Refactor `investigation_service.py`
   - ⏳ Refactor `therapy_service.py`
   - ⏳ Git commit (all three together)

3. **Day 3: Cleanup**
   - ⏳ Delete deprecated alert services
   - ⏳ Search for any remaining imports
   - ⏳ Update imports in any tests
   - ⏳ Final git commit
   - ⏳ Update REFACTORING_PROGRESS.md

---

## 🚀 NEXT STEPS

**Immediate:** Ask user which service to refactor first, or proceed with patient_service.py as it's the most widely used.

**After Phase 4:** Move to Phase 5 (Frontend shared modules) and Phase 6 (Testing).

---

**Status:** Ready to begin Phase 4 refactoring
**Recommended Start:** `patient_service.py` (highest impact, widely used)
