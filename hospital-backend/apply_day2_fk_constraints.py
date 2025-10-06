"""
Apply Day 2 FK constraints to investigations, therapy, casesheetentries
"""
import asyncio
import asyncpg
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.core.config import settings


async def apply_constraints():
    """Apply Day 2 FK constraints"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("=" * 60)
        print("APPLYING DAY 2 FK CONSTRAINTS")
        print("=" * 60)

        migration_path = Path(__file__).parent / "migrations" / "002_add_foreign_keys.sql"

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

        # Check investigations
        print("\nINVESTIGATIONS table FK constraints:")
        inv_constraints = await conn.fetch("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'investigations'
            AND constraint_type = 'FOREIGN KEY'
            ORDER BY constraint_name
        """)
        for c in inv_constraints:
            print(f"  - {c['constraint_name']}")

        # Check therapy
        print("\nTHERAPY table FK constraints:")
        therapy_constraints = await conn.fetch("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'therapy'
            AND constraint_type = 'FOREIGN KEY'
            ORDER BY constraint_name
        """)
        for c in therapy_constraints:
            print(f"  - {c['constraint_name']}")

        # Check casesheetentries
        print("\nCASESHEETENTRIES table FK constraints:")
        case_constraints = await conn.fetch("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'casesheetentries'
            AND constraint_type = 'FOREIGN KEY'
            ORDER BY constraint_name
        """)
        for c in case_constraints:
            print(f"  - {c['constraint_name']}")

        # Verify expected counts
        expected_inv = ['fk_investigations_patient', 'fk_investigations_performer', 'fk_investigations_prescriber']
        expected_therapy = ['fk_therapy_patient', 'fk_therapy_prescriber']
        expected_case = ['fk_casesheetentries_creator', 'fk_casesheetentries_patient', 'fk_casesheetentries_performer']

        inv_names = [c['constraint_name'] for c in inv_constraints]
        therapy_names = [c['constraint_name'] for c in therapy_constraints]
        case_names = [c['constraint_name'] for c in case_constraints]

        inv_ok = all(name in inv_names for name in expected_inv)
        therapy_ok = all(name in therapy_names for name in expected_therapy)
        case_ok = all(name in case_names for name in expected_case)

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        print(f"\ninvestigations: {'[PASS]' if inv_ok else '[FAIL]'} {len(inv_names)}/3 FK constraints")
        print(f"therapy:        {'[PASS]' if therapy_ok else '[FAIL]'} {len(therapy_names)}/2 FK constraints")
        print(f"casesheetentries: {'[PASS]' if case_ok else '[FAIL]'} {len(case_names)}/3 FK constraints")

        all_ok = inv_ok and therapy_ok and case_ok

        if all_ok:
            print(f"\n[SUCCESS] All Day 2 FK constraints applied successfully!")
        else:
            print(f"\n[WARNING] Some constraints missing")

        print("\n" + "=" * 60)
        return all_ok

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
