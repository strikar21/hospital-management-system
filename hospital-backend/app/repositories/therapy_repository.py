"""
Therapy Repository - Data access layer for therapy operations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .base_repository import BaseRepository
from ..core.database import getDbConnection
from ..services.audit import logAuditEvent


class TherapyRepository(BaseRepository):
    """Therapy repository for all therapy-related database operations"""

    def __init__(self):
        super().__init__("therapy", None)

    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get therapies by patient ID"""
        return await self.get_all(filters={'patientId': patient_id})

    async def get_therapy_sessions_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get therapy sessions by patient ID"""
        query = """
            SELECT ts.*, t.type as therapy_type, t.description as therapy_description
            FROM therapysessions ts
            JOIN therapy t ON ts."therapyId" = t.id::text
            WHERE ts."patientId" = $1
            ORDER BY ts."scheduledDate" DESC
        """

        result = await self.execute_custom_query(query, [patient_id])
        return result if result else []

    async def add_therapy(self, patient_id: str, therapy_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add therapy to patient"""
        try:
            # Prepare therapy record (no id - database handles SERIAL ID)
            therapy_record = {
                'patientId': patient_id,
                'type': therapy_data.get('therapy_type') or therapy_data.get('type'),
                'description': therapy_data.get('description'),
                'frequency': therapy_data.get('frequency'),
                'duration': therapy_data.get('duration'),
                'prescribedBy': therapy_data.get('prescribed_by') or therapy_data.get('prescribedBy'),
                'createdBy': created_by,  # Audit trail - who created this record
                'notes': therapy_data.get('notes'),
                'status': 'active'
            }

            # Custom insert for therapy table (SERIAL ID)
            columns = list(therapy_record.keys())
            quoted_columns = [f'"{col}"' if any(c.isupper() for c in col) else col for col in columns]
            placeholders = [f'${i+1}' for i in range(len(columns))]
            values = list(therapy_record.values())

            query = f"""
                INSERT INTO {self.table_name} ({', '.join(quoted_columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """

            async with getDbConnection() as conn:
                result = await conn.fetchrow(query, *values)

                if result:
                    # Audit logging
                    await logAuditEvent(
                        userId=created_by,
                        action="create_therapy",
                        resourceType="therapy",
                        resourceId=str(result['id']),
                        details=f"Created therapy: {therapy_record['type']} for patient {patient_id}"
                    )

                    self.logger.info(f"Created therapy: {result['id']} for patient {patient_id}")
                    return dict(result)

            return None

        except Exception as e:
            self.logger.error(f"Error adding therapy to patient {patient_id}: {e}")
            raise

    async def update_therapy_status(self, patient_id: str, therapy_id: str, status: str, updated_by: str) -> bool:
        """Update therapy status"""
        result = await self.update(therapy_id, {'status': status}, updated_by)
        return result is not None

    async def add_therapy_session(self, patient_id: str, therapy_id: str, session_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add therapy session"""
        try:
            session_data['therapyId'] = therapy_id
            session_data['patientId'] = patient_id

            query = """
                INSERT INTO therapysessions (id, "therapyId", "patientId", duration, "sessionNotes", "performedBy", "createdBy", status, "sessionNumber", "scheduledDate", "createdAt", "updatedAt")
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $11)
                RETURNING *
            """

            import uuid
            from datetime import datetime
            session_id = str(uuid.uuid4())
            now = datetime.utcnow()

            result = await self.execute_custom_query(query, [
                session_id,
                therapy_id,
                patient_id,
                str(session_data.get('duration', '')),
                session_data.get('sessionNotes') or session_data.get('notes'),
                session_data.get('therapist') or session_data.get('performedBy'),
                created_by,  # Audit trail - who created this session record
                'completed',
                1,  # Default session number
                now,  # Use datetime object for scheduledDate
                now   # Use datetime object for createdAt too
            ])

            return result[0] if result else None

        except Exception as e:
            self.logger.error(f"Error adding therapy session: {e}")
            raise