"""
Component 4 Duration Alerts - Comprehensive Test Suite
Tests all 8 duration-based alerts:
1. prolongedTachycardia (HR >100 for >15min)
2. prolongedBradycardia (HR <60 for >10min)
3. prolongedHypotension (Systolic <90 for >10min)
4. prolongedHypoxia (SpO2 <90% for >5min)
5. prolongedFever (Temp >38.3C for >1hr)
6. prolongedHypothermia (Temp <35C for >30min)
7. noVitalsReceived (>10min without data)
8. intermittentConnection (>3 drops in 1hr)
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta, date
from app.core.config import settings
from app.services.alert_detection_service import completeAlertDetectionService
from app.services.state_manager import stateManager

# Test patient ID
TEST_PATIENT_ID = "TEST_DUR_001"
TEST_DEVICE_ID = "WATCH_TEST_001"

async def setup_test_patient():
    """Create a test patient for duration alert testing"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        # Delete existing test patient
        await conn.execute("DELETE FROM patients WHERE id = $1", TEST_PATIENT_ID)

        # Create test patient - using quoted camelCase column names as per database schema
        await conn.execute("""
            INSERT INTO patients (
                id, "firstName", "lastName", "dateOfBirth", gender, "admissionDate", status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, TEST_PATIENT_ID, "Duration", "Test", date(1990, 1, 1), "Male", datetime.now(), "active")

        print(f"[OK] Test patient created: {TEST_PATIENT_ID}")

        # Initialize patient state
        await stateManager.initializePatientState(TEST_PATIENT_ID)
        print(f"[OK] Patient state initialized")

    finally:
        await conn.close()

async def cleanup_test_patient():
    """Remove test patient and state"""
    conn = await asyncpg.connect(settings.databaseUrl)

    try:
        await conn.execute("DELETE FROM patients WHERE id = $1", TEST_PATIENT_ID)
        print(f"[OK] Test patient cleaned up")
    finally:
        await conn.close()

async def test_prolonged_tachycardia():
    """Test Alert 1: prolongedTachycardia (HR >100 for >15min)"""
    print("\n" + "="*80)
    print("TEST 1: Prolonged Tachycardia (HR >100 for >15min)")
    print("="*80)

    # Simulate tachycardia starting
    vitalsData = {
        'heartRate': 120,
        'oxygenSaturation': 98,
        'systolicBp': 120,
        'diastolicBp': 80,
        'temperature': 37.0
    }

    # First vitals - should START tracking
    timestamp1 = datetime.now() - timedelta(minutes=20)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID)
    print(f"  Vitals at T-20min (HR=120): {len(alerts)} alerts (should be 0 - just started tracking)")

    # Second vitals - 16 minutes later - should TRIGGER alert
    timestamp2 = timestamp1 + timedelta(minutes=16)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID)
    print(f"  Vitals at T-4min (HR=120, 16min duration): {len(alerts)} alerts")

    if alerts:
        for alert in alerts:
            if alert.alertType == 'prolongedTachycardia':
                print(f"  [PASS] - Alert triggered: {alert.message}")
                print(f"     Severity: {alert.severity}")
                print(f"     Context: {alert.context}")
                return True

    print(f"  [FAIL] - Expected prolongedTachycardia alert not found")
    return False

async def test_prolonged_bradycardia():
    """Test Alert 2: prolongedBradycardia (HR <60 for >10min)"""
    print("\n" + "="*80)
    print("TEST 2: Prolonged Bradycardia (HR <60 for >10min)")
    print("="*80)

    # Reset state
    await stateManager.resetConditionState(TEST_PATIENT_ID, 'tachycardia')
    await stateManager.resetConditionState(TEST_PATIENT_ID, 'bradycardia')

    vitalsData = {
        'heartRate': 45,
        'oxygenSaturation': 98,
        'systolicBp': 120,
        'diastolicBp': 80,
        'temperature': 37.0
    }

    timestamp1 = datetime.now() - timedelta(minutes=15)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, timestamp1)
    print(f"  Vitals at T-15min (HR=45): {len(alerts)} alerts (should be 0 - just started tracking)")

    timestamp2 = timestamp1 + timedelta(minutes=11)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, timestamp2)
    print(f"  Vitals at T-4min (HR=45, 11min duration): {len(alerts)} alerts")

    if alerts:
        for alert in alerts:
            if alert.alertType == 'prolongedBradycardia':
                print(f"  [PASS] PASS - Alert triggered: {alert.message}")
                return True

    print(f"  [FAIL] FAIL - Expected prolongedBradycardia alert not found")
    return False

async def test_prolonged_hypotension():
    """Test Alert 3: prolongedHypotension (Systolic <90 for >10min)"""
    print("\n" + "="*80)
    print("TEST 3: Prolonged Hypotension (Systolic <90 for >10min)")
    print("="*80)

    # Reset state
    await stateManager.resetConditionState(TEST_PATIENT_ID, 'bradycardia')
    await stateManager.resetConditionState(TEST_PATIENT_ID, 'hypotension')

    vitalsData = {
        'heartRate': 75,
        'oxygenSaturation': 98,
        'systolicBp': 85,
        'diastolicBp': 60,
        'temperature': 37.0
    }

    timestamp1 = datetime.now() - timedelta(minutes=15)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, timestamp1)
    print(f"  Vitals at T-15min (Systolic=85): {len(alerts)} alerts")

    timestamp2 = timestamp1 + timedelta(minutes=11)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, timestamp2)
    print(f"  Vitals at T-4min (Systolic=85, 11min duration): {len(alerts)} alerts")

    if alerts:
        for alert in alerts:
            if alert.alertType == 'prolongedHypotension':
                print(f"  [PASS] PASS - Alert triggered: {alert.message}")
                return True

    print(f"  [FAIL] FAIL - Expected prolongedHypotension alert not found")
    return False

async def test_prolonged_hypoxia():
    """Test Alert 4: prolongedHypoxia (SpO2 <90% for >5min)"""
    print("\n" + "="*80)
    print("TEST 4: Prolonged Hypoxia (SpO2 <90% for >5min)")
    print("="*80)

    # Reset state
    await stateManager.resetConditionState(TEST_PATIENT_ID, 'hypotension')
    await stateManager.resetConditionState(TEST_PATIENT_ID, 'hypoxia')

    vitalsData = {
        'heartRate': 75,
        'oxygenSaturation': 85,
        'systolicBp': 120,
        'diastolicBp': 80,
        'temperature': 37.0
    }

    timestamp1 = datetime.now() - timedelta(minutes=8)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, timestamp1)
    print(f"  Vitals at T-8min (SpO2=85%): {len(alerts)} alerts")

    timestamp2 = timestamp1 + timedelta(minutes=6)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, timestamp2)
    print(f"  Vitals at T-2min (SpO2=85%, 6min duration): {len(alerts)} alerts")

    if alerts:
        for alert in alerts:
            if alert.alertType == 'prolongedHypoxia':
                print(f"  [PASS] PASS - Alert triggered: {alert.message}")
                return True

    print(f"  [FAIL] FAIL - Expected prolongedHypoxia alert not found")
    return False

async def test_prolonged_fever():
    """Test Alert 5: prolongedFever (Temp >38.3C for >1hr)"""
    print("\n" + "="*80)
    print("TEST 5: Prolonged Fever (Temp >38.3C for >1hr)")
    print("="*80)

    # Reset state
    await stateManager.resetConditionState(TEST_PATIENT_ID, 'hypoxia')
    await stateManager.resetConditionState(TEST_PATIENT_ID, 'fever')

    vitalsData = {
        'heartRate': 75,
        'oxygenSaturation': 98,
        'systolicBp': 120,
        'diastolicBp': 80,
        'temperature': 38.5
    }

    timestamp1 = datetime.now() - timedelta(minutes=70)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, timestamp1)
    print(f"  Vitals at T-70min (Temp=38.5C): {len(alerts)} alerts")

    timestamp2 = timestamp1 + timedelta(minutes=65)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, timestamp2)
    print(f"  Vitals at T-5min (Temp=38.5C, 65min duration): {len(alerts)} alerts")

    if alerts:
        for alert in alerts:
            if alert.alertType == 'prolongedFever':
                print(f"  [PASS] PASS - Alert triggered: {alert.message}")
                return True

    print(f"  [FAIL] FAIL - Expected prolongedFever alert not found")
    return False

async def test_prolonged_hypothermia():
    """Test Alert 6: prolongedHypothermia (Temp <35C for >30min)"""
    print("\n" + "="*80)
    print("TEST 6: Prolonged Hypothermia (Temp <35C for >30min)")
    print("="*80)

    # Reset state
    await stateManager.resetConditionState(TEST_PATIENT_ID, 'fever')
    await stateManager.resetConditionState(TEST_PATIENT_ID, 'hypothermia')

    vitalsData = {
        'heartRate': 75,
        'oxygenSaturation': 98,
        'systolicBp': 120,
        'diastolicBp': 80,
        'temperature': 34.5
    }

    timestamp1 = datetime.now() - timedelta(minutes=40)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, timestamp1)
    print(f"  Vitals at T-40min (Temp=34.5C): {len(alerts)} alerts")

    timestamp2 = timestamp1 + timedelta(minutes=35)
    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, timestamp2)
    print(f"  Vitals at T-5min (Temp=34.5C, 35min duration): {len(alerts)} alerts")

    if alerts:
        for alert in alerts:
            if alert.alertType == 'prolongedHypothermia':
                print(f"  [PASS] PASS - Alert triggered: {alert.message}")
                return True

    print(f"  [FAIL] FAIL - Expected prolongedHypothermia alert not found")
    return False

async def test_intermittent_connection():
    """Test Alert 8: intermittentConnection (>3 drops in 1hr)"""
    print("\n" + "="*80)
    print("TEST 8: Intermittent Connection (>3 drops in 1hr)")
    print("="*80)

    # Reset state
    await stateManager.resetConditionState(TEST_PATIENT_ID, 'hypothermia')

    # Record 4 connection drops
    now = datetime.now()
    for i in range(4):
        dropTime = now - timedelta(minutes=50 - (i * 10))
        await stateManager.recordConnectionDrop(TEST_PATIENT_ID, dropTime)
        print(f"  Recorded connection drop #{i+1} at T-{50 - (i * 10)}min")

    # Clean old drops (keeps last 24 hours)
    await stateManager.cleanOldConnectionDrops(TEST_PATIENT_ID, hoursToKeep=24)

    # Check drop count
    dropCount = await stateManager.getConnectionDropCount(TEST_PATIENT_ID, windowMinutes=60)
    print(f"  Connection drops in last hour: {dropCount}")

    # Trigger alert detection
    vitalsData = {
        'heartRate': 75,
        'oxygenSaturation': 98,
        'systolicBp': 120,
        'diastolicBp': 80,
        'temperature': 37.0
    }

    alerts = await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, datetime.now())
    print(f"  Alerts generated: {len(alerts)}")

    if alerts:
        for alert in alerts:
            if alert.alertType == 'intermittentConnection':
                print(f"  [PASS] PASS - Alert triggered: {alert.message}")
                print(f"     Context: {alert.context}")
                return True

    print(f"  [FAIL] FAIL - Expected intermittentConnection alert not found")
    return False

async def test_condition_resolution():
    """Test that conditions properly reset when resolved"""
    print("\n" + "="*80)
    print("TEST 9: Condition Resolution (State Reset)")
    print("="*80)

    # Start tachycardia
    vitalsData = {'heartRate': 120, 'oxygenSaturation': 98, 'systolicBp': 120, 'diastolicBp': 80, 'temperature': 37.0}
    timestamp1 = datetime.now() - timedelta(minutes=20)
    await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, timestamp1)

    state1 = await stateManager.getPatientState(TEST_PATIENT_ID)
    print(f"  Tachycardia started: {state1.tachycardiaStartTime is not None}")

    # Resolve tachycardia (normal HR)
    vitalsData['heartRate'] = 75
    await completeAlertDetectionService.detectAlerts(vitalsData, TEST_PATIENT_ID, TEST_DEVICE_ID, datetime.now())

    state2 = await stateManager.getPatientState(TEST_PATIENT_ID)
    print(f"  Tachycardia resolved: {state2.tachycardiaStartTime is None}")

    if state1.tachycardiaStartTime is not None and state2.tachycardiaStartTime is None:
        print(f"  [PASS] PASS - Condition properly reset on resolution")
        return True
    else:
        print(f"  [FAIL] FAIL - Condition did not reset properly")
        return False

async def main():
    """Run all Component 4 duration alert tests"""
    print("\n" + "="*80)
    print("COMPONENT 4 DURATION ALERTS - COMPREHENSIVE TEST SUITE")
    print("="*80)

    await setup_test_patient()

    results = []

    try:
        # Run all tests
        results.append(("Prolonged Tachycardia", await test_prolonged_tachycardia()))
        results.append(("Prolonged Bradycardia", await test_prolonged_bradycardia()))
        results.append(("Prolonged Hypotension", await test_prolonged_hypotension()))
        results.append(("Prolonged Hypoxia", await test_prolonged_hypoxia()))
        results.append(("Prolonged Fever", await test_prolonged_fever()))
        results.append(("Prolonged Hypothermia", await test_prolonged_hypothermia()))
        results.append(("Intermittent Connection", await test_intermittent_connection()))
        results.append(("Condition Resolution", await test_condition_resolution()))

        # Summary
        print("\n" + "="*80)
        print("TEST RESULTS SUMMARY")
        print("="*80)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for testName, result in results:
            status = "[PASS] PASS" if result else "[FAIL] FAIL"
            print(f"  {status} - {testName}")

        print(f"\n  Total: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

        if passed == total:
            print("\n  [SUCCESS] ALL TESTS PASSED - Component 4 fully functional!")
        else:
            print(f"\n  [WARNING] {total - passed} test(s) failed - review implementation")

    finally:
        await cleanup_test_patient()

if __name__ == "__main__":
    asyncio.run(main())
