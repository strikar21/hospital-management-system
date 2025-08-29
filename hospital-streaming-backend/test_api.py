#!/usr/bin/env python3
"""
Simple test script for the Hospital Streaming Backend API
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8001"

def test_api():
    print("Hospital Streaming Backend API Test")
    print("=" * 50)
    
    # Test root endpoint
    print("\n1. Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test health endpoint
    print("\n2. Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/api/v1/health/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Register a test device
    print("\n3. Registering a test device...")
    device_data = {
        "device_id": "TEST_WATCH_001",
        "name": "Test Patient Watch #1",
        "device_type": "watch",
        "location": "ICU-101",
        "capabilities": {
            "vitals": True,
            "location": True,
            "battery": True
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/devices/", json=device_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        device = response.json()
        print(f"Device registered: {device['device_id']}")
        device_token = device.get('device_token', 'N/A')
        print(f"Device token: {device_token}")
        
        # Test getting devices
        print("\n4. Getting all devices...")
        response = requests.get(f"{BASE_URL}/api/v1/devices/")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Found {len(response.json().get('devices', []))} devices")
        
        # Test sending vital signs data
        if device_token != 'N/A':
            print("\n5. Testing vital signs ingestion...")
            vital_data = {
                "device_id": "TEST_WATCH_001",
                "patient_id": "TEST_PATIENT_001",
                "heart_rate": 75,
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80,
                "temperature": 98.6,
                "oxygen_saturation": 98.5,
                "reading_timestamp": datetime.utcnow().isoformat()
            }
            
            headers = {
                "X-Device-Token": device_token,
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/v1/ingest/vitals",
                json=vital_data,
                headers=headers
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 201:
                print("Vital signs data ingested successfully!")
            else:
                print(f"Error: {response.text}")
    else:
        print(f"Error registering device: {response.text}")
    
    # Test streaming stats
    print("\n6. Testing streaming stats...")
    response = requests.get(f"{BASE_URL}/api/v1/streaming/stats")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"WebSocket connections: {stats['total_connections']}")
        print(f"Channels: {list(stats['channels'].keys())}")

if __name__ == "__main__":
    test_api()