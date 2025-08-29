import asyncio
import asyncpg

async def fix_schema():
    try:
        conn = await asyncpg.connect('postgresql://hospital_user:hospital_pass@localhost:5433/hospital_streaming')
        
        # Check and add is_active to device_assignments
        result = await conn.fetchrow("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'device_assignments' AND column_name = 'is_active'
        """)
        
        if result[0] == 0:
            await conn.execute('ALTER TABLE device_assignments ADD COLUMN is_active BOOLEAN DEFAULT true')
            await conn.execute('UPDATE device_assignments SET is_active = true WHERE is_active IS NULL')
            print('SUCCESS: Added is_active column to device_assignments')
        else:
            print('INFO: is_active column already exists in device_assignments')
            
        # Check tables
        tables = await conn.fetch("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name IN ('device_assignments', 'patients', 'staff') 
              AND column_name = 'is_active'
            ORDER BY table_name
        """)
        
        print('\nCurrent schema:')
        for row in tables:
            print(f'  {row["table_name"]}.{row["column_name"]}: {row["data_type"]}')
            
        await conn.close()
        print('\nSUCCESS: Database schema fixed!')
        
    except Exception as e:
        print(f'ERROR: Database fix failed: {e}')

if __name__ == '__main__':
    asyncio.run(fix_schema())