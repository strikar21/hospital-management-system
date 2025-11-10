# Module 5: Patient Queries - Properly Organized ✅

**Date:** 2025-11-10
**Finding:** Module 5 is already properly organized with no duplicate code

---

## Summary

Module 5 patient queries are **not duplicated** - they serve **different purposes** with proper separation of concerns:

1. **Common Queries** (`app/common/queries/patient.py`) - Simple, focused SELECT queries
2. **Repository Queries** (`app/repositories/patient_repository.py`) - Complex queries with JOINs, aggregations, and business logic

These are **complementary**, not duplicate!

---

## Architecture Analysis

### 1. Common Queries Module (Simple & Focused)

**File:** [app/common/queries/patient.py](hospital-backend/app/common/queries/patient.py)

**Purpose:** Lightweight, reusable queries for basic patient data retrieval

**Functions:**
- `get_patient_by_id()` - Get single patient by ID (16 fields)
- `get_patients_by_status()` - Get patients filtered by status

**Characteristics:**
- ✅ Simple SELECT statements
- ✅ No JOINs
- ✅ Minimal fields (core patient data only)
- ✅ Direct asyncpg connection usage
- ✅ Tested with 9/9 tests passing

**Example:**
```python
async def get_patient_by_id(conn: asyncpg.Connection, patient_id: str):
    query = """
        SELECT
            id, "firstName", "lastName", "dateOfBirth", gender,
            "phoneNumber", "emergencyContactName", "emergencyContactPhone",
            "bloodType", "admissionDate", "roomNumber", "bedNumber",
            diagnosis, status, "createdAt", "updatedAt"
        FROM patients
        WHERE id = $1
    """
    row = await conn.fetchrow(query, patient_id)
    return dict(row) if row else None
```

---

### 2. Repository Queries (Complex & Feature-Rich)

**File:** [app/repositories/patient_repository.py](hospital-backend/app/repositories/patient_repository.py)

**Purpose:** Full-featured repository with complex queries for medical records

**Functions:**
- `get_by_id()` - Get patient WITH device assignment (JOIN with devices table)
- `get_all()` - Get patients WITH device assignments AND alerts (multiple JOINs + aggregation)
- `get_complete_patient_data()` - Get patient WITH medical records, medications, investigations, therapy (6 table JOINs)
- `search_patients()` - Full-text search across multiple fields
- `get_patients_by_ward()` - Complex filtering with ILIKE patterns
- `get_aggregated_timeline()` - Complex timeline of ALL medical activities (7 table JOINs)
- Plus 15+ other specialized methods

**Characteristics:**
- ✅ Complex JOIN queries (up to 7 tables)
- ✅ Aggregations (json_agg, GROUP BY)
- ✅ Business logic (calculate device status, format timelines)
- ✅ Repository pattern implementation
- ✅ Extends BaseRepository class

**Example (Complex Query):**
```python
async def get_complete_patient_data(self, patient_id: str):
    query = """
        SELECT
            p.*,
            da."deviceId" as "assignedDeviceId",
            CASE
                WHEN d."lastSeen" >= NOW() - INTERVAL '5 minutes' THEN 'connected'
                WHEN d."lastSeen" >= NOW() - INTERVAL '30 minutes' THEN 'recentlySeen'
                ELSE 'offline'
            END as "deviceStatus",
            json_agg(DISTINCT pn.*) FILTER (WHERE pn.id IS NOT NULL) as notes,
            json_agg(DISTINCT m.*) FILTER (WHERE m.id IS NOT NULL) as medications,
            json_agg(DISTINCT i.*) FILTER (WHERE i.id IS NOT NULL) as investigations,
            json_agg(DISTINCT t.*) FILTER (WHERE t.id IS NOT NULL) as therapies,
            json_agg(DISTINCT pa.*) FILTER (WHERE pa.id IS NOT NULL
                AND pa.status IN ('active', 'acknowledged')) as alerts
        FROM patients p
        LEFT JOIN deviceassignments da ON p.id = da."patientId" AND da."unassignedAt" IS NULL
        LEFT JOIN devices d ON da."deviceId" = d.id
        LEFT JOIN patientnotes pn ON p.id = pn."patientId"
        LEFT JOIN medications m ON p.id = m."patientId"
        LEFT JOIN investigations i ON p.id = i."patientId"
        LEFT JOIN therapy t ON p.id = t."patientId"
        LEFT JOIN patient_alerts pa ON p.id = pa."patientId"
        WHERE p.id = $1
        GROUP BY p.id, da."deviceId", da."assignedAt", da."assignedBy", d."batteryLevel", d."lastSeen", d."serialNumber"
    """
```

---

## Separation of Concerns

### Common Queries Use Case
**When to use:** Services/utilities needing basic patient data

```python
from app.common.queries import get_patient_by_id

async def some_service_function():
    async with db_pool.acquire() as conn:
        # Quick lookup of basic patient info
        patient = await get_patient_by_id(conn, patient_id)
        if patient:
            print(f"Patient: {patient['firstName']} {patient['lastName']}")
```

### Repository Use Case
**When to use:** API endpoints needing full patient context

```python
from app.repositories.patient_repository import PatientRepository

patient_repo = PatientRepository()

# Get complete patient data with all medical records
patient_data = await patient_repo.get_complete_patient_data(patient_id)
# Returns patient + device + notes + meds + investigations + therapy + alerts

# Get aggregated timeline
timeline = await patient_repo.get_aggregated_timeline(patient_id)
# Returns chronological timeline of ALL medical activities
```

---

## No Duplication Found

**Analysis Result:** ❌ No duplicate code between common queries and repository

**Differences:**
| Aspect | Common Queries | Repository Queries |
|--------|---------------|-------------------|
| **Complexity** | Simple SELECT | Complex JOINs + aggregations |
| **Fields** | 16 core fields | 40+ fields with JOINs |
| **JOINs** | None | Up to 7 tables |
| **Use Case** | Quick lookups | Full medical records |
| **Dependencies** | asyncpg only | BaseRepository + models |
| **Business Logic** | None | Extensive (status calc, formatting) |

---

## Test Coverage

**Module 5 Tests:** 9/9 passing ✅

The tests cover the **common queries** module:
- [test_phase2_queries_patient.py](hospital-backend/tests/test_phase2_queries_patient.py)
- Tests `get_patient_by_id()` function
- Tests `get_patients_by_status()` function
- Validates camelCase field names
- Validates data types and structure

**Repository tests:** Covered by integration tests (not part of Phase testing)

---

## Conclusion

✅ **Module 5 is properly organized - NO migration needed**

The two query layers serve different purposes:
- **Common queries:** Lightweight, reusable, simple
- **Repository queries:** Feature-rich, complex, business logic

This is **good architecture**, not duplicate code!

**Status:** ✅ Properly organized (no action needed)
**Test Results:** 9/9 tests passing
