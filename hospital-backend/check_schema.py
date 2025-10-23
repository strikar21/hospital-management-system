import asyncio
import asyncpg

async def check_schema():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    for table in ['devices', 'deviceassignments', 'patients']:
        rows = await conn.fetch(f"""
            SELECT column_name, data_type, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_name='{table}'
            ORDER BY ordinal_position
        """)

        print(f'\n{table.upper()} table schema:')
        print(f"{'Column':<30} {'Type':<20} {'Precision':<15} {'Scale':<10}")
        print("=" * 80)
        for r in rows:
            print(f"{r['column_name']:<30} {r['data_type']:<20} {str(r['numeric_precision']):<15} {str(r['numeric_scale']):<10}")

    await conn.close()

asyncio.run(check_schema())
