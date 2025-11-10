"""
Phase 3 Tests: Vital Alert Generator
Tests for app/domain/alerts/generators/vital.py

These tests validate:
1. generate_vital_alert() creates correct alert records
2. Alert messages are human-readable
3. Severity levels are correct
4. Alerts include proper metadata
5. Normal vitals return None (no alert)

Related Files:
- hospital-backend/app/domain/alerts/generators/vital.py
- hospital-backend/app/domain/alerts/rules/checker.py
- hospital-backend/app/domain/alerts/rules/thresholds.py
"""

import pytest
from datetime import datetime
from app.domain.alerts.generators.vital import generate_vital_alert


@pytest.mark.unit
@pytest.mark.critical
class TestVitalAlertGenerator:
    """Test vital alert generation"""

    def test_generate_vital_alert_critical_low_heartrate(self):
        """
        Test: Generate alert for critically low heartrate
        Expected: Returns critical alert with proper message
        """
        result = generate_vital_alert(
            patient_id='test-patient-123',
            vital_type='heartrate',
            vital_value=35
        )

        assert result is not None
        assert isinstance(result, dict)

        # Check alert structure
        assert result['patientId'] == 'test-patient-123'
        assert result['type'] == 'vital'
        assert result['severity'] == 'critical'
        assert result['status'] == 'active'
        assert result['vitalType'] == 'heartrate'
        assert result['vitalValue'] == 35
        assert result['thresholdValue'] == 40

        # Check message format
        assert 'Heart Rate' in result['message']
        assert '35' in result['message']
        assert 'bpm' in result['message']
        assert 'Critical' in result['message']

    def test_generate_vital_alert_warning_high_heartrate(self):
        """
        Test: Generate alert for high heartrate (warning level)
        Expected: Returns warning alert
        """
        result = generate_vital_alert(
            patient_id='test-patient-456',
            vital_type='heartrate',
            vital_value=125
        )

        assert result is not None
        assert result['severity'] == 'high'  # Warning returns 'high'
        assert result['vitalValue'] == 125
        assert result['thresholdValue'] == 120

    def test_generate_vital_alert_normal_heartrate(self):
        """
        Test: Generate alert for normal heartrate
        Expected: Returns None (no alert)
        """
        result = generate_vital_alert(
            patient_id='test-patient-789',
            vital_type='heartrate',
            vital_value=75
        )

        assert result is None

    def test_generate_vital_alert_critical_low_oxygen(self):
        """
        Test: Generate alert for critically low oxygen
        Expected: Returns critical alert with oxygen-specific message
        """
        result = generate_vital_alert(
            patient_id='test-patient-123',
            vital_type='oxygen',
            vital_value=80
        )

        assert result is not None
        assert result['severity'] == 'critical'
        assert result['vitalType'] == 'oxygen'
        assert result['vitalValue'] == 80
        assert result['thresholdValue'] == 85

        # Check message contains oxygen saturation
        assert 'Oxygen' in result['message']
        assert '80' in result['message']
        assert '%' in result['message']

    def test_generate_vital_alert_critical_high_temperature(self):
        """
        Test: Generate alert for critically high temperature
        Expected: Returns critical alert with temperature-specific message
        """
        result = generate_vital_alert(
            patient_id='test-patient-123',
            vital_type='temperature',
            vital_value=40.0
        )

        assert result is not None
        assert result['severity'] == 'critical'
        assert result['vitalType'] == 'temperature'
        assert result['vitalValue'] == 40.0
        assert result['thresholdValue'] == 39.5

        # Check message
        assert 'Temperature' in result['message']
        assert '40' in result['message']
        assert '°C' in result['message']

    def test_generate_vital_alert_with_device_id(self):
        """
        Test: Generate alert with device ID
        Expected: Alert includes device ID in createdBy
        """
        result = generate_vital_alert(
            patient_id='test-patient-123',
            vital_type='heartrate',
            vital_value=155,
            device_id='ESP32-WATCH-001'
        )

        assert result is not None
        assert result['createdBy'] == 'ESP32-WATCH-001'

    def test_generate_vital_alert_without_device_id(self):
        """
        Test: Generate alert without device ID
        Expected: Alert uses 'system' as createdBy
        """
        result = generate_vital_alert(
            patient_id='test-patient-123',
            vital_type='heartrate',
            vital_value=155
        )

        assert result is not None
        assert result['createdBy'] == 'system'

    def test_generate_vital_alert_includes_timestamp(self):
        """
        Test: Generated alert includes timestamp
        Expected: createdAt is present and is datetime object
        """
        result = generate_vital_alert(
            patient_id='test-patient-123',
            vital_type='heartrate',
            vital_value=155
        )

        assert result is not None
        assert 'createdAt' in result
        assert isinstance(result['createdAt'], datetime)

    def test_generate_vital_alert_all_vital_types(self):
        """
        Test: Generate alerts for all vital types
        Expected: All vital types produce proper alerts
        """
        vital_tests = [
            ('heartrate', 35, 'Heart Rate', 'bpm'),
            ('oxygen', 80, 'Oxygen', '%'),
            ('temperature', 40.0, 'Temperature', '°C'),
            ('systolic', 190, 'Systolic BP', 'mmHg'),
            ('diastolic', 55, 'Diastolic BP', 'mmHg'),
            ('respiratory', 6, 'Respiratory Rate', '/min'),
        ]

        for vital_type, value, expected_name, expected_unit in vital_tests:
            result = generate_vital_alert(
                patient_id='test-patient',
                vital_type=vital_type,
                vital_value=value
            )

            assert result is not None, f"Failed for {vital_type}"
            assert result['vitalType'] == vital_type
            assert result['vitalValue'] == value
            assert expected_name in result['message']
            assert expected_unit in result['message']


@pytest.mark.unit
class TestVitalAlertMessageFormat:
    """Test alert message formatting"""

    def test_alert_message_includes_severity_prefix(self):
        """
        Test: Alert message includes severity prefix
        Expected: Message starts with 'Critical Low' or 'High', etc.
        """
        result = generate_vital_alert(
            patient_id='test-patient',
            vital_type='heartrate',
            vital_value=35
        )

        assert result is not None
        # Should have severity prefix like "Critical Low"
        assert result['message'].startswith('Critical')

    def test_alert_message_format_consistency(self):
        """
        Test: Alert messages follow consistent format
        Expected: Format is "{Severity} {VitalName}: {Value}{Unit}"
        """
        result = generate_vital_alert(
            patient_id='test-patient',
            vital_type='heartrate',
            vital_value=155
        )

        assert result is not None
        message = result['message']

        # Should contain: severity, vital name, value, unit
        assert 'Heart Rate' in message
        assert '155' in message
        assert 'bpm' in message
        assert ':' in message  # Format separator


@pytest.mark.unit
class TestVitalAlertRecordStructure:
    """Test alert record data structure"""

    def test_alert_record_has_all_required_fields(self):
        """
        Test: Alert record contains all required fields
        Expected: All fields present with correct types
        """
        result = generate_vital_alert(
            patient_id='test-patient',
            vital_type='heartrate',
            vital_value=35
        )

        assert result is not None

        # Required fields
        required_fields = [
            'id', 'patientId', 'type', 'severity', 'status',
            'message', 'vitalType', 'vitalValue', 'thresholdValue',
            'createdBy', 'createdAt'
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_alert_record_uses_camelcase(self):
        """
        Test: Alert record uses camelCase field names
        Expected: All fields are camelCase, not snake_case
        """
        result = generate_vital_alert(
            patient_id='test-patient',
            vital_type='heartrate',
            vital_value=35
        )

        assert result is not None

        # Check camelCase fields
        camelcase_fields = ['patientId', 'vitalType', 'vitalValue',
                            'thresholdValue', 'createdBy', 'createdAt']

        for field in camelcase_fields:
            assert field in result
            assert '_' not in field  # No snake_case

    def test_alert_type_is_always_vital(self):
        """
        Test: Alert type is always 'vital' for vital alerts
        Expected: type field is 'vital'
        """
        result = generate_vital_alert(
            patient_id='test-patient',
            vital_type='heartrate',
            vital_value=35
        )

        assert result is not None
        assert result['type'] == 'vital'

    def test_alert_status_is_always_active(self):
        """
        Test: Alert status is always 'active' for new alerts
        Expected: status field is 'active'
        """
        result = generate_vital_alert(
            patient_id='test-patient',
            vital_type='heartrate',
            vital_value=35
        )

        assert result is not None
        assert result['status'] == 'active'


@pytest.mark.integration
@pytest.mark.critical
class TestVitalAlertEndToEnd:
    """Integration tests for vital alert generation"""

    def test_complete_alert_workflow_critical(self):
        """
        Test: Complete workflow for critical vital
        Expected: Check threshold -> Generate alert -> Verify structure
        """
        # Critical low oxygen
        alert = generate_vital_alert(
            patient_id='patient-critical-001',
            vital_type='oxygen',
            vital_value=82,
            device_id='ESP32-WATCH-001'
        )

        # Should generate critical alert
        assert alert is not None
        assert alert['severity'] == 'critical'
        assert alert['patientId'] == 'patient-critical-001'
        assert alert['vitalType'] == 'oxygen'
        assert alert['vitalValue'] == 82
        assert alert['createdBy'] == 'ESP32-WATCH-001'

        # Message should be actionable
        assert 'Oxygen' in alert['message']
        assert '82' in alert['message']

    def test_complete_alert_workflow_warning(self):
        """
        Test: Complete workflow for warning-level vital
        Expected: Generates warning alert
        """
        # Warning high heartrate
        alert = generate_vital_alert(
            patient_id='patient-warning-001',
            vital_type='heartrate',
            vital_value=125
        )

        assert alert is not None
        assert alert['severity'] == 'high'
        assert alert['vitalType'] == 'heartrate'

    def test_complete_alert_workflow_normal(self):
        """
        Test: Complete workflow for normal vital
        Expected: No alert generated
        """
        # Normal vital
        alert = generate_vital_alert(
            patient_id='patient-normal-001',
            vital_type='heartrate',
            vital_value=75
        )

        assert alert is None

    def test_multiple_alerts_for_same_patient(self):
        """
        Test: Generate multiple alerts for same patient
        Expected: Each alert is independent
        """
        patient_id = 'patient-multi-001'

        alert1 = generate_vital_alert(patient_id, 'heartrate', 35)
        alert2 = generate_vital_alert(patient_id, 'oxygen', 82)

        assert alert1 is not None
        assert alert2 is not None
        assert alert1['vitalType'] != alert2['vitalType']
        assert alert1['patientId'] == alert2['patientId']
