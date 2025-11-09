import asyncpg
import asyncio

async def check_timescaledb():
    # Connect to TimescaleDB (same database, just different connection pool in app)
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    # Check all tables with 'vital' in name
    print("=== Tables with 'vital' in name ===")
    tables = await conn.fetch("""
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name LIKE '%vital%'
        ORDER BY table_name
    """)

    if tables:
        for table in tables:
            print(f"\n{table['table_name']} ({table['table_type']})")

            # Get columns for each table
            columns = await conn.fetch("""
                SELECT column_name, data_type, character_maximum_length, numeric_precision, numeric_scale
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, table['table_name'])

            print(f"  Columns ({len(columns)}):")
            for col in columns:
                type_info = col['data_type']
                if col['character_maximum_length']:
                    type_info += f"({col['character_maximum_length']})"
                elif col['numeric_precision'] and col['numeric_scale'] is not None:
                    type_info += f"({col['numeric_precision']},{col['numeric_scale']})"
                print(f"    {col['column_name']}: {type_info}")
    else:
        print("  No tables found with 'vital' in name")

    # Check if TimescaleDB extension is installed
    print("\n=== TimescaleDB Extension ===")
    extension = await conn.fetchval("""
        SELECT COUNT(*) FROM pg_extension WHERE extname = 'timescaledb'
    """)
    print(f"  TimescaleDB installed: {extension > 0}")

    # Check hypertables
    if extension > 0:
        print("\n=== Hypertables ===")
        hypertables = await conn.fetch("""
            SELECT hypertable_schema, hypertable_name
            FROM timescaledb_information.hypertables
            WHERE hypertable_schema = 'public'
        """)
        if hypertables:
            for ht in hypertables:
                print(f"  - {ht['hypertable_name']}")
        else:
            print("  No hypertables found")

    await conn.close()

asyncio.run(check_timescaledb())
