#!/usr/bin/env python3
"""
Test the create_atomic_case_entry function directly
"""

import asyncio
import asyncpg

async def test_case_entry_function():
    conn = await asyncpg.connect("postgresql://hospital_user:hospital123@localhost:5432/hospitaldb")

    try:
        # Test calling the function directly
        print("[TEST] Testing create_atomic_case_entry function...")

        patient_id = "6b851aa6-e564-40b6-963f-e1a5efdf024c"
        entry_type = "medicationStatusChange"
        description = "Test medication status change from active to held"
        performed_by = "DOC0001"

        print(f"[INFO] Parameters:")
        print(f"  - patient_id: {patient_id}")
        print(f"  - entry_type: {entry_type}")
        print(f"  - description: {description}")
        print(f"  - performed_by: {performed_by}")

        result = await conn.fetchrow(
            'SELECT create_atomic_case_entry($1, $2, $3, $4) as id',
            patient_id, entry_type, description, performed_by
        )

        print(f"[OK] Function returned ID: {result['id']}")

        # Now try to fetch the created case entry
        case_entry = await conn.fetchrow(
            'SELECT * FROM "caseEntries" WHERE id = $1',
            result['id']
        )

        if case_entry:
            print(f"[OK] Case entry created successfully:")
            print(f"  - ID: {case_entry['id']}")
            print(f"  - Patient ID: {case_entry['patientId']}")
            print(f"  - Entry Type: {case_entry['entryType']}")
            print(f"  - Description: {case_entry['description']}")
            print(f"  - Created By: {case_entry['createdBy']}")
            print(f"  - Timestamp: {case_entry['timestamp']}")
        else:
            print(f"[ERROR] Could not find created case entry with ID {result['id']}")

    except Exception as e:
        print(f"[ERROR] Function test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_case_entry_function())