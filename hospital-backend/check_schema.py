import asyncio
import asyncpg
from app.core.config import settings

async def check_schema():
    conn = await asyncpg.connect(settings.POSTGRES_URI)

    cols = await conn.fetch("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'patients'
        ORDER BY ordinal_position
    """)

    print("Patients table columns:")
    for row in cols:
        print(f"  - {row['column_name']}")

    await conn.close()

asyncio.run(check_schema())
