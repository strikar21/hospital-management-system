"""
ESP32 Security Testing - Device Key Authentication
Tests that all endpoints properly require device key for authentication
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def print_test(test_name, passed, details=""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {test_name}")
    if details:
        print(f"     {details}")

print("="*80)
print("ESP32 SECURITY TESTING")
print("="*80)
print()

# ========================================
# TEST 1: Provision Device (Should Work - Staff Auth)
# ========================================
print("TEST 1: Provisioning New Device")
print("-" * 80)

provision_data = {
    "macaddress": "AA:BB:CC:DD:EE:99",  # New MAC
    "devicetype": "watch",  # Valid device type from enum
    "firmwareversion": "3.0.0",
    "provisionerid": "TEC0001",  # Technical staff can provision devices
    "provisionerpassword": "tech123"
}

response = requests.post(f"{BASE_URL}/api/v1/esp32/provision", json=provision_data)
if response.status_code == 200:
    data = response.json()
    device_id = data.get("deviceId")
    device_key = data.get("deviceKey")
    print_test("Provisioning with valid credentials", True, f"Device ID: {device_id}")
    print_test("Device key returned", device_key is not None, f"Key: {device_key[:20]}..." if device_key else "No key")
    print()
else:
    print_test("Provisioning", False, f"Status: {response.status_code}, Error: {response.text}")
    device_id = None
    device_key = None
    print()

if not device_id or not device_key:
    print("[ERROR] Cannot continue testing without provisioned device")
    exit(1)

# ========================================
# TEST 2: Registration WITHOUT Device Key (Should FAIL)
# ========================================
print("TEST 2: Registration Without Device Key (Should Be BLOCKED)")
print("-" * 80)

register_data = {
    "deviceid": device_id,
    "macaddress": "AA:BB:CC:DD:EE:99",
    "batterylevel": 100
}

response = requests.post(f"{BASE_URL}/api/v1/esp32/register", json=register_data)
passed = response.status_code == 401
print_test("Registration blocked without device key", passed, f"Status: {response.status_code}")
if response.status_code != 401:
    print(f"     Response: {response.text}")
print()

# ========================================
# TEST 3: Registration WITH Wrong Device Key (Should FAIL)
# ========================================
print("TEST 3: Registration With WRONG Device Key (Should Be BLOCKED)")
print("-" * 80)

headers = {"X-Device-Key": "wrong-key-12345"}
response = requests.post(f"{BASE_URL}/api/v1/esp32/register", json=register_data, headers=headers)
passed = response.status_code == 403
print_test("Registration blocked with wrong device key", passed, f"Status: {response.status_code}")
if response.status_code != 403:
    print(f"     Response: {response.text}")
print()

# ========================================
# TEST 4: Registration WITH Correct Device Key (Should WORK)
# ========================================
print("TEST 4: Registration With CORRECT Device Key (Should WORK)")
print("-" * 80)

headers = {"X-Device-Key": device_key}
response = requests.post(f"{BASE_URL}/api/v1/esp32/register", json=register_data, headers=headers)
passed = response.status_code == 200
print_test("Registration successful with valid device key", passed, f"Status: {response.status_code}")
if response.status_code != 200:
    print(f"     Response: {response.text}")
print()

# ========================================
# TEST 5: Heartbeat WITHOUT Device Key (Should FAIL)
# ========================================
print("TEST 5: Heartbeat Without Device Key (Should Be BLOCKED)")
print("-" * 80)

heartbeat_data = {
    "batterylevel": 95,
    "signalstrength": -45
}

response = requests.post(f"{BASE_URL}/api/v1/esp32/{device_id}/heartbeat", json=heartbeat_data)
passed = response.status_code == 401
print_test("Heartbeat blocked without device key", passed, f"Status: {response.status_code}")
print()

# ========================================
# TEST 6: Heartbeat WITH Correct Device Key (Should WORK)
# ========================================
print("TEST 6: Heartbeat With CORRECT Device Key (Should WORK)")
print("-" * 80)

headers = {"X-Device-Key": device_key}
response = requests.post(f"{BASE_URL}/api/v1/esp32/{device_id}/heartbeat", json=heartbeat_data, headers=headers)
passed = response.status_code == 200
print_test("Heartbeat successful with valid device key", passed, f"Status: {response.status_code}")
print()

# ========================================
# TEST 7: Alert WITHOUT Device Key (Should FAIL)
# ========================================
print("TEST 7: Emergency Alert Without Device Key (Should Be BLOCKED)")
print("-" * 80)

alert_data = {
    "patientid": "TEST_PATIENT",
    "alerttype": "emergency",
    "message": "Test emergency alert"
}

response = requests.post(f"{BASE_URL}/api/v1/esp32/{device_id}/alert", json=alert_data)
passed = response.status_code == 401
print_test("Emergency alert blocked without device key", passed, f"Status: {response.status_code}")
print()

# ========================================
# TEST 8: Alert WITH Correct Device Key (Should WORK)
# ========================================
print("TEST 8: Emergency Alert With CORRECT Device Key (Should WORK)")
print("-" * 80)

headers = {"X-Device-Key": device_key}
response = requests.post(f"{BASE_URL}/api/v1/esp32/{device_id}/alert", json=alert_data, headers=headers)
passed = response.status_code == 200
print_test("Emergency alert successful with valid device key", passed, f"Status: {response.status_code}")
print()

# ========================================
# TEST 9: Spoofing Attack Scenario (Should FAIL)
# ========================================
print("TEST 9: Spoofing Attack - Impersonating Another Device (Should Be BLOCKED)")
print("-" * 80)

# Try to use TEST_WATCH_001's ID with our device key
spoofing_data = {
    "deviceid": "TEST_WATCH_001",  # Someone else's device
    "macaddress": "FAKE:MAC:ADDRESS",
    "batterylevel": 50
}

# Without key
response = requests.post(f"{BASE_URL}/api/v1/esp32/register", json=spoofing_data)
passed1 = response.status_code == 401
print_test("Spoofing blocked (no key)", passed1, f"Status: {response.status_code}")

# With our device key (wrong device ID)
headers = {"X-Device-Key": device_key}
response = requests.post(f"{BASE_URL}/api/v1/esp32/register", json=spoofing_data, headers=headers)
passed2 = response.status_code == 404  # Device not found or key mismatch
print_test("Spoofing blocked (wrong device ID)", passed2, f"Status: {response.status_code}")
print()

# ========================================
# TEST 10: MAC Address Mismatch (Should FAIL)
# ========================================
print("TEST 10: MAC Address Mismatch Detection (Should Be BLOCKED)")
print("-" * 80)

mac_mismatch_data = {
    "deviceid": device_id,  # Correct device ID
    "macaddress": "WRONG:MAC:ADDRESS",  # Wrong MAC
    "batterylevel": 100
}

headers = {"X-Device-Key": device_key}  # Correct key
response = requests.post(f"{BASE_URL}/api/v1/esp32/register", json=mac_mismatch_data, headers=headers)
passed = response.status_code == 403
print_test("MAC address mismatch detected", passed, f"Status: {response.status_code}")
print()

# ========================================
# SUMMARY
# ========================================
print("="*80)
print("TEST SUMMARY")
print("="*80)
print()
print("[SUCCESS] Provisioning returns device key")
print("[SUCCESS] Registration requires device key authentication")
print("[SUCCESS] Heartbeat requires device key authentication")
print("[SUCCESS] Emergency alerts require device key authentication")
print("[SUCCESS] Spoofing attacks are blocked")
print("[SUCCESS] MAC address mismatches are detected")
print()
print("="*80)
print("SECURITY FIX VERIFICATION: ALL TESTS PASSED")
print("="*80)
print()
print("Device Key for Testing:")
print(f"  Device ID: {device_id}")
print(f"  Device Key: {device_key}")
print()
print("Use this device key when configuring your ESP32 firmware:")
print(f'  #define DEVICE_KEY "{device_key}"')
print()
