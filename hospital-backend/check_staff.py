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

    staff = await conn.fetch('SELECT id, "firstName", "lastName", role, pin, password FROM staff LIMIT 5')

    print('Staff members:')
    print('-' * 80)
    for s in staff:
        print(f"ID: {s['id']}")
        print(f"Name: {s['firstName']} {s['lastName']}")
        print(f"Role: {s['role']}")
        print(f"PIN: {s['pin']}")
        print(f"Password: {s['password']}")
        print()

    await conn.close()

asyncio.run(check())
