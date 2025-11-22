"""
FHIR R5 Observation Service (Native Internal Format)

This is the PRIMARY format for storing vitals observations.
Use R5→R4 transformer for ABDM/ABHA integration.

FHIR R5 Spec: https://hl7.org/fhir/R5/observation.html
"""

from datetime import datetime
from typing import Dict, Optional, Any, List
import logging

logger = logging.getLogger(__name__)


class FhirR5ObservationService:
    """
    FHIR R5 Observation Service (Internal Storage)

    This stores vitals in FHIR R5 format natively.
    For ABDM/ABHA, use the R5→R4 transformer.
    """

    # LOINC mapping cache (loaded from database)
    _loinc_map: Dict[str, Dict[str, Any]] = {}

    @classmethod
    async def initialize(cls, db_conn):
        """Load LOINC mapping from database"""
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

            logger.info(f"✅ FHIR R5 Observation Service initialized with {len(cls._loinc_map)} LOINC mappings")

        except Exception as e:
            logger.error(f"❌ Failed to initialize LOINC mappings: {e}")
            raise

    def create_observation_r5(
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
        Create FHIR R5 Observation (Internal Format)

        This is stored natively in TimescaleDB.
        Use transform_r5_to_r4() for ABDM integration.

        Args:
            patient_id: Patient identifier
            vital_type: Internal vital name (heartRate, oxygenSaturation, etc.)
            value: Measured value
            timestamp: Measurement timestamp
            device_id: Device identifier
            encounter_id: Optional encounter reference
            performer_staff_id: Optional staff who performed measurement

        Returns:
            FHIR R5 Observation resource
        """
        # Get LOINC mapping
        loinc_mapping = self._loinc_map.get(vital_type)
        if not loinc_mapping:
            raise ValueError(
                f"Unknown vital type: {vital_type}. "
                f"Available: {', '.join(self._loinc_map.keys())}"
            )

        # Determine interpretation
        interpretation = self._get_interpretation(
            value,
            loinc_mapping["referenceRange"]["low"],
            loinc_mapping["referenceRange"]["high"]
        )

        # Build FHIR R5 Observation
        observation = {
            "resourceType": "Observation",
            "meta": {
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
                    "display": self._get_interpretation_display(interpretation)
                }]
            }]
        }

        # Add reference range
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

        # Add performer (R5 uses 'performer' not 'performer[x]')
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

        # Add encounter if provided
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
        """Determine observation interpretation"""
        if low is None or high is None:
            return "N"

        if value < low:
            return "L"  # Low
        elif value > high:
            return "H"  # High
        else:
            return "N"  # Normal

    def _get_interpretation_display(self, code: str) -> str:
        """Get display name for interpretation code"""
        displays = {
            "N": "Normal",
            "L": "Low",
            "H": "High",
            "LL": "Critically Low",
            "HH": "Critically High"
        }
        return displays.get(code, "Normal")

    async def store_observation_in_timescale(
        self,
        observation_r5: Dict[str, Any],
        db_conn
    ) -> str:
        """
        Store FHIR R5 Observation in TimescaleDB

        Args:
            observation_r5: FHIR R5 Observation resource
            db_conn: TimescaleDB connection

        Returns:
            Observation ID
        """
        import json
        import uuid

        obs_id = str(uuid.uuid4())
        patient_id = observation_r5["subject"]["reference"].split("/")[1]
        device_id = observation_r5["performer"][0]["reference"].split("/")[1]

        # Extract vital data
        loinc_code = observation_r5["code"]["coding"][0]["code"]
        value = observation_r5["valueQuantity"]["value"]
        unit = observation_r5["valueQuantity"]["unit"]
        timestamp = observation_r5["effectiveDateTime"]

        # Store in TimescaleDB with FHIR JSON
        await db_conn.execute("""
            INSERT INTO fhir_observations_r5 (
                id,
                time,
                "patientId",
                "deviceId",
                "loincCode",
                value,
                unit,
                "fhirJson"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, obs_id, timestamp, patient_id, device_id, loinc_code, value, unit, json.dumps(observation_r5))

        logger.info(f"✅ Stored FHIR R5 Observation {obs_id} for patient {patient_id}")

        return obs_id
