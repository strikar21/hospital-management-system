"""
Door Scanner NFC Adapter

Converts NFC tap events to FHIR AuditEvent and Observation resources
Tracks access to patient rooms for compliance
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid


class DoorScannerAdapter:
    """
    Adapter for NFC-based door scanner

    Tracks:
    - Staff entering/exiting patient rooms
    - Patient location changes
    - Access logs for DPDP compliance
    """

    def transform_to_fhir_audit_event(
        self,
        nfc_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform NFC tap to FHIR AuditEvent

        Args:
            nfc_payload: NFC event data
                Expected format:
                {
                    "deviceId": "DEV000003",
                    "location": "ICU-Ward-Room-101",
                    "nfcBadgeId": "NFC-DOC-001",
                    "staffId": "STF000001",
                    "staffRole": "doctor",
                    "patientId": "PAT000001",  # Optional - if room has patient
                    "action": "entry",  # or "exit"
                    "timestamp": "2025-11-21T14:30:00Z"
                }

        Returns:
            FHIR R5 AuditEvent resource
        """
        device_id = nfc_payload.get("deviceId")
        location = nfc_payload.get("location")
        staff_id = nfc_payload.get("staffId")
        staff_role = nfc_payload.get("staffRole")
        patient_id = nfc_payload.get("patientId")
        action = nfc_payload.get("action", "entry")
        nfc_badge = nfc_payload.get("nfcBadgeId")
        timestamp = nfc_payload.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Parse timestamp
        if isinstance(timestamp, str):
            recorded = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            recorded = datetime.now(timezone.utc)

        # Generate event ID
        event_id = f"AUDIT-ACCESS-{uuid.uuid4().hex[:8]}"

        # Determine action code
        action_code = "E"  # Execute (access event)
        action_display = f"Room {action}"

        audit_event = {
            "resourceType": "AuditEvent",
            "id": event_id,
            "type": {
                "system": "http://terminology.hl7.org/CodeSystem/audit-event-type",
                "code": action_code,
                "display": action_display
            },
            "subtype": [
                {
                    "system": "http://hl7.org/fhir/restful-interaction",
                    "code": action,
                    "display": f"{action.title()} patient room"
                }
            ],
            "action": action_code,
            "recorded": recorded.isoformat(),
            "outcome": "0",  # Success
            "outcomeDesc": f"Staff {staff_id} {action} {location}",
            "agent": [
                {
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType",
                                "code": "PROV",
                                "display": "healthcare provider"
                            }
                        ]
                    },
                    "who": {
                        "reference": f"Practitioner/{staff_id}"
                    },
                    "requestor": True,
                    "role": [
                        {
                            "text": staff_role
                        }
                    ],
                    "network": {
                        "address": nfc_badge,
                        "type": "5"  # URI/badge identifier
                    }
                }
            ],
            "source": {
                "site": location,
                "observer": {
                    "reference": f"Device/{device_id}"
                },
                "type": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/security-source-type",
                        "code": "4",
                        "display": "Application Server"
                    }
                ]
            },
            "entity": []
        }

        # Add patient entity if present
        if patient_id:
            audit_event["entity"].append({
                "what": {
                    "reference": f"Patient/{patient_id}"
                },
                "type": {
                    "system": "http://terminology.hl7.org/CodeSystem/audit-entity-type",
                    "code": "1",
                    "display": "Person"
                },
                "role": {
                    "system": "http://terminology.hl7.org/CodeSystem/object-role",
                    "code": "1",
                    "display": "Patient"
                }
            })

        # Add location entity
        audit_event["entity"].append({
            "what": {
                "reference": f"Location/{location}"
            },
            "type": {
                "system": "http://terminology.hl7.org/CodeSystem/audit-entity-type",
                "code": "3",
                "display": "Organization"
            },
            "role": {
                "system": "http://terminology.hl7.org/CodeSystem/object-role",
                "code": "13",
                "display": "Security Resource"
            },
            "detail": [
                {
                    "type": "location",
                    "valueString": location
                }
            ]
        })

        # Add metadata
        audit_event["meta"] = {
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "tag": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "DPDP",
                    "display": "DPDP Act 2023 Compliance"
                }
            ]
        }

        # Add internal metadata
        audit_event["_internal"] = {
            "nfcBadgeId": nfc_badge,
            "action": action,
            "location": location,
            "deviceId": device_id
        }

        return audit_event

    def transform_to_fhir_observation(
        self,
        nfc_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform NFC tap to FHIR Observation (access log)

        Creates an observation for tracking patient room occupancy

        Args:
            nfc_payload: NFC event data

        Returns:
            FHIR R5 Observation resource
        """
        patient_id = nfc_payload.get("patientId")
        location = nfc_payload.get("location")
        action = nfc_payload.get("action", "entry")
        timestamp = nfc_payload.get("timestamp", datetime.now(timezone.utc).isoformat())

        if not patient_id:
            return None  # No patient in room

        # Parse timestamp
        if isinstance(timestamp, str):
            effective_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            effective_time = datetime.now(timezone.utc)

        obs_id = f"OBS-ACCESS-{uuid.uuid4().hex[:8]}"

        observation = {
            "resourceType": "Observation",
            "id": obs_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "activity",
                            "display": "Activity"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "89247-1",
                        "display": "Patient location"
                    }
                ],
                "text": f"Room access - {action}"
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "effectiveDateTime": effective_time.isoformat(),
            "issued": datetime.now(timezone.utc).isoformat(),
            "valueString": location,
            "device": {
                "reference": f"Device/{nfc_payload.get('deviceId')}"
            },
            "performer": [
                {
                    "reference": f"Practitioner/{nfc_payload.get('staffId')}"
                }
            ],
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat()
            },
            "_internal": {
                "action": action,
                "location": location,
                "nfcBadgeId": nfc_payload.get("nfcBadgeId")
            }
        }

        return observation

    def validate_nfc_payload(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate NFC payload structure

        Args:
            payload: NFC message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        required_fields = ["deviceId", "location", "nfcBadgeId", "staffId", "staffRole"]

        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"

        # Validate action
        if "action" in payload:
            if payload["action"] not in ["entry", "exit"]:
                return False, "action must be 'entry' or 'exit'"

        return True, None

    def create_bundle(
        self,
        audit_event: Dict[str, Any],
        observation: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a FHIR Bundle with audit event and optional observation

        Args:
            audit_event: AuditEvent resource
            observation: Optional Observation resource

        Returns:
            FHIR R5 Bundle resource
        """
        entries = [
            {
                "fullUrl": f"urn:uuid:{audit_event['id']}",
                "resource": audit_event,
                "request": {
                    "method": "POST",
                    "url": "AuditEvent"
                }
            }
        ]

        if observation:
            entries.append({
                "fullUrl": f"urn:uuid:{observation['id']}",
                "resource": observation,
                "request": {
                    "method": "POST",
                    "url": "Observation"
                }
            })

        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry": entries
        }

        return bundle
