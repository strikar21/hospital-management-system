"""
Patient Repository - Data access layer for patient operations
Implements all patient-related database operations with medical record support
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date
import logging

from .base_repository import BaseRepository
from ..models.patient import Patient


class PatientRepository(BaseRepository[Patient]):
    """
    Patient repository handling all patient data operations
    Includes medical records, notes, and discharge management
    """

    def __init__(self):
        super().__init__("patients", Patient)

    # ================================
    # PATIENT CORE OPERATIONS
    # ================================

    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get patient records by patient ID (implements base class abstract method)"""
        # For patients, this is the same as get_by_id since patient_id IS the id
        result = await self.get_by_id(patient_id)
        return [result] if result else []

    async def get_complete_patient_data(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient with all associated medical records"""
        try:
            # Use actual tables with data (patientnotes has 10 records, therapy is standard)
            query = """
                SELECT
                    p.*,
                    json_agg(DISTINCT pn.*) FILTER (WHERE pn.id IS NOT NULL) as notes,
                    json_agg(DISTINCT m.*) FILTER (WHERE m.id IS NOT NULL) as medications,
                    json_agg(DISTINCT i.*) FILTER (WHERE i.id IS NOT NULL) as investigations,
                    json_agg(DISTINCT t.*) FILTER (WHERE t.id IS NOT NULL) as therapies
                FROM patients p
                LEFT JOIN patientnotes pn ON p.id = pn."patientId"
                LEFT JOIN medications m ON p.id = m."patientId"
                LEFT JOIN investigations i ON p.id = i."patientId"
                LEFT JOIN therapies t ON p.id = t."patientId"
                WHERE p.id = $1
                GROUP BY p.id
            """

            results = await self.execute_custom_query(query, [patient_id])
            return results[0] if results else None

        except Exception as e:
            self.logger.error(f"Error fetching complete patient data for {patient_id}: {e}")
            raise

    async def search_patients(self, search_query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search patients by name, ID, or room number"""
        try:
            # No deletedAt column exists in patients table
            query = """
                SELECT * FROM patients
                WHERE (
                    LOWER("firstName") ILIKE $1
                    OR LOWER("lastName") ILIKE $1
                    OR id ILIKE $1
                    OR "roomNumber" ILIKE $1
                    OR LOWER(CONCAT("firstName", ' ', "lastName")) ILIKE $1
                )
                ORDER BY
                    CASE
                        WHEN id ILIKE $1 THEN 1
                        WHEN "roomNumber" ILIKE $1 THEN 2
                        ELSE 3
                    END,
                    "firstName", "lastName"
                LIMIT $2
            """

            search_pattern = f"%{search_query.lower()}%"
            return await self.execute_custom_query(query, [search_pattern, limit])

        except Exception as e:
            self.logger.error(f"Error searching patients with query '{search_query}': {e}")
            raise

    async def get_patients_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get patients filtered by status"""
        return await self.get_all(filters={'status': status})

    async def get_patients_by_room(self, room_number: str) -> List[Dict[str, Any]]:
        """Get patients in specific room"""
        return await self.get_all(filters={'roomNumber': room_number})

    async def get_patients_by_ward(self, ward: str) -> List[Dict[str, Any]]:
        """Get patients in specific ward"""
        # Assuming ward is part of room number (e.g., "ICU-101")
        try:
            query = """
                SELECT * FROM patients
                WHERE "deletedAt" IS NULL
                AND roomNumber ILIKE $1
                ORDER BY roomNumber, firstName, lastName
            """

            ward_pattern = f"{ward}%"
            return await self.execute_custom_query(query, [ward_pattern])

        except Exception as e:
            self.logger.error(f"Error fetching patients by ward '{ward}': {e}")
            raise

    # ================================
    # PATIENT NOTES OPERATIONS
    # ================================

    async def add_patient_note(self, patient_id: str, content: str, author_id: str,
                              author_name: str, author_role: str) -> Dict[str, Any]:
        """Add a note to patient record"""
        try:
            note_data = {
                'patientId': patient_id,
                'content': content,
                'authorId': author_id,
                'authorName': author_name,
                'authorRole': author_role,
                'timestamp': datetime.utcnow().isoformat()
            }

            query = """
                INSERT INTO patientnotes ("patientId", content, "authorId", "authorName", "authorRole")
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
            """

            result = await self.execute_custom_query(query, [
                patient_id, content, author_id, author_name, author_role
            ])

            return result[0] if result else None

        except Exception as e:
            self.logger.error(f"Error adding note to patient {patient_id}: {e}")
            raise

    async def update_patient_note(self, patient_id: str, note_id: str, content: str, editor_id: str) -> bool:
        """Update patient note"""
        try:
            query = """
                UPDATE patientnotes
                SET content = $1, "editedAt" = $2, "isEdited" = true
                WHERE id = $3 AND "patientId" = $4
                RETURNING id
            """

            now = datetime.utcnow()
            # Handle different note ID formats (from v1 logic)
            if note_id.isdigit():
                numeric_id = int(note_id)
            elif note_id.startswith('note_'):
                numeric_id = int(note_id.split('_')[1])
            else:
                raise ValueError(f"Invalid note ID format: {note_id}")

            result = await self.execute_custom_query(query, [content, now, numeric_id, patient_id])
            return len(result) > 0

        except Exception as e:
            self.logger.error(f"Error updating note {note_id} for patient {patient_id}: {e}")
            raise

    async def delete_patient_note(self, patient_id: str, note_id: str, deleted_by: str) -> bool:
        """Delete patient note"""
        try:
            query = """
                DELETE FROM patientnotes
                WHERE id = $1 AND "patientId" = $2
                RETURNING id
            """

            # Handle different note ID formats (from v1 logic)
            if note_id.isdigit():
                numeric_id = int(note_id)
            elif note_id.startswith('note_'):
                numeric_id = int(note_id.split('_')[1])
            else:
                raise ValueError(f"Invalid note ID format: {note_id}")

            result = await self.execute_custom_query(query, [numeric_id, patient_id])
            return len(result) > 0

        except Exception as e:
            self.logger.error(f"Error deleting note {note_id} for patient {patient_id}: {e}")
            raise

    # ================================
    # DISCHARGE OPERATIONS
    # ================================

    async def discharge_patient(self, patient_id: str, discharged_by: str) -> bool:
        """Discharge patient and update status"""
        try:
            query = """
                UPDATE patients
                SET
                    status = 'discharged',
                    "dischargeStatus" = 'completed',
                    "dischargeDate" = $1,
                    "updatedAt" = $1
                WHERE id = $2 AND "deletedAt" IS NULL AND status != 'discharged'
                RETURNING id
            """

            now = datetime.utcnow().isoformat()
            result = await self.execute_custom_query(query, [now, patient_id])
            return len(result) > 0

        except Exception as e:
            self.logger.error(f"Error discharging patient {patient_id}: {e}")
            raise

    # ================================
    # ALERT OPERATIONS
    # ================================

    async def acknowledge_alert(self, patient_id: str, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge patient alert"""
        try:
            query = """
                UPDATE patient_alerts
                SET
                    acknowledgedBy = $1,
                    acknowledgedAt = $2,
                    status = 'acknowledged',
                    "updatedAt" = $2
                WHERE id = $3 AND "patientId" = $4 AND status = 'active'
                RETURNING id
            """

            now = datetime.utcnow().isoformat()
            result = await self.execute_custom_query(query, [acknowledged_by, now, alert_id, patient_id])
            return len(result) > 0

        except Exception as e:
            self.logger.error(f"Error acknowledging alert {alert_id} for patient {patient_id}: {e}")
            raise

    # ================================
    # CASE ENTRY OPERATIONS
    # ================================

    async def add_case_entry(self, patient_id: str, entry_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add case entry to patient record"""
        try:
            query = """
                INSERT INTO "caseEntries" (
                    id, "patientId", "entryType", description, findings,
                    recommendations, "followUpDate", severity, category,
                    "createdBy", timestamp, "createdAt", "updatedAt"
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $11, $11)
                RETURNING *
            """

            import uuid
            entry_id = str(uuid.uuid4())
            now = datetime.utcnow()  # Use datetime object, not string

            result = await self.execute_custom_query(query, [
                entry_id,
                patient_id,
                entry_data.get('entryType'),
                entry_data.get('description'),
                entry_data.get('findings'),
                entry_data.get('recommendations'),
                entry_data.get('followUpDate'),
                entry_data.get('severity'),
                entry_data.get('category'),
                created_by,
                now
            ])

            return result[0] if result else None

        except Exception as e:
            self.logger.error(f"Error adding case entry to patient {patient_id}: {e}")
            raise

    async def get_case_entries(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all case entries for patient"""
        try:
            query = """
                SELECT * FROM "caseEntries"
                WHERE "patientId" = $1 AND "deletedAt" IS NULL
                ORDER BY timestamp DESC
            """

            return await self.execute_custom_query(query, [patient_id])

        except Exception as e:
            self.logger.error(f"Error fetching case entries for patient {patient_id}: {e}")
            raise

    async def get_aggregated_timeline(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get aggregated timeline of all medical activities for patient"""
        try:
            timeline_entries = []

            # Get medications
            medications_query = """
                SELECT id, name, dosage, frequency, route, status, "prescribedBy",
                       "createdAt" as timestamp, 'medication' as entry_type
                FROM medications
                WHERE "patientId" = $1
                ORDER BY "createdAt" DESC
            """
            medications = await self.execute_custom_query(medications_query, [patient_id])
            for med in medications:
                timeline_entries.append({
                    'id': f"med_{med['id']}",
                    'timestamp': med['timestamp'],
                    'type': 'medication',
                    'description': f"Medication prescribed: {med['name']} - {med['dosage']} {med['frequency']} via {med['route']}",
                    'performedBy': med['prescribedBy'],
                    'canEdit': True,
                    'details': med
                })

            # Get investigations
            investigations_query = """
                SELECT id, name, type, status, results, "performedBy",
                       "createdAt" as timestamp, 'investigation' as entry_type
                FROM investigations
                WHERE "patientId" = $1
                ORDER BY "createdAt" DESC
            """
            investigations = await self.execute_custom_query(investigations_query, [patient_id])
            for inv in investigations:
                timeline_entries.append({
                    'id': f"inv_{inv['id']}",
                    'timestamp': inv['timestamp'],
                    'type': 'investigation',
                    'description': f"Investigation ordered: {inv['name']} ({inv['type']}, {inv['status']})",
                    'performedBy': inv['performedBy'],
                    'canEdit': True,
                    'details': inv
                })

            # Get therapy sessions
            therapy_query = """
                SELECT id, "therapyType" as type, description, frequency, status, "createdBy" as "performedBy",
                       "createdAt" as timestamp, 'therapy' as entry_type
                FROM therapies
                WHERE "patientId" = $1
                ORDER BY "createdAt" DESC
            """
            therapies = await self.execute_custom_query(therapy_query, [patient_id])
            for therapy in therapies:
                timeline_entries.append({
                    'id': f"therapy_{therapy['id']}",
                    'timestamp': therapy['timestamp'],
                    'type': 'therapy',
                    'description': f"Therapy prescribed: {therapy['type']} - {therapy['description']} ({therapy['frequency']})",
                    'performedBy': therapy['performedBy'],
                    'canEdit': True,
                    'details': therapy
                })

            # Get patient notes
            notes_query = """
                SELECT id, content, "authorId" as "performedBy", "authorName", "authorRole",
                       timestamp, 'note' as entry_type
                FROM patientnotes
                WHERE "patientId" = $1
                ORDER BY timestamp DESC
            """
            notes = await self.execute_custom_query(notes_query, [patient_id])
            for note in notes:
                note_type = 'doctorNotes' if 'doctor' in note['authorRole'].lower() else 'nursingNotes'
                timeline_entries.append({
                    'id': f"note_{note['id']}",
                    'timestamp': note['timestamp'],
                    'type': note_type,
                    'description': f"Note by {note['authorName']}: {note['content']}",
                    'performedBy': note['performedBy'],
                    'performedByName': note['authorName'],
                    'canEdit': True,
                    'details': note
                })

            # Get dedicated case entries
            case_entries_query = """
                SELECT id, "entryType" as type, description, "createdBy" as "performedBy",
                       timestamp, 'caseEntry' as entry_type
                FROM "caseEntries"
                WHERE "patientId" = $1 AND "deletedAt" IS NULL
                ORDER BY timestamp DESC
            """
            case_entries = await self.execute_custom_query(case_entries_query, [patient_id])
            for entry in case_entries:
                timeline_entries.append({
                    'id': f"case_{entry['id']}",
                    'timestamp': entry['timestamp'],
                    'type': entry['type'],
                    'description': entry['description'],
                    'performedBy': entry['performedBy'],
                    'canEdit': True,
                    'details': entry
                })

            # Get patient alerts and acknowledgments
            alerts_query = """
                SELECT id, message, severity, "createdAt" as timestamp,
                       'vitalAlert' as entry_type, status, "acknowledgedBy", "acknowledgedAt"
                FROM patient_alerts
                WHERE "patientId" = $1
                ORDER BY "createdAt" DESC
            """
            alerts = await self.execute_custom_query(alerts_query, [patient_id])
            for alert in alerts:
                # Add alert creation entry
                timeline_entries.append({
                    'id': f"alert_{alert['id']}",
                    'timestamp': alert['timestamp'],
                    'type': 'vitalAlert',
                    'description': f"Alert: {alert['message']} (Severity: {alert['severity']})",
                    'performedBy': 'SYSTEM',
                    'canEdit': False,
                    'details': alert
                })

                # Add alert acknowledgment entry if acknowledged
                if alert['status'] == 'acknowledged' and alert['acknowledgedAt']:
                    timeline_entries.append({
                        'id': f"alert_ack_{alert['id']}",
                        'timestamp': alert['acknowledgedAt'],
                        'type': 'alertAcknowledged',
                        'description': f"Alert acknowledged: {alert['message']}",
                        'performedBy': alert['acknowledgedBy'],
                        'canEdit': False,
                        'details': alert
                    })

            # Resolve staff names for all entries
            staff_ids = set()
            for entry in timeline_entries:
                if entry.get('performedBy') and entry['performedBy'] not in ['SYSTEM', 'System']:
                    staff_ids.add(entry['performedBy'])

            if staff_ids:
                staff_names = await self.get_staff_names(list(staff_ids))

                # Add performedByName to entries that don't have it
                for entry in timeline_entries:
                    performed_by = entry.get('performedBy')
                    if performed_by and performed_by in staff_names and not entry.get('performedByName'):
                        entry['performedByName'] = staff_names[performed_by]

            # Sort all entries by timestamp (newest first)
            timeline_entries.sort(key=lambda x: x['timestamp'], reverse=True)

            return timeline_entries

        except Exception as e:
            self.logger.error(f"Error fetching aggregated timeline for patient {patient_id}: {e}")
            raise

    # ================================
    # UTILITY METHODS
    # ================================

    def calculate_age(self, birth_date: Any) -> int:
        """Calculate age from birth date"""
        try:
            if not birth_date:
                return 0

            if isinstance(birth_date, str):
                birth_date = datetime.fromisoformat(birth_date.replace('Z', '+00:00')).date()
            elif isinstance(birth_date, datetime):
                birth_date = birth_date.date()

            today = date.today()
            age = today.year - birth_date.year

            # Check if birthday hasn't occurred this year yet
            if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
                age -= 1

            return max(0, age)

        except Exception as e:
            self.logger.error(f"Error calculating age: {e}")
            return 0

    async def get_staff_names(self, staff_ids: List[str]) -> Dict[str, str]:
        """Get staff names by IDs"""
        try:
            if not staff_ids:
                return {}

            # Create placeholders for PostgreSQL ($1, $2, $3, etc.)
            placeholders = ','.join([f'${i+1}' for i in range(len(staff_ids))])

            query = f"""
                SELECT id, "firstName", "lastName"
                FROM staff
                WHERE id IN ({placeholders})
            """

            rows = await self.execute_custom_query(query, staff_ids)

            # Build staff name mapping
            staff_names = {}
            for row in rows:
                staff_id = row['id']
                first_name = row['firstName'] or ''
                last_name = row['lastName'] or ''

                # Format name based on role prefix
                if staff_id.startswith('DOC'):
                    staff_names[staff_id] = f"Dr. {first_name} {last_name}".strip()
                else:
                    staff_names[staff_id] = f"{first_name} {last_name}".strip()

            return staff_names

        except Exception as e:
            self.logger.error(f"Error getting staff names: {e}")
            return {}