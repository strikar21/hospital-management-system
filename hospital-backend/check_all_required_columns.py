import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host='localhost', port=5432, user='hospital_user',
        password='hospital123', database='hospitaldb'
    )
    
    try:
        result = await conn.fetch("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'patient_alerts' 
            AND is_nullable = 'NO'
            ORDER BY ordinal_position
        """)
        
        print("\n=== patient_alerts NOT NULL columns ===")
        for row in result:
            default = row['column_default'] or 'NO DEFAULT'
            print(f"{row['column_name']:20s} {row['data_type']:20s} {default}")
        
    finally:
        await conn.close()

asyncio.run(check())
