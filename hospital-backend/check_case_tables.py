"""Check which case-related tables exist in database"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb"

async def check():
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 60)
    print("CASE-RELATED TABLES IN DATABASE")
    print("=" * 60)

    tables = await conn.fetch("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public' AND tablename LIKE '%case%'
        ORDER BY tablename
    """)

    print("\nTables found:")
    for t in tables:
        print(f"  - {t['tablename']}")

    # Check casesheetentries columns
    if any(t['tablename'] == 'casesheetentries' for t in tables):
        print("\n" + "=" * 60)
        print("casesheetentries SCHEMA")
        print("=" * 60)
        cols = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'casesheetentries'
            ORDER BY ordinal_position
        """)
        for col in cols:
            print(f"  {col['column_name']}: {col['data_type']}")

    # Check caseEntries columns if exists
    if any(t['tablename'] == 'caseEntries' for t in tables):
        print("\n" + "=" * 60)
        print("caseEntries SCHEMA")
        print("=" * 60)
        cols = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'caseEntries'
            ORDER BY ordinal_position
        """)
        for col in cols:
            print(f"  {col['column_name']}: {col['data_type']}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(check())
