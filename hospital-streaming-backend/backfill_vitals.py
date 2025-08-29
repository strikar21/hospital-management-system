#!/usr/bin/env python3
"""
Backfill script to add recent vitals data for frontend patients
"""

import asyncio
import asyncpg
import random
from datetime import datetime, timedelta, timezone

# Vitals templates with realistic ranges
VITAL_RANGES = {
    "heart_rate": {"min": 60, "max": 120, "unit": "BPM"},
    "blood_pressure_systolic": {"min": 90, "max": 160, "unit": "mmHg"},
    "blood_pressure_diastolic": {"min": 60, "max": 90, "unit": "mmHg"},
    "temperature": {"min": 97.0, "max": 101.0, "unit": "°F"},
    "oxygen_saturation": {"min": 92, "max": 100, "unit": "%"},
    "respiratory_rate": {"min": 12, "max": 24, "unit": "/min"}
}

async def backfill_vitals():
    # Connect to main database to get patient IDs
    postgres_conn = await asyncpg.connect(
        "postgresql://hospital_user:hospital_pass@localhost:5433/hospital_streaming"
    )
    
    # Connect to TimescaleDB for vitals data
    timescale_conn = await asyncpg.connect(
        "postgresql://hospital_user:hospital_pass@localhost:5434/hospital_vitals"
    )
    
    try:
        # Get active patients from main database
        patients = await postgres_conn.fetch(
            "SELECT id, name FROM patients WHERE is_active = true"
        )
        
        print(f"Found {len(patients)} active patients")
        
        # Generate recent vitals data (last 6 hours)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=6)
        
        for patient in patients:
            patient_id = patient['id']
            print(f"Generating vitals for patient {patient_id} ({patient['name']})")
            
            # Generate readings every 30 seconds for 6 hours = 720 readings per vital
            current_time = start_time
            
            while current_time <= end_time:
                for vital_type, ranges in VITAL_RANGES.items():
                    # Generate realistic value with some variation
                    base_value = random.uniform(ranges["min"], ranges["max"])
                    
                    # Add some realistic variation based on time of day
                    hour = current_time.hour
                    if vital_type == "heart_rate":
                        if 6 <= hour <= 10:  # Morning activity
                            base_value += random.uniform(0, 15)
                        elif 22 <= hour or hour <= 4:  # Sleep
                            base_value -= random.uniform(0, 10)
                    
                    value = max(ranges["min"], min(ranges["max"], base_value))
                    
                    # Quality indicator
                    quality = random.choices(
                        ["excellent", "good", "poor"],
                        weights=[70, 25, 5]
                    )[0]
                    
                    # Insert vital reading
                    await timescale_conn.execute("""
                        INSERT INTO vital_readings 
                        (timestamp, device_id, patient_id, vital_type, value, unit, quality_indicator, metadata)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (timestamp, device_id, vital_type) DO NOTHING
                    """,
                        current_time,
                        f"WATCH_{patient_id[-3:]}",  # Device ID based on patient
                        patient_id,
                        vital_type,
                        round(value, 1),
                        ranges["unit"],
                        quality,
                        f'{{"source": "backfill", "generated_at": "{datetime.now().isoformat()}"}}'
                    )
                
                # Next reading in 30 seconds
                current_time += timedelta(seconds=30)
                
            print(f"  -> Generated ~{6*60*2} readings per vital type")
        
        print("Backfill complete!")
        
        # Verify data
        count = await timescale_conn.fetchval(
            "SELECT COUNT(*) FROM vital_readings WHERE timestamp >= $1",
            start_time
        )
        print(f"Total vitals records inserted: {count}")
        
    finally:
        await postgres_conn.close()
        await timescale_conn.close()

if __name__ == "__main__":
    asyncio.run(backfill_vitals())