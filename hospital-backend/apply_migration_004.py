"""
Apply Migration 004: Add remaining audit trail fields
Adds createdBy to 5 tables and editedBy to patientnotes
"""

import asyncio
import asyncpg
from app.core.config import settings

async def apply_migration():
    """Apply migration 004 to add audit trail fields"""
    print("=" * 60)
    print("Migration 004: Add Remaining Audit Trail Fields")
    print("=" * 60)

    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        # Read migration file
        with open('migrations/004_add_remaining_audit_fields.sql', 'r') as f:
            migration_sql = f.read()

        print("\nApplying migration...")
        print("-" * 60)

        # Execute migration
        await conn.execute(migration_sql)

        print("\nMigration applied successfully!")
        print("-" * 60)

        # Verify all columns exist
        print("\nVerifying migration...")
        print("-" * 60)

        tables_to_check = [
            ('medicationadministrations', 'createdBy'),
            ('investigations', 'createdBy'),
            ('therapy', 'createdBy'),
            ('therapysessions', 'createdBy'),
            ('patient_alerts', 'createdBy'),
            ('patientnotes', 'editedBy')
        ]

        all_present = True
        for table_name, column_name in tables_to_check:
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = $1 AND column_name = $2
                )
            """, table_name, column_name)

            status = "[OK]" if result else "[FAIL]"
            print(f"{status} {table_name}.{column_name}: {'EXISTS' if result else 'MISSING'}")

            if not result:
                all_present = False

        print("-" * 60)

        if all_present:
            print("\nSUCCESS: All 6 audit trail fields added!")
            print("\nAdded fields:")
            print("  - medicationadministrations.createdBy")
            print("  - investigations.createdBy")
            print("  - therapy.createdBy")
            print("  - therapysessions.createdBy")
            print("  - patient_alerts.createdBy")
            print("  - patientnotes.editedBy")
            return True
        else:
            print("\nFAILURE: Some fields are missing!")
            return False

    except Exception as e:
        print(f"\nMigration failed with error:")
        print(f"   {type(e).__name__}: {str(e)}")
        return False

    finally:
        await conn.close()
        print("\n" + "=" * 60)

if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    exit(0 if success else 1)
