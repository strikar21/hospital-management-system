"""
Vital Sign Alert Service
Generates clinical alerts based on vital sign thresholds

Medical thresholds based on standard adult clinical guidelines.
Compliant with Medical Council of India (MCI) monitoring standards.
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)

class VitalAlertService:
    """Service to generate alerts based on vital sign thresholds"""

    # Medical thresholds (based on standard clinical guidelines)
    THRESHOLDS = {
        'heartrate': {
            'criticalLow': 40,   # Severe bradycardia - immediate intervention
            'warningLow': 50,    # Bradycardia - monitor closely
            'warningHigh': 120,  # Tachycardia - monitor closely
            'criticalHigh': 150, # Severe tachycardia - immediate intervention
            'unit': 'bpm'
        },
        'oxygensaturation': {
            'criticalLow': 85,   # Critical hypoxemia - emergency oxygen
            'warningLow': 90,    # Hypoxemia - oxygen therapy
            'normal': 95,        # Normal threshold
            'unit': '%'
        },
        'bloodpressuresystolic': {
            'criticalLow': 80,   # Severe hypotension - emergency
            'warningLow': 90,    # Hypotension - monitor
            'warningHigh': 140,  # Hypertension - medication review
            'criticalHigh': 180, # Hypertensive crisis - emergency
            'unit': 'mmHg'
        },
        'temperature': {
            'criticalLow': 95.0,  # Hypothermia - emergency warming (Fahrenheit)
            'warningLow': 97.0,   # Low - monitor
            'warningHigh': 100.4, # Fever - antipyretics
            'criticalHigh': 103.0,# Hyperpyrexia - emergency cooling
            'unit': '°F'
        },
        'respiratoryrate': {
            'criticalLow': 10,    # Bradypnea - respiratory support
            'warningLow': 12,     # Low normal - monitor
            'warningHigh': 20,    # Tachypnea - monitor
            'criticalHigh': 30,   # Severe tachypnea - assessment
            'unit': '/min'
        }
    }

    async def check_vitals_and_generate_alerts(
        self,
        patient_id: str,
        device_id: str,
        vitals: Dict[str, Any],
        conn
    ) -> List[Dict[str, Any]]:
        """
        Check vitals against thresholds and generate alerts if needed

        Args:
            patient_id: Patient ID
            device_id: Device ID that sent vitals
            vitals: Dictionary with vital sign values (ESP32 format)
            conn: Database connection for alert insertion

        Returns:
            List of alert dictionaries for WebSocket broadcast
        """
        alerts = []

        try:
            # Map ESP32 field names to database field names
            vital_mapping = {
                'heartrate': 'heartrate',
                'oxygensat': 'oxygensaturation',
                'bloodpressurevalue': 'bloodpressuresystolic',
                'temperature': 'temperature',
                'respiratoryrate': 'respiratoryrate'
            }

            for esp32_field, db_field in vital_mapping.items():
                if esp32_field in vitals and vitals[esp32_field] is not None:
                    value = vitals[esp32_field]
                    thresholds = self.THRESHOLDS.get(db_field)

                    if thresholds:
                        alert = await self._check_threshold(
                            patient_id, device_id, db_field,
                            value, thresholds, conn
                        )
                        if alert:
                            alerts.append(alert)

        except Exception as e:
            logger.error(f"Error checking vitals for alerts: {e}")
            # Don't raise - return empty list if checking fails

        return alerts

    async def _check_threshold(
        self,
        patient_id: str,
        device_id: str,
        vital_type: str,
        value: float,
        thresholds: Dict[str, Any],
        conn
    ) -> Optional[Dict[str, Any]]:
        """Check a single vital against thresholds"""

        severity = None
        message = None
        threshold_breached = None

        # Check critical low
        if 'criticalLow' in thresholds and value < thresholds['criticalLow']:
            severity = 'critical'
            threshold_breached = thresholds['criticalLow']
            message = self._get_critical_low_message(vital_type, value, thresholds['unit'])

        # Check critical high
        elif 'criticalHigh' in thresholds and value > thresholds['criticalHigh']:
            severity = 'critical'
            threshold_breached = thresholds['criticalHigh']
            message = self._get_critical_high_message(vital_type, value, thresholds['unit'])

        # Check warning low
        elif 'warningLow' in thresholds and value < thresholds['warningLow']:
            severity = 'high'
            threshold_breached = thresholds['warningLow']
            message = self._get_warning_low_message(vital_type, value, thresholds['unit'])

        # Check warning high
        elif 'warningHigh' in thresholds and value > thresholds['warningHigh']:
            severity = 'high'
            threshold_breached = thresholds['warningHigh']
            message = self._get_warning_high_message(vital_type, value, thresholds['unit'])

        # No threshold breached
        if not severity:
            return None

        # Create alert in database
        try:
            return await self._create_alert(
                patient_id, device_id, vital_type, value,
                threshold_breached, severity, message, conn
            )
        except Exception as e:
            logger.error(f"Failed to create alert for {vital_type}: {e}")
            return None

    async def _create_alert(
        self,
        patient_id: str,
        device_id: str,
        vital_type: str,
        vital_value: float,
        threshold_value: float,
        severity: str,
        message: str,
        conn
    ) -> Optional[Dict[str, Any]]:
        """
        Create alert in patient_alerts table.

        NOTE: This service is DEPRECATED - alerts are now created through
        alert_detection_service.py → alert_manager_service.py with proper deduplication.

        This code path is kept for backwards compatibility but should not be actively used.
        """

        # Create alert with new schema (includes vitalType, vitalValue, etc.)
        alert_id = await conn.fetchval('''
            INSERT INTO patient_alerts (
                "patientId", type, message, severity, status,
                "vitalType", "vitalValue", "thresholdValue",
                "createdAt", "createdBy"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
        ''', patient_id, 'vital', message, severity, 'active',
             vital_type, vital_value, threshold_value,
             datetime.now(), device_id)

        logger.warning(f"🚨 Alert generated (via deprecated service): {alert_id} - {severity} - {message}")

        return {
            'alertId': alert_id,
            'severity': severity,
            'message': message,
            'vitalType': vital_type,
            'vitalValue': vital_value,
            'thresholdValue': threshold_value
        }

    def _get_critical_low_message(self, vital_type: str, value: float, unit: str) -> str:
        """Generate critical low message"""
        messages = {
            'heartrate': f'Severe Bradycardia: {value:.0f} {unit} (Critical Low)',
            'oxygensaturation': f'Critical Hypoxemia: {value:.0f}{unit} (Critical Low)',
            'bloodpressuresystolic': f'Severe Hypotension: {value:.0f} {unit} (Critical Low)',
            'temperature': f'Hypothermia: {value:.1f}{unit} (Critical Low)',
            'respiratoryrate': f'Severe Bradypnea: {value:.0f} {unit} (Critical Low)'
        }
        return messages.get(vital_type, f'{vital_type} critically low: {value} {unit}')

    def _get_critical_high_message(self, vital_type: str, value: float, unit: str) -> str:
        """Generate critical high message"""
        messages = {
            'heartrate': f'Severe Tachycardia: {value:.0f} {unit} (Critical High)',
            'bloodpressuresystolic': f'Hypertensive Crisis: {value:.0f} {unit} (Critical High)',
            'temperature': f'Hyperpyrexia: {value:.1f}{unit} (Critical High)',
            'respiratoryrate': f'Severe Tachypnea: {value:.0f} {unit} (Critical High)'
        }
        return messages.get(vital_type, f'{vital_type} critically high: {value} {unit}')

    def _get_warning_low_message(self, vital_type: str, value: float, unit: str) -> str:
        """Generate warning low message"""
        messages = {
            'heartrate': f'Bradycardia: {value:.0f} {unit} (Below Normal)',
            'oxygensaturation': f'Low Oxygen Saturation: {value:.0f}{unit} (Below Normal)',
            'bloodpressuresystolic': f'Hypotension: {value:.0f} {unit} (Below Normal)',
            'temperature': f'Low Temperature: {value:.1f}{unit} (Below Normal)',
            'respiratoryrate': f'Low Respiratory Rate: {value:.0f} {unit} (Below Normal)'
        }
        return messages.get(vital_type, f'{vital_type} low: {value} {unit}')

    def _get_warning_high_message(self, vital_type: str, value: float, unit: str) -> str:
        """Generate warning high message"""
        messages = {
            'heartrate': f'Tachycardia: {value:.0f} {unit} (Above Normal)',
            'bloodpressuresystolic': f'Hypertension: {value:.0f} {unit} (Above Normal)',
            'temperature': f'Fever: {value:.1f}{unit} (Above Normal)',
            'respiratoryrate': f'Tachypnea: {value:.0f} {unit} (Above Normal)'
        }
        return messages.get(vital_type, f'{vital_type} high: {value} {unit}')

# Global service instance
vital_alert_service = VitalAlertService()
