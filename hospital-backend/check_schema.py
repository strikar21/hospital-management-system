import asyncio
import asyncpg
from app.core.config import settings

async def check_schema():
    conn = await asyncpg.connect(settings.databaseUrl)

    cols = await conn.fetch("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'patients'
        ORDER BY ordinal_position
    """)

    print("Patients table columns:")
    print("-" * 60)
    for row in cols:
        print(f"  {row['column_name']:30s} {row['data_type']}")
    print("-" * 60)

    await conn.close()

asyncio.run(check_schema())
