"""
Seed FHIR R5 Database with Initial Test Data
- 2 staff members (doctor + nurse with NFC badges)
- 3 devices (2 ESP32 watches + 1 door scanner)
"""

import asyncio
import asyncpg
import json
from datetime import datetime, timezone
import bcrypt

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'hospital',
    'password': 'hospital123',
    'database': 'hospitaldb'
}

async def seed_staff(conn):
    """Seed 2 staff members"""
    print("\n[1] Seeding staff...")

    # Hash password for staff
    password_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    staff_data = [
        {
            'id': 'STF000001',
            'nfcBadgeId': 'NFC-DOC-001',
            'pin': '1234',
            'passwordHash': password_hash,
            'role': 'doctor'
        },
        {
            'id': 'STF000002',
            'nfcBadgeId': 'NFC-NURSE-001',
            'pin': '5678',
            'passwordHash': password_hash,
            'role': 'nurse'
        }
    ]

    for staff in staff_data:
        await conn.execute("""
            INSERT INTO staff (id, nfcBadgeId, pin, passwordHash, role, status)
            VALUES ($1, $2, $3, $4, $5, 'active')
        """, staff['id'], staff['nfcBadgeId'], staff['pin'],
           staff['passwordHash'], staff['role'])

        print(f"  [CREATED] Staff {staff['id']} - {staff['role']} (NFC: {staff['nfcBadgeId']})")

    # Create corresponding FHIR Practitioner resources
    practitioner_resources = [
        {
            "resourceType": "Practitioner",
            "id": "PRAC-STF000001",
            "identifier": [
                {"system": "http://hospital.example.com/staff", "value": "STF000001"}
            ],
            "name": [
                {"family": "Smith", "given": ["Sarah"], "prefix": ["Dr."]}
            ],
            "qualification": [
                {"code": {"coding": [{"code": "MD", "display": "Doctor of Medicine"}]}}
            ],
            "active": True
        },
        {
            "resourceType": "Practitioner",
            "id": "PRAC-STF000002",
            "identifier": [
                {"system": "http://hospital.example.com/staff", "value": "STF000002"}
            ],
            "name": [
                {"family": "Johnson", "given": ["Michael"]}
            ],
            "qualification": [
                {"code": {"coding": [{"code": "RN", "display": "Registered Nurse"}]}}
            ],
            "active": True
        }
    ]

    for prac in practitioner_resources:
        await conn.execute("""
            INSERT INTO fhirResources (resourceType, resourceId, resource, status)
            VALUES ($1, $2, $3, $4)
        """, prac['resourceType'], prac['id'], json.dumps(prac), 'active')

        print(f"  [CREATED] FHIR Resource {prac['resourceType']}/{prac['id']}")

    print(f"[SUCCESS] Seeded {len(staff_data)} staff members\n")

async def seed_devices(conn):
    """Seed 3 devices (2 ESP32 watches + 1 door scanner)"""
    print("[2] Seeding devices...")

    devices = [
        {
            "resourceType": "Device",
            "id": "DEV000001",
            "identifier": [
                {"system": "http://hospital.example.com/device", "value": "ESP32-WATCH-001"}
            ],
            "type": [{
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "706767009",
                    "display": "Patient monitoring system"
                }]
            }],
            "status": "active",
            "manufacturer": "Waveshare",
            "modelNumber": "ESP32-S3-Touch-AMOLED-1.64",
            "property": [
                {"type": {"text": "deviceType"}, "valueCodeableConcept": [{"text": "watch"}]},
                {"type": {"text": "batteryLevel"}, "valueQuantity": [{"value": 100, "unit": "%"}]},
                {"type": {"text": "lastCalibrated"}, "valueDateTime": datetime.now(timezone.utc).isoformat()}
            ]
        },
        {
            "resourceType": "Device",
            "id": "DEV000002",
            "identifier": [
                {"system": "http://hospital.example.com/device", "value": "ESP32-WATCH-002"}
            ],
            "type": [{
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "706767009",
                    "display": "Patient monitoring system"
                }]
            }],
            "status": "active",
            "manufacturer": "Waveshare",
            "modelNumber": "ESP32-S3-Touch-AMOLED-1.64",
            "property": [
                {"type": {"text": "deviceType"}, "valueCodeableConcept": [{"text": "watch"}]},
                {"type": {"text": "batteryLevel"}, "valueQuantity": [{"value": 95, "unit": "%"}]},
                {"type": {"text": "lastCalibrated"}, "valueDateTime": datetime.now(timezone.utc).isoformat()}
            ]
        },
        {
            "resourceType": "Device",
            "id": "DEV000003",
            "identifier": [
                {"system": "http://hospital.example.com/device", "value": "ESP32-DOOR-SCANNER-001"}
            ],
            "type": [{
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "464135003",
                    "display": "Access control device"
                }]
            }],
            "status": "active",
            "manufacturer": "Hospital IoT Labs",
            "modelNumber": "ESP32-NFC-SCANNER-V1",
            "property": [
                {"type": {"text": "deviceType"}, "valueCodeableConcept": [{"text": "door_scanner"}]},
                {"type": {"text": "location"}, "valueString": "ICU Ward - Main Entrance"}
            ]
        }
    ]

    for device in devices:
        await conn.execute("""
            INSERT INTO fhirResources (resourceType, resourceId, resource, status)
            VALUES ($1, $2, $3, $4)
        """, device['resourceType'], device['id'], json.dumps(device), device['status'])

        device_type = next((p['valueCodeableConcept'][0]['text'] for p in device.get('property', [])
                          if p['type']['text'] == 'deviceType'), 'unknown')
        print(f"  [CREATED] Device {device['id']} - {device_type} ({device['status']})")

    print(f"[SUCCESS] Seeded {len(devices)} devices\n")

async def seed_initial_calibration(conn):
    """Seed initial calibration records for devices"""
    print("[3] Seeding device calibration records...")

    calibrations = [
        {
            'time': datetime.now(timezone.utc),
            'deviceId': 'Device/DEV000001',
            'calibrationType': 'initial',
            'performedBy': 'Practitioner/PRAC-STF000001',
            'heartRateAccuracy': 98.5,
            'spo2Accuracy': 99.2,
            'temperatureAccuracy': 99.8,
            'bloodPressureAccuracy': 97.5,
            'status': 'pass',
            'notes': 'Initial calibration successful. All sensors within acceptable range.',
            'nextCalibrationDue': datetime(2026, 1, 21, 0, 0, 0, tzinfo=timezone.utc)
        },
        {
            'time': datetime.now(timezone.utc),
            'deviceId': 'Device/DEV000002',
            'calibrationType': 'initial',
            'performedBy': 'Practitioner/PRAC-STF000001',
            'heartRateAccuracy': 97.8,
            'spo2Accuracy': 98.9,
            'temperatureAccuracy': 99.5,
            'bloodPressureAccuracy': 96.8,
            'status': 'pass',
            'notes': 'Initial calibration successful. All sensors within acceptable range.',
            'nextCalibrationDue': datetime(2026, 1, 21, 0, 0, 0, tzinfo=timezone.utc)
        }
    ]

    for cal in calibrations:
        await conn.execute("""
            INSERT INTO deviceCalibration
            (time, deviceId, calibrationType, performedBy, heartRateAccuracy,
             spo2Accuracy, temperatureAccuracy, bloodPressureAccuracy, status, notes, nextCalibrationDue)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """, cal['time'], cal['deviceId'], cal['calibrationType'], cal['performedBy'],
           cal['heartRateAccuracy'], cal['spo2Accuracy'], cal['temperatureAccuracy'],
           cal['bloodPressureAccuracy'], cal['status'], cal['notes'], cal['nextCalibrationDue'])

        print(f"  [CREATED] Calibration for {cal['deviceId']} - {cal['status']} ({cal['calibrationType']})")

    print(f"[SUCCESS] Seeded {len(calibrations)} calibration records\n")

async def verify_seed_data(conn):
    """Verify seeded data"""
    print("[4] Verifying seeded data...\n")

    # Count records in each table
    staff_count = await conn.fetchval("SELECT COUNT(*) FROM staff")
    resources_count = await conn.fetchval("SELECT COUNT(*) FROM fhirResources")
    calibration_count = await conn.fetchval("SELECT COUNT(*) FROM deviceCalibration")

    print(f"  Staff: {staff_count} records")
    print(f"  FHIR Resources: {resources_count} records")
    print(f"    - Practitioners: {await conn.fetchval('SELECT COUNT(*) FROM fhirResources WHERE resourceType = $1', 'Practitioner')}")
    print(f"    - Devices: {await conn.fetchval('SELECT COUNT(*) FROM fhirResources WHERE resourceType = $1', 'Device')}")
    print(f"  Device Calibrations: {calibration_count} records")

    # Show staff details
    print("\n  Staff Details:")
    staff_list = await conn.fetch("SELECT id, role, nfcBadgeId, status FROM staff ORDER BY id")
    for s in staff_list:
        print(f"    - {s['id']}: {s['role']} (NFC: {s['nfcbadgeid']}, Status: {s['status']})")

    # Show device details
    print("\n  Device Details:")
    devices = await conn.fetch("""
        SELECT resourceId, resource->>'status' as status,
               resource->'identifier'->0->>'value' as identifier
        FROM fhirResources
        WHERE resourceType = 'Device'
        ORDER BY resourceId
    """)
    for d in devices:
        print(f"    - {d['resourceid']}: {d['identifier']} (Status: {d['status']})")

    print()

async def main():
    """Main seed function"""
    print("=" * 70)
    print("FHIR R5 Database Seeding - Test Data")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        await seed_staff(conn)
        await seed_devices(conn)
        await seed_initial_calibration(conn)
        await verify_seed_data(conn)

        print("=" * 70)
        print("[SUCCESS] Database seeding completed successfully!")
        print("=" * 70)
        print("\nTest credentials:")
        print("  Doctor:  ID=STF000001, NFC=NFC-DOC-001, PIN=1234, Password=password123")
        print("  Nurse:   ID=STF000002, NFC=NFC-NURSE-001, PIN=5678, Password=password123")
        print("\nDevices available:")
        print("  - DEV000001: ESP32-WATCH-001 (active, calibrated)")
        print("  - DEV000002: ESP32-WATCH-002 (active, calibrated)")
        print("  - DEV000003: ESP32-DOOR-SCANNER-001 (active)")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Seeding failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
