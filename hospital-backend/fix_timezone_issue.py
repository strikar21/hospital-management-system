import asyncio
import asyncpg

async def check_alert_table():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='hospital_user',
        password='hospital123',
        database='hospitaldb'
    )
    
    try:
        # Check patient_alerts table schema
        result = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'patient_alerts'
            AND column_name LIKE '%At'
            ORDER BY ordinal_position
        """)
        
        print("\n=== patient_alerts TIMESTAMP COLUMNS ===")
        for row in result:
            print(f"{row['column_name']}: {row['data_type']}")
        
        print("\n=== RECOMMENDED FIX ===")
        print("Change timestamp columns from 'timestamp' to 'timestamp with time zone'")
        
    finally:
        await conn.close()

asyncio.run(check_alert_table())
