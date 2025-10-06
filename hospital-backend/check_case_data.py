"""Check data in case-related tables"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb"

async def check():
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 60)
    print("DATA IN CASE TABLES")
    print("=" * 60)

    count1 = await conn.fetchval('SELECT COUNT(*) FROM casesheetentries')
    count2 = await conn.fetchval('SELECT COUNT(*) FROM "caseEntries"')

    print(f"\ncasesheetentries: {count1} rows")
    print(f"caseEntries: {count2} rows")

    if count1 > 0:
        print("\nSample from casesheetentries (first 3 rows):")
        samples = await conn.fetch('SELECT * FROM casesheetentries LIMIT 3')
        for s in samples:
            print(f"  {dict(s)}")

    if count2 > 0:
        print("\nSample from caseEntries (first 3 rows):")
        samples = await conn.fetch('SELECT * FROM "caseEntries" LIMIT 3')
        for s in samples:
            print(f"  {dict(s)}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(check())
