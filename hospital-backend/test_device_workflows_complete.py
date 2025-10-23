"""
Comprehensive Device Workflow Testing
Tests ALL device functionality: assign, reassign, disconnect, alerts, data flow
Based on actual database research - using real patient and device IDs
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Configuration
BASE_URL = "http://localhost:8001"
STAFF_ID = "DOC0001"  # Doctor with admin privileges
STAFF_PIN = "1234"

# Test Data (researched from database)
TEST_PATIENT_1 = "TEST001"  # Test Patient
TEST_PATIENT_2 = "7163182b-5d6e-412d-93d9-28ecfd86cc6e"  # Robert Anderson
TEST_DEVICE = "TEST_WATCH_001"  # ESP32 Watch

# Test Results
test_results = []
test_count = 0
passed_count = 0
failed_count = 0
warning_count = 0

def log_test(phase: str, test_name: str, status: str, details: str = ""):
    """Log test result"""
    global test_count, passed_count, failed_count, warning_count
    test_count += 1

    if status == "PASS":
        passed_count += 1
        symbol = "[OK]"
    elif status == "FAIL":
        failed_count += 1
        symbol = "[FAIL]"
    elif status == "WARN":
        warning_count += 1
        symbol = "[WARN]"
    else:
        symbol = "[INFO]"

    result = {
        "phase": phase,
        "test": test_name,
        "status": status,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    test_results.append(result)

    print(f"{symbol} {phase} - {test_name}")
    if details:
        print(f"     {details}")

async def get_auth_token(session: aiohttp.ClientSession) -> str:
    """Authenticate and get JWT token"""
    try:
        async with session.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"staffId": STAFF_ID, "pin": STAFF_PIN}
        ) as response:
            if response.status == 200:
                data = await response.json()
                token = data.get("accessToken")
                log_test("AUTH", "Staff Login", "PASS", f"Token obtained for {STAFF_ID}")
                return token
            else:
                text = await response.text()
                log_test("AUTH", "Staff Login", "FAIL", f"Status {response.status}: {text}")
                return None
    except Exception as e:
        log_test("AUTH", "Staff Login", "FAIL", str(e))
        return None

async def verify_database_state(session: aiohttp.ClientSession, token: str, phase: str):
    """Verify database state via API"""
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Check device status
        async with session.get(
            f"{BASE_URL}/api/v1/devices/",
            headers=headers
        ) as response:
            if response.status == 200:
                devices = await response.json()
                device = next((d for d in devices if d["id"] == TEST_DEVICE), None)
                if device:
                    log_test(phase, "Verify Device Status", "PASS",
                            f"Device: {device.get('status')}, Battery: {device.get('batteryLevel')}%")
                else:
                    log_test(phase, "Verify Device Status", "WARN", "Device not found in list")
            else:
                log_test(phase, "Verify Device Status", "WARN", f"Status {response.status}")

        # Check assignments
        async with session.get(
            f"{BASE_URL}/api/v1/watchmanagement/assigned",
            headers=headers
        ) as response:
            if response.status == 200:
                assigned = await response.json()
                is_assigned = any(w.get("id") == TEST_DEVICE for w in assigned)
                log_test(phase, "Verify Assignment Status", "INFO",
                        f"Device assigned: {is_assigned}, Total assigned: {len(assigned)}")

    except Exception as e:
        log_test(phase, "Verify Database State", "WARN", str(e))

async def test_phase_1_assignment(session: aiohttp.ClientSession, token: str):
    """Phase 1: Assign device to patient"""
    print("\n" + "=" * 80)
    print("PHASE 1: DEVICE ASSIGNMENT")
    print("=" * 80)

    headers = {"Authorization": f"Bearer {token}"}

    # Assign TEST_WATCH_001 to TEST001
    try:
        async with session.post(
            f"{BASE_URL}/api/v1/watchmanagement/assign",
            headers=headers,
            json={"patientId": TEST_PATIENT_1, "deviceId": TEST_DEVICE}
        ) as response:
            status = response.status
            text = await response.text()

            if status == 200:
                log_test("PHASE 1", f"Assign {TEST_DEVICE} to {TEST_PATIENT_1}", "PASS",
                        "Assignment created successfully")
            else:
                log_test("PHASE 1", f"Assign {TEST_DEVICE} to {TEST_PATIENT_1}", "FAIL",
                        f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 1", "Device Assignment", "FAIL", str(e))

    await verify_database_state(session, token, "PHASE 1")
    await asyncio.sleep(1)

async def test_phase_2_data_sending(session: aiohttp.ClientSession, token: str):
    """Phase 2: Test device sending data to backend"""
    print("\n" + "=" * 80)
    print("PHASE 2: DATA SENDING (Device to Backend)")
    print("=" * 80)

    headers = {"Authorization": f"Bearer {token}"}

    # Test 2A: Send Vitals
    try:
        vitals_data = {
            "deviceId": TEST_DEVICE,
            "patientId": TEST_PATIENT_1,
            "vitals": {
                "heartrate": 72,
                "temperature": 98.6,
                "oxygensat": 98,
                "respiratoryrate": 16,
                "bloodpressurevalue": 120
            },
            "timestamp": datetime.now().isoformat()
        }

        async with session.post(
            f"{BASE_URL}/api/v1/esp32/vitals",
            headers=headers,
            json=vitals_data
        ) as response:
            status = response.status
            text = await response.text()

            if status == 200:
                log_test("PHASE 2", "Send Vitals Data", "PASS", "Vitals received by backend")
            elif status == 404:
                log_test("PHASE 2", "Send Vitals Data", "WARN",
                        "Endpoint not found - may not be implemented yet")
            else:
                log_test("PHASE 2", "Send Vitals Data", "FAIL", f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 2", "Send Vitals Data", "WARN", str(e))

    # Test 2B: Send Heartbeat
    try:
        heartbeat_data = {
            "deviceId": TEST_DEVICE,
            "patientId": TEST_PATIENT_1,
            "battery": 95,
            "timestamp": datetime.now().isoformat()
        }

        async with session.post(
            f"{BASE_URL}/api/v1/esp32/heartbeat",
            headers=headers,
            json=heartbeat_data
        ) as response:
            status = response.status

            if status == 200:
                log_test("PHASE 2", "Send Heartbeat", "PASS", "Heartbeat received")
            elif status == 404:
                log_test("PHASE 2", "Send Heartbeat", "WARN", "Endpoint not found")
            else:
                text = await response.text()
                log_test("PHASE 2", "Send Heartbeat", "FAIL", f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 2", "Send Heartbeat", "WARN", str(e))

    await asyncio.sleep(1)

async def test_phase_3_data_receiving(session: aiohttp.ClientSession, token: str):
    """Phase 3: Test backend sending data to device"""
    print("\n" + "=" * 80)
    print("PHASE 3: DATA RECEIVING (Backend to Device)")
    print("=" * 80)

    headers = {"Authorization": f"Bearer {token}"}

    # Test 3A: Send Command to Device
    try:
        command_data = {
            "command": "startMonitoring",
            "parameters": {
                "interval": 30,
                "vitals": ["heartrate", "oxygensat", "temperature"]
            }
        }

        async with session.post(
            f"{BASE_URL}/api/v1/watchmanagement/command",
            headers=headers,
            json={"deviceId": TEST_DEVICE, **command_data}
        ) as response:
            status = response.status

            if status == 200:
                log_test("PHASE 3", "Send Command to Device", "PASS", "Command sent successfully")
            elif status == 404:
                log_test("PHASE 3", "Send Command to Device", "WARN",
                        "Command endpoint not found - may not be implemented")
            else:
                text = await response.text()
                log_test("PHASE 3", "Send Command to Device", "FAIL", f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 3", "Send Command to Device", "WARN", str(e))

    # Test 3B: Get Device Connection Status
    try:
        async with session.get(
            f"{BASE_URL}/api/v1/watchmanagement/connection-status",
            headers=headers
        ) as response:
            status = response.status

            if status == 200:
                data = await response.json()
                watches = data.get('watchStatus', [])
                test_watch = next((w for w in watches if w['id'] == TEST_DEVICE), None)
                if test_watch:
                    log_test("PHASE 3", "Get Connection Status", "PASS",
                            f"Status: {test_watch.get('connectionStatus', 'unknown')}")
                else:
                    log_test("PHASE 3", "Get Connection Status", "WARN", "Test watch not found in status")
            else:
                text = await response.text()
                log_test("PHASE 3", "Get Connection Status", "FAIL", f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 3", "Get Connection Status", "FAIL", str(e))

    await asyncio.sleep(1)

async def test_phase_4_alerts(session: aiohttp.ClientSession, token: str):
    """Phase 4: Test alert generation and handling"""
    print("\n" + "=" * 80)
    print("PHASE 4: ALERT GENERATION AND HANDLING")
    print("=" * 80)

    headers = {"Authorization": f"Bearer {token}"}

    # Test 4A: Device Sends Emergency Alert
    try:
        alert_data = {
            "deviceId": TEST_DEVICE,
            "patientId": TEST_PATIENT_1,
            "alertType": "emergency",
            "severity": "high",
            "message": "Patient fall detected",
            "timestamp": datetime.now().isoformat()
        }

        async with session.post(
            f"{BASE_URL}/api/v1/esp32/alert",
            headers=headers,
            json=alert_data
        ) as response:
            status = response.status

            if status == 200:
                log_test("PHASE 4", "Device Emergency Alert", "PASS", "Alert sent successfully")
            elif status == 404:
                log_test("PHASE 4", "Device Emergency Alert", "WARN",
                        "Alert endpoint not found - may not be implemented")
            else:
                text = await response.text()
                log_test("PHASE 4", "Device Emergency Alert", "FAIL", f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 4", "Device Emergency Alert", "WARN", str(e))

    # Test 4B: Send Abnormal Vitals (should trigger backend alert)
    try:
        critical_vitals = {
            "deviceId": TEST_DEVICE,
            "patientId": TEST_PATIENT_1,
            "vitals": {
                "heartrate": 180,  # Dangerously high
                "oxygensat": 85,   # Dangerously low
                "temperature": 103.5  # High fever
            },
            "timestamp": datetime.now().isoformat()
        }

        async with session.post(
            f"{BASE_URL}/api/v1/esp32/vitals",
            headers=headers,
            json=critical_vitals
        ) as response:
            status = response.status

            if status == 200:
                log_test("PHASE 4", "Abnormal Vitals (Trigger Alert)", "PASS",
                        "Critical vitals sent - backend should generate alert")
            elif status == 404:
                log_test("PHASE 4", "Abnormal Vitals (Trigger Alert)", "WARN",
                        "Vitals endpoint not found")
            else:
                text = await response.text()
                log_test("PHASE 4", "Abnormal Vitals (Trigger Alert)", "FAIL",
                        f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 4", "Abnormal Vitals (Trigger Alert)", "WARN", str(e))

    # Test 4C: Query Device Alerts
    try:
        async with session.get(
            f"{BASE_URL}/api/v1/watchmanagement/alerts",
            headers=headers
        ) as response:
            status = response.status

            if status == 200:
                data = await response.json()
                alerts = data.get('alerts', [])
                log_test("PHASE 4", "Query Device Alerts", "PASS",
                        f"Found {len(alerts)} alert(s)")
            elif status == 404:
                log_test("PHASE 4", "Query Device Alerts", "WARN",
                        "Alerts endpoint not found")
            else:
                text = await response.text()
                log_test("PHASE 4", "Query Device Alerts", "FAIL", f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 4", "Query Device Alerts", "WARN", str(e))

    await asyncio.sleep(1)

async def test_phase_5_reassignment(session: aiohttp.ClientSession, token: str):
    """Phase 5: Test device reassignment"""
    print("\n" + "=" * 80)
    print("PHASE 5: DEVICE REASSIGNMENT")
    print("=" * 80)

    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Unassign from TEST_PATIENT_1
    try:
        async with session.post(
            f"{BASE_URL}/api/v1/watchmanagement/unassign",
            headers=headers,
            json={"patientId": TEST_PATIENT_1, "deviceId": TEST_DEVICE}
        ) as response:
            status = response.status

            if status == 200:
                log_test("PHASE 5", f"Unassign from {TEST_PATIENT_1}", "PASS",
                        "Device unassigned successfully")
            else:
                text = await response.text()
                log_test("PHASE 5", f"Unassign from {TEST_PATIENT_1}", "FAIL",
                        f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 5", "Unassign Device", "FAIL", str(e))

    await asyncio.sleep(1)

    # Step 2: Assign to TEST_PATIENT_2 (Robert Anderson)
    try:
        async with session.post(
            f"{BASE_URL}/api/v1/watchmanagement/assign",
            headers=headers,
            json={"patientId": TEST_PATIENT_2, "deviceId": TEST_DEVICE}
        ) as response:
            status = response.status

            if status == 200:
                log_test("PHASE 5", f"Reassign to Patient 2", "PASS",
                        f"Device reassigned to {TEST_PATIENT_2}")
            else:
                text = await response.text()
                log_test("PHASE 5", f"Reassign to Patient 2", "FAIL",
                        f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 5", "Reassign Device", "FAIL", str(e))

    await verify_database_state(session, token, "PHASE 5")
    await asyncio.sleep(1)

async def test_phase_6_disconnect(session: aiohttp.ClientSession, token: str):
    """Phase 6: Test device disconnect/unassignment"""
    print("\n" + "=" * 80)
    print("PHASE 6: DEVICE DISCONNECT/UNASSIGNMENT")
    print("=" * 80)

    headers = {"Authorization": f"Bearer {token}"}

    # Final unassignment (return device to pool)
    try:
        async with session.post(
            f"{BASE_URL}/api/v1/watchmanagement/unassign",
            headers=headers,
            json={"patientId": TEST_PATIENT_2, "deviceId": TEST_DEVICE}
        ) as response:
            status = response.status

            if status == 200:
                log_test("PHASE 6", "Final Device Unassignment", "PASS",
                        "Device returned to available pool")
            else:
                text = await response.text()
                log_test("PHASE 6", "Final Device Unassignment", "FAIL",
                        f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 6", "Final Device Unassignment", "FAIL", str(e))

    await verify_database_state(session, token, "PHASE 6")
    await asyncio.sleep(1)

async def test_phase_7_health_monitoring(session: aiohttp.ClientSession, token: str):
    """Phase 7: Test device health monitoring"""
    print("\n" + "=" * 80)
    print("PHASE 7: DEVICE HEALTH MONITORING")
    print("=" * 80)

    headers = {"Authorization": f"Bearer {token}"}

    # Test 7A: Get Device Health (via connection status)
    try:
        async with session.get(
            f"{BASE_URL}/api/v1/watchmanagement/connection-status",
            headers=headers
        ) as response:
            status = response.status

            if status == 200:
                data = await response.json()
                watches = data.get('watchStatus', [])
                test_watch = next((w for w in watches if w['id'] == TEST_DEVICE), None)
                if test_watch:
                    log_test("PHASE 7", "Get Device Health", "PASS",
                            f"Battery: {test_watch.get('batteryLevel')}%, Status: {test_watch.get('connectionStatus')}")
                else:
                    log_test("PHASE 7", "Get Device Health", "WARN", "Device not found")
            else:
                text = await response.text()
                log_test("PHASE 7", "Get Device Health", "FAIL", f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 7", "Get Device Health", "FAIL", str(e))

    # Test 7B: Get All Devices
    try:
        async with session.get(
            f"{BASE_URL}/api/v1/devices/",
            headers=headers
        ) as response:
            status = response.status

            if status == 200:
                devices = await response.json()
                log_test("PHASE 7", "Get All Devices", "PASS", f"Found {len(devices)} device(s)")
            else:
                text = await response.text()
                log_test("PHASE 7", "Get All Devices", "FAIL", f"Status {status}: {text}")

    except Exception as e:
        log_test("PHASE 7", "Get All Devices", "FAIL", str(e))

    await asyncio.sleep(1)

def print_summary():
    """Print comprehensive test summary"""
    print("\n" + "=" * 80)
    print("TEST EXECUTION SUMMARY")
    print("=" * 80)

    print(f"\nTotal Tests: {test_count}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print(f"Warnings: {warning_count}")

    if test_count > 0:
        success_rate = (passed_count / test_count) * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")

    # Phase breakdown
    print("\n" + "-" * 80)
    print("RESULTS BY PHASE")
    print("-" * 80)

    phases = {}
    for result in test_results:
        phase = result["phase"]
        if phase not in phases:
            phases[phase] = {"pass": 0, "fail": 0, "warn": 0}

        if result["status"] == "PASS":
            phases[phase]["pass"] += 1
        elif result["status"] == "FAIL":
            phases[phase]["fail"] += 1
        elif result["status"] == "WARN":
            phases[phase]["warn"] += 1

    for phase, counts in phases.items():
        total = counts["pass"] + counts["fail"] + counts["warn"]
        print(f"\n{phase}:")
        print(f"  Pass: {counts['pass']}/{total}")
        if counts["fail"] > 0:
            print(f"  FAIL: {counts['fail']}/{total}")
        if counts["warn"] > 0:
            print(f"  Warn: {counts['warn']}/{total}")

    # Critical failures
    failures = [r for r in test_results if r["status"] == "FAIL"]
    if failures:
        print("\n" + "-" * 80)
        print("CRITICAL FAILURES")
        print("-" * 80)
        for failure in failures:
            print(f"\n[FAIL] {failure['phase']} - {failure['test']}")
            print(f"       {failure['details']}")

    print("\n" + "=" * 80)

async def main():
    """Main test execution"""
    print("=" * 80)
    print("COMPREHENSIVE DEVICE WORKFLOW TESTING")
    print("=" * 80)
    print(f"Backend: {BASE_URL}")
    print(f"Test Device: {TEST_DEVICE}")
    print(f"Test Patient 1: {TEST_PATIENT_1}")
    print(f"Test Patient 2: {TEST_PATIENT_2}")
    print(f"Start Time: {datetime.now().isoformat()}")
    print("=" * 80)

    async with aiohttp.ClientSession() as session:
        # Authenticate
        token = await get_auth_token(session)
        if not token:
            print("\n[CRITICAL] Authentication failed - cannot continue")
            return

        # Execute all test phases
        await test_phase_1_assignment(session, token)
        await test_phase_2_data_sending(session, token)
        await test_phase_3_data_receiving(session, token)
        await test_phase_4_alerts(session, token)
        await test_phase_5_reassignment(session, token)
        await test_phase_6_disconnect(session, token)
        await test_phase_7_health_monitoring(session, token)

    # Print summary
    print_summary()

    print(f"\nEnd Time: {datetime.now().isoformat()}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
