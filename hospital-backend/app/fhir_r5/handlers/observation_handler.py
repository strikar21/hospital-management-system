"""
Observation Handler - FHIR R5
Manages vital signs and other observations
Stores in TimescaleDB fhirObservations table
Supports: GET, POST
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import asyncpg


class ObservationHandler:
    """Handle FHIR Observation resources (stored in TimescaleDB)"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.pool = db_pool

    async def create_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new observation

        Args:
            observation: FHIR R5 Observation resource

        Returns:
            Created observation resource
        """
        # Validate required fields
        if 'resourceType' not in observation or observation['resourceType'] != 'Observation':
            raise ValueError("Invalid resource type. Must be 'Observation'")

        if 'id' not in observation:
            raise ValueError("Observation ID is required")

        if 'status' not in observation:
            observation['status'] = 'final'

        # Extract fields for indexing
        observation_id = observation['id']
        patient_id = observation.get('subject', {}).get('reference', '').replace('Patient/', '')
        device_id = observation.get('device', {}).get('reference', '').replace('Device/', '') if 'device' in observation else None

        # Extract code (LOINC)
        code = observation.get('code', {}).get('coding', [{}])[0].get('code', '')
        category = observation.get('category', [{}])[0].get('coding', [{}])[0].get('code', '')

        # Extract value
        value_quantity = observation.get('valueQuantity', {}).get('value')
        value_unit = observation.get('valueQuantity', {}).get('unit')

        # Extract effective time
        effective_time = observation.get('effectiveDateTime')

        if not effective_time:
            effective_time = datetime.now(timezone.utc).isoformat()

        # Convert ISO string to datetime
        if isinstance(effective_time, str):
            time = datetime.fromisoformat(effective_time.replace('Z', '+00:00'))
        else:
            time = datetime.now(timezone.utc)

        # Add metadata
        if 'meta' not in observation:
            observation['meta'] = {}

        observation['meta']['lastUpdated'] = datetime.now(timezone.utc).isoformat()

        # Insert into TimescaleDB
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO fhirObservations
                (time, observationId, patientId, deviceId, observation,
                 code, category, valueQuantity, valueUnit, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, time, observation_id, patient_id, device_id,
               observation, code, category, value_quantity, value_unit, observation['status'])

        return observation

    async def get_observations(
        self,
        patient_id: Optional[str] = None,
        code: Optional[str] = None,
        category: Optional[str] = None,
        device_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search observations with filters

        Args:
            patient_id: Filter by patient
            code: Filter by LOINC code
            category: Filter by category
            device_id: Filter by device
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of observation resources
        """
        query = "SELECT observation FROM fhirObservations WHERE 1=1"
        params = []
        param_counter = 1

        # Build dynamic query
        if patient_id:
            query += f" AND patientId = ${param_counter}"
            params.append(patient_id)
            param_counter += 1

        if code:
            query += f" AND code = ${param_counter}"
            params.append(code)
            param_counter += 1

        if category:
            query += f" AND category = ${param_counter}"
            params.append(category)
            param_counter += 1

        if device_id:
            query += f" AND deviceId = ${param_counter}"
            params.append(device_id)
            param_counter += 1

        if start_time:
            query += f" AND time >= ${param_counter}"
            params.append(start_time)
            param_counter += 1

        if end_time:
            query += f" AND time <= ${param_counter}"
            params.append(end_time)
            param_counter += 1

        query += f" ORDER BY time DESC LIMIT ${param_counter} OFFSET ${param_counter + 1}"
        params.extend([limit, offset])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [row['observation'] for row in rows]

    async def get_latest_observation(
        self,
        patient_id: str,
        code: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest observation for a patient and code

        Args:
            patient_id: Patient ID
            code: LOINC code

        Returns:
            Latest observation or None
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT observation FROM fhirObservations
                WHERE patientId = $1 AND code = $2
                ORDER BY time DESC
                LIMIT 1
            """, patient_id, code)

        return row['observation'] if row else None

    async def get_observation_stats(
        self,
        patient_id: str,
        code: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for observations

        Args:
            patient_id: Patient ID
            code: LOINC code
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Statistics (min, max, avg, count)
        """
        query = """
            SELECT
                COUNT(*) as count,
                MIN(valueQuantity) as min_value,
                MAX(valueQuantity) as max_value,
                AVG(valueQuantity) as avg_value
            FROM fhirObservations
            WHERE patientId = $1 AND code = $2
        """
        params = [patient_id, code]
        param_counter = 3

        if start_time:
            query += f" AND time >= ${param_counter}"
            params.append(start_time)
            param_counter += 1

        if end_time:
            query += f" AND time <= ${param_counter}"
            params.append(end_time)
            param_counter += 1

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        return {
            'count': row['count'] or 0,
            'min': float(row['min_value']) if row['min_value'] else None,
            'max': float(row['max_value']) if row['max_value'] else None,
            'avg': float(row['avg_value']) if row['avg_value'] else None
        }
