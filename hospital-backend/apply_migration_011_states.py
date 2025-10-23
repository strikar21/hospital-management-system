"""
Apply Migration 011: Patient States for Duration Tracking
Component 4: Duration/State Tracking
"""

import asyncio
import asyncpg
from app.core.config import settings

async def apply_migration():
    """Apply migration 011: Patient states table"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        print("[INFO] Applying migration 011: Patient states table")

        # Read migration file
        with open('migrations/011_add_patient_states.sql', 'r', encoding='utf-8') as f:
            migration_sql = f.read()

        # Apply migration
        await conn.execute(migration_sql)
        print("[OK] Migration 011 applied: patient states table created")

        # Verify table created
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'patientstates'
        """)

        if tables:
            print(f"[OK] Table created: patientstates")

            # Verify columns
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'patientstates'
                ORDER BY ordinal_position
            """)

            print(f"[OK] Table has {len(columns)} columns")
            print("[INFO] Columns:")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']}")

            # Verify indexes
            indexes = await conn.fetch("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'patientstates'
            """)

            print(f"[OK] Created {len(indexes)} indexes:")
            for idx in indexes:
                print(f"  - {idx['indexname']}")

        else:
            print("[ERROR] Table 'patientstates' not found after migration")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())
