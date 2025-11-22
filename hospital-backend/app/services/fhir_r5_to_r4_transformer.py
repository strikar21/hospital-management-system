"""
FHIR R5 → R4 Transformer for ABDM/ABHA Integration

Transforms FHIR R5 resources (internal format) to NRCES-compliant FHIR R4
for ABDM (Ayushman Bharat Digital Mission) integration.

Architecture:
- Internal APIs: FHIR R5 (future-proof, better device models)
- ABDM APIs: FHIR R4 (current ABDM requirement)

NRCES Specification: https://nrces.in/ndhm/fhir/r4/
ObservationVitalSigns Profile: https://nrces.in/ndhm/fhir/r4/StructureDefinition/ObservationVitalSigns
"""

from datetime import datetime
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class FhirR5ToR4Transformer:
    """
    FHIR R5 → R4 Transformer for ABDM Integration

    Transforms FHIR R5 resources to NRCES-compliant FHIR R4.
    Use this for ABDM/ABHA health record exchange.

    Supported transforms:
    - Observation R5 → R4 (with NRCES profile)
    - Patient R5 → R4 (with ABHA identifiers)
    - Device R5 → R4
    """

    NRCES_PROFILE_BASE = "https://nrces.in/ndhm/fhir/r4/StructureDefinition/"

    def transform_observation_r5_to_r4(
        self,
        observation_r5: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform FHIR R5 Observation to NRCES-compliant R4

        R5 and R4 Observations are mostly compatible.
        Main differences:
        - R4 uses 'performer' (same as R5)
        - Add NRCES profile to meta

        Args:
            observation_r5: FHIR R5 Observation resource

        Returns:
            FHIR R4 Observation with NRCES profile
        """
        # R5 Observation is mostly compatible with R4
        observation_r4 = observation_r5.copy()

        # Add NRCES profile if not present
        if "meta" not in observation_r4:
            observation_r4["meta"] = {}

        observation_r4["meta"]["profile"] = [
            f"{self.NRCES_PROFILE_BASE}ObservationVitalSigns"
        ]

        # Ensure versionId and lastUpdated are present
        if "versionId" not in observation_r4["meta"]:
            observation_r4["meta"]["versionId"] = "1"
        if "lastUpdated" not in observation_r4["meta"]:
            observation_r4["meta"]["lastUpdated"] = datetime.utcnow().isoformat() + "Z"

        logger.info(f"✅ Transformed R5 Observation to NRCES R4")

        return observation_r4

    # LOINC mapping cache (loaded from database)
    _loinc_map: Dict[str, Dict[str, Any]] = {}

    @classmethod
    async def initialize(cls, db_conn):
        """
        Initialize LOINC mapping from database

        Call this on app startup:
        ```python
        await NrcesFhirTransformer.initialize(db_pool)
        ```
        """
        try:
            mappings = await db_conn.fetch("""
                SELECT
                    "vitalType",
                    "loincCode",
                    "loincDisplay",
                    "ucumUnit",
                    "ucumCode",
                    "snomedCode",
                    "referenceRangeLow",
                    "referenceRangeHigh"
                FROM loinc_vital_mapping
            """)

            cls._loinc_map = {
                m["vitalType"]: {
                    "loincCode": m["loincCode"],
                    "loincDisplay": m["loincDisplay"],
                    "ucumUnit": m["ucumUnit"],
                    "ucumCode": m["ucumCode"],
                    "snomedCode": m.get("snomedCode"),
                    "referenceRange": {
                        "low": float(m["referenceRangeLow"]) if m["referenceRangeLow"] else None,
                        "high": float(m["referenceRangeHigh"]) if m["referenceRangeHigh"] else None
                    }
                }
                for m in mappings
            }

            logger.info(f"✅ NRCES FHIR Transformer initialized with {len(cls._loinc_map)} LOINC mappings")

        except Exception as e:
            logger.error(f"❌ Failed to initialize LOINC mappings: {e}")
            raise

    def create_observation_vital_signs(
        self,
        patient_id: str,
        vital_type: str,
        value: float,
        timestamp: datetime,
        device_id: str,
        encounter_id: Optional[str] = None,
        performer_staff_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create NRCES ObservationVitalSigns resource

        Args:
            patient_id: Patient MRN or ABHA number
            vital_type: Internal vital name (heartRate, oxygenSaturation, etc.)
            value: Measured value
            timestamp: Measurement timestamp
            device_id: Device identifier (e.g., fit-00001)
            encounter_id: Optional encounter reference
            performer_staff_id: Optional staff who performed measurement

        Returns:
            FHIR Observation resource (dict) compliant with NRCES profile

        Raises:
            ValueError: If vital_type is not in LOINC mapping

        Example:
            ```python
            obs = transformer.create_observation_vital_signs(
                patient_id="PAT0001",
                vital_type="heartRate",
                value=72.0,
                timestamp=datetime.utcnow(),
                device_id="fit-00001"
            )
            ```
        """
        # Get LOINC mapping
        loinc_mapping = self._loinc_map.get(vital_type)
        if not loinc_mapping:
            raise ValueError(
                f"Unknown vital type: {vital_type}. "
                f"Available types: {', '.join(self._loinc_map.keys())}"
            )

        # Determine interpretation (high/low/normal)
        interpretation = self._get_interpretation(
            value,
            loinc_mapping["referenceRange"]["low"],
            loinc_mapping["referenceRange"]["high"]
        )

        # Build FHIR Observation resource
        observation = {
            "resourceType": "Observation",
            "meta": {
                "profile": [f"{self.NRCES_PROFILE_BASE}ObservationVitalSigns"],
                "versionId": "1",
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            },
            "status": "final",
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": "vital-signs",
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": loinc_mapping["loincCode"],
                    "display": loinc_mapping["loincDisplay"]
                }],
                "text": loinc_mapping["loincDisplay"]
            },
            "subject": {
                "reference": f"Patient/{patient_id}",
                "display": f"Patient {patient_id}"
            },
            "effectiveDateTime": timestamp.isoformat(),
            "issued": datetime.utcnow().isoformat() + "Z",
            "valueQuantity": {
                "value": value,
                "unit": loinc_mapping["ucumUnit"],
                "system": "http://unitsofmeasure.org",
                "code": loinc_mapping["ucumCode"]
            },
            "interpretation": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                    "code": interpretation,
                    "display": interpretation.capitalize()
                }]
            }]
        }

        # Add reference ranges if available
        if loinc_mapping["referenceRange"]["low"] is not None:
            observation["referenceRange"] = [{
                "low": {
                    "value": loinc_mapping["referenceRange"]["low"],
                    "unit": loinc_mapping["ucumUnit"],
                    "system": "http://unitsofmeasure.org",
                    "code": loinc_mapping["ucumCode"]
                },
                "high": {
                    "value": loinc_mapping["referenceRange"]["high"],
                    "unit": loinc_mapping["ucumUnit"],
                    "system": "http://unitsofmeasure.org",
                    "code": loinc_mapping["ucumCode"]
                },
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/referencerange-meaning",
                        "code": "normal",
                        "display": "Normal Range"
                    }]
                }
            }]

        # Add performer (device is primary, staff if NFC tap)
        performers = [{
            "reference": f"Device/{device_id}",
            "display": f"ESP32 Watch {device_id}"
        }]

        if performer_staff_id:
            performers.append({
                "reference": f"Practitioner/{performer_staff_id}",
                "display": f"Staff {performer_staff_id}"
            })

        observation["performer"] = performers

        # Add encounter if NFC interaction logged
        if encounter_id:
            observation["encounter"] = {
                "reference": f"Encounter/{encounter_id}"
            }

        return observation

    def _get_interpretation(
        self,
        value: float,
        low: Optional[float],
        high: Optional[float]
    ) -> str:
        """
        Determine observation interpretation based on reference range

        Returns:
            - "L" (Low) if value < low
            - "H" (High) if value > high
            - "N" (Normal) if within range
            - "N" (Normal) if no reference range provided
        """
        if low is None or high is None:
            return "N"  # No reference range, assume normal

        if value < low:
            return "L"  # Low
        elif value > high:
            return "H"  # High
        else:
            return "N"  # Normal

    def create_patient_with_abha(
        self,
        patient_id: str,
        abha_address: Optional[str],
        abha_number: Optional[str],
        first_name: str,
        last_name: str,
        dob: str,
        gender: str,
        phone: str,
        mrn: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create NRCES Patient resource with ABHA identifiers

        Args:
            patient_id: Internal patient ID
            abha_address: ABHA address (e.g., john.doe@abdm)
            abha_number: 14-digit ABHA number
            first_name: Patient first name
            last_name: Patient last name
            dob: Date of birth (YYYY-MM-DD)
            gender: Gender (male/female/other/unknown)
            phone: Phone number with country code
            mrn: Medical Record Number (optional)

        Returns:
            FHIR Patient resource (dict) with ABHA identifiers

        Example:
            ```python
            patient = transformer.create_patient_with_abha(
                patient_id="PAT0001",
                abha_address="john.doe@abdm",
                abha_number="1234-5678-9012-3456",
                first_name="John",
                last_name="Doe",
                dob="1985-06-15",
                gender="male",
                phone="+91-9876543210",
                mrn="MRN001"
            )
            ```
        """
        identifiers = []

        # ABHA Address
        if abha_address:
            identifiers.append({
                "type": {
                    "coding": [{
                        "system": "https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code",
                        "code": "ABHA",
                        "display": "Ayushman Bharat Health Account"
                    }]
                },
                "system": "https://healthid.ndhm.gov.in",
                "value": abha_address
            })

        # ABHA Number (14-digit)
        if abha_number:
            identifiers.append({
                "type": {
                    "coding": [{
                        "system": "https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code",
                        "code": "ABHA-NUMBER",
                        "display": "ABHA Number"
                    }]
                },
                "system": "https://healthid.ndhm.gov.in",
                "value": abha_number
            })

        # Hospital MRN (if provided)
        if mrn:
            identifiers.append({
                "system": "https://hospital.example.com/mrn",
                "value": mrn
            })

        # Internal patient ID (always present)
        identifiers.append({
            "system": "https://hospital.example.com/patient-id",
            "value": patient_id
        })

        patient = {
            "resourceType": "Patient",
            "id": patient_id,
            "meta": {
                "profile": [f"{self.NRCES_PROFILE_BASE}Patient"],
                "versionId": "1",
                "lastUpdated": datetime.utcnow().isoformat() + "Z"
            },
            "identifier": identifiers,
            "name": [{
                "text": f"{first_name} {last_name}",
                "family": last_name,
                "given": [first_name]
            }],
            "telecom": [{
                "system": "phone",
                "value": phone,
                "use": "mobile"
            }],
            "gender": gender.lower(),
            "birthDate": dob
        }

        return patient

    def create_device_esp32_watch(
        self,
        device_id: str,
        serial_number: str,
        mac_address: str,
        firmware_version: str,
        battery_level: int,
        patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create FHIR Device resource for ESP32 watch

        Args:
            device_id: Device identifier (e.g., fit-00001)
            serial_number: Device serial number
            mac_address: MAC address
            firmware_version: Firmware version (e.g., v5.2.13)
            battery_level: Battery percentage (0-100)
            patient_id: Currently assigned patient (optional)

        Returns:
            FHIR Device resource (dict)
        """
        device = {
            "resourceType": "Device",
            "id": device_id,
            "identifier": [{
                "system": "https://hospital.example.com/devices",
                "value": device_id
            }, {
                "type": {"text": "MAC Address"},
                "value": mac_address
            }],
            "status": "active",
            "manufacturer": "Hospital ESP32 Watches",
            "deviceName": [{
                "name": f"ESP32 Hospital Watch {device_id}",
                "type": "user-friendly-name"
            }],
            "modelNumber": "ESP32-WATCH-V5",
            "serialNumber": serial_number,
            "type": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "706172005",
                    "display": "Wearable monitoring device"
                }]
            },
            "property": [
                {
                    "type": {"text": "Battery Level"},
                    "valueQuantity": {
                        "value": battery_level,
                        "unit": "%",
                        "system": "http://unitsofmeasure.org",
                        "code": "%"
                    }
                },
                {
                    "type": {"text": "Firmware Version"},
                    "valueString": firmware_version
                }
            ]
        }

        # Add patient reference if assigned
        if patient_id:
            device["patient"] = {
                "reference": f"Patient/{patient_id}"
            }

        return device
