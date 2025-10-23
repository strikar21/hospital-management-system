"""
Check current devices in database
"""
import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='hospitaldb',
        user='hospital_user',
        password='hospital123'
    )

    try:
        print('\n[Devices in database]')
        devices = await conn.fetch('SELECT id, name, "deviceType", status FROM devices ORDER BY id')

        if devices:
            for device in devices:
                print(f"  - {device['id']}: {device['name']} ({device['deviceType']}) - {device['status']}")
        else:
            print('  No devices found')

        print('\n[MAC Mappings]')
        mappings = await conn.fetch('SELECT mac_address, device_id FROM device_mac_mapping ORDER BY device_id')

        if mappings:
            for mapping in mappings:
                print(f"  - {mapping['mac_address']} -> {mapping['device_id']}")
        else:
            print('  No mappings found')

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check())
