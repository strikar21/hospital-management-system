"""
Apply Day 3 CHECK constraints for data validation
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def apply_constraints():
    """Apply Day 3 CHECK constraints"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("=" * 60)
        print("APPLYING DAY 3 CHECK CONSTRAINTS")
        print("=" * 60)

        migration_path = Path(__file__).parent / "migrations" / "003_add_check_constraints.sql"

        if not migration_path.exists():
            print(f"[ERROR] Migration file not found: {migration_path}")
            return False

        with open(migration_path, 'r') as f:
            migration_sql = f.read()

        print("\nExecuting CHECK constraint migration...")
        await conn.execute(migration_sql)

        print("\n[SUCCESS] CHECK constraints applied!")

        # Verify all constraints exist
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        # Check all CHECK constraints
        constraints = await conn.fetch("""
            SELECT
                conname as constraint_name,
                conrelid::regclass as table_name
            FROM pg_constraint
            WHERE conname IN (
                'medications_status_check',
                'medications_route_check',
                'medications_date_range_check',
                'investigations_status_check',
                'investigations_priority_check',
                'investigations_urgency_check',
                'therapy_status_check',
                'therapy_date_range_check',
                'patients_status_check',
                'patients_gender_check',
                'patients_dob_check',
                'staff_role_check'
            )
            ORDER BY table_name, constraint_name
        """)

        # Group by table
        tables = {}
        for c in constraints:
            table = str(c['table_name'])
            if table not in tables:
                tables[table] = []
            tables[table].append(c['constraint_name'])

        for table, constraint_list in sorted(tables.items()):
            print(f"\n{table}:")
            for constraint in constraint_list:
                print(f"  - {constraint}")

        # Verify count
        expected_count = 12
        actual_count = len(constraints)

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        print(f"\nExpected: {expected_count} CHECK constraints")
        print(f"Found:    {actual_count} CHECK constraints")

        if actual_count == expected_count:
            print(f"\n[SUCCESS] All Day 3 CHECK constraints applied successfully!")
        else:
            print(f"\n[WARNING] Missing {expected_count - actual_count} constraints")

        print("\n" + "=" * 60)
        return actual_count == expected_count

    except Exception as e:
        print(f"\n[ERROR] Failed to apply constraints: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(apply_constraints())
    sys.exit(0 if success else 1)
