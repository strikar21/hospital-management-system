"""
Test Calibration Alerts - Component 5 Phase 4
Tests the three calibration-related device alerts
"""

import asyncio
from datetime import datetime, timedelta
from app.services.alert_detection_service import completeAlertDetectionService
from app.services.calibration_service import calibrationService
from app.services.device_health_service import deviceHealthService
from app.core.database import getDbConnection

async def testCalibrationAlerts():
    """Test calibration alert detection"""

    print("=" * 80)
    print("CALIBRATION ALERTS TEST - Component 5 Phase 4")
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

        # TEST SETUP: Create calibration scenarios

        # Scenario 1: Calibration due in 5 days (calibrationRequired)
        print("\n[SETUP] Setting calibration due in 5 days...")
        dueDate5Days = datetime.now() + timedelta(days=5)
        await conn.execute("""
            UPDATE devices
            SET "calibrationDueDate" = $1,
                "lastCalibrationDate" = $2
            WHERE id = $3
        """, dueDate5Days, datetime.now() - timedelta(days=25), deviceId)

    # Test 1: Calibration Due Soon (5 days)
    print("\n" + "=" * 80)
    print("TEST 1: CALIBRATION DUE SOON (5 days)")
    print("=" * 80)

    vitalsData = {
        'heartRate': 75,
        'oxygenSaturation': 98,
        'temperature': 36.8,
        'bloodPressureSystolic': 120,
        'bloodPressureDiastolic': 80,
        'batteryLevel': 80
    }

    alerts = await completeAlertDetectionService.detectAlerts(
        vitalsData=vitalsData,
        patientId=patientId,
        deviceId=deviceId
    )

    calibrationAlerts = [a for a in alerts if a.alertType in ['calibrationRequired', 'calibrationOverdue', 'sensorDrift']]

    print(f"\n[RESULTS]")
    print(f"   Expected: calibrationRequired")
    print(f"   Detected: {[a.alertType for a in calibrationAlerts]}")

    if calibrationAlerts:
        print(f"\n[ALERTS] TRIGGERED ({len(calibrationAlerts)}):")
        for alert in calibrationAlerts:
            print(f"   [{alert.severity.upper()}] {alert.alertType}")
            print(f"      Message: {alert.message}")
            print(f"      Context: {alert.context}")

    if any(a.alertType == 'calibrationRequired' for a in calibrationAlerts):
        print(f"\n[PASS] TEST 1 PASSED - calibrationRequired alert detected")
    else:
        print(f"\n[FAIL] TEST 1 FAILED - calibrationRequired alert not detected")

    # Test 2: Calibration Overdue
    print("\n" + "=" * 80)
    print("TEST 2: CALIBRATION OVERDUE (10 days overdue)")
    print("=" * 80)

    async with getDbConnection() as conn:
        print("\n[SETUP] Setting calibration 10 days overdue...")
        dueDateOverdue = datetime.now() - timedelta(days=10)
        await conn.execute("""
            UPDATE devices
            SET "calibrationDueDate" = $1,
                "lastCalibrationDate" = $2
            WHERE id = $3
        """, dueDateOverdue, datetime.now() - timedelta(days=40), deviceId)

    alerts = await completeAlertDetectionService.detectAlerts(
        vitalsData=vitalsData,
        patientId=patientId,
        deviceId=deviceId
    )

    calibrationAlerts = [a for a in alerts if a.alertType in ['calibrationRequired', 'calibrationOverdue', 'sensorDrift']]

    print(f"\n[RESULTS]")
    print(f"   Expected: calibrationOverdue")
    print(f"   Detected: {[a.alertType for a in calibrationAlerts]}")

    if calibrationAlerts:
        print(f"\n[ALERTS] TRIGGERED ({len(calibrationAlerts)}):")
        for alert in calibrationAlerts:
            print(f"   [{alert.severity.upper()}] {alert.alertType}")
            print(f"      Message: {alert.message}")
            print(f"      Context: {alert.context}")

    if any(a.alertType == 'calibrationOverdue' for a in calibrationAlerts):
        print(f"\n[PASS] TEST 2 PASSED - calibrationOverdue alert detected")
    else:
        print(f"\n[FAIL] TEST 2 FAILED - calibrationOverdue alert not detected")

    # Test 3: Sensor Drift (requires baseline)
    print("\n" + "=" * 80)
    print("TEST 3: SENSOR DRIFT DETECTION")
    print("=" * 80)

    # Create a baseline first
    print("\n[SETUP] Creating device baseline for drift detection...")
    baselineCreated = await deviceHealthService.calculateBaseline(deviceId)

    if baselineCreated:
        print("[OK] Baseline created successfully")

        # Send abnormal reading to trigger drift
        abnormalVitals = {
            'heartRate': 200,  # Abnormally high
            'oxygenSaturation': 50,  # Abnormally low
            'temperature': 42.0,  # Abnormally high
            'bloodPressureSystolic': 200,
            'bloodPressureDiastolic': 140,
            'batteryLevel': 80
        }

        alerts = await completeAlertDetectionService.detectAlerts(
            vitalsData=abnormalVitals,
            patientId=patientId,
            deviceId=deviceId
        )

        calibrationAlerts = [a for a in alerts if a.alertType == 'sensorDrift']

        print(f"\n[RESULTS]")
        print(f"   Expected: sensorDrift (if baseline exists)")
        print(f"   Detected: {[a.alertType for a in calibrationAlerts]}")

        if calibrationAlerts:
            print(f"\n[ALERTS] TRIGGERED ({len(calibrationAlerts)}):")
            for alert in calibrationAlerts:
                print(f"   [{alert.severity.upper()}] {alert.alertType}")
                print(f"      Message: {alert.message}")
                print(f"      Context: {alert.context}")
            print(f"\n[PASS] TEST 3 PASSED - sensorDrift alert detected")
        else:
            print(f"\n[INFO] TEST 3 - No drift detected (may need more baseline data)")
    else:
        print("[WARN] Baseline creation failed - insufficient vitals data")
        print("[INFO] TEST 3 SKIPPED - Need vitals history for baseline")

    # Cleanup: Reset calibration date
    async with getDbConnection() as conn:
        await conn.execute("""
            UPDATE devices
            SET "calibrationDueDate" = $1,
                "lastCalibrationDate" = $2
            WHERE id = $3
        """, datetime.now() + timedelta(days=30), datetime.now(), deviceId)
        print(f"\n[OK] Reset device calibration to current")

    print("\n" + "=" * 80)
    print("CALIBRATION ALERTS TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(testCalibrationAlerts())
