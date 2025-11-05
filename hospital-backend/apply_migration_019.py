"""
Apply Migration 019: Fix duration column type to DECIMAL(5,2)
"""
import asyncio
import asyncpg
from pathlib import Path

async def apply_migration():
    # TimescaleDB connection
    conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        database='hospitaltimescale',
        user='hospital_user',
        password='hospital123'
    )

    try:
        # Read migration file
        migration_file = Path(__file__).parent / 'migrations' / '019_fix_duration_float.sql'
        with open(migration_file, 'r') as f:
            sql = f.read()

        print(">> Applying Migration 019: Fix duration column type to DECIMAL(5,2)...")
        await conn.execute(sql)
        print(">> Migration 019 applied successfully!")

        # Verify changes
        print("\n>> Verifying column types...")
        columns = await conn.fetch("""
            SELECT
                table_name,
                column_name,
                data_type,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_name IN ('waveform_snapshots', 'vitals_realtime', 'neural_events')
              AND column_name = 'duration'
            ORDER BY table_name
        """)

        print("\n>> Duration column types:")
        for col in columns:
            print(f"   - {col['table_name']}.{col['column_name']}: {col['data_type']} ({col['numeric_precision']}, {col['numeric_scale']})")

    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(apply_migration())
