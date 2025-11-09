"""
P0 CRITICAL TESTS: Database Interval Functions
Tests the SQL interval syntax fixes in database.py

These tests verify that the make_interval() fix resolves the SQL syntax errors
that were causing 240+ errors per minute in production.

Test Coverage:
- getHistoricalVitals() - Historical vitals query with interval
- getVitalsTimeBuckets() - Time-bucketed vitals aggregation
- countPatientsWithCondition() - Fever and SpO2 declining detection
- countRecentAdmissions() - Recent admission counting
"""

import pytest
from datetime import datetime, timedelta
from app.core.database import (
    getHistoricalVitals,
    getVitalsTimeBuckets,
    countPatientsWithCondition,
    countRecentAdmissions
)


@pytest.mark.asyncio
@pytest.mark.critical
class TestDatabaseIntervalFunctions:
    """Critical tests for SQL interval syntax fixes"""

    async def test_getHistoricalVitals_valid_interval(self, test_patient_id):
        """
        Test: getHistoricalVitals with make_interval() syntax
        Expected: No SQL syntax errors, returns list (empty or with data)

        This validates the fix from:
        INTERVAL '%s hours' → make_interval(hours => $3)
        """
        if not test_patient_id:
            pytest.skip("No test patients in database")

        result = await getHistoricalVitals(
            patientId=test_patient_id,
            vitalType='heartRate',
            hoursBack=24
        )

        # Should return a list (empty if no data, populated if data exists)
        assert isinstance(result, list)
        # If data exists, validate structure
        if result:
            assert 'timestamp' in result[0]
            assert 'value' in result[0]

    async def test_getHistoricalVitals_fractional_hours(self, test_patient_id):
        """
        Test: Fractional hours (0.5 = 30 minutes)
        Expected: Query executes without error

        Validates parameter binding works with float values
        """
        if not test_patient_id:
            pytest.skip("No test patients in database")

        result = await getHistoricalVitals(
            patientId=test_patient_id,
            vitalType='oxygenSaturation',
            hoursBack=0.5  # 30 minutes
        )

        assert isinstance(result, list)

    async def test_getHistoricalVitals_no_sql_syntax_error(self):
        """
        Test: Query with non-existent patient
        Expected: Returns empty list, NOT SQL syntax error

        Before fix: Would raise SQL syntax error
        After fix: Returns [] gracefully
        """
        result = await getHistoricalVitals(
            patientId='NONEXISTENT_PATIENT',
            vitalType='heartRate',
            hoursBack=1
        )

        assert result == []

    async def test_getVitalsTimeBuckets_valid_interval(self, test_patient_id):
        """
        Test: getVitalsTimeBuckets with make_interval() syntax
        Expected: No SQL syntax errors

        This validates the fix from:
        INTERVAL '%s hours' → make_interval(hours => $4)
        """
        if not test_patient_id:
            pytest.skip("No test patients in database")

        result = await getVitalsTimeBuckets(
            patientId=test_patient_id,
            vitalType='heartRate',
            hoursBack=24,
            bucketMinutes=5
        )

        assert isinstance(result, list)
        # If data exists, validate time bucket structure
        if result:
            assert 'bucket' in result[0]
            assert 'avgValue' in result[0] or 'avgvalue' in result[0]

    async def test_getVitalsTimeBuckets_different_bucket_sizes(self, test_patient_id):
        """
        Test: Different time bucket sizes
        Expected: All execute without SQL errors
        """
        if not test_patient_id:
            pytest.skip("No test patients in database")

        bucket_sizes = [1, 5, 15, 60]  # 1min, 5min, 15min, 1hour

        for bucket_minutes in bucket_sizes:
            result = await getVitalsTimeBuckets(
                patientId=test_patient_id,
                vitalType='temperature',
                hoursBack=12,
                bucketMinutes=bucket_minutes
            )
            assert isinstance(result, list)

    async def test_countPatientsWithCondition_fever(self):
        """
        Test: Fever condition query with make_interval(mins => $2)
        Expected: Returns integer count (0 or more)

        Validates fix from:
        INTERVAL '%s minutes' → make_interval(mins => $2)
        """
        result = await countPatientsWithCondition(
            wardId=None,  # All wards
            condition='fever',
            timeWindowMinutes=60
        )

        assert isinstance(result, int)
        assert result >= 0

    async def test_countPatientsWithCondition_spo2_declining(self):
        """
        Test: SpO2 declining condition query
        Expected: Returns integer count

        Validates complex window function query with make_interval()
        """
        result = await countPatientsWithCondition(
            wardId=None,
            condition='spo2_declining',
            timeWindowMinutes=30
        )

        assert isinstance(result, int)
        assert result >= 0

    async def test_countPatientsWithCondition_invalid_condition(self):
        """
        Test: Invalid condition type
        Expected: Returns 0 (graceful handling)
        """
        result = await countPatientsWithCondition(
            wardId=None,
            condition='invalid_condition',
            timeWindowMinutes=60
        )

        assert result == 0

    async def test_countRecentAdmissions_valid_interval(self):
        """
        Test: Recent admissions query with make_interval()
        Expected: Returns integer count

        Validates fix from:
        INTERVAL '%s hours' → make_interval(hours => $1)
        """
        result = await countRecentAdmissions(hoursBack=24)

        assert isinstance(result, int)
        assert result >= 0

    async def test_countRecentAdmissions_different_time_windows(self):
        """
        Test: Different time windows for admission counting
        Expected: All execute without SQL errors
        """
        time_windows = [1, 6, 12, 24, 48, 168]  # 1hr to 1 week

        for hours in time_windows:
            result = await countRecentAdmissions(hoursBack=hours)
            assert isinstance(result, int)
            assert result >= 0

    @pytest.mark.slow
    async def test_all_interval_queries_performance(self, test_patient_id):
        """
        Test: All interval queries complete in reasonable time
        Expected: Each query < 1 second (should be much faster)

        Performance validation for production readiness
        """
        if not test_patient_id:
            pytest.skip("No test patients in database")

        import time

        # Test getHistoricalVitals performance
        start = time.time()
        await getHistoricalVitals(test_patient_id, 'heartRate', 24)
        duration = time.time() - start
        assert duration < 1.0, f"getHistoricalVitals took {duration:.2f}s (> 1s threshold)"

        # Test getVitalsTimeBuckets performance
        start = time.time()
        await getVitalsTimeBuckets(test_patient_id, 'heartRate', 24, 5)
        duration = time.time() - start
        assert duration < 1.0, f"getVitalsTimeBuckets took {duration:.2f}s (> 1s threshold)"

        # Test countPatientsWithCondition performance
        start = time.time()
        await countPatientsWithCondition(None, 'fever', 60)
        duration = time.time() - start
        assert duration < 1.0, f"countPatientsWithCondition took {duration:.2f}s (> 1s threshold)"

        # Test countRecentAdmissions performance
        start = time.time()
        await countRecentAdmissions(24)
        duration = time.time() - start
        assert duration < 1.0, f"countRecentAdmissions took {duration:.2f}s (> 1s threshold)"


# Summary test - validates all critical fixes
@pytest.mark.asyncio
@pytest.mark.critical
async def test_sql_interval_fixes_complete():
    """
    SUMMARY TEST: All SQL interval syntax fixes working

    This test validates that all 5 fixed functions execute without
    SQL syntax errors. Success here means the 240+ errors/min issue is resolved.
    """
    # Function 1: getHistoricalVitals (fixed line 679)
    result1 = await getHistoricalVitals('TEST001', 'heartRate', 24)
    assert isinstance(result1, list)

    # Function 2: getVitalsTimeBuckets (fixed line 718)
    result2 = await getVitalsTimeBuckets('TEST001', 'heartRate', 24, 5)
    assert isinstance(result2, list)

    # Function 3: countPatientsWithCondition - fever (fixed line 794)
    result3 = await countPatientsWithCondition(None, 'fever', 60)
    assert isinstance(result3, int)

    # Function 4: countPatientsWithCondition - spo2 (fixed line 808)
    result4 = await countPatientsWithCondition(None, 'spo2_declining', 60)
    assert isinstance(result4, int)

    # Function 5: countRecentAdmissions (fixed line 839)
    result5 = await countRecentAdmissions(24)
    assert isinstance(result5, int)

    # All functions executed without SQL syntax errors
    print("\n✅ All 5 SQL interval fixes validated")
    print(f"  - getHistoricalVitals: OK")
    print(f"  - getVitalsTimeBuckets: OK")
    print(f"  - countPatientsWithCondition (fever): OK")
    print(f"  - countPatientsWithCondition (spo2): OK")
    print(f"  - countRecentAdmissions: OK")
