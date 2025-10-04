#!/usr/bin/env python3
"""
Test medication status changes using atomic operations
"""

import asyncio
import asyncpg
import json
import requests
from datetime import datetime

async def test_medication_status():
    # First, check if backend is healthy
    try:
        response = requests.get("http://localhost:8001/health")
        print(f"[OK] Backend health: {response.json()}")
    except Exception as e:
        print(f"[ERROR] Backend not responding: {e}")
        return

    # Connect to database
    conn = await asyncpg.connect("postgresql://hospital_user:hospital123@localhost:5432/hospitaldb")

    try:
        # 1. Check if patients exist
        patients = await conn.fetch("SELECT id, \"firstName\", \"lastName\" FROM patients LIMIT 3")
        print(f"\n[INFO] Found {len(patients)} patients:")
        for patient in patients:
            print(f"  - {patient['id']}: {patient['firstName']} {patient['lastName']}")

        if not patients:
            print("[ERROR] No patients found. Creating test patient...")
            # Create test patient using API
            patient_data = {
                "firstName": "TestPatient",
                "lastName": "MedicationTest",
                "dateOfBirth": "1990-01-01",
                "gender": "M",
                "contactNumber": "1234567890",
                "emergencyContact": "9876543210",
                "bloodGroup": "O+",
                "roomNumber": "101",
                "bedNumber": "A1",
                "admittedBy": "DOC0001"
            }

            response = requests.post("http://localhost:8001/api/v2/patients", json=patient_data)
            if response.status_code == 200:
                patient_result = response.json()
                test_patient_id = patient_result['patient']['id']
                print(f"[OK] Created test patient: {test_patient_id}")
            else:
                print(f"[ERROR] Failed to create patient: {response.text}")
                return
        else:
            test_patient_id = patients[0]['id']
            print(f"[INFO] Using patient: {test_patient_id}")

        # 2. Check medications for this patient
        medications = await conn.fetch("""
            SELECT id, name, dosage, status, "prescribedBy", "createdAt"
            FROM medications
            WHERE "patientId" = $1
        """, test_patient_id)

        print(f"\n[INFO] Found {len(medications)} medications for patient {test_patient_id}:")
        for med in medications:
            print(f"  - {med['id']}: {med['name']} {med['dosage']} ({med['status']})")

        if not medications:
            print("[ERROR] No medications found. Creating test medication using atomic endpoint...")
            # Create test medication using atomic API
            medication_data = {
                "name": "Test Medication",
                "dosage": "10mg",
                "frequency": "Twice daily",
                "route": "PO",
                "duration": "7 days",
                "status": "active",
                "startDate": datetime.now().strftime("%Y-%m-%d"),
                "prescribedBy": "DOC0001",
                "createdAt": datetime.now().isoformat()
            }

            response = requests.post(f"http://localhost:8001/api/v2/atomic/patients/{test_patient_id}/medications",
                                   json=medication_data)
            if response.status_code == 200:
                med_result = response.json()
                if med_result.get('success'):
                    test_med_id = med_result['medical_record']['id']
                    print(f"[OK] Created test medication: {test_med_id}")
                else:
                    print(f"[ERROR] Failed to create medication: {med_result}")
                    return
            else:
                print(f"[ERROR] Failed to create medication: {response.text}")
                return
        else:
            test_med_id = medications[0]['id']
            print(f"[INFO] Using medication: {test_med_id}")

        # 3. Test medication status change using atomic operation
        print(f"\n[TEST] Testing medication status change for medication {test_med_id}...")

        # Change status to 'held'
        status_change_data = {
            "medication_id": str(test_med_id),
            "status": "held",
            "changed_by": "DOC0001"
        }

        response = requests.post(f"http://localhost:8001/api/v2/atomic/patients/{test_patient_id}/medications/{test_med_id}/status",
                               json=status_change_data)

        if response.status_code == 200:
            result = response.json()
            print(f"[OK] Status change response: {json.dumps(result, indent=2)}")

            if result.get('success'):
                print("[OK] Medication status changed successfully!")

                # 4. Verify persistence in database
                print("\n[TEST] Verifying data persistence...")

                # Check medication status in database
                updated_med = await conn.fetchrow("""
                    SELECT status, "modifiedBy", "updatedAt"
                    FROM medications
                    WHERE id = $1
                """, test_med_id)

                if updated_med:
                    print(f"[OK] Database shows medication status: {updated_med['status']}")
                    print(f"[OK] Modified by: {updated_med['modifiedBy']}")
                    print(f"[OK] Updated at: {updated_med['updatedAt']}")
                else:
                    print("[ERROR] Could not find updated medication in database")

                # Check if case entry was created
                case_entries = await conn.fetch("""
                    SELECT description, "performedBy", timestamp
                    FROM case_entries
                    WHERE "patientId" = $1
                    ORDER BY timestamp DESC
                    LIMIT 5
                """, test_patient_id)

                print(f"\n[INFO] Found {len(case_entries)} recent case entries:")
                for entry in case_entries:
                    print(f"  - {entry['timestamp']}: {entry['description']} (by {entry['performedBy']})")

                # Test changing back to active
                print(f"\n[TEST] Testing status change back to 'active'...")
                status_change_data['status'] = 'active'

                response = requests.post(f"http://localhost:8001/api/v2/atomic/patients/{test_patient_id}/medications/{test_med_id}/status",
                                       json=status_change_data)

                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print("[OK] Status changed back to active successfully!")

                        # Final verification
                        final_med = await conn.fetchrow("""
                            SELECT status, "updatedAt"
                            FROM medications
                            WHERE id = $1
                        """, test_med_id)
                        print(f"[OK] Final medication status: {final_med['status']}")
                    else:
                        print(f"[ERROR] Failed to change status back: {result}")
                else:
                    print(f"[ERROR] Failed to change status back: {response.text}")
            else:
                print(f"[ERROR] Status change failed: {result}")
        else:
            print(f"[ERROR] Failed to change medication status: {response.text}")

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_medication_status())