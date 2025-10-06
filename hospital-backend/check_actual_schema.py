"""
Check actual database schema - verify column names
"""
import asyncio
import asyncpg

DATABASE_URL = "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb"

async def check_schema():
    conn = await asyncpg.connect(DATABASE_URL)

    tables_to_check = [
        'medicationadministrations',
        'patient_alerts',
        'patientnotes',
        'atomic_transactions',
        'medical_operations',
        'casesheetentries',
        'therapies',
        'therapies_legacy'
    ]

    print("=" * 80)
    print("ACTUAL DATABASE SCHEMA CHECK")
    print("=" * 80)

    for table in tables_to_check:
        print(f"\n### TABLE: {table}")
        try:
            # Check if table exists
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = $1
                )
            """, table)

            if not exists:
                print(f"  [X] TABLE DOES NOT EXIST")
                continue

            # Get columns
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, table)

            print(f"  [OK] TABLE EXISTS - {len(columns)} columns:")
            for col in columns:
                print(f"     - {col['column_name']}: {col['data_type']}")

        except Exception as e:
            print(f"  [ERROR] {e}")

    await conn.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(check_schema())
