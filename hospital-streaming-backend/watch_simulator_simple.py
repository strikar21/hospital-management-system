#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hospital Watch Data Simulator (Windows Compatible)
Generates realistic vital signs data for 10 ESP32 watches and sends to the backend
"""

import asyncio
import aiohttp
import json
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List

# Backend configuration
BACKEND_URL = "http://localhost:8001"
INGESTION_ENDPOINT = f"{BACKEND_URL}/api/v1/ingest/vitals"

# 10 Simulated ESP32 Watches
WATCHES = [
    {
        "device_id": "ESP32_WATCH_001",
        "patient_id": "P25082350",
        "device_token": "watch_001_token",
        "baseline": {"hr": 72, "temp": 98.6, "spo2": 98, "bp_sys": 120, "bp_dia": 80, "rr": 16}
    },
    {
        "device_id": "ESP32_WATCH_002", 
        "patient_id": "P2508241819",
        "device_token": "watch_002_token",
        "baseline": {"hr": 68, "temp": 98.4, "spo2": 97, "bp_sys": 118, "bp_dia": 78, "rr": 15}
    },
    {
        "device_id": "ESP32_WATCH_003",
        "patient_id": "P2508250207",
        "device_token": "watch_003_token",
        "baseline": {"hr": 75, "temp": 98.2, "spo2": 96, "bp_sys": 125, "bp_dia": 82, "rr": 14}
    },
    {
        "device_id": "ESP32_WATCH_004",
        "patient_id": "P2508250225",
        "device_token": "watch_004_token", 
        "baseline": {"hr": 65, "temp": 98.8, "spo2": 99, "bp_sys": 130, "bp_dia": 85, "rr": 18}
    },
    {
        "device_id": "ESP32_WATCH_005",
        "patient_id": "P25084208",
        "device_token": "watch_005_token",
        "baseline": {"hr": 80, "temp": 99.2, "spo2": 95, "bp_sys": 115, "bp_dia": 75, "rr": 20}
    },
    {
        "device_id": "ESP32_WATCH_006",
        "patient_id": "P25085479",
        "device_token": "watch_006_token",
        "baseline": {"hr": 85, "temp": 99.5, "spo2": 94, "bp_sys": 110, "bp_dia": 70, "rr": 22}
    },
    {
        "device_id": "ESP32_WATCH_007", 
        "patient_id": "P25087330",
        "device_token": "watch_007_token",
        "baseline": {"hr": 62, "temp": 98.1, "spo2": 97, "bp_sys": 140, "bp_dia": 90, "rr": 16}
    },
    {
        "device_id": "ESP32_WATCH_008",
        "patient_id": "TEST001",
        "device_token": "watch_008_token",
        "baseline": {"hr": 78, "temp": 98.4, "spo2": 96, "bp_sys": 135, "bp_dia": 88, "rr": 17}
    },
    {
        "device_id": "ESP32_WATCH_009",
        "patient_id": "TEST002",
        "device_token": "watch_009_token", 
        "baseline": {"hr": 71, "temp": 98.7, "spo2": 98, "bp_sys": 122, "bp_dia": 79, "rr": 15}
    },
    {
        "device_id": "ESP32_WATCH_010",
        "patient_id": "test-workflow-001",
        "device_token": "watch_010_token",
        "baseline": {"hr": 74, "temp": 98.3, "spo2": 99, "bp_sys": 118, "bp_dia": 76, "rr": 14}
    }
]

class WatchSimulator:
    def __init__(self, watch_config: Dict):
        self.config = watch_config
        self.device_id = watch_config["device_id"]
        self.patient_id = watch_config["patient_id"] 
        self.device_token = watch_config["device_token"]
        self.baseline = watch_config["baseline"]
        
        # Simulation state
        self.battery_level = random.randint(65, 100)
        self.sequence_number = 0
        
        print(f"[INIT] {self.device_id} -> Patient {self.patient_id}")

    def get_realistic_vitals(self) -> Dict:
        """Generate realistic vital signs with variations"""
        
        # Base vitals with random variations
        heart_rate = max(45, min(150, self.baseline["hr"] + random.randint(-10, 15)))
        temperature = round(self.baseline["temp"] + random.uniform(-0.5, 1.0), 1)
        oxygen_saturation = max(85, min(100, self.baseline["spo2"] + random.randint(-3, 2)))
        bp_systolic = max(80, min(200, self.baseline["bp_sys"] + random.randint(-15, 20)))
        bp_diastolic = max(50, min(120, self.baseline["bp_dia"] + random.randint(-10, 15)))
        respiratory_rate = max(8, min(35, self.baseline["rr"] + random.randint(-3, 5)))
        
        # Simulate battery drain
        self.battery_level = max(10, self.battery_level - random.uniform(0.1, 0.3))
        
        return {
            "heart_rate": heart_rate,
            "temperature": temperature,
            "oxygen_saturation": oxygen_saturation,
            "blood_pressure_systolic": bp_systolic,
            "blood_pressure_diastolic": bp_diastolic,
            "respiratory_rate": respiratory_rate,
            "battery_level": int(self.battery_level)
        }

    def create_payload(self) -> Dict:
        """Create ESP32-compatible payload"""
        vitals = self.get_realistic_vitals()
        now = datetime.now(timezone.utc)
        self.sequence_number += 1
        
        return {
            "device_id": self.device_id,
            "patient_id": self.patient_id,
            "timestamp": now.isoformat(),
            "sequence_number": self.sequence_number,
            "vitals": {
                "heart_rate": vitals["heart_rate"],
                "temperature": vitals["temperature"], 
                "oxygen_saturation": vitals["oxygen_saturation"],
                "blood_pressure_systolic": vitals["blood_pressure_systolic"],
                "blood_pressure_diastolic": vitals["blood_pressure_diastolic"],
                "respiratory_rate": vitals["respiratory_rate"]
            },
            "device_metrics": {
                "battery_level": vitals["battery_level"],
                "signal_strength": random.randint(-60, -30),
                "memory_usage": random.randint(45, 85)
            }
        }

    async def send_vitals(self, session: aiohttp.ClientSession) -> bool:
        """Send vitals data to backend"""
        try:
            payload = self.create_payload()
            
            headers = {
                "Content-Type": "application/json",
                "X-Device-Token": self.device_token
            }
            
            async with session.post(INGESTION_ENDPOINT, json=payload, headers=headers, timeout=10) as response:
                if response.status == 201:
                    vitals = payload["vitals"]
                    
                    # Check for alerts
                    alerts = []
                    if vitals["heart_rate"] > 100: alerts.append("HIGH_HR")
                    if vitals["temperature"] > 99.5: alerts.append("FEVER") 
                    if vitals["oxygen_saturation"] < 95: alerts.append("LOW_O2")
                    if vitals["blood_pressure_systolic"] > 140: alerts.append("HIGH_BP")
                    
                    status = " [ALERTS: " + ",".join(alerts) + "]" if alerts else " [OK]"
                    
                    print(f"[DATA] {self.device_id}: HR={vitals['heart_rate']} T={vitals['temperature']}F O2={vitals['oxygen_saturation']}% BP={vitals['blood_pressure_systolic']}/{vitals['blood_pressure_diastolic']}{status}")
                    return True
                else:
                    print(f"[ERROR] {self.device_id}: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            print(f"[ERROR] {self.device_id}: {str(e)}")
            return False

async def run_simulation(interval_seconds=3):
    """Run continuous simulation"""
    simulators = [WatchSimulator(watch) for watch in WATCHES]
    
    print(f"\n[START] Hospital Watch Data Simulator")
    print(f"[INFO] Simulating {len(simulators)} ESP32 watches")
    print(f"[INFO] Sending data every {interval_seconds} seconds")
    print(f"[INFO] Target: {INGESTION_ENDPOINT}")
    print("-" * 60)
    
    # Check backend
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/health", timeout=5) as response:
                if response.status == 200:
                    print("[OK] Backend is reachable")
                else:
                    print(f"[WARN] Backend status: {response.status}")
    except Exception as e:
        print(f"[ERROR] Backend check failed: {e}")
        return
    
    # Main simulation loop
    async with aiohttp.ClientSession() as session:
        iteration = 0
        successful = 0
        failed = 0
        
        try:
            while True:
                iteration += 1
                start_time = time.time()
                
                print(f"\n[SEND] Iteration {iteration} - Broadcasting from all {len(simulators)} watches...")
                
                # Send from all watches concurrently
                tasks = [sim.send_vitals(session) for sim in simulators]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count results
                batch_success = sum(1 for r in results if r is True)
                batch_failed = len(results) - batch_success
                
                successful += batch_success
                failed += batch_failed
                
                elapsed = time.time() - start_time
                success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
                
                print(f"[STATS] Batch: {batch_success}/{len(simulators)} success | Overall: {successful} success, {failed} failed ({success_rate:.1f}% rate)")
                
                # Wait for next iteration
                await asyncio.sleep(max(0, interval_seconds - elapsed))
                
        except KeyboardInterrupt:
            print(f"\n[STOP] Simulation stopped by user")
        except Exception as e:
            print(f"\n[ERROR] Simulation error: {e}")
        finally:
            print(f"\n[FINAL] Statistics:")
            print(f"   Total transmissions: {successful + failed}")
            print(f"   Successful: {successful}")
            print(f"   Failed: {failed}")
            print(f"   Success rate: {success_rate:.1f}%")

if __name__ == "__main__":
    try:
        asyncio.run(run_simulation(interval_seconds=3))
    except KeyboardInterrupt:
        print("\n[GOODBYE]")
