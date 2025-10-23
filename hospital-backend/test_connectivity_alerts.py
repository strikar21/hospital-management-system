"""
Test Connectivity Alerts - Component 5 Phase 5
Tests the three connectivity-related device alerts
"""

import asyncio
from datetime import datetime, timedelta
from app.services.alert_detection_service import completeAlertDetectionService
from app.core.database import getDbConnection

async def testConnectivityAlerts():
    """Test connectivity alert detection"""

    print("=" * 80)
    print("CONNECTIVITY ALERTS TEST - Component 5 Phase 5")
    print("=" * 80)

    # Get a real patient and device from database
    async with getDbConnection() as conn:
        assignment = await conn.fetchrow("""
            SELECT da."patientId", da."deviceId"
            FROM deviceassignments da
            WHERE da.status = 'active'
            LIMIT 1
        """)

        if not assignment:
            print("[ERROR] No patients with assigned devices found")
            return

        patientId = assignment['patientId']
        deviceId = assignment['deviceId']

        print(f"\n[INFO] Using Patient: {patientId}, Device: {deviceId}")

    vitalsData = {
        'heartRate': 75,
        'oxygenSaturation': 98,
        'temperature': 36.8,
        'bloodPressureSystolic': 120,
        'bloodPressureDiastolic': 80,
        'batteryLevel': 80
    }

    # Test 1: Frequent Disconnects
    print("\n" + "=" * 80)
    print("TEST 1: FREQUENT DISCONNECTS (10 disconnects)")
    print("=" * 80)

    async with getDbConnection() as conn:
        print("\n[SETUP] Setting disconnect count to 10...")
        await conn.execute("""
            UPDATE devices
            SET "totalDisconnects" = 10
            WHERE id = $1
        """, deviceId)

    alerts = await completeAlertDetectionService.detectAlerts(
        vitalsData=vitalsData,
        patientId=patientId,
        deviceId=deviceId
    )

    connectivityAlerts = [a for a in alerts if a.alertType in ['frequentDisconnects', 'deviceUnresponsive', 'firmwareUpdateRequired']]

    print(f"\n[RESULTS]")
    print(f"   Expected: frequentDisconnects")
    print(f"   Detected: {[a.alertType for a in connectivityAlerts]}")

    if connectivityAlerts:
        print(f"\n[ALERTS] TRIGGERED ({len(connectivityAlerts)}):")
        for alert in connectivityAlerts:
            print(f"   [{alert.severity.upper()}] {alert.alertType}")
            print(f"      Message: {alert.message}")
            print(f"      Context: {alert.context}")

    if any(a.alertType == 'frequentDisconnects' for a in connectivityAlerts):
        print(f"\n[PASS] TEST 1 PASSED - frequentDisconnects alert detected")
    else:
        print(f"\n[FAIL] TEST 1 FAILED - frequentDisconnects alert not detected")

    # Test 2: Device Unresponsive
    print("\n" + "=" * 80)
    print("TEST 2: DEVICE UNRESPONSIVE (15 minutes)")
    print("=" * 80)

    async with getDbConnection() as conn:
        print("\n[SETUP] Setting device as unresponsive...")
        # Set last command sent 15 minutes ago with no acknowledgment
        await conn.execute("""
            UPDATE devices
            SET "lastCommandSentAt" = $1,
                "lastCommandAckAt" = NULL
            WHERE id = $2
        """, datetime.now() - timedelta(minutes=15), deviceId)

    alerts = await completeAlertDetectionService.detectAlerts(
        vitalsData=vitalsData,
        patientId=patientId,
        deviceId=deviceId
    )

    connectivityAlerts = [a for a in alerts if a.alertType in ['frequentDisconnects', 'deviceUnresponsive', 'firmwareUpdateRequired']]

    print(f"\n[RESULTS]")
    print(f"   Expected: deviceUnresponsive (and possibly frequentDisconnects)")
    print(f"   Detected: {[a.alertType for a in connectivityAlerts]}")

    if connectivityAlerts:
        print(f"\n[ALERTS] TRIGGERED ({len(connectivityAlerts)}):")
        for alert in connectivityAlerts:
            print(f"   [{alert.severity.upper()}] {alert.alertType}")
            print(f"      Message: {alert.message}")
            print(f"      Context: {alert.context}")

    if any(a.alertType == 'deviceUnresponsive' for a in connectivityAlerts):
        print(f"\n[PASS] TEST 2 PASSED - deviceUnresponsive alert detected")
    else:
        print(f"\n[FAIL] TEST 2 FAILED - deviceUnresponsive alert not detected")

    # Test 3: Firmware Update Required
    print("\n" + "=" * 80)
    print("TEST 3: FIRMWARE UPDATE REQUIRED (v1.0.0)")
    print("=" * 80)

    async with getDbConnection() as conn:
        print("\n[SETUP] Setting outdated firmware version...")
        await conn.execute("""
            UPDATE devices
            SET "firmwareVersion" = '1.0.0'
            WHERE id = $1
        """, deviceId)

    alerts = await completeAlertDetectionService.detectAlerts(
        vitalsData=vitalsData,
        patientId=patientId,
        deviceId=deviceId
    )

    connectivityAlerts = [a for a in alerts if a.alertType == 'firmwareUpdateRequired']

    print(f"\n[RESULTS]")
    print(f"   Expected: firmwareUpdateRequired")
    print(f"   Detected: {[a.alertType for a in connectivityAlerts]}")

    if connectivityAlerts:
        print(f"\n[ALERTS] TRIGGERED ({len(connectivityAlerts)}):")
        for alert in connectivityAlerts:
            print(f"   [{alert.severity.upper()}] {alert.alertType}")
            print(f"      Message: {alert.message}")
            print(f"      Context: {alert.context}")
        print(f"\n[PASS] TEST 3 PASSED - firmwareUpdateRequired alert detected")
    else:
        print(f"\n[FAIL] TEST 3 FAILED - firmwareUpdateRequired alert not detected")

    # Cleanup
    async with getDbConnection() as conn:
        await conn.execute("""
            UPDATE devices
            SET "totalDisconnects" = 0,
                "lastCommandSentAt" = NULL,
                "lastCommandAckAt" = NULL,
                "firmwareVersion" = '2.1.0'
            WHERE id = $1
        """, deviceId)
        print(f"\n[OK] Reset device connectivity status")

    print("\n" + "=" * 80)
    print("CONNECTIVITY ALERTS TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(testConnectivityAlerts())
