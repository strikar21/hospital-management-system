import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(user='hospital_user', password='hospital123', database='hospitaldb')
    cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='patients' ORDER BY ordinal_position")
    print("Patients table columns:")
    for c in cols:
        print(f"  {c['column_name']}")
    await conn.close()

asyncio.run(check())
