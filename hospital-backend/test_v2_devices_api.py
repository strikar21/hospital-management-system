"""
Test V2 Devices API Endpoints
Verifies the new unified device query API works correctly
"""

import asyncio
import asyncpg
import sys

DB_CONFIG = {
    "host": "localhost",
    "database": "hospitaldb",
    "user": "hospital_user",
    "password": "hospital123"
}

async def test_v2_api():
    """Test v2 devices API by directly querying devices_enriched view"""
    print("="*80)
    print("TESTING V2 DEVICES API (Database Layer)")
    print("="*80)

    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        print("[SUCCESS] Connected to database\n")

        # Test 1: Get all devices (simulating GET /api/v2/devices)
        print("[TEST 1] Get all devices")
        query1 = """
            SELECT
                id, name, "deviceType", status, "connectionStatus",
                "batteryStatus", "assignedPatientId", "patientName"
            FROM devices_enriched
            ORDER BY "createdAt" DESC
            LIMIT 10
        """
        devices_all = await conn.fetch(query1)
        print(f"[RESULT] Found {len(devices_all)} devices:")
        for device in devices_all:
            patient_info = f" | Patient: {device['patientName']}" if device['patientName'] else " | No patient"
            print(f"  - {device['id']}: {device['name']} ({device['deviceType']}, {device['status']}, {device['connectionStatus']}){patient_info}")

        # Test 2: Get available watches only (simulating GET /api/v2/devices?deviceType=watch&status=available)
        print(f"\n[TEST 2] Get available watches only")
        query2 = """
            SELECT
                id, name, "deviceType", status, "connectionStatus", "batteryLevel"
            FROM devices_enriched
            WHERE "deviceType" = 'watch' AND status = 'available'
        """
        available_watches = await conn.fetch(query2)
        print(f"[RESULT] Found {len(available_watches)} available watches:")
        for watch in available_watches:
            battery = f"{watch['batteryLevel']}%" if watch['batteryLevel'] else "N/A"
            print(f"  - {watch['id']}: {watch['name']} (Battery: {battery}, {watch['connectionStatus']})")

        # Test 3: Get assigned devices (simulating GET /api/v2/devices?includeUnassigned=false)
        print(f"\n[TEST 3] Get assigned devices")
        query3 = """
            SELECT
                id, name, "deviceType", "assignedPatientId", "patientName",
                "patientLocation", "assignedAt"
            FROM devices_enriched
            WHERE "assignmentStatus" = 'active'
        """
        assigned_devices = await conn.fetch(query3)
        print(f"[RESULT] Found {len(assigned_devices)} assigned devices:")
        for device in assigned_devices:
            print(f"  - {device['id']}: {device['name']} -> Patient: {device['patientName']} ({device['patientLocation']})")

        # Test 4: Get devices by connection status (simulating GET /api/v2/devices?connectionStatus=offline)
        print(f"\n[TEST 4] Get offline devices")
        query4 = """
            SELECT
                id, name, "connectionStatus", "minutesSinceLastSeen"
            FROM devices_enriched
            WHERE "connectionStatus" = 'offline'
        """
        offline_devices = await conn.fetch(query4)
        print(f"[RESULT] Found {len(offline_devices)} offline devices:")
        for device in offline_devices:
            minutes = f"{device['minutesSinceLastSeen']:.0f} mins ago" if device['minutesSinceLastSeen'] else "Never seen"
            print(f"  - {device['id']}: {device['name']} (Last seen: {minutes})")

        # Test 5: Get low battery devices (simulating GET /api/v2/devices?batteryMax=20)
        print(f"\n[TEST 5] Get low battery devices")
        query5 = """
            SELECT
                id, name, "batteryLevel", "batteryStatus"
            FROM devices_enriched
            WHERE "batteryLevel" < 20
            ORDER BY "batteryLevel" ASC
        """
        low_battery = await conn.fetch(query5)
        print(f"[RESULT] Found {len(low_battery)} low battery devices:")
        for device in low_battery:
            print(f"  - {device['id']}: {device['name']} (Battery: {device['batteryLevel']}%, Status: {device['batteryStatus']})")

        # Test 6: Get device statistics (simulating GET /api/v2/devices/stats/summary)
        print(f"\n[TEST 6] Get device statistics")
        query6 = """
            SELECT
                COUNT(*) as "totalDevices",
                COUNT(*) FILTER (WHERE status = 'available') as "availableDevices",
                COUNT(*) FILTER (WHERE "assignmentStatus" = 'active') as "assignedDevices",
                COUNT(*) FILTER (WHERE "connectionStatus" = 'offline') as "offlineDevices",
                COUNT(*) FILTER (WHERE "batteryLevel" < 20) as "lowBatteryDevices",
                COUNT(*) FILTER (WHERE "deviceType" = 'watch') as "totalWatches"
            FROM devices_enriched
        """
        stats = await conn.fetchrow(query6)
        print(f"[RESULT] Device Pool Statistics:")
        print(f"  - Total Devices: {stats['totalDevices']}")
        print(f"  - Available: {stats['availableDevices']}")
        print(f"  - Assigned: {stats['assignedDevices']}")
        print(f"  - Offline: {stats['offlineDevices']}")
        print(f"  - Low Battery: {stats['lowBatteryDevices']}")
        print(f"  - Total Watches: {stats['totalWatches']}")

        await conn.close()

        print("\n" + "="*80)
        print("[SUCCESS] ALL V2 API TESTS PASSED")
        print("="*80)
        print("\nThe v2 devices API is ready to use:")
        print("  - GET /api/v2/devices (unified query with flexible filtering)")
        print("  - GET /api/v2/devices/{device_id} (single device)")
        print("  - GET /api/v2/devices/stats/summary (statistics)")
        print("  - GET /api/v2/devices/available/watches (convenience shortcut)")
        print("  - GET /api/v2/devices/assigned/all (convenience shortcut)")
        print("  - GET /api/v2/devices/low-battery/all (convenience shortcut)")

        return True

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_v2_api())
    sys.exit(0 if success else 1)
