"""
Apply remaining FK constraints to medications table
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def apply_constraints():
    """Apply remaining FK constraints"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("=" * 60)
        print("APPLYING REMAINING FK CONSTRAINTS")
        print("=" * 60)

        migration_path = Path(__file__).parent / "migrations" / "001_add_remaining_fk_constraints.sql"

        if not migration_path.exists():
            print(f"[ERROR] Migration file not found: {migration_path}")
            return False

        with open(migration_path, 'r') as f:
            migration_sql = f.read()

        print("\nExecuting FK constraint migration...")
        await conn.execute(migration_sql)

        print("\n[SUCCESS] FK constraints applied!")

        # Verify all constraints exist
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)

        constraints = await conn.fetch("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'medications'
            AND constraint_type = 'FOREIGN KEY'
            ORDER BY constraint_name
        """)

        print("\nForeign Key Constraints on medications table:")
        for constraint in constraints:
            print(f"  - {constraint['constraint_name']}")

        expected_constraints = ['fk_medications_creator', 'fk_medications_patient', 'fk_medications_prescriber']
        constraint_names = [c['constraint_name'] for c in constraints]

        all_exist = all(name in constraint_names for name in expected_constraints)

        if all_exist:
            print(f"\n[SUCCESS] All {len(expected_constraints)} FK constraints are in place!")
        else:
            print(f"\n[WARNING] Missing constraints:")
            for name in expected_constraints:
                if name not in constraint_names:
                    print(f"  - {name}")

        print("\n" + "=" * 60)
        return all_exist

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
