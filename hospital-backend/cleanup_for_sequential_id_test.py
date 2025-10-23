"""
Cleanup script to prepare for sequential device ID testing
Deletes the current ESP32-WATCH-A0A3B3AA13B0 device to allow reprovisioning with new sequential ID
"""
import asyncio
import asyncpg

async def cleanup():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='hospitaldb',
        user='hospital_user',
        password='hospital123'
    )

    try:
        device_id = 'ESP32-WATCH-A0A3B3AA13B0'

        print(f'\n[Checking device: {device_id}]')
        device = await conn.fetchrow('SELECT * FROM devices WHERE id = $1', device_id)

        if device:
            print(f'  Found: {device["name"]} ({device["deviceType"]}) - {device["status"]}')

            # Check if assigned to patient
            if device['status'] == 'assigned':
                print('  [WARNING] Device is assigned to a patient')
                print('  Please unassign the device first before deleting')
                return

            # Delete device (cascades to device_mac_mapping due to FK constraint)
            await conn.execute('DELETE FROM devices WHERE id = $1', device_id)
            print(f'  [OK] Deleted device: {device_id}')

            # Verify deletion
            count = await conn.fetchval('SELECT COUNT(*) FROM devices WHERE id = $1', device_id)
            if count == 0:
                print('  [OK] Device successfully removed from database')
            else:
                print('  [ERROR] Device still exists in database')

        else:
            print(f'  Device not found in database')

        print('\n[Current devices after cleanup]')
        devices = await conn.fetch('SELECT id, name, "deviceType", status FROM devices ORDER BY id')

        if devices:
            for d in devices:
                print(f"  - {d['id']}: {d['name']} ({d['deviceType']}) - {d['status']}")
        else:
            print('  No devices found')

    except Exception as e:
        print(f'[ERROR] Cleanup failed: {e}')
        raise

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(cleanup())
