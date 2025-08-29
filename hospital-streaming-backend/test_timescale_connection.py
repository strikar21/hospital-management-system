#!/usr/bin/env python3
"""
Test TimescaleDB connection
"""
import asyncio
import asyncpg

async def test_connection():
    print("Testing TimescaleDB connection...")
    
    try:
        # Connect
        conn = await asyncpg.connect("postgresql://hospital_user:hospital_pass@localhost:5434/hospital_vitals")
        print("[OK] Connected to TimescaleDB")
        
        # Test query
        count = await conn.fetchval("SELECT COUNT(*) FROM vital_readings")
        print(f"[OK] Current records: {count}")
        
        # Test insert
        from datetime import datetime, timezone
        test_time = datetime.now(timezone.utc)
        
        await conn.execute("""
            INSERT INTO vital_readings 
            (timestamp, device_id, patient_id, vital_type, value, unit, quality_indicator, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, 
        test_time,
        "TEST_DEVICE_001", 
        "TEST_PATIENT_001",
        "heart_rate",
        75.0,
        "BPM",
        "excellent", 
        '{"test": true}'
        )
        
        print("[OK] Test insert successful")
        
        # Count again
        new_count = await conn.fetchval("SELECT COUNT(*) FROM vital_readings")
        print(f"[OK] New count: {new_count}")
        
        await conn.close()
        print("[OK] Connection closed")
        
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())