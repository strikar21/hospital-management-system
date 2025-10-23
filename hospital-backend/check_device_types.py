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

    # Get all unique device types
    device_types = await conn.fetch('SELECT DISTINCT "deviceType" FROM devices ORDER BY "deviceType"')
    
    print('\nDevice Types in Database:')
    print('=' * 50)
    for dt in device_types:
        count = await conn.fetchval(f'SELECT COUNT(*) FROM devices WHERE "deviceType" = $1', dt['deviceType'])
        print(f'- {dt["deviceType"]}: {count} device(s)')
    
    # Get sample devices
    print('\n\nAll Devices:')
    print('=' * 50)
    devices = await conn.fetch('SELECT id, "deviceType", name, status FROM devices ORDER BY "deviceType", id')
    for d in devices:
        print(f'{d["deviceType"].upper()}: {d["id"]} - {d["name"]} ({d["status"]})')

    await conn.close()

asyncio.run(check())
