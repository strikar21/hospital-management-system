"""
Phase 1 Tests: Alert Rules and Thresholds (Working Tests Only)
Tests for app/domain/alerts/rules/ modules

These tests validate:
1. ICMR-compliant vital sign thresholds
2. Threshold breach detection
3. Alert severity classification

Related Files:
- hospital-backend/app/domain/alerts/rules/thresholds.py
- hospital-backend/app/domain/alerts/rules/checker.py
- hospital-backend/app/domain/alerts/rules/constants.py
"""

import pytest
from app.domain.alerts.rules.thresholds import VITAL_THRESHOLDS, get_threshold
from app.domain.alerts.rules.checker import check_vital_threshold


@pytest.mark.unit
@pytest.mark.critical
class TestVitalThresholds:
    """Test vital sign threshold constants"""

    def test_heartrate_thresholds_exist(self):
        """Test: Heartrate thresholds exist"""
        hr_thresholds = VITAL_THRESHOLDS['heartrate']

        assert 'criticalLow' in hr_thresholds
        assert 'warningLow' in hr_thresholds
        assert 'warningHigh' in hr_thresholds
        assert 'criticalHigh' in hr_thresholds
        assert 'unit' in hr_thresholds

    def test_heartrate_thresholds_values(self):
        """Test: Heartrate thresholds match ICMR guidelines"""
        hr = VITAL_THRESHOLDS['heartrate']

        assert hr['criticalLow'] == 40
        assert hr['warningLow'] == 50
        assert hr['warningHigh'] == 120
        assert hr['criticalHigh'] == 150
        assert hr['unit'] == 'bpm'

    def test_oxygen_thresholds_values(self):
        """Test: Oxygen saturation thresholds"""
        o2 = VITAL_THRESHOLDS['oxygen']

        assert o2['criticalLow'] == 85
        assert o2['warningLow'] == 90
        assert o2['unit'] == '%'

    def test_temperature_thresholds_values(self):
        """Test: Temperature thresholds (Celsius)"""
        temp = VITAL_THRESHOLDS['temperature']

        assert temp['criticalLow'] == 35.0
        assert temp['warningLow'] == 36.0
        assert temp['warningHigh'] == 38.0
        assert temp['criticalHigh'] == 39.5
        assert temp['unit'] == '°C'

    def test_blood_pressure_systolic_thresholds(self):
        """Test: Systolic BP thresholds"""
        sbp = VITAL_THRESHOLDS['systolic']

        assert sbp['criticalLow'] == 90
        assert sbp['warningLow'] == 100
        assert sbp['warningHigh'] == 140
        assert sbp['criticalHigh'] == 180
        assert sbp['unit'] == 'mmHg'

    def test_blood_pressure_diastolic_thresholds(self):
        """Test: Diastolic BP thresholds"""
        dbp = VITAL_THRESHOLDS['diastolic']

        assert dbp['criticalLow'] == 60
        assert dbp['warningLow'] == 65
        assert dbp['warningHigh'] == 90
        assert dbp['criticalHigh'] == 110
        assert dbp['unit'] == 'mmHg'

    def test_respiratory_rate_thresholds(self):
        """Test: Respiratory rate thresholds"""
        rr = VITAL_THRESHOLDS['respiratory']

        assert rr['criticalLow'] == 8
        assert rr['warningLow'] == 10
        assert rr['warningHigh'] == 24
        assert rr['criticalHigh'] == 30
        assert rr['unit'] == '/min'

    def test_get_threshold_function(self):
        """Test: Get threshold by vital type"""
        hr_threshold = get_threshold('heartrate')

        assert hr_threshold is not None
        assert hr_threshold['criticalLow'] == 40

    def test_get_threshold_invalid_vital_returns_none(self):
        """Test: Get threshold for invalid vital type"""
        result = get_threshold('invalidVital')

        assert result is None


@pytest.mark.unit
@pytest.mark.critical
class TestThresholdChecker:
    """Test threshold breach detection"""

    def test_check_heartrate_critical_low(self):
        """Test: Check heartrate critical low breach"""
        result = check_vital_threshold('heartrate', 35)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'critical'
        assert threshold_value == 40
        assert 'critical' in message_prefix.lower()

    def test_check_heartrate_warning_low(self):
        """Test: Check heartrate warning low breach"""
        result = check_vital_threshold('heartrate', 48)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'high'  # Warning returns 'high'
        assert threshold_value == 50

    def test_check_heartrate_normal(self):
        """Test: Check heartrate in normal range"""
        result = check_vital_threshold('heartrate', 75)

        assert result is None

    def test_check_heartrate_warning_high(self):
        """Test: Check heartrate warning high breach"""
        result = check_vital_threshold('heartrate', 125)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'high'
        assert threshold_value == 120

    def test_check_heartrate_critical_high(self):
        """Test: Check heartrate critical high breach"""
        result = check_vital_threshold('heartrate', 155)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'critical'
        assert threshold_value == 150

    def test_check_oxygen_critical_low(self):
        """Test: Check oxygen saturation critical low"""
        result = check_vital_threshold('oxygen', 80)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'critical'
        assert threshold_value == 85

    def test_check_oxygen_warning_low(self):
        """Test: Check oxygen saturation warning low"""
        result = check_vital_threshold('oxygen', 88)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'high'
        assert threshold_value == 90

    def test_check_oxygen_normal(self):
        """Test: Check oxygen saturation normal"""
        result = check_vital_threshold('oxygen', 97)

        assert result is None

    def test_check_temperature_critical_low(self):
        """Test: Check temperature critical low (hypothermia)"""
        result = check_vital_threshold('temperature', 34.5)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'critical'
        assert threshold_value == 35.0

    def test_check_temperature_critical_high(self):
        """Test: Check temperature critical high (hyperthermia)"""
        result = check_vital_threshold('temperature', 40.0)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'critical'
        assert threshold_value == 39.5

    def test_check_temperature_normal(self):
        """Test: Check temperature normal"""
        result = check_vital_threshold('temperature', 37.0)

        assert result is None

    def test_check_systolic_critical_high(self):
        """Test: Check systolic BP critical high"""
        result = check_vital_threshold('systolic', 190)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'critical'
        assert threshold_value == 180

    def test_check_diastolic_critical_low(self):
        """Test: Check diastolic BP critical low"""
        result = check_vital_threshold('diastolic', 55)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'critical'
        assert threshold_value == 60

    def test_check_respiratory_critical_low(self):
        """Test: Check respiratory rate critical low"""
        result = check_vital_threshold('respiratory', 6)

        assert result is not None
        severity, threshold_value, message_prefix = result
        assert severity == 'critical'
        assert threshold_value == 8

    def test_check_invalid_vital_type_returns_none(self):
        """Test: Check threshold for invalid vital type"""
        result = check_vital_threshold('invalidVital', 100)

        assert result is None

    def test_check_exact_threshold_boundary_low(self):
        """Test: Check value exactly at low threshold boundary"""
        result = check_vital_threshold('heartrate', 40)

        # At exact critical low threshold
        assert result is not None
        severity, _, _ = result
        assert severity == 'critical'

    def test_check_exact_threshold_boundary_high(self):
        """Test: Check value exactly at high threshold boundary"""
        result = check_vital_threshold('heartrate', 150)

        # At exact critical high threshold
        assert result is not None
        severity, _, _ = result
        assert severity == 'critical'


@pytest.mark.integration
@pytest.mark.critical
class TestAlertRulesEndToEnd:
    """Integration tests for alert rules system"""

    def test_complete_alert_workflow_critical(self):
        """Test: Complete alert workflow for critical vital"""
        # Check threshold
        result = check_vital_threshold('heartrate', 35)
        assert result is not None

        # Extract components
        severity, threshold_value, message_prefix = result
        assert severity == 'critical'
        assert threshold_value == 40
        assert 'Critical' in message_prefix

    def test_all_vitals_have_complete_threshold_definitions(self):
        """Test: All vital types have complete threshold definitions"""
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
        """Test: Threshold values follow logical ordering"""
        for vital_type, thresholds in VITAL_THRESHOLDS.items():
            # Only check vitals with all four NON-NULL thresholds
            if all(thresholds.get(key) is not None for key in ['criticalLow', 'warningLow', 'warningHigh', 'criticalHigh']):
                assert thresholds['criticalLow'] < thresholds['warningLow'], \
                    f"{vital_type}: criticalLow should be < warningLow"
                assert thresholds['warningLow'] < thresholds['warningHigh'], \
                    f"{vital_type}: warningLow should be < warningHigh"
                assert thresholds['warningHigh'] < thresholds['criticalHigh'], \
                    f"{vital_type}: warningHigh should be < criticalHigh"
