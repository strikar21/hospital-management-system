"""
ESP32 Watch Adapter

Converts MQTT vitals data to FHIR R5 Observation resources
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import uuid
from .loinc_mapping import get_loinc_for_vital
from .alert_detector import VitalsAlertDetector


class ESP32WatchAdapter:
    """
    Adapter for ESP32 Hospital Watch

    Receives MQTT messages and converts to FHIR R5 Observations
    """

    def __init__(self):
        self.alert_detector = VitalsAlertDetector()

    def transform_to_fhir_observations(
        self,
        mqtt_payload: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Transform MQTT payload to FHIR R5 Observation resources

        Args:
            mqtt_payload: Raw MQTT message from ESP32 watch
                Expected format:
                {
                    "deviceId": "DEV000001",
                    "patientId": "PAT000001",
                    "timestamp": "2025-11-21T12:00:00Z",
                    "vitals": {
                        "heartRate": 78,
                        "spo2": 98,
                        "temperature": 36.8,
                        "systolicBP": 120,
                        "diastolicBP": 80,
                        "respiratoryRate": 16
                    },
                    "batteryLevel": 85,
                    "signalStrength": -45
                }

        Returns:
            List of FHIR R5 Observation resources (one per vital sign)
        """
        observations = []

        device_id = mqtt_payload.get("deviceId")
        patient_id = mqtt_payload.get("patientId")
        timestamp = mqtt_payload.get("timestamp", datetime.now(timezone.utc).isoformat())
        vitals = mqtt_payload.get("vitals", {})

        # Parse timestamp
        if isinstance(timestamp, str):
            effective_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            effective_time = datetime.now(timezone.utc)

        # Create observation for each vital sign
        for vital_type, value in vitals.items():
            if value is None:
                continue

            observation = self._create_observation(
                vital_type=vital_type,
                value=value,
                patient_id=patient_id,
                device_id=device_id,
                effective_time=effective_time
            )

            if observation:
                observations.append(observation)

        return observations

    def _create_observation(
        self,
        vital_type: str,
        value: Any,  # Changed from float to Any to handle string values (activity)
        patient_id: str,
        device_id: str,
        effective_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Create a single FHIR R5 Observation for a vital sign

        Args:
            vital_type: Type of vital (heartRate, spo2, activity, etc.)
            value: Measured value (float for vitals, string for activity)
            patient_id: Patient ID
            device_id: Device ID
            effective_time: Time of measurement

        Returns:
            FHIR R5 Observation resource or None if vital type unknown
        """
        loinc = get_loinc_for_vital(vital_type)

        if not loinc:
            return None  # Unknown vital type

        observation_id = f"OBS-{vital_type}-{uuid.uuid4().hex[:8]}"

        observation = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": loinc["category"],
                            "display": loinc["category"].replace("-", " ").title()
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": loinc["system"],
                        "code": loinc["code"],
                        "display": loinc["display"]
                    }
                ],
                "text": loinc["display"]
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_time.isoformat(),
            "issued": datetime.now(timezone.utc).isoformat(),
            "device": {
                "reference": f"Device/{device_id}"
            },
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat(),
                "source": f"#{device_id}"
            }
        }

        # Handle activity status (CodeableConcept instead of Quantity)
        if vital_type == "activity" and isinstance(value, str):
            value_set = loinc.get("valueSet", {})
            activity_code = value_set.get(value, value_set.get("UNKNOWN"))

            observation["valueCodeableConcept"] = {
                "coding": [
                    {
                        "system": activity_code["system"],
                        "code": activity_code["code"],
                        "display": activity_code["display"]
                    }
                ],
                "text": activity_code["display"]
            }
        else:
            # Standard quantity for numeric vitals
            observation["valueQuantity"] = {
                "value": value,
                "unit": loinc["unit"],
                "system": "http://unitsofmeasure.org",
                "code": loinc["ucum"]
            }

        # Add interpretation if outside normal range (only for numeric vitals)
        if isinstance(value, (int, float)):
            from .loinc_mapping import is_within_normal_range, is_critical

            if is_critical(vital_type, value):
                observation["interpretation"] = [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": "HH" if value > 100 else "LL",
                                "display": "Critical high" if value > 100 else "Critical low"
                            }
                        ]
                    }
                ]
            elif not is_within_normal_range(vital_type, value):
                observation["interpretation"] = [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": "A",
                                "display": "Abnormal"
                            }
                        ]
                    }
                ]
            else:
                observation["interpretation"] = [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": "N",
                                "display": "Normal"
                            }
                        ]
                    }
                ]

        return observation

    def detect_alerts(
        self,
        mqtt_payload: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Detect alerts from vitals data

        Args:
            mqtt_payload: MQTT message with vitals

        Returns:
            List of FHIR Flag resources for detected alerts
        """
        vitals = mqtt_payload.get("vitals", {})
        patient_id = mqtt_payload.get("patientId")
        device_id = mqtt_payload.get("deviceId")

        return self.alert_detector.detect_alerts(vitals, patient_id, device_id)

    def validate_mqtt_payload(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate MQTT payload structure

        Args:
            payload: MQTT message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        required_fields = ["deviceId", "patientId", "vitals"]

        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"

        # Check vitals is a dictionary
        if not isinstance(payload["vitals"], dict):
            return False, "vitals must be a dictionary"

        # Check at least one vital is present
        if not payload["vitals"]:
            return False, "vitals dictionary is empty"

        return True, None

    def create_bundle(
        self,
        observations: List[Dict[str, Any]],
        alerts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a FHIR Bundle containing observations and alerts

        Args:
            observations: List of Observation resources
            alerts: List of Flag resources

        Returns:
            FHIR R5 Bundle resource
        """
        entries = []

        # Add observations
        for obs in observations:
            entries.append({
                "fullUrl": f"urn:uuid:{obs['id']}",
                "resource": obs,
                "request": {
                    "method": "POST",
                    "url": "Observation"
                }
            })

        # Add alerts
        for alert in alerts:
            entries.append({
                "fullUrl": f"urn:uuid:{alert['id']}",
                "resource": alert,
                "request": {
                    "method": "POST",
                    "url": "Flag"
                }
            })

        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry": entries
        }

        return bundle
