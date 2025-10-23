"""
Test ESP32 Field Mapper Integration
Tests bidirectional field transformation for ESP32 device communication
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(__file__))

from app.middleware.esp32_field_mapper import ESP32FieldMapper

def test_esp32_field_mapper():
    """Test ESP32 field transformation in both directions"""
    print("="*80)
    print("TESTING ESP32 FIELD MAPPER")
    print("="*80)

    all_tests_passed = True

    # Test 1: Transform ESP32 vitals data (lowercase to camelCase)
    print("\n[TEST 1] ESP32 Vitals Data Transformation (lowercase to camelCase)")
    esp32_vitals = {
        "deviceid": "WATCH_001",
        "patientid": "PAT_001",
        "heartrate": 75,
        "oxygensat": 98,
        "temperature": 98.6,
        "bloodpressurevalue": 120,
        "respiratoryrate": 16,
        "devicebattery": 85
    }

    transformed_vitals = ESP32FieldMapper.transform_request(esp32_vitals)
    print(f"[INPUT] ESP32 sent: {esp32_vitals}")
    print(f"[OUTPUT] Backend receives: {transformed_vitals}")

    # Verify transformation
    expected_vitals = {
        "deviceId": "WATCH_001",
        "patientId": "PAT_001",
        "heartRate": 75,
        "oxygenSaturation": 98,
        "bodyTemperature": 98.6,
        "bloodPressureSystolic": 120,
        "respiratoryRate": 16,
        "deviceBattery": 85
    }

    if transformed_vitals == expected_vitals:
        print("[RESULT] [OK] PASS - All fields transformed correctly")
    else:
        print("[RESULT] [FAIL] - Field transformation mismatch")
        print(f"Expected: {expected_vitals}")
        print(f"Got: {transformed_vitals}")
        all_tests_passed = False

    # Test 2: Transform backend response (camelCase to lowercase)
    print("\n[TEST 2] Backend Response Transformation (camelCase to lowercase)")
    backend_data = {
        "deviceId": "WATCH_001",
        "heartRate": 75,
        "oxygenSaturation": 98,
        "bodyTemperature": 98.6,
        "batteryLevel": 85,
        "lastSeen": "2025-10-13T10:30:00",
        "connectionStatus": "connected"
    }

    esp32_response = ESP32FieldMapper.transform_response(backend_data)
    print(f"[INPUT] Backend has: {backend_data}")
    print(f"[OUTPUT] ESP32 receives: {esp32_response}")

    # Verify key fields transformed
    if (esp32_response.get('deviceid') == 'WATCH_001' and
        esp32_response.get('heartrate') == 75 and
        esp32_response.get('oxygensat') == 98):
        print("[RESULT] [OK] PASS - Backend to ESP32 transformation working")
    else:
        print("[RESULT] [FAIL] - Backend to ESP32 transformation failed")
        all_tests_passed = False

    # Test 3: Transform device registration data
    print("\n[TEST 3] Device Registration Data Transformation")
    esp32_registration = {
        "deviceid": "ESP32_WATCH_002",
        "macaddress": "AA:BB:CC:DD:EE:FF",
        "firmwareversion": "3.0.0",
        "batterylevel": 100,
        "devicetype": "watch"
    }

    transformed_registration = ESP32FieldMapper.transform_request(esp32_registration)
    print(f"[INPUT] ESP32 registration: {esp32_registration}")
    print(f"[OUTPUT] Backend receives: {transformed_registration}")

    if (transformed_registration.get('deviceId') == 'ESP32_WATCH_002' and
        transformed_registration.get('macAddress') == 'AA:BB:CC:DD:EE:FF' and
        transformed_registration.get('firmwareVersion') == '3.0.0'):
        print("[RESULT] [OK] PASS - Registration data transformed correctly")
    else:
        print("[RESULT] [FAIL] - Registration transformation failed")
        all_tests_passed = False

    # Test 4: Transform heartbeat data
    print("\n[TEST 4] Heartbeat Data Transformation")
    esp32_heartbeat = {
        "deviceid": "WATCH_001",
        "batterylevel": 75,
        "signalstrength": -45,
        "status": "active"
    }

    transformed_heartbeat = ESP32FieldMapper.transform_request(esp32_heartbeat)
    print(f"[INPUT] ESP32 heartbeat: {esp32_heartbeat}")
    print(f"[OUTPUT] Backend receives: {transformed_heartbeat}")

    if (transformed_heartbeat.get('deviceId') == 'WATCH_001' and
        transformed_heartbeat.get('batteryLevel') == 75 and
        transformed_heartbeat.get('signalStrength') == -45):
        print("[RESULT] [OK] PASS - Heartbeat data transformed correctly")
    else:
        print("[RESULT] [FAIL] - Heartbeat transformation failed")
        all_tests_passed = False

    # Test 5: Transform door scanner data
    print("\n[TEST 5] Door Scanner Data Transformation")
    esp32_scan_data = {
        "scannerid": "DOOR_SCANNER_001",
        "roomid": "ROOM_101",
        "detecteddevices": [
            {"deviceid": "WATCH_001", "rssi": -50},
            {"deviceid": "TABLET_002", "rssi": -45}
        ]
    }

    transformed_scan = ESP32FieldMapper.transform_request(esp32_scan_data)
    print(f"[INPUT] Door scanner data: {esp32_scan_data}")
    print(f"[OUTPUT] Backend receives: {transformed_scan}")

    if (transformed_scan.get('scannerId') == 'DOOR_SCANNER_001' and
        transformed_scan.get('roomId') == 'ROOM_101' and
        len(transformed_scan.get('detectedDevices', [])) == 2):
        print("[RESULT] [OK] PASS - Door scanner data transformed correctly")
    else:
        print("[RESULT] [FAIL] - Door scanner transformation failed")
        all_tests_passed = False

    # Test 6: Transform nested vitals data
    print("\n[TEST 6] Nested Vitals Data Transformation")
    esp32_complex_vitals = {
        "deviceid": "WATCH_001",
        "vitals": {
            "heartrate": 80,
            "oxygensat": 97,
            "temperature": 98.6
        },
        "metadata": {
            "batterylevel": 90,
            "signalstrength": -40
        }
    }

    transformed_complex = ESP32FieldMapper.transform_request(esp32_complex_vitals, recursive=True)
    print(f"[INPUT] Nested vitals: {esp32_complex_vitals}")
    print(f"[OUTPUT] Backend receives: {transformed_complex}")

    if (transformed_complex.get('deviceId') == 'WATCH_001' and
        transformed_complex.get('vitals', {}).get('heartRate') == 80 and
        transformed_complex.get('metadata', {}).get('batteryLevel') == 90):
        print("[RESULT] [OK] PASS - Nested data transformed recursively")
    else:
        print("[RESULT] [FAIL] - Nested transformation failed")
        all_tests_passed = False

    # Test 7: Validation methods
    print("\n[TEST 7] Validation Methods")
    valid_esp32_data = {
        "deviceid": "WATCH_001",
        "heartrate": 75
    }
    invalid_esp32_data = None

    validation1_result, validation1_issues = ESP32FieldMapper.validate_esp32_data(valid_esp32_data)
    validation2_result, validation2_issues = ESP32FieldMapper.validate_esp32_data(invalid_esp32_data)

    print(f"[TEST] Valid data: {validation1_result} (issues: {validation1_issues})")
    print(f"[TEST] Invalid data: {validation2_result} (issues: {validation2_issues})")

    if validation1_result and not validation2_result:
        print("[RESULT] [OK] PASS - Validation methods working correctly")
    else:
        print("[RESULT] [FAIL] - Validation failed")
        all_tests_passed = False

    # Summary
    print("\n" + "="*80)
    if all_tests_passed:
        print("[SUCCESS] ALL ESP32 FIELD MAPPER TESTS PASSED")
        print("="*80)
        print("\nThe ESP32FieldMapper is working correctly:")
        print("  [OK] ESP32 lowercase to Backend camelCase transformation")
        print("  [OK] Backend camelCase to ESP32 lowercase transformation")
        print("  [OK] Device registration data transformation")
        print("  [OK] Heartbeat data transformation")
        print("  [OK] Door scanner data transformation")
        print("  [OK] Recursive nested data transformation")
        print("  [OK] Validation methods working")
        return True
    else:
        print("[FAILED] SOME ESP32 FIELD MAPPER TESTS FAILED")
        print("="*80)
        return False

if __name__ == "__main__":
    success = test_esp32_field_mapper()
    sys.exit(0 if success else 1)
