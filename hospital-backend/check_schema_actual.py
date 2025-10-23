"""
Check actual database schema - find correct table names
"""

import asyncio
import asyncpg

DB_CONFIG = {
    "host": "localhost",
    "database": "hospitaldb",
    "user": "hospital_user",
    "password": "hospital123"
}

async def check_schema():
    conn = await asyncpg.connect(**DB_CONFIG)

    # Get all tables
    tables = await conn.fetch(
        """SELECT tablename FROM pg_tables
           WHERE schemaname = 'public'
           ORDER BY tablename"""
    )

    print("="*80)
    print("DATABASE TABLES")
    print("="*80)
    for table in tables:
        print(f"   - {table['tablename']}")

    # Get all views
    views = await conn.fetch(
        """SELECT viewname FROM pg_views
           WHERE schemaname = 'public'
           ORDER BY viewname"""
    )

    print("\n" + "="*80)
    print("DATABASE VIEWS")
    print("="*80)
    for view in views:
        print(f"   - {view['viewname']}")

    # Check devices table columns
    device_columns = await conn.fetch(
        """SELECT column_name, data_type
           FROM information_schema.columns
           WHERE table_name = 'devices'
           ORDER BY ordinal_position"""
    )

    print("\n" + "="*80)
    print("DEVICES TABLE COLUMNS")
    print("="*80)
    for col in device_columns:
        print(f"   - {col['column_name']}: {col['data_type']}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_schema())
