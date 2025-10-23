# Device Management - SQL JOIN Implementation Plan

## Date: 2025-10-13
## Approach: Use SQL JOINs (matching medication pattern in patient_repository.py)

---

## ACTUAL DATA VERIFIED

### Patient IDs (UUIDs, not PAT0001):
- `6b851aa6-e564-40b6-963f-e1a5efdf024c`
- `7163182b-5d6e-412d-93d9-28ecfd86cc6e`
- `TEST001`

### Staff IDs:
- `DOC0001`, `STF0001`, `SYSTEM`

### Device IDs:
- `TEST_WATCH_001`

---

## MEDICATION PATTERN (Reference)

From `patient_repository.py:323-330`:
```sql
SELECT m.id, m.name, m.dosage, m.frequency, m.route, m.status, m."prescribedBy",
       COALESCE(s."firstName" || ' ' || s."lastName", 'Unknown') as "prescribedByName",
       m."createdAt" as timestamp, 'medication' as entry_type
FROM medications m
LEFT JOIN staff s ON m."prescribedBy" = s.id
WHERE m."patientId" = $1
```

From `patient_repository.py:392-399` (with role):
```sql
SELECT pn.id, pn.content, pn."createdBy" as "performedBy",
       COALESCE(s."firstName" || ' ' || s."lastName", 'Unknown') as "authorName",
       COALESCE(s.role, 'Unknown') as "authorRole",
       pn.timestamp, 'note' as entry_type
FROM patientnotes pn
LEFT JOIN staff s ON pn."createdBy" = s.id
```

**Pattern**:
1. `LEFT JOIN staff s ON table."staffIdField" = s.id`
2. `COALESCE(s."firstName" || ' ' || s."lastName", 'Unknown') as "fieldName"`
3. `COALESCE(s.role, 'Unknown') as "fieldRole"`

---

## IMPLEMENTATION

### File: `hospital-backend/app/api/v1/watch_management.py`

### Change 1: getAssignedWatches() - Line 66-112

**CURRENT Query (Line 71-81)**:
```sql
SELECT d.*, da.*, p."firstName", p."lastName", p."roomNumber", p."bedNumber",
       CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
            WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
            ELSE 'offline' END as connectionStatus
FROM devices d
JOIN deviceassignments da ON d.id = da."deviceId"
JOIN patients p ON da."patientId" = p.id
WHERE d."deviceType" = 'watch' AND da.status = 'active'
ORDER BY p."lastName", p."firstName"
```

**NEW Query**:
```sql
SELECT d.*, da.*, p."firstName", p."lastName", p."roomNumber", p."bedNumber",
       CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
            WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
            ELSE 'offline' END as connectionStatus,
       COALESCE(s."firstName" || ' ' || s."lastName", 'Unknown') as "assignedByName",
       COALESCE(s.role, 'Unknown') as "assignedByRole"
FROM devices d
JOIN deviceassignments da ON d.id = da."deviceId"
JOIN patients p ON da."patientId" = p.id
LEFT JOIN staff s ON da."assignedBy" = s.id
WHERE d."deviceType" = 'watch' AND da.status = 'active'
ORDER BY p."lastName", p."firstName"
```

**Changes**:
- Added `LEFT JOIN staff s ON da."assignedBy" = s.id`
- Added `COALESCE(s."firstName" || ' ' || s."lastName", 'Unknown') as "assignedByName"`
- Added `COALESCE(s.role, 'Unknown') as "assignedByRole"`

### Change 2: assignWatchToPatient() - Line 114-185

**CURRENT (Line 127)**:
```python
assignedBy = assignmentData.get('assignedBy', 'System')
```

**NEW**:
```python
assignedBy = current_user['id']  # Always use authenticated user
```

**Security Fix**: assignedBy must ALWAYS be the logged-in user's ID from JWT token, not from request body.

### Change 3: unassignWatchFromPatient() - Line 187-248

**CURRENT (Line 200)**:
```python
unassignedBy = unassignmentData.get('unassignedBy', 'System')
```

**NEW**:
```python
unassignedBy = current_user['id']  # Always use authenticated user
```

**Security Fix**: unassignedBy must ALWAYS be the logged-in user's ID from JWT token.

---

## CHANGES SUMMARY

### SQL Changes (1 location):
1. **watch_management.py:71-81** - Add LEFT JOIN to staff for assignedBy resolution

### Security Fixes (2 locations):
2. **watch_management.py:127** - Use `current_user['id']` instead of request data
3. **watch_management.py:200** - Use `current_user['id']` instead of request data

### Other Endpoints:
- **getWatchConnectionStatus()** - Already doesn't have staff fields (only has patient names)
- **getWatchAlerts()** - Doesn't show assignment info, no changes needed

---

## IMPLEMENTATION STEPS

1. **Step 1**: Update getAssignedWatches() query to add staff JOIN
2. **Step 2**: Fix assignWatchToPatient() to use current_user['id']
3. **Step 3**: Fix unassignWatchFromPatient() to use current_user['id']
4. **Step 4**: Run device pool tests (should still be 8/8)
5. **Step 5**: Test assigned watches endpoint for staff names

---

## TESTING PLAN

### Test 1: Verify SQL JOIN Works
```bash
cd hospital-backend
python -c "
import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    query = '''
    SELECT da.\"assignedBy\",
           COALESCE(s.\"firstName\" || \' \' || s.\"lastName\", \'Unknown\') as \"assignedByName\",
           COALESCE(s.role, \'Unknown\') as \"assignedByRole\"
    FROM deviceassignments da
    LEFT JOIN staff s ON da.\"assignedBy\" = s.id
    LIMIT 1
    '''

    row = await conn.fetchrow(query)
    if row:
        print(f'assignedBy: {row[\"assignedBy\"]}')
        print(f'assignedByName: {row[\"assignedByName\"]}')
        print(f'assignedByRole: {row[\"assignedByRole\"]}')
    else:
        print('No device assignments found')

    await conn.close()

asyncio.run(test())
"
```

### Test 2: API Response Check
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8001/api/v1/watchmanagement/assigned
```

Expected response:
```json
{
  "success": true,
  "assignedWatches": [{
    "assignedBy": "DOC0001",
    "assignedByName": "Dr. Sarah Johnson",
    "assignedByRole": "Doctor",
    ...
  }]
}
```

### Test 3: Security Test
- Assign watch with current user
- Verify assignedBy is JWT user's ID, not request data

---

## BACKWARD COMPATIBILITY

✅ **No breaking changes**:
- Adds `assignedByName` and `assignedByRole` fields
- All existing fields remain unchanged
- Old clients ignore new fields

---

## SUCCESS CRITERIA

✅ getAssignedWatches() returns assignedByName and assignedByRole
✅ assignedBy uses current_user['id'] from JWT
✅ unassignedBy uses current_user['id'] from JWT
✅ Device pool tests pass (8/8)
✅ SQL JOIN uses LEFT JOIN (handles missing staff gracefully)
✅ COALESCE provides fallback to 'Unknown'

---

## READY TO IMPLEMENT

Waiting for user confirmation to proceed.
