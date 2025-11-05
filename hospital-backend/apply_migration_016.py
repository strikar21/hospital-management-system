"""
Apply Migration 016: Fix provisioning_codes table to camelCase
"""
import asyncpg
import asyncio
import sys

# Set UTF-8 encoding for Windows console
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def apply_migration():
    """Apply migration 016 to rename provisioning_codes columns to camelCase"""

    DATABASE_URL = "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb"

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("[OK] Connected to database")

        # Read migration file with UTF-8 encoding
        with open('migrations/016_fix_provisioning_codes_camelcase.sql', 'r', encoding='utf-8') as f:
            migration_sql = f.read()

        print("\n[MIGRATION] Executing Migration 016: provisioning_codes camelCase conversion...")

        # Execute the migration
        await conn.execute(migration_sql)

        print("\n[OK] Migration 016 applied successfully!")

        # Verify the changes
        print("\n[VERIFY] Verifying column names...")
        rows = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'provisioning_codes'
            ORDER BY ordinal_position
        """)

        print("\n[SCHEMA] provisioning_codes table schema:")
        for row in rows:
            print(f"  - {row['column_name']}: {row['data_type']} {'NULL' if row['is_nullable'] == 'YES' else 'NOT NULL'}")

        # Check for camelCase columns
        camelcase_columns = ['technicianId', 'createdAt', 'expiresAt', 'usedAt', 'deviceId']
        found_columns = [row['column_name'] for row in rows]

        all_found = all(col in found_columns for col in camelcase_columns)

        if all_found:
            print("\n[OK] All camelCase columns found successfully!")
        else:
            print("\n[WARNING] Some camelCase columns may be missing")
            missing = [col for col in camelcase_columns if col not in found_columns]
            if missing:
                print(f"   Missing: {', '.join(missing)}")

        await conn.close()
        print("\n[OK] Migration 016 complete!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Error applying migration: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    sys.exit(0 if success else 1)
