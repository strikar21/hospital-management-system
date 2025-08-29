#!/usr/bin/env python3
"""
Test timezone conversion
"""
import asyncpg
import asyncio
from datetime import datetime, timezone

async def test_timezone():
    print("Testing timezone conversion...")
    
    # Connect to TimescaleDB
    conn = await asyncpg.connect("postgresql://hospital_user:hospital_pass@localhost:5434/hospital_vitals")
    
    # Get a sample timestamp
    row = await conn.fetchrow("SELECT timestamp FROM vital_readings WHERE patient_id = 'P25082350' ORDER BY timestamp DESC LIMIT 1")
    
    if row:
        utc_timestamp = row['timestamp']
        print(f"UTC timestamp from DB: {utc_timestamp} (tzinfo: {utc_timestamp.tzinfo})")
        
        # Convert to local time
        if utc_timestamp.tzinfo is not None:
            local_time = utc_timestamp.astimezone()
        else:
            local_time = utc_timestamp.replace(tzinfo=timezone.utc).astimezone()
            
        print(f"Local timestamp: {local_time}")
        print(f"Formatted UTC: {utc_timestamp.strftime('%H:%M')}")  
        print(f"Formatted Local: {local_time.strftime('%H:%M')}")
        
        # Check current time
        now_utc = datetime.now(timezone.utc)
        now_local = datetime.now()
        print(f"Current UTC: {now_utc.strftime('%H:%M:%S')}")
        print(f"Current Local: {now_local.strftime('%H:%M:%S')}")
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(test_timezone())