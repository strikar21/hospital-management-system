import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='hospitaldb',
        user='hospital_user',
        password='hospital123'
    )

    tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
        ORDER BY table_name
    """)

    print('\nDatabase Tables:')
    print('=' * 50)
    for t in tables:
        print(f'- {t["table_name"]}')
    
    # Check device-related tables
    print('\n\nDevice-Related Tables:')
    print('=' * 50)
    device_tables = [t['table_name'] for t in tables if 'device' in t['table_name'].lower() or 'watch' in t['table_name'].lower() or 'door' in t['table_name'].lower()]
    for dt in device_tables:
        print(f'\n[{dt}]')
        cols = await conn.fetch(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{dt}' 
            ORDER BY ordinal_position
        """)
        for c in cols:
            print(f"  {c['column_name']}: {c['data_type']}")

    await conn.close()

asyncio.run(check())
