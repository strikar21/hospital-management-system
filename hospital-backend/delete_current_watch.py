"""
Delete ESP32-WATCH-A0A3B3AA13B0 device from database
"""
import asyncio
import asyncpg

async def delete_watch():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='hospitaldb',
        user='hospital_user',
        password='hospital123'
    )

    try:
        device_id = 'ESP32-WATCH-A0A3B3AA13B0'

        print(f'\n[Deleting device: {device_id}]')

        # Check if exists
        device = await conn.fetchrow('SELECT * FROM devices WHERE id = $1', device_id)

        if device:
            print(f'  Found: {device["name"]} ({device["deviceType"]}) - {device["status"]}')

            # Delete device
            await conn.execute('DELETE FROM devices WHERE id = $1', device_id)
            print(f'  [OK] Deleted device: {device_id}')
        else:
            print(f'  Device not found in database')

        print('\n[Remaining devices]')
        devices = await conn.fetch('SELECT id, name FROM devices ORDER BY id')

        if devices:
            for d in devices:
                print(f"  - {d['id']}: {d['name']}")
        else:
            print('  No devices found')

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(delete_watch())
