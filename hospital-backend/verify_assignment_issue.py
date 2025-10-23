import asyncio
import asyncpg

async def verify():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='hospitaldb',
        user='hospital_user',
        password='hospital123'
    )

    print('\n[ISSUE VERIFICATION]')
    print('=' * 60)
    
    # Check deviceassignments table structure
    print('\ndeviceassignments table:')
    cols = await conn.fetch("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'deviceassignments'
        ORDER BY ordinal_position
    """)
    
    for c in cols:
        nullable = "NULL" if c['is_nullable'] == 'YES' else "NOT NULL"
        print(f"  {c['column_name']}: {c['data_type']} ({nullable})")
    
    # Check existing data
    print('\n\nExisting assignments:')
    assignments = await conn.fetch('SELECT * FROM deviceassignments')
    if assignments:
        for a in assignments:
            print(f"  ID: {a['id']} (type: {type(a['id']).__name__})")
            print(f"    Patient: {a['patientId']}, Device: {a['deviceId']}")
            print(f"    Status: {a['status']}")
    else:
        print('  (No assignments found)')
    
    # Check if id column has sequence
    print('\n\nSequence check:')
    seq = await conn.fetch("""
        SELECT column_default 
        FROM information_schema.columns 
        WHERE table_name = 'deviceassignments' AND column_name = 'id'
    """)
    print(f"  ID default: {seq[0]['column_default'] if seq else 'None'}")
    
    await conn.close()

asyncio.run(verify())
