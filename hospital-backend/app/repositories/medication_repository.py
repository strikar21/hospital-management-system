"""
Medication Repository - Data access layer for medication operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from .base_repository import BaseRepository
from ..core.database import getDbConnection
from ..services.audit import logAuditEvent


class MedicationRepository(BaseRepository):
    """Medication repository for all medication-related database operations"""

    def __init__(self):
        super().__init__("medications", None)

    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get medications by patient ID"""
        return await self.get_all(filters={'patientId': patient_id})

    async def add_medication(self, patient_id: str, medication_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add medication to patient"""
        try:
            # DEBUG: Log what we're receiving
            self.logger.info(f"DEBUG add_medication: patient_id={patient_id}, created_by={created_by}")
            self.logger.info(f"DEBUG medication_data keys: {list(medication_data.keys())}")

            # Prepare medication record (no id, createdAt, updatedAt - database handles these)
            # Note: medication_data comes from service layer already transformed to snake_case
            med_data = {
                'patientId': patient_id,
                'name': medication_data.get('medication_name'),  # transformed from medicationName
                'dosage': medication_data.get('dosage'),
                'frequency': medication_data.get('frequency'),
                'route': medication_data.get('route'),
                'startDate': medication_data.get('start_date') or medication_data.get('startDate', datetime.utcnow()),
                'endDate': medication_data.get('end_date') or medication_data.get('endDate'),
                'duration': medication_data.get('duration'),
                'prescribedBy': medication_data.get('prescribed_by'),  # transformed from prescribedBy
                'createdBy': created_by,  # Audit trail - who created this record
                'status': 'active'
            }

            # DEBUG: Log the prepared data
            self.logger.info(f"DEBUG med_data prepared: prescribedBy={med_data.get('prescribedBy')}, createdBy={med_data.get('createdBy')}")

            # Custom insert for medications table (SERIAL ID, auto timestamps)
            columns = list(med_data.keys())
            quoted_columns = [f'"{col}"' if any(c.isupper() for c in col) else col for col in columns]
            placeholders = [f'${i+1}' for i in range(len(columns))]
            values = list(med_data.values())

            query = f"""
                INSERT INTO {self.table_name} ({', '.join(quoted_columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """

            async with getDbConnection() as conn:
                self.logger.info(f"DEBUG Executing INSERT query with {len(values)} values")
                self.logger.info(f"DEBUG Query columns: {quoted_columns}")

                result = await conn.fetchrow(query, *values)

                if result:
                    # DEBUG: Check what was actually inserted
                    self.logger.info(f"DEBUG Inserted medication ID={result['id']}, createdBy in result: {result.get('createdBy')}")

                    # Audit logging
                    await logAuditEvent(
                        userId=created_by,
                        action=f"create_medication",
                        resourceType="medication",
                        resourceId=str(result['id']),
                        details=f"Created medication: {med_data['name']} for patient {patient_id}"
                    )

                    self.logger.info(f"Created medication: {result['id']} for patient {patient_id}")
                    return dict(result)

            return None

        except Exception as e:
            self.logger.error(f"Error adding medication to patient {patient_id}: {e}")
            raise

    async def update_medication_status(self, patient_id: str, medication_id: str, status: str, updated_by: str) -> bool:
        """Update medication status"""
        try:
            # Convert string ID to integer for SERIAL primary key
            med_id = int(medication_id)
            result = await self.update(med_id, {'status': status}, updated_by)
            return result is not None

        except Exception as e:
            self.logger.error(f"Error updating medication {medication_id}: {e}")
            raise

    async def get_medication_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get complete medication history for patient"""
        try:
            query = """
                SELECT m.*, json_agg(ma.*) FILTER (WHERE ma.id IS NOT NULL) as administrations
                FROM medications m
                LEFT JOIN medicationadministrations ma ON m.id = ma."medicationId"
                WHERE m."patientId" = $1
                GROUP BY m.id
                ORDER BY m."createdAt" DESC
            """

            return await self.execute_custom_query(query, [patient_id])

        except Exception as e:
            self.logger.error(f"Error fetching medication history for patient {patient_id}: {e}")
            raise

    async def get_medications_with_schedule(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get medications with their next scheduled administration times"""
        try:
            query = """
                SELECT
                    m.*,
                    (
                        SELECT json_build_object(
                            'nextDose', ma."scheduledTime",
                            'status', ma.status,
                            'notes', ma.notes
                        )
                        FROM medicationadministrations ma
                        WHERE ma."medicationId" = m.id
                        AND ma."patientId" = m."patientId"
                        AND ma."scheduledTime" > NOW()
                        AND ma.status IN ('scheduled', 'prn')
                        ORDER BY ma."scheduledTime" ASC
                        LIMIT 1
                    ) as next_administration
                FROM medications m
                WHERE m."patientId" = $1
                ORDER BY m."createdAt" DESC
            """

            return await self.execute_custom_query(query, [patient_id])

        except Exception as e:
            self.logger.error(f"Error fetching medications with schedule for patient {patient_id}: {e}")
            raise