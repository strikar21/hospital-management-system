import asyncio
import asyncpg

async def check_ids():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    print("\n=== ACTUAL PATIENT IDS ===")
    rows = await conn.fetch('SELECT id, "firstName", "lastName" FROM patients LIMIT 5')
    for r in rows:
        print(f'{r["id"]} - {r["firstName"]} {r["lastName"]}')

    print("\n=== ACTUAL STAFF IDS ===")
    rows = await conn.fetch('SELECT id, "firstName", "lastName", role FROM staff LIMIT 5')
    for r in rows:
        print(f'{r["id"]} - {r["firstName"]} {r["lastName"]} ({r["role"]})')

    print("\n=== ACTUAL DEVICE IDS ===")
    rows = await conn.fetch('SELECT id, "serialNumber", "deviceType" FROM devices LIMIT 5')
    for r in rows:
        print(f'{r["id"]} - {r["serialNumber"]} ({r["deviceType"]})')

    await conn.close()

asyncio.run(check_ids())
