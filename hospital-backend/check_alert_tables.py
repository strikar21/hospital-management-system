import asyncpg
import asyncio

async def check_alerts():
    # Check main database (hospitaldb)
    conn1 = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    print("="*80)
    print("ALERT TABLES IN hospitaldb (port 5432)")
    print("="*80)

    tables = await conn1.fetch("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_name LIKE '%alert%'
        ORDER BY table_name
    """)

    if tables:
        for table in tables:
            table_name = table['table_name']
            print(f"\nTABLE: {table_name}")

            cols = await conn1.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, table_name)

            for col in cols:
                print(f"  {col['column_name']}: {col['data_type']}")
    else:
        print("No alert tables found in hospitaldb")

    await conn1.close()

    # Check TimescaleDB (hospitaltimescale) - already checked neural_events
    print("\n" + "="*80)
    print("ALERT/EVENT TABLES IN hospitaltimescale (port 5433)")
    print("="*80)
    print("neural_events table already listed above (18 columns)")
    print("  - Stores ECG arrhythmia events and EEG seizure events")

    # Check for fall risk or IMU-related columns
    print("\n" + "="*80)
    print("FALL/IMU ALERTS IN vitals_realtime")
    print("="*80)
    print("  - imuFallRisk: numeric(4,2) [0-10 scale]")
    print("  - tremor: numeric(4,2) [0-10 scale]")
    print("  - watchWorn: boolean")
    print("  - lastMovementTime: integer (milliseconds)")

asyncio.run(check_alerts())
