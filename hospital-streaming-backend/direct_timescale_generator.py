#!/usr/bin/env python3
"""
Direct TimescaleDB Data Generator
Bypasses the backend API and writes directly to TimescaleDB
Generates realistic vitals data for 10 ESP32 watches
"""

import asyncio
import asyncpg
import json
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List

# TimescaleDB connection
TIMESCALE_URL = "postgresql://hospital_user:hospital_pass@localhost:5434/hospital_vitals"

# 10 Simulated Watches with realistic baselines
WATCHES = [
    {"device_id": "ESP32_WATCH_001", "patient_id": "P25082350", "hr": 72, "temp": 98.6, "spo2": 98, "bp_sys": 120, "bp_dia": 80, "rr": 16},
    {"device_id": "ESP32_WATCH_002", "patient_id": "P2508241819", "hr": 68, "temp": 98.4, "spo2": 97, "bp_sys": 118, "bp_dia": 78, "rr": 15},
    {"device_id": "ESP32_WATCH_003", "patient_id": "P2508250207", "hr": 75, "temp": 98.2, "spo2": 96, "bp_sys": 125, "bp_dia": 82, "rr": 14},
    {"device_id": "ESP32_WATCH_004", "patient_id": "P2508250225", "hr": 65, "temp": 98.8, "spo2": 99, "bp_sys": 130, "bp_dia": 85, "rr": 18},
    {"device_id": "ESP32_WATCH_005", "patient_id": "P25084208", "hr": 80, "temp": 99.2, "spo2": 95, "bp_sys": 115, "bp_dia": 75, "rr": 20},
    {"device_id": "ESP32_WATCH_006", "patient_id": "P25085479", "hr": 85, "temp": 99.5, "spo2": 94, "bp_sys": 110, "bp_dia": 70, "rr": 22},
    {"device_id": "ESP32_WATCH_007", "patient_id": "P25087330", "hr": 62, "temp": 98.1, "spo2": 97, "bp_sys": 140, "bp_dia": 90, "rr": 16},
    {"device_id": "ESP32_WATCH_008", "patient_id": "TEST001", "hr": 78, "temp": 98.4, "spo2": 96, "bp_sys": 135, "bp_dia": 88, "rr": 17},
    {"device_id": "ESP32_WATCH_009", "patient_id": "TEST002", "hr": 71, "temp": 98.7, "spo2": 98, "bp_sys": 122, "bp_dia": 79, "rr": 15},
    {"device_id": "ESP32_WATCH_010", "patient_id": "test-workflow-001", "hr": 74, "temp": 98.3, "spo2": 99, "bp_sys": 118, "bp_dia": 76, "rr": 14}
]

class DirectTimescaleGenerator:
    def __init__(self):
        self.connection = None
        
    async def connect(self):
        """Connect to TimescaleDB"""
        try:
            self.connection = await asyncpg.connect(TIMESCALE_URL)
            print("[CONNECT] Connected to TimescaleDB successfully")
            
            # Test the connection
            result = await self.connection.fetchval("SELECT COUNT(*) FROM vital_readings")
            print(f"[INFO] Current vital_readings count: {result}")
            
        except Exception as e:
            print(f"[ERROR] Failed to connect to TimescaleDB: {e}")
            raise
    
    def generate_realistic_vitals(self, watch_config: Dict) -> Dict:
        """Generate realistic vitals with variations"""
        baseline = watch_config
        
        # Add realistic variations to baseline
        vitals = {
            "heart_rate": max(45, min(150, baseline["hr"] + random.randint(-10, 15))),
            "temperature": round(baseline["temp"] + random.uniform(-0.5, 1.0), 1),
            "oxygen_saturation": max(85, min(100, baseline["spo2"] + random.randint(-3, 2))),
            "blood_pressure_systolic": max(80, min(200, baseline["bp_sys"] + random.randint(-15, 20))),
            "blood_pressure_diastolic": max(50, min(120, baseline["bp_dia"] + random.randint(-10, 15))),
            "respiratory_rate": max(8, min(35, baseline["rr"] + random.randint(-3, 5)))
        }
        
        return vitals
    
    async def insert_vitals_for_watch(self, watch_config: Dict, timestamp: datetime):
        """Insert a complete set of vitals for one watch"""
        vitals = self.generate_realistic_vitals(watch_config)
        device_id = watch_config["device_id"]
        patient_id = watch_config["patient_id"]
        
        # Prepare data for insertion (one row per vital type)
        inserts = []
        vital_mappings = [
            ("heart_rate", vitals["heart_rate"], "BPM"),
            ("temperature", vitals["temperature"], "F"),
            ("oxygen_saturation", vitals["oxygen_saturation"], "%"),
            ("blood_pressure_systolic", vitals["blood_pressure_systolic"], "mmHg"),
            ("blood_pressure_diastolic", vitals["blood_pressure_diastolic"], "mmHg"),
            ("respiratory_rate", vitals["respiratory_rate"], "/min")
        ]
        
        for vital_type, value, unit in vital_mappings:
            metadata = {
                "source": "esp32_direct_generator",
                "battery_level": random.randint(70, 95),
                "signal_quality": random.uniform(0.85, 0.98),
                "generator_version": "1.0"
            }
            
            inserts.append((
                timestamp,
                device_id,
                patient_id, 
                vital_type,
                float(value),
                unit,
                "excellent",
                json.dumps(metadata)
            ))
        
        # Batch insert all vitals for this watch
        await self.connection.executemany("""
            INSERT INTO vital_readings 
            (timestamp, device_id, patient_id, vital_type, value, unit, quality_indicator, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, inserts)
        
        # Check for alerts  
        alerts = []
        if vitals["heart_rate"] > 100: alerts.append("HIGH_HR")
        if vitals["temperature"] > 99.5: alerts.append("FEVER") 
        if vitals["oxygen_saturation"] < 95: alerts.append("LOW_O2")
        if vitals["blood_pressure_systolic"] > 140: alerts.append("HIGH_BP")
        
        status = f" [ALERTS: {','.join(alerts)}]" if alerts else " [OK]"
        
        print(f"[INSERT] {device_id}: HR={vitals['heart_rate']} T={vitals['temperature']}F O2={vitals['oxygen_saturation']}% BP={vitals['blood_pressure_systolic']}/{vitals['blood_pressure_diastolic']}{status}")
        
        return len(inserts)

    async def generate_continuous_data(self, interval_seconds=5):
        """Generate continuous realistic vital signs data"""
        print(f"\n[START] Direct TimescaleDB Vitals Generator")
        print(f"[INFO] Generating data for {len(WATCHES)} ESP32 watches")
        print(f"[INFO] Interval: {interval_seconds} seconds per batch")
        print(f"[INFO] Database: {TIMESCALE_URL}")
        print("-" * 60)
        
        iteration = 0
        total_inserts = 0
        
        try:
            while True:
                iteration += 1
                batch_start = time.time()
                
                # Use current time for realistic timestamping
                current_time = datetime.now(timezone.utc)
                
                print(f"\n[BATCH {iteration}] Generating vitals at {current_time.strftime('%H:%M:%S')}")
                
                # Insert data for all watches
                batch_inserts = 0
                for watch in WATCHES:
                    inserts_count = await self.insert_vitals_for_watch(watch, current_time)
                    batch_inserts += inserts_count
                
                total_inserts += batch_inserts
                elapsed = time.time() - batch_start
                
                print(f"[STATS] Batch complete: {batch_inserts} records inserted in {elapsed:.2f}s")
                print(f"[TOTAL] {total_inserts} total records inserted across {iteration} iterations")
                
                # Wait for next iteration
                await asyncio.sleep(max(0, interval_seconds - elapsed))
                
        except KeyboardInterrupt:
            print(f"\n[STOP] Generator stopped by user")
            print(f"[FINAL] Total records inserted: {total_inserts}")
        except Exception as e:
            print(f"\n[ERROR] Generator error: {e}")
        
    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            print("[DISCONNECT] Database connection closed")

async def main():
    """Main entry point"""
    print("Direct TimescaleDB Vitals Generator v1.0")
    print("=" * 50)
    
    generator = DirectTimescaleGenerator()
    
    try:
        await generator.connect()
        print("\n[READY] Starting data generation in 3 seconds...")
        await asyncio.sleep(3)
        
        await generator.generate_continuous_data(interval_seconds=5)
        
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        await generator.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[GOODBYE] Generator stopped")