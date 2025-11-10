"""
VitalsNormalizer - Single source of truth for vital signs data processing.

Replaces inline normalization logic scattered across:
- app/services/mqtt_service.py (process_vital_signs)
- app/services/patient_service.py (get_latest_vitals)
- app/api/routes/patient_routes.py (vitals endpoint)

Usage:
    from app.domain.vitals import VitalsNormalizer

    normalizer = VitalsNormalizer()
    vitals = normalizer.normalize_mqtt_payload(mqtt_data)
    validated = normalizer.validate_vitals(vitals)
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from app.domain.schemas import VitalsRecord, VITAL_THRESHOLDS
from app.common.datetime import parse_iso8601, now_utc

logger = logging.getLogger(__name__)


class VitalsNormalizer:
    """
    Centralizes vital signs data normalization and validation.

    Responsibilities:
    1. Normalize incoming MQTT payload to VitalsRecord format
    2. Validate vital values against clinical thresholds
    3. Calculate data quality scores
    4. Handle sensor mode switching (ECG/EEG toggle)
    """

    def __init__(self):
        """Initialize normalizer with vital thresholds."""
        self.thresholds = VITAL_THRESHOLDS

    def normalize_mqtt_payload(self, payload: Dict[str, Any]) -> VitalsRecord:
        """
        Normalize MQTT payload from ESP32 watch to VitalsRecord format.

        Args:
            payload: Raw MQTT message payload with camelCase fields

        Returns:
            VitalsRecord with normalized and validated data

        Raises:
            ValueError: If required fields missing or invalid
        """
        # Validate required fields
        if 'patientId' not in payload:
            raise ValueError("Missing required field: patientId")
        if 'deviceId' not in payload:
            raise ValueError("Missing required field: deviceId")

        # Parse timestamp (use current time if not provided)
        timestamp = now_utc()
        if 'timestamp' in payload:
            try:
                timestamp = parse_iso8601(payload['timestamp'])
            except Exception as e:
                logger.warning(f"Invalid timestamp in payload, using current time: {e}")

        # Build VitalsRecord with normalized values
        vitals: VitalsRecord = {
            'patientId': str(payload['patientId']),
            'deviceId': str(payload['deviceId']),
            'timestamp': timestamp,

            # Cardiovascular vitals
            'heartRate': self._parse_int(payload.get('heartRate')),
            'systolicPressure': self._parse_int(payload.get('systolicPressure')),
            'diastolicPressure': self._parse_int(payload.get('diastolicPressure')),

            # Respiratory vitals
            'respiratoryRate': self._parse_int(payload.get('respiratoryRate')),
            'oxygenSaturation': self._parse_int(payload.get('oxygenSaturation')),

            # Temperature
            'skinTemperature': self._parse_float(payload.get('skinTemperature')),

            # Neurological/Cardiac
            'ecgReading': self._parse_int(payload.get('ecgReading')),
            'eegReading': self._parse_int(payload.get('eegReading')),
            'isEcgMode': payload.get('isEcgMode', True),  # Default to ECG mode

            # Advanced sensors (new in v5.2.13+)
            'bioimpedance': self._parse_float(payload.get('bioimpedance')),
            'tremor': self._parse_float(payload.get('tremor')),
            'imuFallRisk': self._parse_float(payload.get('imuFallRisk')),
            'perfusionIndex': self._parse_float(payload.get('perfusionIndex')),

            # Computed ECG/EEG metrics
            'rrInterval': self._parse_int(payload.get('rrInterval')),
            'prInterval': self._parse_int(payload.get('prInterval')),
            'qtcInterval': self._parse_int(payload.get('qtcInterval')),
            'qrsWidth': self._parse_int(payload.get('qrsWidth')),
            'pWaveAmplitude': self._parse_float(payload.get('pWaveAmplitude')),
            'tWaveAmplitude': self._parse_float(payload.get('tWaveAmplitude')),
            'stSegmentDeviation': self._parse_float(payload.get('stSegmentDeviation')),
        }

        # Calculate data quality score
        vitals['dataQualityScore'] = self._calculate_quality_score(vitals)

        return vitals

    def validate_vitals(self, vitals: VitalsRecord) -> Tuple[bool, Optional[str]]:
        """
        Validate vital values against clinical thresholds.

        Args:
            vitals: VitalsRecord to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check heart rate
        if vitals.get('heartRate') is not None:
            hr = vitals['heartRate']
            threshold = self.thresholds['heartrate']
            if hr < threshold['criticalLow'] or hr > threshold['criticalHigh']:
                return False, f"Heart rate {hr} outside safe range ({threshold['criticalLow']}-{threshold['criticalHigh']} bpm)"

        # Check oxygen saturation
        if vitals.get('oxygenSaturation') is not None:
            spo2 = vitals['oxygenSaturation']
            threshold = self.thresholds['oxygen']
            if spo2 < threshold['criticalLow']:
                return False, f"Oxygen saturation {spo2}% critically low (minimum {threshold['criticalLow']}%)"

        # Check temperature
        if vitals.get('skinTemperature') is not None:
            temp = vitals['skinTemperature']
            threshold = self.thresholds['temperature']
            if temp < threshold['criticalLow'] or temp > threshold['criticalHigh']:
                return False, f"Temperature {temp}°F outside safe range ({threshold['criticalLow']}-{threshold['criticalHigh']}°F)"

        # Check blood pressure if both values present
        if vitals.get('systolicPressure') is not None and vitals.get('diastolicPressure') is not None:
            systolic = vitals['systolicPressure']
            diastolic = vitals['diastolicPressure']

            # Validate systolic
            threshold_sys = self.thresholds['systolic']
            if systolic < threshold_sys['criticalLow'] or systolic > threshold_sys['criticalHigh']:
                return False, f"Systolic pressure {systolic} mmHg outside safe range"

            # Validate diastolic
            threshold_dia = self.thresholds['diastolic']
            if diastolic < threshold_dia['criticalLow'] or diastolic > threshold_dia['criticalHigh']:
                return False, f"Diastolic pressure {diastolic} mmHg outside safe range"

            # Validate pulse pressure (systolic - diastolic should be 30-50)
            pulse_pressure = systolic - diastolic
            if pulse_pressure < 20 or pulse_pressure > 100:
                return False, f"Abnormal pulse pressure {pulse_pressure} mmHg"

        # Check respiratory rate
        if vitals.get('respiratoryRate') is not None:
            rr = vitals['respiratoryRate']
            threshold = self.thresholds['respiratory']
            if rr < threshold['criticalLow'] or rr > threshold['criticalHigh']:
                return False, f"Respiratory rate {rr} breaths/min outside safe range"

        return True, None

    def _calculate_quality_score(self, vitals: VitalsRecord) -> float:
        """
        Calculate data quality score (0.0 to 1.0) based on completeness.

        Args:
            vitals: VitalsRecord to score

        Returns:
            Quality score between 0.0 (poor) and 1.0 (excellent)
        """
        # Core vital fields (highest weight)
        core_fields = ['heartRate', 'oxygenSaturation', 'skinTemperature']
        core_present = sum(1 for field in core_fields if vitals.get(field) is not None)
        core_score = core_present / len(core_fields)

        # Additional vital fields (medium weight)
        additional_fields = ['respiratoryRate', 'systolicPressure', 'diastolicPressure']
        additional_present = sum(1 for field in additional_fields if vitals.get(field) is not None)
        additional_score = additional_present / len(additional_fields)

        # Advanced sensor fields (lower weight)
        advanced_fields = ['bioimpedance', 'tremor', 'imuFallRisk', 'perfusionIndex']
        advanced_present = sum(1 for field in advanced_fields if vitals.get(field) is not None)
        advanced_score = advanced_present / len(advanced_fields)

        # Weighted average: 50% core, 30% additional, 20% advanced
        quality_score = (
            0.50 * core_score +
            0.30 * additional_score +
            0.20 * advanced_score
        )

        return round(quality_score, 2)

    def _parse_int(self, value: Any) -> Optional[int]:
        """Safely parse integer value."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse int value: {value}")
            return None

    def _parse_float(self, value: Any) -> Optional[float]:
        """Safely parse float value."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse float value: {value}")
            return None
