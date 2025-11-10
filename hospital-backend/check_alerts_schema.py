import asyncio
import asyncpg

async def check_schema():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='hospital_user',
        password='hospital123',
        database='hospitaldb'
    )
    
    try:
        # Check id column definition
        result = await conn.fetchrow("""
            SELECT column_name, data_type, column_default, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'patient_alerts' AND column_name = 'id'
        """)
        
        print("\n=== patient_alerts 'id' column ===")
        print(f"Data Type: {result['data_type']}")
        print(f"Default: {result['column_default']}")
        print(f"Nullable: {result['is_nullable']}")
        
        if not result['column_default']:
            print("\n❌ PROBLEM: 'id' column has NO DEFAULT value!")
            print("   Solution: ALTER TABLE to add gen_random_uuid()")
        
    finally:
        await conn.close()

asyncio.run(check_schema())
