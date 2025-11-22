"""
FHIR Observation Service
Manages FHIR R5 Observation resources in TimescaleDB for vitals time-series data
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging
from uuid import UUID
import json

from .fhir_base_service import FhirBaseService


class FhirObservationService(FhirBaseService):
    """
    Service for managing FHIR R5 Observation resources (vitals)
    Uses TimescaleDB for time-series optimization
    """

    def __init__(self):
        super().__init__(table_name='fhir_observations', use_timescale=True)
        self.logger = logging.getLogger(__name__)

    # ================================
    # OBSERVATION CRUD OPERATIONS
    # ================================

    async def create_observation(self, observation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create FHIR R5 Observation (vitals reading)

        Args:
            observation_data: {
                "patientContextId": "uuid",
                "deviceId": "uuid",
                "code": "8867-4",  # LOINC code
                "codeDisplay": "Heart rate",
                "valueQuantity": 72,
                "valueUnit": "beats/min",
                "timestamp": "2025-11-18T10:30:00Z",
                "status": "final",
                "aiAnalysis": {"severity": "normal", "trend": "stable"},
                "isAbnormal": false,
                "dataQuality": "good"
            }

        Returns:
            Created Observation resource
        """
        try:
            # Build FHIR R5 Observation resource
            resource = self._build_observation_resource(observation_data)

            # Extract searchable fields
            extracted = self.extract_searchable_fields(observation_data)

            # Create with JSONB + extracted fields
            async with self.get_connection() as conn:
                query = """
                    INSERT INTO fhir_observations
                    (timestamp, resource, "patientContextId", "deviceId", "abhaNumber",
                     category, code, "codeDisplay", "valueQuantity", "valueUnit", status,
                     "aiAnalysis", "isAbnormal", "alertGenerated", "dataQuality", "signalStrength")
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    RETURNING id, timestamp, resource, "patientContextId", "deviceId", code, "valueQuantity", "valueUnit"
                """

                result = await conn.fetchrow(
                    query,
                    extracted['timestamp'],
                    json.dumps(resource),
                    UUID(extracted['patientContextId']),
                    UUID(extracted['deviceId']),
                    extracted.get('abhaNumber'),
                    extracted.get('category', 'vital-signs'),
                    extracted['code'],
                    extracted.get('codeDisplay'),
                    extracted.get('valueQuantity'),
                    extracted.get('valueUnit'),
                    extracted.get('status', 'final'),
                    json.dumps(extracted.get('aiAnalysis', {})),
                    extracted.get('isAbnormal', False),
                    extracted.get('alertGenerated', False),
                    extracted.get('dataQuality', 'good'),
                    extracted.get('signalStrength')
                )

                result_dict = dict(result)
                result_dict['resource'] = json.loads(result_dict['resource']) if isinstance(result_dict['resource'], str) else result_dict['resource']

                self.logger.debug(f"Created observation for patient {extracted['patientContextId']}, code {extracted['code']}")
                return result_dict

        except Exception as e:
            self.logger.error(f"Error creating observation: {e}")
            raise

    async def create_batch_observations(self, observations: List[Dict[str, Any]]) -> int:
        """
        Batch create observations for performance (ESP32 streaming)

        Args:
            observations: List of observation data dicts

        Returns:
            Number of observations created
        """
        try:
            if not observations:
                return 0

            async with self.get_connection() as conn:
                # Use COPY for bulk insert (fastest for time-series)
                query = """
                    INSERT INTO fhir_observations
                    (timestamp, resource, "patientContextId", "deviceId", code, "codeDisplay",
                     "valueQuantity", "valueUnit", status, "dataQuality")
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """

                rows = []
                for obs_data in observations:
                    resource = self._build_observation_resource(obs_data)
                    extracted = self.extract_searchable_fields(obs_data)

                    rows.append((
                        extracted['timestamp'],
                        json.dumps(resource),
                        UUID(extracted['patientContextId']),
                        UUID(extracted['deviceId']),
                        extracted['code'],
                        extracted.get('codeDisplay'),
                        extracted.get('valueQuantity'),
                        extracted.get('valueUnit'),
                        extracted.get('status', 'final'),
                        extracted.get('dataQuality', 'good')
                    ))

                # Execute batch insert
                await conn.executemany(query, rows)

                self.logger.info(f"Batch created {len(rows)} observations")
                return len(rows)

        except Exception as e:
            self.logger.error(f"Error batch creating observations: {e}")
            raise

    # ================================
    # QUERY OPERATIONS (Time-Series)
    # ================================

    async def get_latest_vitals(self, patient_context_id: str) -> List[Dict[str, Any]]:
        """
        Get most recent vitals for each LOINC code

        Returns:
            List of latest observations (one per vital type)
        """
        try:
            async with self.get_connection() as conn:
                # Use helper function from migration
                query = """
                    SELECT * FROM get_latest_vitals($1)
                """

                results = await conn.fetch(query, UUID(patient_context_id))
                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error getting latest vitals: {e}")
            raise

    async def get_vitals_trend(self, patient_context_id: str, loinc_code: str,
                              hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Get vitals trend for specific LOINC code over time

        Args:
            patient_context_id: Patient UUID
            loinc_code: LOINC code (8867-4 = heart rate)
            hours_back: How many hours back to query

        Returns:
            List of observations sorted by time
        """
        try:
            async with self.get_connection() as conn:
                # Use helper function from migration
                query = """
                    SELECT * FROM get_vitals_trend($1, $2, $3)
                """

                results = await conn.fetch(query, UUID(patient_context_id), loinc_code, hours_back)
                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error getting vitals trend: {e}")
            raise

    async def get_observations_in_timerange(self, patient_context_id: str,
                                           start_time: datetime,
                                           end_time: datetime,
                                           loinc_codes: Optional[List[str]] = None,
                                           limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get observations within time range

        Args:
            patient_context_id: Patient UUID
            start_time: Start of time range
            end_time: End of time range
            loinc_codes: Optional filter by LOINC codes
            limit: Max results

        Returns:
            List of observations
        """
        try:
            async with self.get_connection() as conn:
                where_clauses = [
                    '"patientContextId" = $1',
                    'timestamp >= $2',
                    'timestamp <= $3'
                ]
                values = [UUID(patient_context_id), start_time, end_time]
                param_count = 4

                if loinc_codes:
                    where_clauses.append(f'code = ANY(${param_count})')
                    values.append(loinc_codes)
                    param_count += 1

                where_sql = ' AND '.join(where_clauses)

                query = f"""
                    SELECT id, timestamp, code, "codeDisplay", "valueQuantity", "valueUnit",
                           status, "isAbnormal", "aiAnalysis", "dataQuality"
                    FROM fhir_observations
                    WHERE {where_sql}
                    ORDER BY timestamp ASC
                    LIMIT ${param_count}
                """

                values.append(limit)

                results = await conn.fetch(query, *values)

                result_list = []
                for row in results:
                    row_dict = dict(row)
                    if 'aiAnalysis' in row_dict:
                        row_dict['aiAnalysis'] = json.loads(row_dict['aiAnalysis']) if isinstance(row_dict['aiAnalysis'], str) else row_dict['aiAnalysis']
                    result_list.append(row_dict)

                return result_list

        except Exception as e:
            self.logger.error(f"Error getting observations in timerange: {e}")
            raise

    async def get_abnormal_observations(self, patient_context_id: str,
                                       hours_back: int = 24,
                                       limit: int = 100) -> List[Dict[str, Any]]:
        """Get abnormal/alert-worthy observations"""
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT id, timestamp, code, "codeDisplay", "valueQuantity", "valueUnit",
                           "aiAnalysis", "isAbnormal", "alertGenerated"
                    FROM fhir_observations
                    WHERE "patientContextId" = $1
                      AND "isAbnormal" = true
                      AND timestamp >= NOW() - ($2 || ' hours')::INTERVAL
                    ORDER BY timestamp DESC
                    LIMIT $3
                """

                results = await conn.fetch(query, UUID(patient_context_id), hours_back, limit)

                result_list = []
                for row in results:
                    row_dict = dict(row)
                    if 'aiAnalysis' in row_dict:
                        row_dict['aiAnalysis'] = json.loads(row_dict['aiAnalysis']) if isinstance(row_dict['aiAnalysis'], str) else row_dict['aiAnalysis']
                    result_list.append(row_dict)

                return result_list

        except Exception as e:
            self.logger.error(f"Error getting abnormal observations: {e}")
            raise

    async def get_device_observations(self, device_id: str,
                                     hours_back: int = 1,
                                     limit: int = 1000) -> List[Dict[str, Any]]:
        """Get recent observations from a specific device"""
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT id, timestamp, "patientContextId", code, "codeDisplay",
                           "valueQuantity", "valueUnit", "dataQuality", "signalStrength"
                    FROM fhir_observations
                    WHERE "deviceId" = $1
                      AND timestamp >= NOW() - ($2 || ' hours')::INTERVAL
                    ORDER BY timestamp DESC
                    LIMIT $3
                """

                results = await conn.fetch(query, UUID(device_id), hours_back, limit)
                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error getting device observations: {e}")
            raise

    # ================================
    # AGGREGATIONS (Use Continuous Aggregates)
    # ================================

    async def get_aggregated_vitals(self, patient_context_id: str,
                                   loinc_code: str,
                                   bucket_size: str = '1 minute',
                                   hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Get aggregated vitals (min, max, avg) using continuous aggregates

        Args:
            patient_context_id: Patient UUID
            loinc_code: LOINC code
            bucket_size: '1 minute' or '1 hour'
            hours_back: Time range

        Returns:
            List of aggregated buckets
        """
        try:
            # Choose appropriate continuous aggregate view
            view_name = 'fhir_observations_1min' if bucket_size == '1 minute' else 'fhir_observations_1hour'

            async with self.get_connection() as conn:
                query = f"""
                    SELECT bucket, "avg_value", "min_value", "max_value",
                           "stddev_value", "abnormal_count", "reading_count"
                    FROM {view_name}
                    WHERE "patientContextId" = $1
                      AND code = $2
                      AND bucket >= NOW() - ($3 || ' hours')::INTERVAL
                    ORDER BY bucket ASC
                """

                results = await conn.fetch(query, UUID(patient_context_id), loinc_code, hours_back)
                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error getting aggregated vitals: {e}")
            raise

    # ================================
    # AI ANALYSIS UPDATES
    # ================================

    async def update_ai_analysis(self, observation_id: str, ai_analysis: Dict[str, Any],
                                is_abnormal: bool, alert_generated: bool = False) -> None:
        """
        Update AI analysis results for an observation

        Args:
            observation_id: Observation UUID
            ai_analysis: AI analysis results dict
            is_abnormal: Whether vitals are abnormal
            alert_generated: Whether an alert was sent
        """
        try:
            async with self.get_connection() as conn:
                query = """
                    UPDATE fhir_observations
                    SET "aiAnalysis" = $1,
                        "isAbnormal" = $2,
                        "alertGenerated" = $3
                    WHERE id = $4
                """

                await conn.execute(
                    query,
                    json.dumps(ai_analysis),
                    is_abnormal,
                    alert_generated,
                    UUID(observation_id)
                )

                self.logger.debug(f"Updated AI analysis for observation {observation_id}")

        except Exception as e:
            self.logger.error(f"Error updating AI analysis: {e}")
            raise

    # ================================
    # STATISTICS
    # ================================

    async def get_observation_stats(self, patient_context_id: str,
                                   hours_back: int = 24) -> Dict[str, Any]:
        """Get observation statistics for a patient"""
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT
                        COUNT(*) as total_observations,
                        COUNT(DISTINCT code) as unique_vitals,
                        SUM(CASE WHEN "isAbnormal" = true THEN 1 ELSE 0 END) as abnormal_count,
                        SUM(CASE WHEN "alertGenerated" = true THEN 1 ELSE 0 END) as alert_count,
                        MIN(timestamp) as earliest_observation,
                        MAX(timestamp) as latest_observation
                    FROM fhir_observations
                    WHERE "patientContextId" = $1
                      AND timestamp >= NOW() - ($2 || ' hours')::INTERVAL
                """

                result = await conn.fetchrow(query, UUID(patient_context_id), hours_back)
                return dict(result)

        except Exception as e:
            self.logger.error(f"Error getting observation stats: {e}")
            raise

    # ================================
    # VALIDATION & EXTRACTION
    # ================================

    async def validate_resource(self, resource: Dict[str, Any]) -> None:
        """Validate FHIR Observation resource"""
        if resource.get('resourceType') != 'Observation':
            raise ValueError("Resource type must be Observation")

        # Must have code (LOINC)
        if not resource.get('code'):
            raise ValueError("Observation must have a code")

        # Must have subject (patient)
        if not resource.get('subject'):
            raise ValueError("Observation must have a subject (patient)")

        # Must have value or dataAbsentReason
        if not resource.get('valueQuantity') and not resource.get('dataAbsentReason'):
            raise ValueError("Observation must have a value or dataAbsentReason")

    def extract_searchable_fields(self, observation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields from observation data for table columns"""
        extracted = {}

        # Required fields
        extracted['timestamp'] = observation_data.get('timestamp', datetime.utcnow())
        if isinstance(extracted['timestamp'], str):
            extracted['timestamp'] = datetime.fromisoformat(extracted['timestamp'].replace('Z', '+00:00'))

        extracted['patientContextId'] = observation_data['patientContextId']
        extracted['deviceId'] = observation_data['deviceId']
        extracted['code'] = observation_data['code']

        # Optional fields
        if 'abhaNumber' in observation_data:
            extracted['abhaNumber'] = observation_data['abhaNumber']
        if 'category' in observation_data:
            extracted['category'] = observation_data['category']
        if 'codeDisplay' in observation_data:
            extracted['codeDisplay'] = observation_data['codeDisplay']
        if 'valueQuantity' in observation_data:
            extracted['valueQuantity'] = float(observation_data['valueQuantity'])
        if 'valueUnit' in observation_data:
            extracted['valueUnit'] = observation_data['valueUnit']
        if 'valueString' in observation_data:
            extracted['valueString'] = observation_data['valueString']
        if 'status' in observation_data:
            extracted['status'] = observation_data['status']
        if 'aiAnalysis' in observation_data:
            extracted['aiAnalysis'] = observation_data['aiAnalysis']
        if 'isAbnormal' in observation_data:
            extracted['isAbnormal'] = bool(observation_data['isAbnormal'])
        if 'alertGenerated' in observation_data:
            extracted['alertGenerated'] = bool(observation_data['alertGenerated'])
        if 'dataQuality' in observation_data:
            extracted['dataQuality'] = observation_data['dataQuality']
        if 'signalStrength' in observation_data:
            extracted['signalStrength'] = int(observation_data['signalStrength'])

        return extracted

    def _build_observation_resource(self, observation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build FHIR R5 Observation resource from observation data"""
        resource = {
            "resourceType": "Observation",
            "status": observation_data.get('status', 'final'),
            "category": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": observation_data.get('category', 'vital-signs'),
                    "display": "Vital Signs"
                }]
            }],
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": observation_data['code'],
                    "display": observation_data.get('codeDisplay', '')
                }]
            },
            "subject": {
                "reference": f"PatientClinicalContext/{observation_data['patientContextId']}"
            },
            "effectiveDateTime": observation_data.get('timestamp', datetime.utcnow()).isoformat() + 'Z',
            "device": {
                "reference": f"Device/{observation_data['deviceId']}"
            }
        }

        # Add value
        if observation_data.get('valueQuantity') is not None:
            resource['valueQuantity'] = {
                "value": observation_data['valueQuantity'],
                "unit": observation_data.get('valueUnit', ''),
                "system": "http://unitsofmeasure.org"
            }

        # Add data quality extension
        if observation_data.get('dataQuality'):
            resource['extension'] = [{
                "url": "https://hospital.local/fhir/StructureDefinition/data-quality",
                "valueString": observation_data['dataQuality']
            }]

        return resource

    # ================================
    # LOINC CODE HELPERS
    # ================================

    LOINC_CODES = {
        'heart_rate': '8867-4',
        'spo2': '2708-6',
        'temperature': '8310-5',
        'respiratory_rate': '9279-1',
        'blood_pressure_systolic': '8480-6',
        'blood_pressure_diastolic': '8462-4',
        'glucose': '2339-0',
        'ecg': '131328'  # ECG study
    }

    @classmethod
    def get_loinc_code(cls, vital_type: str) -> str:
        """Get LOINC code for vital type"""
        return cls.LOINC_CODES.get(vital_type, '')

    @classmethod
    def get_vital_type(cls, loinc_code: str) -> str:
        """Get vital type from LOINC code"""
        reverse_map = {v: k for k, v in cls.LOINC_CODES.items()}
        return reverse_map.get(loinc_code, 'unknown')
