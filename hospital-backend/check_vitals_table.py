import asyncpg
import asyncio

async def check_table():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    # Check if table exists
    exists = await conn.fetchval("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'vitals_realtime'
    """)

    print(f"vitals_realtime table exists: {exists == 1}")

    if exists:
        # List all columns
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'vitals_realtime'
            ORDER BY ordinal_position
        """)

        print(f"\nFound {len(columns)} columns:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")

    await conn.close()

asyncio.run(check_table())
