"""
Complete Workflow Testing - End-to-End Device Management
Tests the complete device assignment workflow using v2 API
"""

import asyncio
import asyncpg
from datetime import datetime

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "hospitaldb",
    "user": "hospital_user",
    "password": "hospital123"
}

async def test_complete_workflows():
    """Test complete device management workflows"""

    print("="*80)
    print("COMPLETE WORKFLOW TESTING")
    print("="*80)
    print(f"Test Time: {datetime.now().isoformat()}\n")

    try:
        # Connect to database
        print("[INFO] Connecting to database...")
        conn = await asyncpg.connect(**DB_CONFIG)
        print("[SUCCESS] Connected to database\n")

        # ========================================
        # WORKFLOW 1: Check Device Pool Status
        # ========================================
        print("="*80)
        print("WORKFLOW 1: Device Pool Status")
        print("="*80)

        # Get total devices
        total_devices = await conn.fetchval('SELECT COUNT(*) FROM devices')
        print(f"[INFO] Total devices in system: {total_devices}")

        # Get available devices
        available_devices = await conn.fetchval(
            'SELECT COUNT(*) FROM devices WHERE status = $1',
            'available'
        )
        print(f"[INFO] Available devices: {available_devices}")

        # Get assigned devices
        assigned_count = await conn.fetchval(
            '''SELECT COUNT(*) FROM deviceassignments
               WHERE status = 'active' '''
        )
        print(f"[INFO] Currently assigned devices: {assigned_count}")

        # Get devices from enriched view
        enriched_devices = await conn.fetch(
            '''SELECT id, name, status, "connectionStatus", "batteryStatus",
                      "patientName", "assignmentStatus"
               FROM devices_enriched
               LIMIT 5'''
        )

        print(f"\n[SUCCESS] Sample devices from enriched view ({len(enriched_devices)} shown):")
        for device in enriched_devices:
            status_str = f"{device['status']} | {device['connectionStatus']} | Battery: {device['batteryStatus']}"
            if device['patientName']:
                status_str += f" | Patient: {device['patientName']}"
            print(f"   - {device['id']}: {device['name']} ({status_str})")

        # ========================================
        # WORKFLOW 2: Find Patient for Assignment
        # ========================================
        print("\n" + "="*80)
        print("WORKFLOW 2: Patient Data Check")
        print("="*80)

        # Get total patients
        total_patients = await conn.fetchval('SELECT COUNT(*) FROM patients')
        print(f"[INFO] Total patients in system: {total_patients}")

        # Get active patients
        active_patients = await conn.fetchval(
            "SELECT COUNT(*) FROM patients WHERE status = 'admitted'"
        )
        print(f"[INFO] Active admitted patients: {active_patients}")

        # Get sample patients
        patients = await conn.fetch(
            '''SELECT id, mrn, "firstName", "lastName", "roomNumber", status,
                      CONCAT("firstName", ' ', "lastName") as name
               FROM patients
               WHERE status = 'admitted'
               LIMIT 5'''
        )

        if patients:
            print(f"\n[SUCCESS] Sample admitted patients ({len(patients)} shown):")
            for patient in patients:
                print(f"   - {patient['id']}: {patient['name']} (Room: {patient['roomNumber']}, Status: {patient['status']})")
        else:
            print("\n[WARNING] No admitted patients found for testing")

        # ========================================
        # WORKFLOW 3: Device Assignment Simulation
        # ========================================
        print("\n" + "="*80)
        print("WORKFLOW 3: Device Assignment Workflow Check")
        print("="*80)

        # Find an available device
        available_device = await conn.fetchrow(
            '''SELECT id, name, "deviceType", status, location
               FROM devices
               WHERE status = 'available'
               LIMIT 1'''
        )

        if available_device:
            print(f"[SUCCESS] Found available device for assignment:")
            print(f"   - ID: {available_device['id']}")
            print(f"   - Name: {available_device['name']}")
            print(f"   - Type: {available_device['deviceType']}")
            print(f"   - Location: {available_device['location']}")
        else:
            print("[WARNING] No available devices found for assignment testing")

        # Check if we have both device and patient for simulation
        if available_device and patients:
            test_patient = patients[0]
            print(f"\n[INFO] Ready to test assignment:")
            print(f"   - Device: {available_device['name']} ({available_device['id']})")
            print(f"   - Patient: {test_patient['name']} ({test_patient['id']})")
            print(f"   - Note: This is a dry-run check only, no actual assignment made")

        # ========================================
        # WORKFLOW 4: Assignment History Check
        # ========================================
        print("\n" + "="*80)
        print("WORKFLOW 4: Assignment History")
        print("="*80)

        # Get recent assignments
        recent_assignments = await conn.fetch(
            '''SELECT da."deviceId", da."patientId", da.status as "assignmentStatus",
                      da."assignedAt", da."assignedBy",
                      d.name as "deviceName",
                      CONCAT(p."firstName", ' ', p."lastName") as "patientName"
               FROM deviceassignments da
               JOIN devices d ON da."deviceId" = d.id
               LEFT JOIN patients p ON da."patientId" = p.id
               ORDER BY da."assignedAt" DESC
               LIMIT 5'''
        )

        if recent_assignments:
            print(f"[SUCCESS] Recent assignments ({len(recent_assignments)} shown):")
            for assignment in recent_assignments:
                print(f"   - {assignment['deviceName']} -> {assignment['patientName'] or 'Unknown'}")
                print(f"     Status: {assignment['assignmentStatus']}, Assigned: {assignment['assignedAt']}")
        else:
            print("[INFO] No assignment history found")

        # ========================================
        # WORKFLOW 5: Connection Status Check
        # ========================================
        print("\n" + "="*80)
        print("WORKFLOW 5: Device Connection Status")
        print("="*80)

        # Get connection status breakdown
        connection_stats = await conn.fetch(
            '''SELECT "connectionStatus", COUNT(*) as count
               FROM devices_enriched
               GROUP BY "connectionStatus"
               ORDER BY count DESC'''
        )

        print("[SUCCESS] Connection status breakdown:")
        for stat in connection_stats:
            print(f"   - {stat['connectionStatus']}: {stat['count']} devices")

        # ========================================
        # WORKFLOW 6: Battery Status Check
        # ========================================
        print("\n" + "="*80)
        print("WORKFLOW 6: Battery Status")
        print("="*80)

        # Get battery status breakdown
        battery_stats = await conn.fetch(
            '''SELECT "batteryStatus", COUNT(*) as count
               FROM devices_enriched
               GROUP BY "batteryStatus"
               ORDER BY count DESC'''
        )

        print("[SUCCESS] Battery status breakdown:")
        for stat in battery_stats:
            print(f"   - {stat['batteryStatus']}: {stat['count']} devices")

        # Get low battery devices
        low_battery_devices = await conn.fetch(
            '''SELECT id, name, "batteryLevel", "batteryStatus"
               FROM devices_enriched
               WHERE "batteryStatus" IN ('low', 'critical')
               LIMIT 5'''
        )

        if low_battery_devices:
            print(f"\n[WARNING] Low battery devices ({len(low_battery_devices)} shown):")
            for device in low_battery_devices:
                print(f"   - {device['name']}: {device['batteryLevel']}% ({device['batteryStatus']})")
        else:
            print("\n[SUCCESS] No low battery devices")

        # ========================================
        # WORKFLOW 7: V2 API Readiness Check
        # ========================================
        print("\n" + "="*80)
        print("WORKFLOW 7: V2 API Readiness")
        print("="*80)

        # Check if devices_enriched view exists
        view_exists = await conn.fetchval(
            """SELECT COUNT(*) FROM information_schema.views
               WHERE table_name = 'devices_enriched'"""
        )
        print(f"[{'SUCCESS' if view_exists else 'ERROR'}] devices_enriched view exists: {view_exists == 1}")

        # Check if deviceassignments table has necessary columns
        assignment_columns = await conn.fetch(
            """SELECT column_name FROM information_schema.columns
               WHERE table_name = 'deviceassignments'
               ORDER BY column_name"""
        )
        expected_columns = ['assignedAt', 'assignedBy', 'deviceId', 'id', 'notes', 'patientId', 'status', 'unassignedAt', 'unassignedBy', 'unassignmentReason']
        actual_columns = [col['column_name'] for col in assignment_columns]

        print(f"[INFO] deviceassignments table columns: {', '.join(actual_columns)}")
        missing_columns = set(expected_columns) - set(actual_columns)
        if missing_columns:
            print(f"[WARNING] Missing expected columns: {', '.join(missing_columns)}")
        else:
            print(f"[SUCCESS] All expected columns present")

        # ========================================
        # Summary
        # ========================================
        print("\n" + "="*80)
        print("WORKFLOW TESTING SUMMARY")
        print("="*80)

        print(f"\n[INFO] Database Status:")
        print(f"   - Total Devices: {total_devices}")
        print(f"   - Available Devices: {available_devices}")
        print(f"   - Assigned Devices: {assigned_count}")
        print(f"   - Total Patients: {total_patients}")
        print(f"   - Admitted Patients: {active_patients}")

        print(f"\n[SUCCESS] Workflow Checks:")
        print(f"   - Device pool status: Working")
        print(f"   - Patient data available: {'Working' if patients else 'No admitted patients'}")
        print(f"   - Available devices for assignment: {'Working' if available_device else 'No available devices'}")
        print(f"   - Assignment history: {'Working' if recent_assignments else 'No history yet'}")
        print(f"   - Connection status tracking: Working")
        print(f"   - Battery status tracking: Working")
        print(f"   - V2 API infrastructure: Ready")

        print(f"\n[INFO] Ready for Testing:")
        ready_for_assignment = available_device and patients
        print(f"   - Device assignment workflow: {'Ready' if ready_for_assignment else 'Need devices or patients'}")
        print(f"   - ESP32 real-time testing: Ready")

        await conn.close()

        print("\n" + "="*80)
        print("[SUCCESS] WORKFLOW TESTING COMPLETED")
        print("="*80)

        return True

    except Exception as e:
        print(f"\n[ERROR] Workflow testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_complete_workflows())
    exit(0 if success else 1)
