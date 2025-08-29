#!/usr/bin/env python3
"""
ESP32 Load Test - Simulate multiple watches sending vitals
Tests: 10 watches × 10 readings each = 100 API calls
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timezone
import random

# Test configuration
BASE_URL = "http://localhost:8001"
NUM_WATCHES = 10
READINGS_PER_WATCH = 10
DEVICE_TOKEN = "dt_HkbpUpVxlFYELpaMMiWClbVX71qffpSz4JiJSoxPhy8"

def generate_vital_reading(device_id: str, patient_id: str, reading_num: int):
    """Generate realistic vital signs with some variation"""
    # Generate unique timestamps by adding microseconds to avoid duplicates
    base_timestamp = datetime.now(timezone.utc)
    timestamp = base_timestamp.replace(microsecond=random.randint(0, 999999))
    
    # For load testing, use the same device ID for all requests since we only have one token
    # In real deployment, each watch would have its own token
    actual_device_id = "ESP32_WATCH_001"  # Use the provisioned device
    
    # Generate realistic vital ranges with some random variation
    vitals = {
        "device_id": actual_device_id,
        "patient_id": patient_id,
        "heart_rate": random.randint(70, 90) + random.choice([-5, 0, 5, 35]),  # Sometimes high
        "blood_pressure_systolic": random.randint(110, 130) + random.choice([0, 0, 0, 30]),
        "blood_pressure_diastolic": random.randint(70, 85),
        "temperature": round(random.uniform(98.0, 99.2) + random.choice([0, 0, 0, 3.5]), 1),
        "oxygen_saturation": random.randint(96, 100) - random.choice([0, 0, 0, 8]),  # Sometimes low
        "respiratory_rate": random.randint(12, 18) + random.choice([0, 0, 0, 12]),
        "reading_timestamp": timestamp.isoformat().replace('+00:00', 'Z'),
        "signal_quality": round(random.uniform(0.85, 0.98), 2),
        "battery_level": random.randint(75, 95)
    }
    
    return vitals

async def send_vital_reading(session: aiohttp.ClientSession, vital_data: dict, watch_num: int, reading_num: int):
    """Send a single vital reading to the ingestion endpoint"""
    headers = {
        "Content-Type": "application/json",
        "X-Device-Token": DEVICE_TOKEN
    }
    
    try:
        start_time = time.time()
        async with session.post(f"{BASE_URL}/api/v1/ingest/vitals", 
                               json=vital_data, 
                               headers=headers,
                               timeout=aiohttp.ClientTimeout(total=10)) as response:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms
            
            if response.status == 201:
                result = await response.json()
                return {
                    "success": True,
                    "watch": watch_num,
                    "reading": reading_num,
                    "response_time": response_time,
                    "stored_vitals": result.get("stored_vitals", 0)
                }
            else:
                error_text = await response.text()
                return {
                    "success": False,
                    "watch": watch_num,
                    "reading": reading_num,
                    "response_time": response_time,
                    "error": f"HTTP {response.status}: {error_text}"
                }
                
    except Exception as e:
        return {
            "success": False,
            "watch": watch_num,
            "reading": reading_num,
            "error": str(e)
        }

async def simulate_esp32_watch(session: aiohttp.ClientSession, watch_num: int):
    """Simulate one ESP32 watch sending multiple readings"""
    device_id = f"ESP32_WATCH_{watch_num:03d}"
    patient_id = f"P{watch_num:03d}"
    
    results = []
    
    for reading_num in range(READINGS_PER_WATCH):
        vital_data = generate_vital_reading(device_id, patient_id, reading_num)
        result = await send_vital_reading(session, vital_data, watch_num, reading_num)
        results.append(result)
        
        # Simulate 1Hz (1 second interval) - but faster for testing
        await asyncio.sleep(0.1)  # 100ms between readings for test speed
    
    return results

async def run_load_test():
    """Run the complete load test"""
    print(f"ESP32 WATCH LOAD TEST")
    print(f"Configuration: {NUM_WATCHES} watches × {READINGS_PER_WATCH} readings = {NUM_WATCHES * READINGS_PER_WATCH} total requests")
    print(f"Target: {BASE_URL}/api/v1/ingest/vitals")
    print("-" * 60)
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        # Create tasks for all watches
        watch_tasks = [
            simulate_esp32_watch(session, watch_num) 
            for watch_num in range(1, NUM_WATCHES + 1)
        ]
        
        # Run all watches concurrently
        watch_results = await asyncio.gather(*watch_tasks)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Analyze results
    all_results = []
    for watch_result in watch_results:
        all_results.extend(watch_result)
    
    successful = [r for r in all_results if r["success"]]
    failed = [r for r in all_results if not r["success"]]
    
    response_times = [r["response_time"] for r in successful if "response_time" in r]
    total_vitals_stored = sum(r.get("stored_vitals", 0) for r in successful)
    
    print(f"LOAD TEST RESULTS")
    print(f"Total requests: {len(all_results)}")
    print(f"Successful: {len(successful)} ({len(successful)/len(all_results)*100:.1f}%)")
    print(f"Failed: {len(failed)} ({len(failed)/len(all_results)*100:.1f}%)")
    print(f"Total vitals stored: {total_vitals_stored}")
    print(f"Total test time: {total_time:.2f} seconds")
    print(f"Throughput: {len(successful)/total_time:.1f} requests/second")
    
    if response_times:
        avg_response = sum(response_times) / len(response_times)
        max_response = max(response_times)
        min_response = min(response_times)
        
        print(f"Response times:")
        print(f"   - Average: {avg_response:.1f}ms")
        print(f"   - Min: {min_response:.1f}ms") 
        print(f"   - Max: {max_response:.1f}ms")
    
    # Show any errors
    if failed:
        print(f"\nERRORS:")
        error_counts = {}
        for failure in failed:
            error = failure.get("error", "Unknown error")
            error_counts[error] = error_counts.get(error, 0) + 1
        
        for error, count in error_counts.items():
            print(f"   - {error}: {count} occurrences")
    
    print("-" * 60)
    print(f"Load test complete! System handled {len(successful)}/{len(all_results)} requests successfully")
    
    # Scaling projection
    if successful:
        successful_rate = len(successful) / len(all_results)
        projected_500_watches = 500 * successful_rate
        print(f"SCALING PROJECTION:")
        print(f"   - Current success rate: {successful_rate*100:.1f}%")
        print(f"   - Projected capacity for 500 watches: ~{projected_500_watches:.0f} watches")
        
        if avg_response < 100:  # Target < 100ms
            print(f"   Response time target met ({avg_response:.1f}ms < 100ms)")
        else:
            print(f"   Response time needs optimization ({avg_response:.1f}ms > 100ms)")

if __name__ == "__main__":
    asyncio.run(run_load_test())