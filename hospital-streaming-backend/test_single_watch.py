#!/usr/bin/env python3
"""
Simple test to send one vitals reading to verify the backend works
"""
import requests
import json
from datetime import datetime, timezone

BACKEND_URL = "http://localhost:8001"
ENDPOINT = f"{BACKEND_URL}/api/v1/ingest/vitals"

# Test payload - ESP32VitalReading schema
payload = {
    "device_id": "ESP32_TEST_001",
    "patient_id": "P25082350",
    "reading_timestamp": datetime.now(timezone.utc).isoformat(),
    "heart_rate": 75,
    "temperature": 98.6,
    "oxygen_saturation": 98,
    "blood_pressure_systolic": 120,
    "blood_pressure_diastolic": 80,
    "respiratory_rate": 16,
    "signal_quality": 0.95,
    "battery_level": 85
}

headers = {
    "Content-Type": "application/json",
    "X-Device-Token": "test_token_123"
}

print("Testing single vitals ingestion...")
print(f"Endpoint: {ENDPOINT}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(ENDPOINT, json=payload, headers=headers, timeout=10)
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 201:
        print("\n[SUCCESS] Vitals data sent successfully!")
    else:
        print(f"\n[ERROR] Failed to send vitals data")
        
except Exception as e:
    print(f"\n[ERROR] Exception: {e}")
