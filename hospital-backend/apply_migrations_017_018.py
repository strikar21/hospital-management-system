"""
Apply Migrations 017 and 018: Fix device_certificates and device_mac_mapping to camelCase
"""
import asyncpg
import asyncio
import sys

# Set UTF-8 encoding for Windows console
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def apply_migrations():
    """Apply migrations 017 and 018 to rename columns to camelCase"""

    DATABASE_URL = "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb"

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("[OK] Connected to database")

        # ========== MIGRATION 017 ==========
        print("\n" + "="*60)
        print("MIGRATION 017: device_certificates")
        print("="*60)

        with open('migrations/017_fix_device_certificates_camelcase.sql', 'r', encoding='utf-8') as f:
            migration_017_sql = f.read()

        print("[MIGRATION] Executing Migration 017...")
        await conn.execute(migration_017_sql)
        print("[OK] Migration 017 applied successfully!")

        # Verify Migration 017
        print("[VERIFY] Verifying device_certificates columns...")
        rows_017 = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'device_certificates'
            ORDER BY ordinal_position
        """)

        print("[SCHEMA] device_certificates table schema:")
        for row in rows_017:
            print(f"  - {row['column_name']}: {row['data_type']}")

        camelcase_cols_017 = ['deviceId', 'certificatePem', 'issuedAt', 'expiresAt',
                               'revokedAt', 'revokedBy', 'revocationReason', 'macAddress', 'serialNumber']
        found_017 = [row['column_name'] for row in rows_017]
        all_found_017 = all(col in found_017 for col in camelcase_cols_017)

        if all_found_017:
            print("[OK] All camelCase columns found in device_certificates!")
        else:
            missing = [col for col in camelcase_cols_017 if col not in found_017]
            print(f"[WARNING] Missing columns: {', '.join(missing)}")

        # ========== MIGRATION 018 ==========
        print("\n" + "="*60)
        print("MIGRATION 018: device_mac_mapping")
        print("="*60)

        with open('migrations/018_fix_device_mac_mapping_camelcase.sql', 'r', encoding='utf-8') as f:
            migration_018_sql = f.read()

        print("[MIGRATION] Executing Migration 018...")
        await conn.execute(migration_018_sql)
        print("[OK] Migration 018 applied successfully!")

        # Verify Migration 018
        print("[VERIFY] Verifying device_mac_mapping columns...")
        rows_018 = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'device_mac_mapping'
            ORDER BY ordinal_position
        """)

        print("[SCHEMA] device_mac_mapping table schema:")
        for row in rows_018:
            print(f"  - {row['column_name']}: {row['data_type']}")

        camelcase_cols_018 = ['macAddress', 'deviceId', 'createdAt', 'updatedAt']
        found_018 = [row['column_name'] for row in rows_018]
        all_found_018 = all(col in found_018 for col in camelcase_cols_018)

        if all_found_018:
            print("[OK] All camelCase columns found in device_mac_mapping!")
        else:
            missing = [col for col in camelcase_cols_018 if col not in found_018]
            print(f"[WARNING] Missing columns: {', '.join(missing)}")

        await conn.close()

        # Final Summary
        print("\n" + "="*60)
        print("MIGRATIONS COMPLETE")
        print("="*60)
        print("[OK] Migration 017 (device_certificates): SUCCESS")
        print("[OK] Migration 018 (device_mac_mapping): SUCCESS")
        print("\n[NEXT STEP] Update provisioning.py with camelCase SQL queries")
        print("="*60)

        return True

    except Exception as e:
        print(f"\n[ERROR] Error applying migrations: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(apply_migrations())
    sys.exit(0 if success else 1)
