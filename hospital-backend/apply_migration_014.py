"""
Apply Migration 014: Device MAC Mapping Table
Creates table to map MAC addresses to sequential device IDs
"""

import asyncio
import asyncpg

async def apply_migration():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='hospitaldb',
        user='hospital_user',
        password='hospital123'
    )

    try:
        print("Applying migration 014: device_mac_mapping table...")

        # Read migration file
        with open('migrations/014_device_mac_mapping.sql', 'r') as f:
            migration_sql = f.read()

        # Execute migration
        await conn.execute(migration_sql)

        print("[OK] Migration 014 applied successfully")

        # Verify
        count = await conn.fetchval('SELECT COUNT(*) FROM device_mac_mapping')
        print(f"Total MAC mappings: {count}")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        raise

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())
