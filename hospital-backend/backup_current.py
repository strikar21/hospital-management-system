import asyncio
import asyncpg
from datetime import datetime

async def backup_database():
    """Create a metadata snapshot of current database state"""
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='hospital',
        password='hospital123',
        database='hospitaldb'
    )

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'backup_metadata_{timestamp}.txt'

    with open(filename, 'w') as f:
        f.write(f"=== Database Backup Metadata - {timestamp} ===\n\n")

        # Get all tables
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)

        f.write(f"Total tables: {len(tables)}\n\n")

        for table in tables:
            table_name = table['tablename']

            # Get row count
            try:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table_name}"')
                f.write(f"{table_name}: {count} rows\n")
            except Exception as e:
                f.write(f"{table_name}: Error - {e}\n")

    await conn.close()
    print(f"[SUCCESS] Backup metadata saved: {filename}")
    print(f"[INFO] Found {len(tables)} tables")
    return filename

if __name__ == "__main__":
    asyncio.run(backup_database())
