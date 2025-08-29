#!/usr/bin/env python3
"""
Tablet BLE Load Test - Simulate tablet forwarding BLE vitals
Tests: 4 tablets × 3 watches each × 20 batches = 240 API calls
Simulates the PRIMARY data path: Watch → BLE → Tablet → Server
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timezone
import random

# Test configuration
BASE_URL = "http://localhost:8001"
NUM_TABLETS = 4  # Simulate 4 tablets
WATCHES_PER_TABLET = 3  # 3 watches per tablet (max recommended)
BATCHES_PER_WATCH = 20  # Each watch sends 20 batches
READINGS_PER_BATCH = 5  # 5 readings per batch (5-second intervals)

def generate_tablet_vitals_batch(tablet_id: int, watch_num: int, patient_id: str, sequence: int):
    """Generate realistic BLE vitals batch from tablet"""
    
    readings = []
    base_timestamp = datetime.now(timezone.utc)
    
    for i in range(READINGS_PER_BATCH):
        # Generate unique timestamps with microseconds
        timestamp = base_timestamp.replace(microsecond=random.randint(0, 999999))
        
        # Simulate realistic vital signs with some variation
        reading = {
            "timestamp": timestamp.isoformat().replace('+00:00', 'Z'),
            "vitals": {
                "heart_rate": random.randint(70, 85) + random.choice([0, 0, 0, 40]),  # Sometimes high
                "blood_pressure_systolic": random.randint(110, 125) + random.choice([0, 0, 0, 30]),
                "blood_pressure_diastolic": random.randint(70, 80),
                "temperature": round(random.uniform(98.0, 99.0) + random.choice([0, 0, 0, 4.0]), 1),
                "oxygen_saturation": random.randint(97, 100) - random.choice([0, 0, 0, 8]),
                "respiratory_rate": random.randint(12, 18) + random.choice([0, 0, 0, 10])
            },
            "quality": round(random.uniform(0.88, 0.98), 2),
            "battery_level": random.randint(70, 95),
            "signal_strength": random.randint(-65, -35)  # BLE RSSI
        }
        readings.append(reading)
        
        # Increment timestamp for next reading
        base_timestamp = base_timestamp.replace(second=base_timestamp.second + 1)
    
    return {
        "device_id": f"ESP32_WATCH_T{tablet_id:02d}W{watch_num}",  # Simulated watch IDs
        "patient_id": patient_id,
        "readings": readings,
        "sequence": sequence,
        "app_info": {
            "version": "1.2.0",
            "device_model": f"Samsung Galaxy Tab A{8 + tablet_id}",
            "build_number": 42,
            "tablet_id": f"TABLET_{tablet_id:03d}",
            "ble_connections": WATCHES_PER_TABLET
        }
    }

async def send_tablet_batch(session: aiohttp.ClientSession, batch_data: dict, tablet_id: int, watch_num: int, batch_num: int):
    """Send BLE vitals batch from tablet to server"""
    
    try:
        start_time = time.time()
        async with session.post(
            f"{BASE_URL}/api/v1/mobile/vitals/batch/{batch_data['patient_id']}", 
            json=batch_data,
            timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            if response.status == 200:
                result = await response.json()
                return {
                    "success": True,
                    "tablet": tablet_id,
                    "watch": watch_num,
                    "batch": batch_num,
                    "response_time": response_time,
                    "stored_readings": result.get("stored_readings", 0),
                    "processed_vitals": result.get("processed_vitals", 0),
                    "alerts": len(result.get("alerts", []))
                }
            else:
                error_text = await response.text()
                return {
                    "success": False,
                    "tablet": tablet_id,
                    "watch": watch_num,
                    "batch": batch_num,
                    "response_time": response_time,
                    "error": f"HTTP {response.status}: {error_text}"
                }
                
    except Exception as e:
        return {
            "success": False,
            "tablet": tablet_id,
            "watch": watch_num,
            "batch": batch_num,
            "error": str(e)
        }

async def simulate_tablet_watch(session: aiohttp.ClientSession, tablet_id: int, watch_num: int):
    """Simulate one BLE watch connected to tablet"""
    patient_id = f"P{tablet_id:02d}{watch_num:02d}"  # Unique patient per watch
    
    results = []
    
    for batch_num in range(BATCHES_PER_WATCH):
        batch_data = generate_tablet_vitals_batch(tablet_id, watch_num, patient_id, batch_num + 1)
        result = await send_tablet_batch(session, batch_data, tablet_id, watch_num, batch_num + 1)
        results.append(result)
        
        # Simulate 5-second batching interval (faster for testing)
        await asyncio.sleep(0.1)  # 100ms for test speed
    
    return results

async def simulate_tablet(session: aiohttp.ClientSession, tablet_id: int):
    """Simulate one Android tablet handling multiple BLE watches"""
    
    # Run all watches on this tablet concurrently
    watch_tasks = [
        simulate_tablet_watch(session, tablet_id, watch_num)
        for watch_num in range(1, WATCHES_PER_TABLET + 1)
    ]
    
    watch_results = await asyncio.gather(*watch_tasks)
    
    # Flatten results from all watches on this tablet
    tablet_results = []
    for watch_result in watch_results:
        tablet_results.extend(watch_result)
    
    return tablet_results

async def run_tablet_ble_load_test():
    """Run the complete tablet BLE load test"""
    print(f"TABLET BLE LOAD TEST")
    print(f"Configuration: {NUM_TABLETS} tablets × {WATCHES_PER_TABLET} watches × {BATCHES_PER_WATCH} batches")
    print(f"Total API calls: {NUM_TABLETS * WATCHES_PER_TABLET * BATCHES_PER_WATCH}")
    print(f"Readings per batch: {READINGS_PER_BATCH}")
    print(f"Target: {BASE_URL}/api/v1/mobile/vitals/batch/{{patient_id}}")
    print("-" * 70)
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        # Create tasks for all tablets
        tablet_tasks = [
            simulate_tablet(session, tablet_id)
            for tablet_id in range(1, NUM_TABLETS + 1)
        ]
        
        # Run all tablets concurrently
        tablet_results = await asyncio.gather(*tablet_tasks)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Analyze results
    all_results = []
    for tablet_result in tablet_results:
        all_results.extend(tablet_result)
    
    successful = [r for r in all_results if r["success"]]
    failed = [r for r in all_results if not r["success"]]
    
    response_times = [r["response_time"] for r in successful if "response_time" in r]
    total_vitals_stored = sum(r.get("stored_readings", 0) for r in successful)
    total_vitals_processed = sum(r.get("processed_vitals", 0) for r in successful)
    total_alerts = sum(r.get("alerts", 0) for r in successful)
    
    print(f"TABLET BLE LOAD TEST RESULTS")
    print(f"Total API calls: {len(all_results)}")
    print(f"Successful: {len(successful)} ({len(successful)/len(all_results)*100:.1f}%)")
    print(f"Failed: {len(failed)} ({len(failed)/len(all_results)*100:.1f}%)")
    print(f"Total vitals stored: {total_vitals_stored}")
    print(f"Total vitals processed: {total_vitals_processed}")
    print(f"Total alerts generated: {total_alerts}")
    print(f"Total test time: {total_time:.2f} seconds")
    print(f"Throughput: {len(successful)/total_time:.1f} batch requests/second")
    print(f"Vitals ingestion rate: {total_vitals_stored/total_time:.1f} vitals/second")
    
    if response_times:
        avg_response = sum(response_times) / len(response_times)
        max_response = max(response_times)
        min_response = min(response_times)
        
        print(f"Response times:")
        print(f"   - Average: {avg_response:.1f}ms")
        print(f"   - Min: {min_response:.1f}ms") 
        print(f"   - Max: {max_response:.1f}ms")
    
    # Analyze by tablet
    tablet_stats = {}
    for result in successful:
        tablet = result.get("tablet", "unknown")
        if tablet not in tablet_stats:
            tablet_stats[tablet] = {"batches": 0, "vitals": 0, "alerts": 0}
        
        tablet_stats[tablet]["batches"] += 1
        tablet_stats[tablet]["vitals"] += result.get("stored_readings", 0)
        tablet_stats[tablet]["alerts"] += result.get("alerts", 0)
    
    print(f"\nPER-TABLET BREAKDOWN:")
    for tablet_id, stats in tablet_stats.items():
        print(f"   Tablet {tablet_id}: {stats['batches']} batches, {stats['vitals']} vitals, {stats['alerts']} alerts")
    
    # Show any errors
    if failed:
        print(f"\nERRORS:")
        error_counts = {}
        for failure in failed:
            error = failure.get("error", "Unknown error")
            error_key = error.split(":")[0] if ":" in error else error
            error_counts[error_key] = error_counts.get(error_key, 0) + 1
        
        for error, count in error_counts.items():
            print(f"   - {error}: {count} occurrences")
    
    print("-" * 70)
    print(f"BLE tablet system test complete! Processed {len(successful)}/{len(all_results)} batch requests")
    
    # Real-world projection
    if successful:
        success_rate = len(successful) / len(all_results)
        batches_per_second = len(successful) / total_time
        
        # Each tablet can handle 3-4 watches, each sending batches every 5 seconds
        real_world_batches_per_second = (NUM_TABLETS * WATCHES_PER_TABLET) / 5  # Every 5 seconds
        
        print(f"\nREAL-WORLD PROJECTION:")
        print(f"   - Test batch rate: {batches_per_second:.1f} batches/second")
        print(f"   - Real-world rate needed: {real_world_batches_per_second:.1f} batches/second") 
        print(f"   - System capacity margin: {batches_per_second/real_world_batches_per_second:.1f}x")
        
        if batches_per_second > real_world_batches_per_second * 2:  # 2x safety margin
            print(f"   System ready for production deployment!")
        else:
            print(f"   System needs optimization for production load")

if __name__ == "__main__":
    asyncio.run(run_tablet_ble_load_test())