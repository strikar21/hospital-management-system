"""
Test TimescaleDB Connection
Verify connection to TimescaleDB Docker container before applying migration
"""
import asyncio
import asyncpg
import os

async def test_connection():
    print(">> Testing TimescaleDB connection...")
    print(f"   Host: {os.getenv('DATABASE_HOST', 'localhost')}")
    print(f"   Port: 5433 (TimescaleDB container)")
    print(f"   Database: hospitaltimescale")
    print(f"   User: {os.getenv('DATABASE_USER', 'hospital_user')}")

    try:
        # Connect to TimescaleDB container
        conn = await asyncpg.connect(
            host=os.getenv('DATABASE_HOST', 'localhost'),
            port=5433,  # TimescaleDB container port
            database='hospitaltimescale',  # TimescaleDB database name
            user=os.getenv('DATABASE_USER', 'hospital_user'),
            password=os.getenv('DATABASE_PASSWORD', 'hospital123')
        )

        print("\n>> Connection successful!")

        # Check TimescaleDB extension
        extension = await conn.fetchrow("""
            SELECT * FROM pg_available_extensions
            WHERE name='timescaledb'
        """)
        print(f"\n>> TimescaleDB extension: {extension['name']} v{extension['installed_version']}")

        # List existing tables
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        print(f"\n>> Existing tables ({len(tables)}):")
        for table in tables:
            print(f"   - {table['tablename']}")

        # List existing hypertables
        hypertables = await conn.fetch("""
            SELECT hypertable_name, num_dimensions, num_chunks, compression_enabled
            FROM timescaledb_information.hypertables
            ORDER BY hypertable_name
        """)
        print(f"\n>> Existing hypertables ({len(hypertables)}):")
        for ht in hypertables:
            print(f"   - {ht['hypertable_name']} (dimensions: {ht['num_dimensions']}, chunks: {ht['num_chunks']}, compression: {ht['compression_enabled']})")

        # Check if migration 010 tables already exist
        migration_tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename IN ('waveform_snapshots', 'vitals_realtime', 'neural_events')
            ORDER BY tablename
        """)

        if migration_tables:
            print(f"\n>> WARNING: Migration 010 tables already exist ({len(migration_tables)}):")
            for table in migration_tables:
                print(f"   - {table['tablename']}")
            print("   Migration may need to use IF NOT EXISTS or be skipped")
        else:
            print("\n>> Migration 010 tables do not exist - safe to apply migration")

        await conn.close()
        print("\n>> Connection test complete - ready for migration!")
        return True

    except Exception as e:
        print(f"\nERROR: Connection failed: {e}")
        return False

if __name__ == '__main__':
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
