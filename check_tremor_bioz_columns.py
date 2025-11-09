import asyncpg
import asyncio

async def check_columns():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    cols = await conn.fetch("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'vitals_realtime'
          AND column_name IN ('tremor', 'bioimpedance')
        ORDER BY column_name
    """)

    print(f'Columns found: {len(cols)}')
    for col in cols:
        print(f"  {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")

    await conn.close()

asyncio.run(check_columns())
