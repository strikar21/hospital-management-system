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

    result = await conn.fetch("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'devices'
        ORDER BY ordinal_position
    """)

    print('\nDevices table schema:')
    print('-' * 40)
    for r in result:
        print(f"{r['column_name']}: {r['data_type']}")

    print('\n\nActual devices in table:')
    print('-' * 40)
    devices = await conn.fetch("SELECT * FROM devices LIMIT 5")
    if devices:
        for d in devices:
            print(dict(d))
    else:
        print("No devices found")

    await conn.close()

asyncio.run(check())
