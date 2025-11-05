"""
Apply Migration 015: Patient Alerts Table
Creates table for persistent alert storage (fixes mqtt_service.py:306 TODO)
"""

import asyncio
import asyncpg
from app.core.config import settings

async def apply_migration():
    """Apply migration 015: Patient alerts table"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("="*80)
        print("MIGRATION 015: Patient Alerts Table")
        print("="*80)
        print()
        print("[INFO] Applying migration 015: Patient alerts table for persistent storage")

        # Read migration SQL
        with open('migrations/015_create_patient_alerts_table.sql', 'r', encoding='utf-8') as f:
            migration_sql = f.read()

        # Execute migration
        await conn.execute(migration_sql)
        print("[OK] Migration 015 executed successfully")
        print()

        # Verify table created
        print("[INFO] Verifying table created...")
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'patient_alerts'
            )
        """)

        if table_exists:
            print("[OK] Table created: patient_alerts")
            print()

            # Verify columns
            print("[INFO] Verifying columns...")
            columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'patient_alerts'
                ORDER BY ordinal_position
            """)

            print(f"[OK] Table has {len(columns)} columns:")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                print(f"     - {col['column_name']}: {col['data_type']} ({nullable})")

            print()

            # Verify indexes
            print("[INFO] Verifying indexes...")
            indexes = await conn.fetch("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'patient_alerts'
                ORDER BY indexname
            """)

            print(f"[OK] Created {len(indexes)} indexes:")
            for idx in indexes:
                print(f"     - {idx['indexname']}")

            print()

            # Verify foreign key constraints
            print("[INFO] Verifying foreign key constraints...")
            fk_constraints = await conn.fetch("""
                SELECT
                    con.conname AS constraint_name,
                    pg_get_constraintdef(con.oid) AS constraint_def
                FROM pg_constraint con
                INNER JOIN pg_class rel ON rel.oid = con.conrelid
                WHERE rel.relname = 'patient_alerts'
                  AND con.contype = 'f'
                ORDER BY con.conname
            """)

            if fk_constraints:
                print(f"[OK] Foreign key constraints ({len(fk_constraints)}):")
                for fk in fk_constraints:
                    print(f"     - {fk['constraint_name']}")
                    print(f"       {fk['constraint_def']}")
            else:
                print("[WARNING] No foreign key constraints found")

            print()

            # Verify trigger
            print("[INFO] Verifying trigger...")
            triggers = await conn.fetch("""
                SELECT trigger_name
                FROM information_schema.triggers
                WHERE event_object_table = 'patient_alerts'
            """)

            if triggers:
                print(f"[OK] Triggers created ({len(triggers)}):")
                for trig in triggers:
                    print(f"     - {trig['trigger_name']}")
            else:
                print("[WARNING] No triggers found")

        else:
            print("[ERROR] Table 'patient_alerts' not found after migration")
            raise Exception("Migration verification failed - table not created")

        print()
        print("="*80)
        print("[SUCCESS] Migration 015 completed successfully!")
        print("="*80)
        print()
        print("Summary:")
        print(f"  - patient_alerts table created with {len(columns)} columns")
        print(f"  - {len(indexes)} indexes created")
        print(f"  - {len(fk_constraints) if fk_constraints else 0} foreign key constraints")
        print(f"  - {len(triggers) if triggers else 0} triggers")
        print()
        print("Next steps:")
        print("  1. Implement alert storage in mqtt_service.py:306")
        print("  2. Add GET /patients/{id}/alerts endpoint if missing")
        print("  3. Test alert persistence and acknowledgment")
        print()

    except Exception as e:
        print()
        print("="*80)
        print(f"[ERROR] Migration 015 failed: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()
        raise

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())
