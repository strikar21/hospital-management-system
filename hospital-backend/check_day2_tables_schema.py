"""
Check schema and data for Day 2 tables: investigations, therapy, casesheetentries
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def check_table_schema(conn, table_name):
    """Check schema and data for a specific table"""
    print("\n" + "=" * 60)
    print(f"{table_name.upper()} TABLE ANALYSIS")
    print("=" * 60)

    # Check if table exists
    table_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = $1
        )
    """, table_name)

    if not table_exists:
        print(f"\n[WARNING] Table '{table_name}' does not exist!")
        return

    # Get column names and types
    print(f"\n1. Column Schema:")
    columns = await conn.fetch("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
    """, table_name)

    for col in columns:
        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
        print(f"   - {col['column_name']}: {col['data_type']} ({nullable})")

    # Check for common FK candidate columns
    print(f"\n2. Potential FK Columns:")
    fk_candidates = ['patientId', 'createdBy', 'modifiedBy', 'prescribedBy',
                     'orderedBy', 'performedBy', 'staffId', 'doctorId']

    column_names = [c['column_name'] for c in columns]
    found_candidates = [name for name in fk_candidates if name in column_names]

    if found_candidates:
        for candidate in found_candidates:
            print(f"   - {candidate}")
    else:
        print("   - No standard FK candidate columns found")

    # Check existing FK constraints
    print(f"\n3. Existing FK Constraints:")
    constraints = await conn.fetch("""
        SELECT
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        LEFT JOIN information_schema.referential_constraints AS rc
            ON tc.constraint_name = rc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = $1
    """, table_name)

    if constraints:
        for c in constraints:
            delete_rule = c['delete_rule'] or 'NO ACTION'
            print(f"   - {c['constraint_name']}: {c['column_name']} -> {c['foreign_table_name']}({c['foreign_column_name']}) ON DELETE {delete_rule}")
    else:
        print("   - No FK constraints found")

    # Get sample data for FK candidate columns
    if found_candidates:
        print(f"\n4. Sample Data for FK Columns:")
        for candidate in found_candidates:
            sample_data = await conn.fetch(f"""
                SELECT DISTINCT "{candidate}"
                FROM {table_name}
                WHERE "{candidate}" IS NOT NULL
                LIMIT 5
            """)

            print(f"\n   {candidate}:")
            if sample_data:
                for row in sample_data:
                    print(f"      - '{row[candidate]}'")
            else:
                print(f"      - (no data)")

    # Check row count
    row_count = await conn.fetchval(f'SELECT COUNT(*) FROM {table_name}')
    print(f"\n5. Total Records: {row_count}")


async def check_all_tables():
    """Check all Day 2 tables"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("=" * 60)
        print("DAY 2 SCHEMA ANALYSIS")
        print("=" * 60)
        print("\nAnalyzing: investigations, therapy, casesheetentries")

        # Check each table
        for table_name in ['investigations', 'therapy', 'casesheetentries']:
            await check_table_schema(conn, table_name)

        print("\n" + "=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_all_tables())
