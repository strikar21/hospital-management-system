"""Drop the old empty casesheetentries table"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb"

async def drop_table():
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 60)
    print("DROP casesheetentries TABLE")
    print("=" * 60)

    try:
        # Verify it's empty first
        count = await conn.fetchval('SELECT COUNT(*) FROM casesheetentries')
        print(f"\nVerifying table is empty: {count} rows")

        if count > 0:
            print("\n[WARNING] Table has data! Aborting.")
            print("Please migrate data to caseEntries before dropping.")
            return

        # Drop the table
        await conn.execute('DROP TABLE casesheetentries CASCADE')
        print("\n[OK] Table dropped successfully")

        # Verify it's gone
        tables = await conn.fetch("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public' AND tablename LIKE '%case%'
            ORDER BY tablename
        """)

        print("\nRemaining case-related tables:")
        for t in tables:
            print(f"  - {t['tablename']}")

        print("\n" + "=" * 60)
        print("[SUCCESS] Migration completed")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(drop_table())
