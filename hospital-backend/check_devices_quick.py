import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    devices = await conn.fetch('SELECT id, name, "deviceType", status, "macAddress" FROM devices ORDER BY "createdAt" DESC LIMIT 10')

    print('\n📱 Devices in database:')
    for d in devices:
        print(f'  {d["id"]}: {d["name"]} ({d["deviceType"]}) - {d["status"]} - MAC: {d["macAddress"]}')

    print(f'\nTotal devices: {len(devices)}')

    await conn.close()

asyncio.run(check())
