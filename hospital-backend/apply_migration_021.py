import asyncpg
import asyncio

async def apply_migration():
    print("Applying migration 021: Add sensor vitals columns...")

    # Connect to TimescaleDB (port 5433, database hospitaltimescale)
    conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        database='hospitaltimescale',
        user='hospital_user',
        password='hospital123'
    )

    try:
        # Read migration file
        with open('migrations/021_add_sensor_vitals.sql', 'r') as f:
            sql = f.read()

        # Execute migration
        await conn.execute(sql)

        print("Migration 021 applied successfully")

        # Verify columns
        cols = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'vitals_realtime'
              AND column_name IN ('tremor', 'bioimpedance', 'imuFallRisk', 'perfusionIndex',
                                   'stepCount', 'watchWorn', 'lastMovementTime')
            ORDER BY column_name
        """)

        print(f"\nVerified {len(cols)} new columns:")
        for col in cols:
            print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")

    finally:
        await conn.close()

asyncio.run(apply_migration())
