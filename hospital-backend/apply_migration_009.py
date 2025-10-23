"""
Apply Migration 009: Single Source of Truth Refactoring
Run this script to apply database changes
"""

import asyncpg
import asyncio
from pathlib import Path

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "database": "hospitaldb",
    "user": "hospital_user",
    "password": "hospital123"
}

async def apply_migration():
    """Apply migration 009"""
    print("="*80)
    print("APPLYING MIGRATION 009: Single Source of Truth Refactoring")
    print("="*80)

    # Read migration SQL
    migration_file = Path(__file__).parent / "migrations" / "009_ssot_refactoring.sql"

    if not migration_file.exists():
        print(f"[ERROR] Migration file not found: {migration_file}")
        return False

    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()

    print(f"\n[INFO] Migration file: {migration_file}")
    print(f"[INFO] SQL length: {len(migration_sql)} characters\n")

    try:
        # Connect to database
        print("[INFO] Connecting to database...")
        conn = await asyncpg.connect(**DB_CONFIG)
        print("[SUCCESS] Connected successfully\n")

        # Execute migration
        print("[INFO] Executing migration...")
        await conn.execute(migration_sql)
        print("[SUCCESS] Migration executed successfully\n")

        # Verification queries
        print("="*80)
        print("VERIFICATION")
        print("="*80)

        # Check view exists
        view_count = await conn.fetchval(
            "SELECT COUNT(*) FROM information_schema.views WHERE table_name = 'devices_enriched'"
        )
        print(f"[SUCCESS] devices_enriched view exists: {view_count == 1}")

        # Check devices in enriched view
        device_count = await conn.fetchval("SELECT COUNT(*) FROM devices_enriched")
        print(f"[SUCCESS] Total devices in enriched view: {device_count}")

        # Check assigned devices
        assigned_count = await conn.fetchval(
            'SELECT COUNT(*) FROM devices_enriched WHERE "assignmentStatus" = \'active\''
        )
        print(f"[SUCCESS] Currently assigned devices: {assigned_count}")

        # Check constraints
        constraints = await conn.fetch("""
            SELECT conname, contype
            FROM pg_constraint
            WHERE conrelid = 'devices'::regclass
            ORDER BY conname
        """)
        print(f"\n[SUCCESS] Constraints on devices table ({len(constraints)}):")
        for row in constraints:
            constraint_types = {
                'c': 'CHECK',
                'f': 'FOREIGN KEY',
                'p': 'PRIMARY KEY',
                'u': 'UNIQUE',
                't': 'TRIGGER'
            }
            print(f"   - {row['conname']}: {constraint_types.get(row['contype'], row['contype'])}")

        # Show sample enriched data
        print(f"\n[SUCCESS] Sample enriched device data:")
        sample = await conn.fetch("""
            SELECT id, name, status, "connectionStatus", "batteryStatus", "patientName"
            FROM devices_enriched
            LIMIT 3
        """)
        for row in sample:
            print(f"   - {row['id']}: {row['name']} ({row['status']}) - {row['connectionStatus']}")

        await conn.close()

        print("\n" + "="*80)
        print("[SUCCESS] MIGRATION 009 COMPLETED SUCCESSFULLY")
        print("="*80)

        return True

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    exit(0 if success else 1)
