"""
Run data cleanup migration for medications table
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def run_cleanup():
    """Run data cleanup migration"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("=" * 60)
        print("RUNNING DATA CLEANUP MIGRATION")
        print("=" * 60)

        migration_path = Path(__file__).parent / "migrations" / "001_data_cleanup.sql"

        if not migration_path.exists():
            print(f"[ERROR] Migration file not found: {migration_path}")
            return False

        with open(migration_path, 'r') as f:
            migration_sql = f.read()

        print("\nExecuting data cleanup migration...")
        await conn.execute(migration_sql)

        print("\n[SUCCESS] Data cleanup migration completed!")

        # Verify the changes
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        # Check if createdBy exists now
        columns = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'medications'
            AND column_name IN ('createdBy', 'modifiedBy')
        """)
        print("\nColumns check:")
        for col in columns:
            print(f"  - {col['column_name']} EXISTS")

        # Check prescribedBy data validity
        invalid_count = await conn.fetchval("""
            SELECT COUNT(*)
            FROM medications
            WHERE "prescribedBy" NOT IN (SELECT id FROM staff)
            AND "prescribedBy" IS NOT NULL
        """)
        print(f"\nInvalid prescribedBy values: {invalid_count}")

        if invalid_count == 0:
            print("[SUCCESS] All prescribedBy values are now valid!")
        else:
            print(f"[WARNING] Still have {invalid_count} invalid prescribedBy values")

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
