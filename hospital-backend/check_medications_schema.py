"""
Quick script to check medications table schema and data
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def check_schema():
    """Check medications table schema and data"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("=" * 60)
        print("MEDICATIONS TABLE SCHEMA CHECK")
        print("=" * 60)

        # Get column names
        print("\n1. Column Names:")
        columns = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'medications'
            ORDER BY ordinal_position
        """)
        for col in columns:
            print(f"   - {col['column_name']}: {col['data_type']}")

        # Check for createdBy vs modifiedBy
        print("\n2. createdBy/modifiedBy Check:")
        has_created_by = any(c['column_name'] == 'createdBy' for c in columns)
        has_modified_by = any(c['column_name'] == 'modifiedBy' for c in columns)
        print(f"   - createdBy exists: {has_created_by}")
        print(f"   - modifiedBy exists: {has_modified_by}")

        # Check prescribedBy data
        print("\n3. prescribedBy Data Sample:")
        prescribed_by_data = await conn.fetch("""
            SELECT DISTINCT "prescribedBy"
            FROM medications
            LIMIT 10
        """)
        for row in prescribed_by_data:
            print(f"   - '{row['prescribedBy']}'")

        # Check if prescribedBy values exist in staff table
        print("\n4. prescribedBy Validation:")
        invalid_count = await conn.fetchval("""
            SELECT COUNT(DISTINCT "prescribedBy")
            FROM medications
            WHERE "prescribedBy" NOT IN (SELECT id FROM staff)
            AND "prescribedBy" IS NOT NULL
        """)
        total_distinct = await conn.fetchval("""
            SELECT COUNT(DISTINCT "prescribedBy")
            FROM medications
            WHERE "prescribedBy" IS NOT NULL
        """)
        print(f"   - Total distinct prescribedBy values: {total_distinct}")
        print(f"   - Invalid (not in staff table): {invalid_count}")
        print(f"   - Valid: {total_distinct - invalid_count}")

        # Check existing FK constraints
        print("\n5. Existing FK Constraints:")
        constraints = await conn.fetch("""
            SELECT constraint_name, column_name
            FROM information_schema.key_column_usage
            WHERE table_name = 'medications'
            AND constraint_name LIKE 'fk_%'
        """)
        if constraints:
            for c in constraints:
                print(f"   - {c['constraint_name']} on {c['column_name']}")
        else:
            print("   - No FK constraints found")

        print("\n" + "=" * 60)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(check_schema())
