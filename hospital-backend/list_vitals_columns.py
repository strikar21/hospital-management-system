import asyncpg
import asyncio

async def list_columns():
    conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        database='hospitaltimescale',
        user='hospital_user',
        password='hospital123'
    )

    cols = await conn.fetch("""
        SELECT column_name, data_type, character_maximum_length, numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_name = 'vitals_realtime'
        ORDER BY ordinal_position
    """)

    print(f"vitals_realtime table has {len(cols)} columns:\n")
    for col in cols:
        type_info = col['data_type']
        if col['character_maximum_length']:
            type_info += f"({col['character_maximum_length']})"
        elif col['numeric_precision'] and col['numeric_scale'] is not None:
            type_info += f"({col['numeric_precision']},{col['numeric_scale']})"
        print(f"  {col['column_name']}: {type_info}")

    await conn.close()

asyncio.run(list_columns())
