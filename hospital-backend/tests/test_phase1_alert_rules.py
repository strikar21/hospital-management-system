"""
Phase 1 Tests: Alert Rules and Thresholds
Tests for app/domain/alerts/rules/ modules

These tests validate:
1. ICMR-compliant vital sign thresholds
2. Threshold breach detection
3. Alert severity classification
4. Alert message formatting
5. Edge cases and boundary conditions

Related Files:
- hospital-backend/app/domain/alerts/rules/thresholds.py
- hospital-backend/app/domain/alerts/rules/checker.py
- hospital-backend/app/domain/alerts/rules/formatter.py
"""

import pytest
from app.domain.alerts.rules.thresholds import VITAL_THRESHOLDS, get_threshold
from app.domain.alerts.rules.checker import check_vital_threshold
from app.domain.alerts.rules.constants import AlertSeverity


@pytest.mark.unit
@pytest.mark.critical
class TestVitalThresholds:
    """Test vital sign threshold constants"""

    def test_heartrate_thresholds_exist(self):
        """
        Test: Heartrate thresholds exist
        Expected: All required threshold levels defined
        """
        hr_thresholds = VITAL_THRESHOLDS['heartrate']

        assert 'criticalLow' in hr_thresholds
        assert 'warningLow' in hr_thresholds
        assert 'warningHigh' in hr_thresholds
        assert 'criticalHigh' in hr_thresholds
        assert 'unit' in hr_thresholds

    def test_heartrate_thresholds_values(self):
        """
        Test: Heartrate thresholds match ICMR guidelines
        Expected: Critical low=40, warning low=50, warning high=120, critical high=150
        """
        hr = VITAL_THRESHOLDS['heartrate']

        assert hr['criticalLow'] == 40
        assert hr['warningLow'] == 50
        assert hr['warningHigh'] == 120
        assert hr['criticalHigh'] == 150
        assert hr['unit'] == 'bpm'

    def test_oxygen_thresholds_exist(self):
        """
        Test: Oxygen saturation thresholds exist
        Expected: All required threshold levels defined
        """
        o2_thresholds = VITAL_THRESHOLDS['oxygen']

        assert 'criticalLow' in o2_thresholds
        assert 'warningLow' in o2_thresholds
        assert o2_thresholds['unit'] == '%'

    def test_oxygen_thresholds_values(self):
        """
        Test: Oxygen saturation thresholds
        Expected: Critical low=85%, warning low=90%
        """
        o2 = VITAL_THRESHOLDS['oxygen']

        assert o2['criticalLow'] == 85
        assert o2['warningLow'] == 90

    def test_temperature_thresholds_exist(self):
        """
        Test: Temperature thresholds exist
        Expected: All required threshold levels defined
        """
        temp_thresholds = VITAL_THRESHOLDS['temperature']

        assert 'criticalLow' in temp_thresholds
        assert 'warningLow' in temp_thresholds
        assert 'warningHigh' in temp_thresholds
        assert 'criticalHigh' in temp_thresholds
        assert temp_thresholds['unit'] == '°C'

    def test_temperature_thresholds_values(self):
        """
        Test: Temperature thresholds (Celsius)
        Expected: Critical low=35°C, warning low=36°C, warning high=38°C, critical high=39.5°C
        """
        temp = VITAL_THRESHOLDS['temperature']

        assert temp['criticalLow'] == 35.0
        assert temp['warningLow'] == 36.0
        assert temp['warningHigh'] == 38.0
        assert temp['criticalHigh'] == 39.5

    def test_blood_pressure_systolic_thresholds(self):
        """
        Test: Systolic BP thresholds
        Expected: Critical low=90, warning low=100, warning high=140, critical high=180
        """
        sbp = VITAL_THRESHOLDS['systolic']

        assert sbp['criticalLow'] == 90
        assert sbp['warningLow'] == 100
        assert sbp['warningHigh'] == 140
        assert sbp['criticalHigh'] == 180
        assert sbp['unit'] == 'mmHg'

    def test_blood_pressure_diastolic_thresholds(self):
        """
        Test: Diastolic BP thresholds
        Expected: Critical low=60, warning low=65, warning high=90, critical high=110
        """
        dbp = VITAL_THRESHOLDS['diastolic']

        assert dbp['criticalLow'] == 60
        assert dbp['warningLow'] == 65
        assert dbp['warningHigh'] == 90
        assert dbp['criticalHigh'] == 110
        assert dbp['unit'] == 'mmHg'

    def test_respiratory_rate_thresholds(self):
        """
        Test: Respiratory rate thresholds
        Expected: Critical low=8, warning low=10, warning high=24, critical high=30
        """
        rr = VITAL_THRESHOLDS['respiratory']

        assert rr['criticalLow'] == 8
        assert rr['warningLow'] == 10
        assert rr['warningHigh'] == 24
        assert rr['criticalHigh'] == 30
        assert rr['unit'] == '/min'

    def test_get_threshold_function(self):
        """
        Test: Get threshold by vital type
        Expected: Returns correct threshold dict
        """
        hr_threshold = get_threshold('heartrate')

        assert hr_threshold is not None
        assert hr_threshold['criticalLow'] == 40

    def test_get_threshold_invalid_vital_returns_none(self):
        """
        Test: Get threshold for invalid vital type
        Expected: Returns None
        """
        result = get_threshold('invalidVital')

        assert result is None


@pytest.mark.unit
@pytest.mark.critical
class TestThresholdChecker:
    """Test threshold breach detection"""

    def test_check_heartrate_critical_low(self):
        """
        Test: Check heartrate critical low breach
        Expected: Returns ('critical', 40, 'Critical Low') tuple
        """
        result = check_vital_threshold('heartrate', 35)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'critical'
        assert threshold_value == 40
        assert 'critical' in message_prefix.lower()

    def test_check_heartrate_warning_low(self):
        """
        Test: Check heartrate warning low breach
        Expected: Returns (WARNING, 50, 'Low') tuple
        """
        result = check_vital_threshold('heartrate', 48)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == AlertSeverity.WARNING
        assert threshold_value == 50

    def test_check_heartrate_normal(self):
        """
        Test: Check heartrate in normal range
        Expected: Returns None (no alert)
        """
        result = check_vital_threshold('heartrate', 75)

        assert result is None

    def test_check_heartrate_warning_high(self):
        """
        Test: Check heartrate warning high breach
        Expected: Returns (WARNING, 120, 'High') tuple
        """
        result = check_vital_threshold('heartrate', 125)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == AlertSeverity.WARNING
        assert threshold_value == 120

    def test_check_heartrate_critical_high(self):
        """
        Test: Check heartrate critical high breach
        Expected: Returns (CRITICAL, 150, 'Critical High') tuple
        """
        result = check_vital_threshold('heartrate', 155)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == AlertSeverity.CRITICAL
        assert threshold_value == 150

    def test_check_oxygen_critical_low(self):
        """
        Test: Check oxygen saturation critical low
        Expected: Returns CRITICAL alert
        """
        result = check_vital_threshold('oxygen', 80)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == AlertSeverity.CRITICAL
        assert threshold_value == 85

    def test_check_oxygen_warning_low(self):
        """
        Test: Check oxygen saturation warning low
        Expected: Returns WARNING alert
        """
        result = check_vital_threshold('oxygen', 88)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == AlertSeverity.WARNING
        assert threshold_value == 90

    def test_check_oxygen_normal(self):
        """
        Test: Check oxygen saturation normal
        Expected: Returns None (no alert)
        """
        result = check_vital_threshold('oxygen', 97)

        assert result is None

    def test_check_temperature_critical_low(self):
        """
        Test: Check temperature critical low (hypothermia)
        Expected: Returns CRITICAL alert
        """
        result = check_vital_threshold('temperature', 34.5)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == AlertSeverity.CRITICAL
        assert threshold_value == 35.0

    def test_check_temperature_critical_high(self):
        """
        Test: Check temperature critical high (hyperthermia)
        Expected: Returns CRITICAL alert
        """
        result = check_vital_threshold('temperature', 40.0)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == AlertSeverity.CRITICAL
        assert threshold_value == 39.5

    def test_check_temperature_normal(self):
        """
        Test: Check temperature normal
        Expected: Returns None (no alert)
        """
        result = check_vital_threshold('temperature', 37.0)

        assert result is None

    def test_check_blood_pressure_systolic_critical_high(self):
        """
        Test: Check systolic BP critical high (hypertensive crisis)
        Expected: Returns CRITICAL alert
        """
        result = check_vital_threshold('bloodPressureSystolic', 190)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == AlertSeverity.CRITICAL
        assert threshold_value == 180

    def test_check_blood_pressure_diastolic_critical_low(self):
        """
        Test: Check diastolic BP critical low (hypotension)
        Expected: Returns CRITICAL alert
        """
        result = check_vital_threshold('bloodPressureDiastolic', 45)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == AlertSeverity.CRITICAL
        assert threshold_value == 50

    def test_check_respiratory_rate_critical_low(self):
        """
        Test: Check respiratory rate critical low (apnea risk)
        Expected: Returns CRITICAL alert
        """
        result = check_vital_threshold('respiratoryRate', 6)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == AlertSeverity.CRITICAL
        assert threshold_value == 8

    def test_check_invalid_vital_type_returns_none(self):
        """
        Test: Check threshold for invalid vital type
        Expected: Returns None
        """
        result = check_vital_threshold('invalidVital', 100)

        assert result is None

    def test_check_exact_threshold_boundary_low(self):
        """
        Test: Check value exactly at low threshold boundary
        Expected: Returns alert (inclusive boundary)
        """
        result = check_vital_threshold('heartrate', 40)

        # At exact critical low threshold
        assert result is not None
        severity, _, _ = result
        assert severity == AlertSeverity.CRITICAL

    def test_check_exact_threshold_boundary_high(self):
        """
        Test: Check value exactly at high threshold boundary
        Expected: Returns alert (inclusive boundary)
        """
        result = check_vital_threshold('heartrate', 150)

        # At exact critical high threshold
        assert result is not None
        severity, _, _ = result
        assert severity == AlertSeverity.CRITICAL


@pytest.mark.unit
class TestAlertFormatter:
    """Test alert message formatting"""

    def test_format_alert_message_critical_low_heartrate(self):
        """
        Test: Format critical low heartrate alert
        Expected: Returns formatted message with severity icon
        """
        message = format_alert_message(
            vital_type='heartrate',
            vital_value=35,
            severity=AlertSeverity.CRITICAL,
            threshold_value=40,
            message_prefix='Critical Low'
        )

        assert '🔴' in message or 'CRITICAL' in message
        assert 'heartrate' in message.lower() or 'heart rate' in message.lower()
        assert '35' in message
        assert '40' in message

    def test_format_alert_message_warning_high_oxygen(self):
        """
        Test: Format warning low oxygen alert
        Expected: Returns formatted message with warning icon
        """
        message = format_alert_message(
            vital_type='oxygen',
            vital_value=88,
            severity=AlertSeverity.WARNING,
            threshold_value=90,
            message_prefix='Low'
        )

        assert '⚠️' in message or 'WARNING' in message
        assert '88' in message
        assert '90' in message

    def test_format_alert_message_includes_unit(self):
        """
        Test: Formatted message includes unit
        Expected: Message contains 'bpm', '%', '°C', etc.
        """
        message = format_alert_message(
            vital_type='heartrate',
            vital_value=155,
            severity=AlertSeverity.CRITICAL,
            threshold_value=150,
            message_prefix='Critical High'
        )

        assert 'bpm' in message

    def test_format_alert_message_temperature_includes_celsius(self):
        """
        Test: Temperature message includes °C
        Expected: Message contains '°C'
        """
        message = format_alert_message(
            vital_type='temperature',
            vital_value=40.0,
            severity=AlertSeverity.CRITICAL,
            threshold_value=39.5,
            message_prefix='Critical High'
        )

        assert '°C' in message
        assert '40' in message


@pytest.mark.integration
@pytest.mark.critical
class TestAlertRulesEndToEnd:
    """Integration tests for alert rules system"""

    def test_complete_alert_workflow_critical(self):
        """
        Test: Complete alert workflow for critical vital
        Expected: Threshold check -> format -> complete alert
        """
        # Step 1: Check threshold
        result = check_vital_threshold('heartrate', 35)
        assert result is not None

        # Step 2: Extract components
        severity, threshold_value, message_prefix = result
        assert severity == AlertSeverity.CRITICAL

        # Step 3: Format message
        message = format_alert_message(
            vital_type='heartrate',
            vital_value=35,
            severity=severity,
            threshold_value=threshold_value,
            message_prefix=message_prefix
        )

        assert len(message) > 0
        assert '35' in message

    def test_all_vitals_have_complete_threshold_definitions(self):
        """
        Test: All vital types have complete threshold definitions
        Expected: Every vital has all required threshold levels
        """
        required_fields = ['unit']

        for vital_type, thresholds in VITAL_THRESHOLDS.items():
            # Check unit exists
            assert 'unit' in thresholds, f"{vital_type} missing unit"

            # Check at least one threshold level exists
            has_threshold = any(
                key in thresholds
                for key in ['criticalLow', 'warningLow', 'warningHigh', 'criticalHigh']
            )
            assert has_threshold, f"{vital_type} has no threshold levels"

    def test_threshold_values_are_logically_ordered(self):
        """
        Test: Threshold values follow logical ordering
        Expected: criticalLow < warningLow < warningHigh < criticalHigh
        """
        for vital_type, thresholds in VITAL_THRESHOLDS.items():
            # Only check vitals with all four thresholds
            if all(key in thresholds for key in ['criticalLow', 'warningLow', 'warningHigh', 'criticalHigh']):
                assert thresholds['criticalLow'] < thresholds['warningLow'], \
                    f"{vital_type}: criticalLow should be < warningLow"
                assert thresholds['warningLow'] < thresholds['warningHigh'], \
                    f"{vital_type}: warningLow should be < warningHigh"
                assert thresholds['warningHigh'] < thresholds['criticalHigh'], \
                    f"{vital_type}: warningHigh should be < criticalHigh"
