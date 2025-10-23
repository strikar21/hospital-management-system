"""
Check Existing Data - Research actual patient and device data
MANDATORY: Never assume IDs - always check what actually exists
"""

import asyncio
import asyncpg
import sys
from datetime import datetime

DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'hospitaldb',
    'user': 'hospital_user',
    'password': 'hospital123'
}

async def check_existing_data():
    """Check what patients and devices actually exist in the database"""

    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)

        print("=" * 80)
        print("EXISTING DATA RESEARCH - Device Workflow Testing")
        print("=" * 80)
        print(f"Timestamp: {datetime.now().isoformat()}\n")

        # Check patients
        print("\n[PATIENTS IN DATABASE]")
        print("-" * 80)
        patients = await conn.fetch("""
            SELECT id, "firstName", "lastName", "dateOfBirth", "admissionDate", "dischargeDate"
            FROM patients
            ORDER BY "admissionDate" DESC
            LIMIT 10
        """)

        if patients:
            print(f"Found {len(patients)} patient(s):\n")
            for idx, p in enumerate(patients, 1):
                status = "Discharged" if p['dischargeDate'] else "Active"
                print(f"{idx}. Patient ID: {p['id']}")
                print(f"   Name: {p['firstName']} {p['lastName']}")
                print(f"   DOB: {p['dateOfBirth']}")
                print(f"   Admission: {p['admissionDate']}")
                print(f"   Status: {status}")
                print()
        else:
            print("WARNING: No patients found in database\n")

        # Check devices
        print("\n[DEVICES IN DATABASE]")
        print("-" * 80)
        devices = await conn.fetch("""
            SELECT id, "deviceType", status, "batteryLevel", "lastSeen", "firmwareVersion"
            FROM devices
            ORDER BY id
        """)

        if devices:
            print(f"Found {len(devices)} device(s):\n")
            for idx, d in enumerate(devices, 1):
                print(f"{idx}. Device ID: {d['id']}")
                print(f"   Type: {d['deviceType']}")
                print(f"   Status: {d['status']}")
                print(f"   Battery: {d['batteryLevel']}%")
                print(f"   Last Seen: {d['lastSeen']}")
                print(f"   Firmware: {d['firmwareVersion']}")
                print()
        else:
            print("WARNING: No devices found in database\n")

        # Check device assignments
        print("\n[CURRENT DEVICE ASSIGNMENTS]")
        print("-" * 80)
        assignments = await conn.fetch("""
            SELECT
                da.id,
                da."patientId",
                da."deviceId",
                da.status,
                da."assignedAt",
                da."unassignedAt",
                p."firstName",
                p."lastName",
                d."deviceType"
            FROM deviceassignments da
            JOIN patients p ON p.id = da."patientId"
            JOIN devices d ON d.id = da."deviceId"
            ORDER BY da."assignedAt" DESC
            LIMIT 10
        """)

        if assignments:
            print(f"Found {len(assignments)} assignment(s):\n")
            for idx, a in enumerate(assignments, 1):
                print(f"{idx}. Assignment ID: {a['id']}")
                print(f"   Patient: {a['firstName']} {a['lastName']} (ID: {a['patientId']})")
                print(f"   Device: {a['deviceId']} ({a['deviceType']})")
                print(f"   Status: {a['status']}")
                print(f"   Assigned: {a['assignedAt']}")
                if a['unassignedAt']:
                    print(f"   Unassigned: {a['unassignedAt']}")
                print()
        else:
            print("WARNING: No device assignments found\n")

        # Check alerts
        print("\n[RECENT ALERTS]")
        print("-" * 80)
        try:
            alerts = await conn.fetch("""
                SELECT
                    id,
                    "patientId",
                    "alertType",
                    severity,
                    message,
                    "isAcknowledged",
                    "createdAt"
                FROM alerts
                ORDER BY "createdAt" DESC
                LIMIT 5
            """)

            if alerts:
                print(f"Found {len(alerts)} recent alert(s):\n")
                for idx, a in enumerate(alerts, 1):
                    ack = "[Acknowledged]" if a['isAcknowledged'] else "[Pending]"
                    print(f"{idx}. Alert ID: {a['id']}")
                    print(f"   Patient ID: {a['patientId']}")
                    print(f"   Type: {a['alertType']}")
                    print(f"   Severity: {a['severity']}")
                    print(f"   Message: {a['message']}")
                    print(f"   Status: {ack}")
                    print(f"   Created: {a['createdAt']}")
                    print()
            else:
                print("INFO: No alerts found\n")
        except Exception as e:
            alerts = []
            print(f"INFO: Alerts table not available ({str(e).split(':')[0]})\n")

        # Check vitals timeseries (TimescaleDB)
        print("\n[CHECKING TIMESCALEDB CONNECTION]")
        print("-" * 80)
        try:
            ts_conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                database='hospital_timeseries',
                user='hospital_user',
                password='hospital123'
            )

            vitals_count = await ts_conn.fetchval("""
                SELECT COUNT(*) FROM vitals_timeseries
            """)

            print(f"[OK] TimescaleDB connected")
            print(f"[OK] Total vitals records: {vitals_count}\n")

            if vitals_count > 0:
                recent_vitals = await ts_conn.fetch("""
                    SELECT
                        "patientId",
                        "deviceId",
                        "vitalType",
                        value,
                        unit,
                        time
                    FROM vitals_timeseries
                    ORDER BY time DESC
                    LIMIT 5
                """)

                print("Recent vitals:")
                for v in recent_vitals:
                    print(f"  - Patient {v['patientId']}: {v['vitalType']} = {v['value']} {v['unit']} (Device: {v['deviceId']})")
                print()

            await ts_conn.close()

        except Exception as e:
            print(f"WARNING: TimescaleDB not available: {e}\n")

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY FOR TEST PLANNING")
        print("=" * 80)
        print(f"[OK] Patients: {len(patients)}")
        print(f"[OK] Devices: {len(devices)}")
        print(f"[OK] Active Assignments: {len([a for a in assignments if a['status'] == 'active'])}")
        print(f"[OK] Total Assignments: {len(assignments)}")
        print(f"[OK] Alerts: {len(alerts)}")

        if len(patients) >= 2 and len(devices) >= 1:
            print("\n[READY] Sufficient data for comprehensive workflow testing")
        elif len(patients) == 0:
            print("\n[WARNING] No patients found - need to create test patients")
        elif len(devices) == 0:
            print("\n[WARNING] No devices found - need to create test devices")
        else:
            print("\n[WARNING] Limited data - may need to create additional test data")

        print("=" * 80)

        await conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(check_existing_data())
    sys.exit(0 if success else 1)
