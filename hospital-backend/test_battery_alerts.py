"""
Test Battery Alerts - Component 5 Phase 3
Tests the three battery-related device alerts
"""

import asyncio
import sys
from datetime import datetime
from app.services.alert_detection_service import completeAlertDetectionService
from app.core.database import getDbConnection

async def testBatteryAlerts():
    """Test battery alert detection with various battery levels"""

    print("=" * 80)
    print("BATTERY ALERTS TEST - Component 5 Phase 3")
    print("=" * 80)

    # Get a real patient and device from database
    async with getDbConnection() as conn:
        patient = await conn.fetchrow("""
            SELECT da."patientId", da."deviceId"
            FROM deviceassignments da
            WHERE da.status = 'active'
            LIMIT 1
        """)

        if not patient:
            print("[ERROR] No patients with assigned devices found")
            return

        patientId = patient['patientId']
        deviceId = patient['deviceId']

        print(f"\n[INFO] Using Patient: {patientId}, Device: {deviceId}")

        # Set battery health to 60% to trigger degradation alert
        await conn.execute("""
            UPDATE devices
            SET "batteryHealthPercentage" = 60
            WHERE id = $1
        """, deviceId)
        print(f"[OK] Set device battery health to 60% for testing")

    # Test scenarios
    testCases = [
        {
            'name': 'CRITICAL BATTERY (5%)',
            'batteryLevel': 5,
            'expectedAlerts': ['criticalBatteryLevel', 'batteryDegradation']
        },
        {
            'name': 'LOW BATTERY (15%)',
            'batteryLevel': 15,
            'expectedAlerts': ['lowBatteryWarning', 'batteryDegradation']
        },
        {
            'name': 'NORMAL BATTERY (80%)',
            'batteryLevel': 80,
            'expectedAlerts': ['batteryDegradation']  # Only degradation due to 60% health
        },
        {
            'name': 'FULL BATTERY (100%)',
            'batteryLevel': 100,
            'expectedAlerts': ['batteryDegradation']  # Only degradation due to 60% health
        }
    ]

    for testCase in testCases:
        print(f"\n{'=' * 80}")
        print(f"TEST CASE: {testCase['name']}")
        print(f"{'=' * 80}")

        # Create vitals data with specific battery level
        vitalsData = {
            'heartRate': 75,
            'oxygenSaturation': 98,
            'temperature': 36.8,
            'bloodPressureSystolic': 120,
            'bloodPressureDiastolic': 80,
            'batteryLevel': testCase['batteryLevel']
        }

        # Detect alerts
        alerts = await completeAlertDetectionService.detectAlerts(
            vitalsData=vitalsData,
            patientId=patientId,
            deviceId=deviceId,
            accelerometerData=None
        )

        # Filter for battery-related alerts
        batteryAlertTypes = ['criticalBatteryLevel', 'lowBatteryWarning', 'batteryDegradation']
        batteryAlerts = [a for a in alerts if a.alertType in batteryAlertTypes]

        print(f"\n[RESULTS]")
        print(f"   Battery Level: {testCase['batteryLevel']}%")
        print(f"   Expected Alerts: {testCase['expectedAlerts']}")
        print(f"   Detected Alerts: {[a.alertType for a in batteryAlerts]}")

        if batteryAlerts:
            print(f"\n[ALERTS] TRIGGERED ({len(batteryAlerts)}):")
            for alert in batteryAlerts:
                print(f"   [{alert.severity.upper()}] {alert.alertType}")
                print(f"      Message: {alert.message}")
                print(f"      Context: {alert.context}")
        else:
            print("\n[OK] No battery alerts (as expected)")

        # Validation
        detectedTypes = [a.alertType for a in batteryAlerts]
        expectedSet = set(testCase['expectedAlerts'])
        detectedSet = set(detectedTypes)

        if expectedSet == detectedSet:
            print(f"\n[PASS] TEST PASSED - Correct alerts detected")
        else:
            print(f"\n[FAIL] TEST FAILED")
            print(f"   Missing: {expectedSet - detectedSet}")
            print(f"   Extra: {detectedSet - expectedSet}")

    # Restore battery health
    async with getDbConnection() as conn:
        await conn.execute("""
            UPDATE devices
            SET "batteryHealthPercentage" = 100
            WHERE id = $1
        """, deviceId)
        print(f"\n[OK] Restored device battery health to 100%")

    print("\n" + "=" * 80)
    print("BATTERY ALERTS TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(testBatteryAlerts())
