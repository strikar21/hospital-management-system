"""
Vitals Alert Detector

Detects abnormal vital signs and generates FHIR Flag resources
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from .loinc_mapping import is_within_normal_range, is_critical, get_normal_range


class VitalsAlertDetector:
    """
    Detects abnormal vital signs and creates FHIR Flag resources

    Alert Levels:
    - info: Slightly outside normal range
    - warning: Outside normal range
    - critical: In dangerous range requiring immediate attention
    """

    @staticmethod
    def detect_alerts(vitals: Dict[str, float], patient_id: str, device_id: str) -> List[Dict[str, Any]]:
        """
        Detect alerts from vital signs

        Args:
            vitals: Dictionary of vital type -> value
            patient_id: Patient reference
            device_id: Device reference

        Returns:
            List of FHIR Flag resources for abnormal vitals
        """
        alerts = []

        for vital_type, value in vitals.items():
            if value is None:
                continue

            # Check if critical
            if is_critical(vital_type, value):
                alert = VitalsAlertDetector._create_alert(
                    vital_type=vital_type,
                    value=value,
                    severity="critical",
                    patient_id=patient_id,
                    device_id=device_id
                )
                alerts.append(alert)

            # Check if outside normal range
            elif not is_within_normal_range(vital_type, value):
                alert = VitalsAlertDetector._create_alert(
                    vital_type=vital_type,
                    value=value,
                    severity="warning",
                    patient_id=patient_id,
                    device_id=device_id
                )
                alerts.append(alert)

        return alerts

    @staticmethod
    def _create_alert(
        vital_type: str,
        value: float,
        severity: str,
        patient_id: str,
        device_id: str
    ) -> Dict[str, Any]:
        """
        Create a FHIR Flag resource for an alert

        Args:
            vital_type: Type of vital sign
            value: Measured value
            severity: Alert severity (info, warning, critical)
            patient_id: Patient ID
            device_id: Device ID

        Returns:
            FHIR R5 Flag resource
        """
        ranges = get_normal_range(vital_type)

        # Determine alert message
        if value < ranges.get("critical_low", 0):
            direction = "critically low"
        elif value > ranges.get("critical_high", 999):
            direction = "critically high"
        elif value < ranges.get("min", 0):
            direction = "low"
        elif value > ranges.get("max", 999):
            direction = "high"
        else:
            direction = "abnormal"

        # Create alert ID
        alert_id = f"ALERT-{vital_type}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create FHIR Flag resource
        flag = {
            "resourceType": "Flag",
            "id": alert_id,
            "status": "active",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/flag-category",
                            "code": "clinical",
                            "display": "Clinical"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "365508006",
                        "display": "Abnormal vital signs"
                    }
                ],
                "text": f"{vital_type.replace('_', ' ').title()} {direction}"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "period": {
                "start": datetime.now(timezone.utc).isoformat()
            },
            "author": {
                "reference": f"Device/{device_id}"
            },
            "text": {
                "status": "generated",
                "div": f"<div xmlns='http://www.w3.org/1999/xhtml'>"
                       f"{vital_type.replace('_', ' ').title()} is {direction}: {value}"
                       f" (Normal: {ranges.get('min', 'N/A')}-{ranges.get('max', 'N/A')})</div>"
            }
        }

        # Add severity
        if severity == "critical":
            flag["code"]["coding"].append({
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "HH",
                "display": "Critical high"
            } if value > ranges.get("critical_high", 999) else {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "LL",
                "display": "Critical low"
            })

        # Add metadata
        flag["_internal"] = {
            "vitalType": vital_type,
            "value": value,
            "severity": severity,
            "normalRange": ranges,
            "detectedAt": datetime.now(timezone.utc).isoformat()
        }

        return flag

    @staticmethod
    def check_trend_alert(
        recent_values: List[float],
        vital_type: str,
        patient_id: str,
        device_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check for trend-based alerts (rapid changes)

        Args:
            recent_values: List of recent values (newest first)
            vital_type: Type of vital
            patient_id: Patient ID
            device_id: Device ID

        Returns:
            FHIR Flag if trend is concerning, None otherwise
        """
        if len(recent_values) < 3:
            return None

        # Calculate trend (simple linear)
        first_val = recent_values[-1]
        last_val = recent_values[0]
        change = last_val - first_val

        # Define concerning change thresholds
        thresholds = {
            "heartRate": 20,      # Change of 20 bpm
            "spo2": 5,            # Change of 5%
            "temperature": 1.0,   # Change of 1°C
            "systolicBP": 20,     # Change of 20 mmHg
            "respiratoryRate": 5  # Change of 5 breaths/min
        }

        threshold = thresholds.get(vital_type)
        if not threshold:
            return None

        if abs(change) >= threshold:
            alert_id = f"ALERT-TREND-{vital_type}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            direction = "increasing" if change > 0 else "decreasing"

            flag = {
                "resourceType": "Flag",
                "id": alert_id,
                "status": "active",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/flag-category",
                                "code": "clinical",
                                "display": "Clinical"
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "703506003",
                            "display": "Rapid change in vital signs"
                        }
                    ],
                    "text": f"Rapid {direction} trend in {vital_type.replace('_', ' ')}"
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "period": {
                    "start": datetime.now(timezone.utc).isoformat()
                },
                "author": {
                    "reference": f"Device/{device_id}"
                },
                "_internal": {
                    "vitalType": vital_type,
                    "trend": direction,
                    "change": change,
                    "recentValues": recent_values,
                    "detectedAt": datetime.now(timezone.utc).isoformat()
                }
            }

            return flag

        return None
