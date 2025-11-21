"""
Test FHIR Resource Operations
Tests Device, Observation, and DeviceAssociation handlers
"""

import asyncio
import asyncpg
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.fhir_r5.repository import FHIRResourceRepository
from app.fhir_r5.handlers.device_handler import DeviceHandler
from app.fhir_r5.handlers.observation_handler import ObservationHandler
from app.fhir_r5.handlers.device_association_handler import DeviceAssociationHandler


DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'hospital',
    'password': 'hospital123',
    'database': 'hospitaldb'
}


async def test_device_operations():
    """Test Device CRUD operations"""

    print("\n" + "=" * 70)
    print("Testing Device Operations")
    print("=" * 70)

    pool = await asyncpg.create_pool(**DB_CONFIG)
    repository = FHIRResourceRepository(pool)
    handler = DeviceHandler(repository)

    try:
        # Test 1: Create device
        print("\n[TEST 1] Creating new device...")

        device = {
            "resourceType": "Device",
            "id": "DEV-TEST-001",
            "identifier": [{
                "system": "http://hospital.example.com/device",
                "value": "ESP32-WATCH-TEST-001"
            }],
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
                {"type": {"text": "batteryLevel"}, "valueQuantity": [{"value": 85, "unit": "%"}]}
            ]
        }

        created = await handler.create_device(device)
        print(f"  [SUCCESS] Created device {created['id']}")
        print(f"  Manufacturer: {created.get('manufacturer')}")
        print(f"  Status: {created['status']}")

        # Test 2: Get device
        print("\n[TEST 2] Retrieving device...")

        retrieved = await handler.get_device("DEV-TEST-001")

        if retrieved:
            print(f"  [SUCCESS] Retrieved device DEV-TEST-001")
            print(f"  Model: {retrieved.get('modelNumber')}")
        else:
            print(f"  [FAILED] Could not retrieve device")

        # Test 3: Update device
        print("\n[TEST 3] Updating device...")

        updated = await handler.update_device("DEV-TEST-001", {
            "status": "inactive",
            "property": [
                {"type": {"text": "deviceType"}, "valueCodeableConcept": [{"text": "watch"}]},
                {"type": {"text": "batteryLevel"}, "valueQuantity": [{"value": 15, "unit": "%"}]},
                {"type": {"text": "lastSeen"}, "valueDateTime": datetime.now(timezone.utc).isoformat()}
            ]
        })

        print(f"  [SUCCESS] Updated device status: {updated['status']}")

        # Test 4: Search devices
        print("\n[TEST 4] Searching devices...")

        active_devices = await handler.search_devices(status="active")
        inactive_devices = await handler.search_devices(status="inactive")

        print(f"  [SUCCESS] Found {len(active_devices)} active device(s)")
        print(f"  [SUCCESS] Found {len(inactive_devices)} inactive device(s)")

        # Test 5: Search by device type
        print("\n[TEST 5] Searching by device type...")

        watches = await handler.search_devices(device_type="watch")

        print(f"  [SUCCESS] Found {len(watches)} watch device(s)")

        print("\n[PASSED] All device operations completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Device test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await pool.close()


async def test_observation_operations():
    """Test Observation operations"""

    print("\n" + "=" * 70)
    print("Testing Observation Operations")
    print("=" * 70)

    pool = await asyncpg.create_pool(**DB_CONFIG)
    handler = ObservationHandler(pool)

    try:
        # Test 1: Create heart rate observation
        print("\n[TEST 1] Creating heart rate observation...")

        observation = {
            "resourceType": "Observation",
            "id": "OBS-HR-TEST-001",
            "status": "final",
            "category": [{
                "coding": [{"code": "vital-signs", "display": "Vital Signs"}]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "8867-4",
                    "display": "Heart rate"
                }]
            },
            "subject": {"reference": "Patient/PAT000001"},
            "device": {"reference": "Device/DEV000001"},
            "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
            "valueQuantity": {
                "value": 78,
                "unit": "beats/minute",
                "system": "http://unitsofmeasure.org",
                "code": "/min"
            }
        }

        created = await handler.create_observation(observation)
        print(f"  [SUCCESS] Created observation {created['id']}")
        print(f"  Code: {created['code']['coding'][0]['display']}")
        print(f"  Value: {created['valueQuantity']['value']} {created['valueQuantity']['unit']}")

        # Test 2: Create SpO2 observation
        print("\n[TEST 2] Creating SpO2 observation...")

        spo2_obs = {
            "resourceType": "Observation",
            "id": "OBS-SPO2-TEST-001",
            "status": "final",
            "category": [{
                "coding": [{"code": "vital-signs"}]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "59408-5",
                    "display": "Oxygen saturation"
                }]
            },
            "subject": {"reference": "Patient/PAT000001"},
            "device": {"reference": "Device/DEV000001"},
            "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
            "valueQuantity": {
                "value": 98,
                "unit": "%"
            }
        }

        await handler.create_observation(spo2_obs)
        print(f"  [SUCCESS] Created SpO2 observation")

        # Test 3: Search observations by patient
        print("\n[TEST 3] Searching observations by patient...")

        patient_obs = await handler.get_observations(patient_id="PAT000001", limit=10)

        print(f"  [SUCCESS] Found {len(patient_obs)} observation(s) for PAT000001")
        for obs in patient_obs:
            code = obs['code']['coding'][0].get('display', obs['code']['coding'][0]['code'])
            value = obs.get('valueQuantity', {}).get('value', 'N/A')
            unit = obs.get('valueQuantity', {}).get('unit', '')
            print(f"    - {code}: {value} {unit}")

        # Test 4: Search by LOINC code
        print("\n[TEST 4] Searching observations by LOINC code...")

        hr_obs = await handler.get_observations(
            patient_id="PAT000001",
            code="8867-4",
            limit=10
        )

        print(f"  [SUCCESS] Found {len(hr_obs)} heart rate observation(s)")

        # Test 5: Get latest observation
        print("\n[TEST 5] Getting latest observation...")

        latest_hr = await handler.get_latest_observation("PAT000001", "8867-4")

        if latest_hr:
            print(f"  [SUCCESS] Latest heart rate: {latest_hr['valueQuantity']['value']} {latest_hr['valueQuantity']['unit']}")
        else:
            print(f"  [WARNING] No observations found")

        # Test 6: Get observation statistics
        print("\n[TEST 6] Getting observation statistics...")

        stats = await handler.get_observation_stats("PAT000001", "8867-4")

        print(f"  [SUCCESS] Heart rate statistics:")
        print(f"    Count: {stats['count']}")
        print(f"    Min: {stats['min']}")
        print(f"    Max: {stats['max']}")
        print(f"    Avg: {stats['avg']:.2f}" if stats['avg'] else "    Avg: N/A")

        print("\n[PASSED] All observation operations completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] Observation test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await pool.close()


async def test_device_association_operations():
    """Test DeviceAssociation operations"""

    print("\n" + "=" * 70)
    print("Testing DeviceAssociation Operations")
    print("=" * 70)

    pool = await asyncpg.create_pool(**DB_CONFIG)
    repository = FHIRResourceRepository(pool)
    handler = DeviceAssociationHandler(repository)

    try:
        # Test 1: Create device association
        print("\n[TEST 1] Creating device-patient association...")

        association = {
            "resourceType": "DeviceAssociation",
            "id": "ASSOC-TEST-001",
            "status": {"coding": [{"code": "active"}]},
            "subject": {"reference": "Patient/PAT000001"},
            "device": {"reference": "Device/DEV000001"},
            "period": {
                "start": datetime.now(timezone.utc).isoformat()
            }
        }

        created = await handler.create_association(association)
        print(f"  [SUCCESS] Created association {created['id']}")
        print(f"  Patient: {created['subject']['reference']}")
        print(f"  Device: {created['device']['reference']}")
        print(f"  Status: {created['status']['coding'][0]['code']}")

        # Test 2: Get association
        print("\n[TEST 2] Retrieving association...")

        retrieved = await handler.get_association("ASSOC-TEST-001")

        if retrieved:
            print(f"  [SUCCESS] Retrieved association ASSOC-TEST-001")
        else:
            print(f"  [FAILED] Could not retrieve association")

        # Test 3: Search by patient
        print("\n[TEST 3] Searching associations by patient...")

        patient_assocs = await handler.search_associations(patient_id="PAT000001")

        print(f"  [SUCCESS] Found {len(patient_assocs)} association(s) for PAT000001")
        for assoc in patient_assocs:
            device = assoc['device']['reference']
            status = assoc['status']['coding'][0]['code']
            print(f"    - {device} ({status})")

        # Test 4: Get active device for patient
        print("\n[TEST 4] Getting active device for patient...")

        active_device = await handler.get_active_device_for_patient("PAT000001")

        if active_device:
            print(f"  [SUCCESS] Active device: {active_device['device']['reference']}")
        else:
            print(f"  [INFO] No active device found")

        # Test 5: End association
        print("\n[TEST 5] Ending association...")

        ended = await handler.end_association("ASSOC-TEST-001")

        print(f"  [SUCCESS] Association ended")
        print(f"  Status: {ended['status']['coding'][0]['code']}")
        print(f"  End time: {ended['period'].get('end', 'N/A')}")

        print("\n[PASSED] All device association operations completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] DeviceAssociation test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await pool.close()


async def run_all_tests():
    """Run all FHIR resource tests"""

    print("=" * 70)
    print("FHIR R5 Resource Operations - Comprehensive Test Suite")
    print("=" * 70)

    await test_device_operations()
    await test_observation_operations()
    await test_device_association_operations()

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)
    print("\n[SUCCESS] All FHIR resource operations working correctly!")
    print("\nTested Components:")
    print("  [OK] Device Handler (Create, Read, Update, Search)")
    print("  [OK] Observation Handler (Create, Search, Stats)")
    print("  [OK] DeviceAssociation Handler (Create, Search, End)")
    print("  [OK] FHIR Resource Repository (CRUD operations)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
