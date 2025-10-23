"""
Apply Migration 010: Create Neural Waveform Tables
"""
import asyncio
import asyncpg
import os
from pathlib import Path

async def apply_migration():
    # TimescaleDB connection (separate Docker container on port 5433)
    conn = await asyncpg.connect(
        host=os.getenv('DATABASE_HOST', 'localhost'),
        port=5433,  # TimescaleDB container port (not 5432)
        database='hospitaltimescale',  # TimescaleDB database name (not hospitaldb)
        user=os.getenv('DATABASE_USER', 'hospital_user'),
        password=os.getenv('DATABASE_PASSWORD', 'hospital123')
    )

    try:
        # Read migration file
        migration_file = Path(__file__).parent / 'migrations' / '010_create_neural_waveform_tables.sql'
        with open(migration_file, 'r') as f:
            sql = f.read()

        print(">> Applying Migration 010: Create Neural Waveform Tables...")
        await conn.execute(sql)
        print(">> Migration 010 applied successfully!")

        # Verify tables created
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename IN ('waveform_snapshots', 'vitals_realtime', 'neural_events')
            ORDER BY tablename
        """)

        print("\n>> Created tables:")
        for table in tables:
            print(f"   - {table['tablename']}")

        # Verify hypertables
        hypertables = await conn.fetch("""
            SELECT hypertable_name FROM timescaledb_information.hypertables
            WHERE hypertable_name IN ('waveform_snapshots', 'vitals_realtime', 'neural_events')
            ORDER BY hypertable_name
        """)

        print("\n>> TimescaleDB hypertables:")
        for ht in hypertables:
            print(f"   - {ht['hypertable_name']}")

        # Verify continuous aggregate
        caggs = await conn.fetch("""
            SELECT view_name FROM timescaledb_information.continuous_aggregates
            WHERE view_name = 'vitals_1min'
        """)

        if caggs:
            print("\n>> Continuous aggregates:")
            for cagg in caggs:
                print(f"   - {cagg['view_name']}")

    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(apply_migration())
