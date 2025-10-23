import asyncio
import asyncpg

async def check_device():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    mac = 'A0:A3:B3:AA:13:B0'

    # First check what columns exist
    columns = await conn.fetch('''
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'devices'
        ORDER BY ordinal_position
    ''')

    print("Columns in devices table:")
    for col in columns:
        print(f"  - {col['column_name']}")
    print()

    result = await conn.fetch('''
        SELECT *
        FROM devices
        WHERE "macAddress" = $1
    ''', mac)

    if result:
        print("Device found in database:")
        for row in result:
            print(dict(row))
    else:
        print(f"No device found with MAC: {mac}")

    await conn.close()

asyncio.run(check_device())
