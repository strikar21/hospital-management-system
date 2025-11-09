import asyncpg
import asyncio

async def list_all_tables():
    conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        database='hospitaltimescale',
        user='hospital_user',
        password='hospital123'
    )

    # Get all tables
    tables = await conn.fetch("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    print(f"Found {len(tables)} tables in hospitaltimescale database:\n")

    for table in tables:
        table_name = table['table_name']
        print(f"\n{'='*80}")
        print(f"TABLE: {table_name}")
        print('='*80)

        # Get columns for this table
        cols = await conn.fetch("""
            SELECT column_name, data_type, character_maximum_length, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
        """, table_name)

        for col in cols:
            type_info = col['data_type']
            if col['character_maximum_length']:
                type_info += f"({col['character_maximum_length']})"
            elif col['numeric_precision'] and col['numeric_scale'] is not None:
                type_info += f"({col['numeric_precision']},{col['numeric_scale']})"
            print(f"  {col['column_name']}: {type_info}")

    await conn.close()

asyncio.run(list_all_tables())
