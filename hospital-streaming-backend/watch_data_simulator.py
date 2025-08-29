#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hospital Watch Data Simulator
Generates realistic vital signs data for 10 ESP32 watches and sends to the backend
Simulates continuous monitoring with realistic variations and occasional alerts
"""

import asyncio
import aiohttp
import json
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List
import uuid

# Backend configuration
BACKEND_URL = "http://localhost:8001"
INGESTION_ENDPOINT = f"{BACKEND_URL}/api/v1/ingest/vitals"

# 10 Simulated ESP32 Watches with realistic patient assignments
WATCHES = [
    {
        "device_id": "ESP32_WATCH_001",
        "patient_id": "P25082350",  # Real patient from your system
        "device_token": "watch_001_secure_token",
        "location": "ICU_Room_101",
        "baseline": {"hr": 72, "temp": 98.6, "spo2": 98, "bp_sys": 120, "bp_dia": 80, "rr": 16}
    },
    {
        "device_id": "ESP32_WATCH_002", 
        "patient_id": "P2508241819",  # Emily Rodriguez
        "device_token": "watch_002_secure_token",
        "location": "Emergency_Ward_401",
        "baseline": {"hr": 68, "temp": 98.4, "spo2": 97, "bp_sys": 118, "bp_dia": 78, "rr": 15}
    },
    {
        "device_id": "ESP32_WATCH_003",
        "patient_id": "P2508250207",  # Michael Chen  
        "device_token": "watch_003_secure_token",
        "location": "General_Ward_201",
        "baseline": {"hr": 75, "temp": 98.2, "spo2": 96, "bp_sys": 125, "bp_dia": 82, "rr": 14}
    },
    {
        "device_id": "ESP32_WATCH_004",
        "patient_id": "P2508250225",  # John Williams
        "device_token": "watch_004_secure_token", 
        "location": "Cardiology_Wing_301",
        "baseline": {"hr": 65, "temp": 98.8, "spo2": 99, "bp_sys": 130, "bp_dia": 85, "rr": 18}
    },
    {
        "device_id": "ESP32_WATCH_005",
        "patient_id": "P25084208",  # Chuck - Dengue patient
        "device_token": "watch_005_secure_token",
        "location": "Internal_Med_205", 
        "baseline": {"hr": 80, "temp": 99.2, "spo2": 95, "bp_sys": 115, "bp_dia": 75, "rr": 20}  # Elevated temp for dengue
    },
    {
        "device_id": "ESP32_WATCH_006",
        "patient_id": "P25085479",  # Chuck - Fever patient
        "device_token": "watch_006_secure_token",
        "location": "Emergency_Med_A102",
        "baseline": {"hr": 85, "temp": 99.5, "spo2": 94, "bp_sys": 110, "bp_dia": 70, "rr": 22}  # Fever symptoms
    },
    {
        "device_id": "ESP32_WATCH_007", 
        "patient_id": "P25087330",  # Chuck - Cardiac patient
        "device_token": "watch_007_secure_token",
        "location": "Cardiology_CCU_401",
        "baseline": {"hr": 62, "temp": 98.1, "spo2": 97, "bp_sys": 140, "bp_dia": 90, "rr": 16}  # Hypertensive
    },
    {
        "device_id": "ESP32_WATCH_008",
        "patient_id": "TEST001",  # Test patient in ICU
        "device_token": "watch_008_secure_token",
        "location": "ICU_Critical_101",
        "baseline": {"hr": 78, "temp": 98.4, "spo2": 96, "bp_sys": 135, "bp_dia": 88, "rr": 17}
    },
    {
        "device_id": "ESP32_WATCH_009",
        "patient_id": "TEST002",  # Test patient 2
        "device_token": "watch_009_secure_token", 
        "location": "ICU_Recovery_102",
        "baseline": {"hr": 71, "temp": 98.7, "spo2": 98, "bp_sys": 122, "bp_dia": 79, "rr": 15}
    },
    {
        "device_id": "ESP32_WATCH_010",
        "patient_id": "test-workflow-001",  # Workflow test patient
        "device_token": "watch_010_secure_token",
        "location": "ICU_Monitoring_201", 
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
        self.location = watch_config["location"]
        
        # Simulation state
        self.battery_level = random.randint(65, 100)
        self.signal_strength = random.randint(-60, -30)  # dBm
        self.sequence_number = 0
        self.last_reading_time = datetime.now(timezone.utc)
        
        # Activity patterns (simulates patient movement, sleep, etc.)
        self.activity_state = "resting"  # resting, active, sleeping, critical
        self.activity_change_time = datetime.now(timezone.utc)
        
        print(f"[OK] Initialized {self.device_id} for patient {self.patient_id} at {self.location}")

    def get_realistic_vitals(self) -> Dict:
        """Generate realistic vital signs with natural variations and trends"""
        now = datetime.now(timezone.utc)
        
        # Change activity state occasionally
        if (now - self.activity_change_time).seconds > random.randint(300, 1800):  # 5-30 minutes
            self.activity_state = random.choices(
                ["resting", "active", "sleeping", "critical"], 
                weights=[60, 25, 10, 5]  # Most time resting, occasional activity/sleep/emergency
            )[0]
            self.activity_change_time = now
            print(f"[CHANGE] {self.device_id}: Activity changed to {self.activity_state}")
        
        # Base vitals from patient baseline
        base_hr = self.baseline["hr"]
        base_temp = self.baseline["temp"] 
        base_spo2 = self.baseline["spo2"]
        base_bp_sys = self.baseline["bp_sys"]
        base_bp_dia = self.baseline["bp_dia"]
        base_rr = self.baseline["rr"]
        
        # Apply activity-based modifications
        if self.activity_state == "active":
            hr_mod = random.randint(15, 35)  # Increased HR during activity
            temp_mod = random.uniform(0.2, 0.8)  # Slight temp increase
            rr_mod = random.randint(4, 8)  # Increased breathing
            bp_sys_mod = random.randint(10, 20)  # Increased BP
        elif self.activity_state == "sleeping": 
            hr_mod = random.randint(-10, -5)  # Lower HR during sleep
            temp_mod = random.uniform(-0.3, 0.1)  # Slightly lower temp
            rr_mod = random.randint(-3, -1)  # Slower breathing
            bp_sys_mod = random.randint(-8, -2)  # Lower BP
        elif self.activity_state == "critical":
            hr_mod = random.randint(25, 50)  # Tachycardia
            temp_mod = random.uniform(1.0, 3.0)  # Fever
            rr_mod = random.randint(8, 15)  # Tachypnea  
            bp_sys_mod = random.randint(-20, 40)  # Variable BP
            base_spo2 = max(88, base_spo2 - random.randint(5, 12))  # Hypoxia
        else:  # resting
            hr_mod = random.randint(-8, 12)  # Normal variation
            temp_mod = random.uniform(-0.4, 0.6)  # Normal temp variation
            rr_mod = random.randint(-2, 4)  # Normal breathing variation
            bp_sys_mod = random.randint(-10, 15)  # Normal BP variation
        
        # Calculate final vitals with natural randomness
        heart_rate = max(45, min(150, base_hr + hr_mod + random.randint(-3, 3)))
        temperature = round(base_temp + temp_mod + random.uniform(-0.2, 0.2), 1)
        oxygen_saturation = max(85, min(100, base_spo2 + random.randint(-2, 2)))
        blood_pressure_systolic = max(80, min(200, base_bp_sys + bp_sys_mod + random.randint(-5, 5)))
        blood_pressure_diastolic = max(50, min(120, base_bp_dia + int(bp_sys_mod * 0.6) + random.randint(-3, 3)))
        respiratory_rate = max(8, min(35, base_rr + rr_mod + random.randint(-1, 2)))
        
        # Simulate device metrics
        self.battery_level = max(10, self.battery_level - random.uniform(0.1, 0.5))  # Battery drain
        self.signal_strength = random.randint(-70, -25)  # WiFi signal variation
        
        # Generate additional sensor data
        skin_temperature = temperature - random.uniform(0.5, 2.0)  # Skin temp lower than core
        movement_intensity = random.uniform(0.1, 2.5) if self.activity_state == "active" else random.uniform(0.0, 0.3)
        
        return {
            "heart_rate": heart_rate,
            "temperature": temperature,
            "oxygen_saturation": oxygen_saturation,
            "blood_pressure_systolic": blood_pressure_systolic,
            "blood_pressure_diastolic": blood_pressure_diastolic,
            "respiratory_rate": respiratory_rate,
            "skin_temperature": round(skin_temperature, 1),
            "movement_intensity": round(movement_intensity, 2),
            "battery_level": int(self.battery_level),
            "signal_strength": self.signal_strength,
            "activity_state": self.activity_state
        }

    def create_esp32_payload(self) -> Dict:
        """Create ESP32-compatible payload matching the backend schema"""
        vitals = self.get_realistic_vitals()
        now = datetime.now(timezone.utc)
        
        self.sequence_number += 1
        
        payload = {
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
                "respiratory_rate": vitals["respiratory_rate"],
                "skin_temperature": vitals["skin_temperature"],
                "movement_intensity": vitals["movement_intensity"]
            },
            "device_metrics": {
                "battery_level": vitals["battery_level"],
                "signal_strength": vitals["signal_strength"],
                "memory_usage": random.randint(45, 85),  # Percentage
                "cpu_temperature": random.uniform(45.0, 75.0),
                "wifi_quality": random.randint(60, 95),
                "uptime_seconds": int((now - self.last_reading_time).total_seconds())
            },
            "location_data": {
                "room": self.location,
                "proximity_confidence": random.uniform(0.85, 0.98)
            },
            "quality_metrics": {
                "sensor_accuracy": random.uniform(0.92, 0.99),
                "data_completeness": random.uniform(0.95, 1.0),
                "signal_noise_ratio": random.uniform(15.0, 25.0)
            }
        }
        
        self.last_reading_time = now
        return payload

    async def send_vitals(self, session: aiohttp.ClientSession) -> bool:
        """Send vitals data to backend ingestion endpoint"""
        try:
            payload = self.create_esp32_payload()
            
            headers = {
                "Content-Type": "application/json",
                "X-Device-Token": self.device_token,
                "User-Agent": f"ESP32-{self.device_id}/1.2.3"
            }
            
            async with session.post(INGESTION_ENDPOINT, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 201:
                    vitals = payload["vitals"]
                    activity = payload.get("device_metrics", {}).get("activity_state", "unknown")
                    
                    # Alert indicators for abnormal vitals
                    alerts = []
                    if vitals["heart_rate"] > 100: alerts.append("🔴HR")
                    if vitals["temperature"] > 99.5: alerts.append("🔥TEMP") 
                    if vitals["oxygen_saturation"] < 95: alerts.append("🫁SPO2")
                    if vitals["blood_pressure_systolic"] > 140: alerts.append("⚡BP")
                    
                    alert_str = " ".join(alerts) if alerts else "✅"
                    
                    print(f"📡 {self.device_id}: HR:{vitals['heart_rate']} T:{vitals['temperature']}°F SpO2:{vitals['oxygen_saturation']}% BP:{vitals['blood_pressure_systolic']}/{vitals['blood_pressure_diastolic']} {alert_str}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ {self.device_id}: HTTP {response.status} - {error_text}")
                    return False
                    
        except asyncio.TimeoutError:
            print(f"⏰ {self.device_id}: Request timeout")
            return False
        except Exception as e:
            print(f"💥 {self.device_id}: Error - {str(e)}")
            return False

class MultiWatchSimulator:
    def __init__(self):
        self.simulators = [WatchSimulator(watch) for watch in WATCHES]
        self.session = None
        self.running = False
        
    async def start(self, interval_seconds: float = 5.0):
        """Start continuous simulation for all watches"""
        print(f"\n🚀 Starting Hospital Watch Data Simulator")
        print(f"📊 Simulating {len(self.simulators)} ESP32 watches")
        print(f"🔄 Sending data every {interval_seconds} seconds")
        print(f"🎯 Target endpoint: {INGESTION_ENDPOINT}")
        print("-" * 80)
        
        connector = aiohttp.TCPConnector(limit=20, ttl_dns_cache=300, use_dns_cache=True)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            self.session = session
            self.running = True
            
            iteration = 0
            successful_sends = 0
            failed_sends = 0
            
            try:
                while self.running:
                    iteration += 1
                    start_time = time.time()
                    
                    print(f"\n📡 Iteration {iteration} - Broadcasting vitals from all {len(self.simulators)} watches...")
                    
                    # Send data from all watches concurrently
                    tasks = [sim.send_vitals(session) for sim in self.simulators]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Count results
                    current_successful = sum(1 for r in results if r is True)
                    current_failed = sum(1 for r in results if r is not True) 
                    
                    successful_sends += current_successful
                    failed_sends += current_failed
                    
                    elapsed = time.time() - start_time
                    success_rate = (successful_sends / (successful_sends + failed_sends) * 100) if (successful_sends + failed_sends) > 0 else 0
                    
                    print(f"📈 Batch complete: {current_successful}/{len(self.simulators)} successful ({elapsed:.2f}s)")
                    print(f"📊 Overall stats: {successful_sends} success, {failed_sends} failed ({success_rate:.1f}% success rate)")
                    
                    # Wait for next iteration
                    await asyncio.sleep(max(0, interval_seconds - elapsed))
                    
            except KeyboardInterrupt:
                print(f"\n⏹️  Simulation stopped by user")
            except Exception as e:
                print(f"\n💥 Simulation error: {e}")
            finally:
                self.running = False
                print(f"\n📊 Final Statistics:")
                print(f"   Total successful transmissions: {successful_sends}")
                print(f"   Total failed transmissions: {failed_sends}")
                print(f"   Overall success rate: {success_rate:.1f}%")
                print(f"   Total iterations: {iteration}")

async def main():
    """Main entry point"""
    print("🏥 Hospital ESP32 Watch Data Simulator v1.0")
    print("=" * 60)
    
    # Check backend connectivity
    print("🔍 Checking backend connectivity...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BACKEND_URL}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    print("✅ Backend is reachable")
                else:
                    print(f"⚠️  Backend returned status {response.status}")
    except Exception as e:
        print(f"❌ Backend connectivity issue: {e}")
        print("   Make sure the backend server is running on http://localhost:8001")
        return
    
    # Initialize and start simulator
    simulator = MultiWatchSimulator()
    
    print(f"\n⚡ Starting simulation in 3 seconds...")
    await asyncio.sleep(3)
    
    # Start with 5-second intervals (realistic for hospital monitoring)
    await simulator.start(interval_seconds=5.0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n👋 Goodbye!")
