import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(host="localhost", database="hospitaldb", user="hospital_user", password="hospital123")
    cols = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name = 'patients' ORDER BY ordinal_position")
    print("Patients columns:", [c["column_name"] for c in cols])
    await conn.close()

asyncio.run(check())
