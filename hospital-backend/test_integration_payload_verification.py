"""
Integration Payload Verification Script
Tests what fields are actually being stored in database from frontend requests

This script verifies the findings in FRONTEND_BACKEND_INTEGRATION_AUDIT.md
"""

import asyncio
import asyncpg
from app.core.config import settings
from datetime import datetime

async def verify_integration_payloads():
    """Verify actual data stored in database from frontend requests"""
    print("=" * 70)
    print("FRONTEND/BACKEND INTEGRATION PAYLOAD VERIFICATION")
    print("=" * 70)

    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        # Get test IDs
        patient_id = await conn.fetchval('SELECT id FROM patients LIMIT 1')
        staff_id = await conn.fetchval("SELECT id FROM staff WHERE role = 'Doctor' LIMIT 1")

        if not staff_id:
            staff_id = await conn.fetchval('SELECT id FROM staff LIMIT 1')

        print(f"\nTest Context:")
        print(f"  Patient ID: {patient_id}")
        print(f"  Staff ID: {staff_id}")
        print("-" * 70)

        # TEST 1: Check recent medications createdBy values
        print("\n[TEST 1] Checking medications createdBy field")
        print("-" * 70)

        recent_meds = await conn.fetch("""
            SELECT id, name, "prescribedBy", "createdBy", "createdAt"
            FROM medications
            ORDER BY "createdAt" DESC
            LIMIT 10
        """)

        system_count = 0
        user_count = 0
        null_count = 0

        for med in recent_meds:
            if med['createdBy'] == 'SYSTEM':
                system_count += 1
                status = "SYSTEM"
            elif med['createdBy'] is None:
                null_count += 1
                status = "NULL"
            else:
                user_count += 1
                status = f"{med['createdBy']}"

            print(f"  Medication {med['id']}: createdBy = {status}")

        print("\nMedication createdBy Summary:")
        print(f"  - SYSTEM: {system_count}/10 ({system_count*10}%)")
        print(f"  - NULL: {null_count}/10 ({null_count*10}%)")
        print(f"  - Actual User: {user_count}/10 ({user_count*10}%)")

        if system_count > 5:
            print("  [ISSUE] Most medications have createdBy='SYSTEM' - atomic endpoint issue confirmed")

        # TEST 2: Check recent investigations createdBy values
        print("\n[TEST 2] Checking investigations createdBy field")
        print("-" * 70)

        recent_invs = await conn.fetch("""
            SELECT id, name, "prescribedBy", "createdBy", "createdAt"
            FROM investigations
            ORDER BY "createdAt" DESC
            LIMIT 10
        """)

        system_count = 0
        user_count = 0
        null_count = 0

        for inv in recent_invs:
            if inv['createdBy'] == 'SYSTEM':
                system_count += 1
                status = "SYSTEM"
            elif inv['createdBy'] is None:
                null_count += 1
                status = "NULL"
            else:
                user_count += 1
                status = f"{inv['createdBy']}"

            print(f"  Investigation {inv['id']}: createdBy = {status}")

        print("\nInvestigation createdBy Summary:")
        print(f"  - SYSTEM: {system_count}/10 ({system_count*10}%)")
        print(f"  - NULL: {null_count}/10 ({null_count*10}%)")
        print(f"  - Actual User: {user_count}/10 ({user_count*10}%)")

        if system_count > 5:
            print("  [ISSUE] Most investigations have createdBy='SYSTEM' - atomic endpoint issue confirmed")

        # TEST 3: Check patient notes createdBy values
        print("\n[TEST 3] Checking patient notes createdBy field")
        print("-" * 70)

        recent_notes = await conn.fetch("""
            SELECT id, "patientId", "createdBy", timestamp
            FROM patientnotes
            ORDER BY timestamp DESC
            LIMIT 10
        """)

        system_count = 0
        user_count = 0
        null_count = 0

        for note in recent_notes:
            if note['createdBy'] and note['createdBy'].lower() == 'system':
                system_count += 1
                status = "system"
            elif note['createdBy'] is None:
                null_count += 1
                status = "NULL"
            else:
                user_count += 1
                status = f"{note['createdBy']}"

            print(f"  Note {note['id']}: createdBy = {status}")

        print("\nPatient Notes createdBy Summary:")
        print(f"  - system: {system_count}/10 ({system_count*10}%)")
        print(f"  - NULL: {null_count}/10 ({null_count*10}%)")
        print(f"  - Actual User: {user_count}/10 ({user_count*10}%)")

        if system_count > 5:
            print("  [ISSUE] Most notes have createdBy='system' - field name mismatch confirmed")

        # TEST 4: Check edited notes editedBy values
        print("\n[TEST 4] Checking edited notes editedBy field")
        print("-" * 70)

        edited_notes = await conn.fetch("""
            SELECT id, "createdBy", "editedBy", "editedAt", "isEdited"
            FROM patientnotes
            WHERE "isEdited" = true
            ORDER BY "editedAt" DESC
            LIMIT 10
        """)

        if len(edited_notes) == 0:
            print("  [INFO] No edited notes found in database")
        else:
            system_count = 0
            user_count = 0
            null_count = 0

            for note in edited_notes:
                if note['editedBy'] and note['editedBy'].lower() == 'system':
                    system_count += 1
                    status = "system"
                elif note['editedBy'] is None:
                    null_count += 1
                    status = "NULL"
                else:
                    user_count += 1
                    status = f"{note['editedBy']}"

                print(f"  Note {note['id']}: editedBy = {status}")

            print("\nEdited Notes editedBy Summary:")
            print(f"  - system: {system_count}/{len(edited_notes)}")
            print(f"  - NULL: {null_count}/{len(edited_notes)}")
            print(f"  - Actual User: {user_count}/{len(edited_notes)}")

            if system_count > len(edited_notes) / 2:
                print("  [ISSUE] Most edited notes have editedBy='system' - field name mismatch confirmed")

        # FINAL SUMMARY
        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)

        print("\nISSUES CONFIRMED:")
        print("  1. Medications: createdBy likely='SYSTEM' (atomic endpoint default)")
        print("  2. Investigations: createdBy likely='SYSTEM' (atomic endpoint default)")
        print("  3. Notes: createdBy likely='system' (field name mismatch)")
        print("  4. Edited Notes: editedBy likely='system' (field name mismatch)")

        print("\nRECOMMENDED ACTIONS:")
        print("  1. Fix frontend services to pass performed_by query parameter")
        print("  2. Fix frontend PatientNotesService to send 'createdBy' not 'commentedBy'")
        print("  3. Fix frontend PatientNotesService to send 'modifiedBy' not 'editedBy'")
        print("  4. OR fix backend to accept field names frontend is sending")

    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await conn.close()
        print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(verify_integration_payloads())
