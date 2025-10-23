"""
Test V2 Devices API via HTTP
Tests all endpoints with proper authentication
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8001"

def login():
    """Login and get JWT token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "staffId": "DOC0001",
            "password": "doctor123"
        }
    )
    if response.status_code == 200:
        data = response.json()
        return data.get("accessToken") or data.get("access_token")
    else:
        print(f"[ERROR] Login failed: {response.status_code} - {response.text}")
        return None

def test_v2_devices_api():
    """Test all v2 devices endpoints"""
    print("="*80)
    print("TESTING V2 DEVICES API (HTTP)")
    print("="*80)

    # Login first
    print("\n[STEP 1] Logging in...")
    token = login()
    if not token:
        print("[FAIL] Cannot proceed without authentication")
        return False

    print(f"[SUCCESS] Logged in successfully")

    headers = {"Authorization": f"Bearer {token}"}

    all_tests_passed = True

    # Test 1: Get all devices
    print("\n[TEST 1] GET /api/v2/devices/ - Get all devices")
    try:
        response = requests.get(f"{BASE_URL}/api/v2/devices/", headers=headers)
        print(f"[STATUS] {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"[RESPONSE] Success: {data.get('success')}")
            print(f"[DATA] Devices count: {data.get('count')}")
            print(f"[DATA] Total: {data.get('total')}")

            if data.get('devices'):
                device = data['devices'][0]
                print(f"[SAMPLE] First device: {device.get('id')} - {device.get('name')}")
                print(f"[FIELDS] connectionStatus: {device.get('connectionStatus')}")
                print(f"[FIELDS] batteryStatus: {device.get('batteryStatus')}")
            print("[RESULT] [OK] PASS")
        else:
            print(f"[RESULT] [FAIL] - Status {response.status_code}: {response.text[:200]}")
            all_tests_passed = False
    except Exception as e:
        print(f"[RESULT] [FAIL] - Exception: {e}")
        all_tests_passed = False

    # Test 2: Filter by device type
    print("\n[TEST 2] GET /api/v2/devices/?deviceType=watch - Filter by type")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v2/devices/",
            headers=headers,
            params={"deviceType": "watch"}
        )
        print(f"[STATUS] {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"[DATA] Watch devices found: {data.get('count')}")
            print("[RESULT] [OK] PASS")
        else:
            print(f"[RESULT] [FAIL] - Status {response.status_code}")
            all_tests_passed = False
    except Exception as e:
        print(f"[RESULT] [FAIL] - Exception: {e}")
        all_tests_passed = False

    # Test 3: Get available devices only
    print("\n[TEST 3] GET /api/v2/devices/?status=available - Available only")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v2/devices/",
            headers=headers,
            params={"status": "available"}
        )
        print(f"[STATUS] {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"[DATA] Available devices: {data.get('count')}")
            print("[RESULT] [OK] PASS")
        else:
            print(f"[RESULT] [FAIL] - Status {response.status_code}")
            all_tests_passed = False
    except Exception as e:
        print(f"[RESULT] [FAIL] - Exception: {e}")
        all_tests_passed = False

    # Test 4: Get single device by ID
    print("\n[TEST 4] GET /api/v2/devices/{deviceId} - Get single device")
    try:
        # First get a device ID
        response = requests.get(f"{BASE_URL}/api/v2/devices/", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('devices'):
                device_id = data['devices'][0]['id']

                # Now get that specific device
                response2 = requests.get(
                    f"{BASE_URL}/api/v2/devices/{device_id}",
                    headers=headers
                )
                print(f"[STATUS] {response2.status_code}")

                if response2.status_code == 200:
                    device = response2.json()
                    print(f"[DATA] Device: {device.get('id')} - {device.get('name')}")
                    print(f"[DATA] Status: {device.get('status')}")
                    print(f"[DATA] Connection: {device.get('connectionStatus')}")
                    print(f"[DATA] Battery: {device.get('batteryStatus')} ({device.get('batteryLevel')}%)")
                    print("[RESULT] [OK] PASS")
                else:
                    print(f"[RESULT] [FAIL] - Status {response2.status_code}")
                    all_tests_passed = False
            else:
                print("[SKIP] No devices to test with")
    except Exception as e:
        print(f"[RESULT] [FAIL] - Exception: {e}")
        all_tests_passed = False

    # Test 5: Get device statistics
    print("\n[TEST 5] GET /api/v2/devices/stats/summary - Statistics")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v2/devices/stats/summary",
            headers=headers
        )
        print(f"[STATUS] {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            summary = data.get('summary', {})
            print(f"[DATA] Total Devices: {summary.get('totalDevices')}")
            print(f"[DATA] Available: {summary.get('availableDevices')}")
            print(f"[DATA] Assigned: {summary.get('assignedDevices')}")
            print(f"[DATA] Offline: {summary.get('offlineDevices')}")
            print(f"[DATA] Low Battery: {summary.get('lowBatteryDevices')}")
            print(f"[DATA] Total Watches: {summary.get('totalWatches')}")
            print("[RESULT] [OK] PASS")
        else:
            print(f"[RESULT] [FAIL] - Status {response.status_code}")
            all_tests_passed = False
    except Exception as e:
        print(f"[RESULT] [FAIL] - Exception: {e}")
        all_tests_passed = False

    # Test 6: Convenience shortcuts
    print("\n[TEST 6] GET /api/v2/devices/available/watches - Convenience shortcut")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v2/devices/available/watches",
            headers=headers
        )
        print(f"[STATUS] {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"[DATA] Available watches: {data.get('count')}")
            print("[RESULT] [OK] PASS")
        else:
            print(f"[RESULT] [FAIL] - Status {response.status_code}")
            all_tests_passed = False
    except Exception as e:
        print(f"[RESULT] [FAIL] - Exception: {e}")
        all_tests_passed = False

    # Summary
    print("\n" + "="*80)
    if all_tests_passed:
        print("[SUCCESS] ALL V2 API HTTP TESTS PASSED")
        print("="*80)
        print("\nThe v2 devices API is working correctly over HTTP:")
        print("  [OK] Authentication working")
        print("  [OK] Get all devices endpoint")
        print("  [OK] Filter by device type")
        print("  [OK] Filter by status")
        print("  [OK] Get single device")
        print("  [OK] Statistics endpoint")
        print("  [OK] Convenience shortcuts")
        print("\nBackend successfully restarted with v2 routes!")
        return True
    else:
        print("[FAILED] SOME V2 API HTTP TESTS FAILED")
        print("="*80)
        return False

if __name__ == "__main__":
    import sys
    success = test_v2_devices_api()
    sys.exit(0 if success else 1)
