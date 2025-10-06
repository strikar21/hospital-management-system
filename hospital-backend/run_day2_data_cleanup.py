"""
Run Day 2 data cleanup migration
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def run_cleanup():
    """Run Day 2 data cleanup migration"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("=" * 60)
        print("DAY 2 DATA CLEANUP MIGRATION")
        print("=" * 60)

        migration_path = Path(__file__).parent / "migrations" / "002_data_cleanup.sql"

        if not migration_path.exists():
            print(f"[ERROR] Migration file not found: {migration_path}")
            return False

        with open(migration_path, 'r') as f:
            migration_sql = f.read()

        print("\nExecuting Day 2 data cleanup migration...")
        await conn.execute(migration_sql)

        print("\n[SUCCESS] Data cleanup migration completed!")

        # Verify the staff records were created
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        # Check if LAB001 and RAD001 now exist
        lab_exists = await conn.fetchrow("SELECT id, role FROM staff WHERE id = 'LAB001'")
        rad_exists = await conn.fetchrow("SELECT id, role FROM staff WHERE id = 'RAD001'")

        print("\nStaff records created:")
        if lab_exists:
            print(f"  [PASS] LAB001 exists ({lab_exists['role']})")
        else:
            print(f"  [FAIL] LAB001 not found")

        if rad_exists:
            print(f"  [PASS] RAD001 exists ({rad_exists['role']})")
        else:
            print(f"  [FAIL] RAD001 not found")

        # Re-run validation
        print("\nRe-validating FK data...")

        # Investigations prescribedBy
        invalid_count = await conn.fetchval("""
            SELECT COUNT(*)
            FROM investigations
            WHERE "prescribedBy" IS NOT NULL
            AND "prescribedBy" NOT IN (SELECT id FROM staff)
        """)

        print(f"\nInvalid investigations.prescribedBy values: {invalid_count}")

        if invalid_count == 0:
            print("[SUCCESS] All investigations.prescribedBy values are now valid!")
        else:
            print(f"[WARNING] Still have {invalid_count} invalid values")

        print("\n" + "=" * 60)
        return True

    except Exception as e:
        print(f"\n[ERROR] Data cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(run_cleanup())
    sys.exit(0 if success else 1)
