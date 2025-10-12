"""
Atomic Medical Action Service - Phase 2 Implementation
Provides failproof atomic operations for all medical actions
Eliminates the "change in 2-3 places" problem through database-level atomicity
"""

import asyncio
import asyncpg
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager

import logging
from ..core.database import getDbConnection
from ..services.audit import logAuditEvent
from ..repositories.patient_repository import PatientRepository
from ..middleware.staff_resolution_middleware import resolve_staff_in_response
from ..core.exceptions import (
    ValidationException,
    NotFoundException,
    DatabaseException,
    BusinessRuleException,
    ConflictException
)


class MedicalActionService:
    """
    Atomic Medical Action Service - Single point of truth for all medical operations

    Core Principle: One Action = One Transaction = One Source of Truth
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.patient_repository = PatientRepository()

    @asynccontextmanager
    async def atomic_transaction(self, patient_id: str):
        """
        Create atomic transaction context with patient row locking
        Prevents race conditions and ensures data consistency
        """
        async with getDbConnection() as conn:
            async with conn.transaction():
                try:
                    # Lock patient row to prevent concurrent modifications
                    locked_patient = await conn.fetchrow(
                        'SELECT lock_patient_for_atomic_operation($1)',
                        patient_id
                    )

                    if not locked_patient:
                        raise ValueError(f"Patient {patient_id} not found or unavailable")

                    self.logger.info(f"Acquired atomic lock for patient {patient_id}")

                    # Yield the connection for atomic operations
                    yield conn

                    self.logger.info(f"Released atomic lock for patient {patient_id}")

                except Exception as e:
                    self.logger.error(f"Atomic transaction failed for patient {patient_id}: {e}")
                    raise

    async def execute_medical_action(
        self,
        action_type: str,
        patient_id: str,
        action_data: Dict[str, Any],
        performedBy: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute any medical action atomically with automatic case entry creation

        Args:
            action_type: Type of medical action ('medication', 'investigation', 'therapy', 'note')
            patient_id: Patient ID
            action_data: Medical action data
            performedBy: Staff ID performing the action
            idempotency_key: Optional key for idempotent operations

        Returns:
            Complete result with medical record and case entry
        """

        # Validate inputs
        if not action_type or not action_type.strip():
            raise ValidationException("Action type is required", field="action_type")

        if not patient_id or not patient_id.strip():
            raise ValidationException("Patient ID is required", field="patient_id")

        if not performedBy or not performedBy.strip():
            raise ValidationException("Performed by staff ID is required", field="performedBy")

        if not action_data or not isinstance(action_data, dict):
            raise ValidationException("Action data must be a non-empty dictionary", field="action_data")

        # Validate action_type
        valid_action_types = [
            'medication', 'investigation', 'therapy', 'note',
            'medication_administration', 'therapy_session',
            'alert_acknowledgment', 'investigation_completion',
            'medication_status_change'
        ]
        if action_type not in valid_action_types:
            raise ValidationException(
                f"Invalid action type: {action_type}. Must be one of: {', '.join(valid_action_types)}",
                field="action_type"
            )

        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = f"{action_type}_{patient_id}_{uuid.uuid4()}"

        try:
            # Check for existing operation (idempotency)
            existing_result = await self._check_existing_operation(idempotency_key)
            if existing_result:
                self.logger.info(f"Returning cached result for idempotency key: {idempotency_key}")
                return existing_result

            # Execute atomic medical action
            async with self.atomic_transaction(patient_id) as conn:

                # Start transaction tracking
                transaction_id = str(uuid.uuid4())
                await self._start_transaction_tracking(
                    conn, transaction_id, patient_id, action_type, action_data
                )

                try:
                    # Execute the specific medical action
                    medical_record = await self._execute_action(
                        conn, action_type, patient_id, action_data, performedBy
                    )

                    # Auto-create case entry in same transaction
                    case_entry = await self._create_case_entry(
                        conn, patient_id, action_type, medical_record, performedBy
                    )

                    # Store idempotency result
                    result = {
                        'medical_record': self._transform_to_camel_case(medical_record),
                        'case_entry': self._transform_to_camel_case(case_entry),
                        'success': True,
                        'action_type': action_type,
                        'transaction_id': transaction_id
                    }

                    await self._store_operation_result(conn, idempotency_key, result)

                    # Complete transaction tracking
                    await self._complete_transaction_tracking(conn, transaction_id, result)

                    # Audit logging
                    await logAuditEvent(
                        userId=performedBy,
                        action=f"atomic_{action_type}",
                        resourceType=action_type,
                        resourceId=str(medical_record.get('id')),
                        details=f"Atomic {action_type} for patient {patient_id}"
                    )

                    self.logger.info(f"Atomic {action_type} completed successfully for patient {patient_id}")
                    return result

                except ValidationException:
                    # Mark transaction as failed and re-raise
                    await self._fail_transaction_tracking(conn, transaction_id, "Validation error")
                    raise

                except asyncpg.UniqueViolationError as e:
                    # Duplicate record
                    await self._fail_transaction_tracking(conn, transaction_id, str(e))
                    raise ConflictException(
                        f"A {action_type} record with this identifier already exists"
                    )

                except asyncpg.ForeignKeyViolationError as e:
                    # Referenced record doesn't exist
                    await self._fail_transaction_tracking(conn, transaction_id, str(e))
                    raise ValidationException(
                        f"Referenced {action_type} record does not exist"
                    )

                except asyncpg.PostgresError as e:
                    # Other database errors
                    await self._fail_transaction_tracking(conn, transaction_id, str(e))
                    self.logger.error(
                        f"Database error in atomic {action_type}: {e}",
                        exc_info=True
                    )
                    raise DatabaseException(f"execute {action_type}", str(e))

                except Exception as e:
                    # Mark transaction as failed
                    await self._fail_transaction_tracking(conn, transaction_id, str(e))
                    raise

        except (ValidationException, NotFoundException, ConflictException, DatabaseException):
            # Re-raise custom exceptions
            raise

        except asyncpg.PostgresError as e:
            # Database errors at transaction level
            self.logger.error(
                f"Database error in atomic medical action {action_type}: {e}",
                exc_info=True
            )
            raise DatabaseException(f"atomic {action_type}", str(e))

        except Exception as e:
            # Unexpected errors
            self.logger.error(
                f"Unexpected error in atomic medical action {action_type}: {e}",
                exc_info=True
            )
            raise

    async def _execute_action(
        self,
        conn: asyncpg.Connection,
        action_type: str,
        patient_id: str,
        action_data: Dict[str, Any],
        performedBy: str
    ) -> Dict[str, Any]:
        """Execute specific medical action based on type"""

        if action_type == 'medication':
            return await self._create_medication(conn, patient_id, action_data, performedBy)
        elif action_type == 'investigation':
            return await self._create_investigation(conn, patient_id, action_data, performedBy)
        elif action_type == 'therapy':
            return await self._create_therapy(conn, patient_id, action_data, performedBy)
        elif action_type == 'note':
            return await self._create_note(conn, patient_id, action_data, performedBy)
        elif action_type == 'medication_administration':
            return await self._record_medication_administration(conn, patient_id, action_data, performedBy)
        elif action_type == 'therapy_session':
            return await self._record_therapy_session(conn, patient_id, action_data, performedBy)
        elif action_type == 'alert_acknowledgment':
            return await self._record_alert_acknowledgment(conn, patient_id, action_data, performedBy)
        elif action_type == 'investigation_completion':
            return await self._record_investigation_completion(conn, patient_id, action_data, performedBy)
        elif action_type == 'medication_status_change':
            return await self._record_medication_status_change(conn, patient_id, action_data, performedBy)
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    async def _create_medication(
        self,
        conn: asyncpg.Connection,
        patient_id: str,
        medication_data: Dict[str, Any],
        performedBy: str
    ) -> Dict[str, Any]:
        """Create medication record atomically"""

        self.logger.debug(f"_create_medication called with medication_data: {medication_data}")
        self.logger.debug(f"performedBy: {performedBy}")

        med_data = {
            'patientId': patient_id,
            'name': medication_data.get('name') or medication_data.get('medication_name'),
            'dosage': medication_data.get('dosage'),
            'frequency': medication_data.get('frequency'),
            'route': medication_data.get('route'),
            'startDate': medication_data.get('startDate', datetime.now()),
            'endDate': medication_data.get('endDate'),
            'duration': medication_data.get('duration'),
            'prescribedBy': medication_data.get('prescribedBy', performedBy),
            'createdBy': performedBy,  # FIXED: Add audit trail - who created this record
            'status': medication_data.get('status', 'active')
        }

        self.logger.debug(f"med_data prepared for INSERT: {med_data}")

        # Insert with RETURNING to get complete record
        columns = list(med_data.keys())
        quoted_columns = [f'"{col}"' if any(c.isupper() for c in col) else col for col in columns]
        placeholders = [f'${i+1}' for i in range(len(columns))]
        values = list(med_data.values())

        query = f"""
            INSERT INTO medications ({', '.join(quoted_columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """

        self.logger.debug(f"SQL Query: {query}")
        self.logger.debug(f"SQL Values: {values}")

        try:
            result = await conn.fetchrow(query, *values)
            self.logger.debug(f"INSERT successful, result: {dict(result)}")
            return dict(result)
        except Exception as e:
            self.logger.error(f"ERROR: SQL INSERT failed: {e}")
            self.logger.error(f"ERROR: Query was: {query}")
            self.logger.error(f"ERROR: Values were: {values}")
            raise

    async def _create_investigation(
        self,
        conn: asyncpg.Connection,
        patient_id: str,
        investigation_data: Dict[str, Any],
        performedBy: str
    ) -> Dict[str, Any]:
        """Create investigation record atomically"""

        inv_data = {
            'patientId': patient_id,
            'type': investigation_data.get('testType', 'Lab'),
            'name': investigation_data.get('testName'),
            'status': 'pending',
            'priority': investigation_data.get('priority', 'Routine'),
            'urgency': investigation_data.get('urgency', 'Routine'),
            'prescribedBy': investigation_data.get('prescribedBy', performedBy),
            'notes': investigation_data.get('notes'),
            'createdAt': datetime.now()
        }

        columns = list(inv_data.keys())
        quoted_columns = [f'"{col}"' if any(c.isupper() for c in col) else col for col in columns]
        placeholders = [f'${i+1}' for i in range(len(columns))]
        values = list(inv_data.values())

        query = f"""
            INSERT INTO investigations ({', '.join(quoted_columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """

        result = await conn.fetchrow(query, *values)
        return dict(result)

    async def _create_therapy(
        self,
        conn: asyncpg.Connection,
        patient_id: str,
        therapy_data: Dict[str, Any],
        performedBy: str
    ) -> Dict[str, Any]:
        """Create therapy record atomically"""

        ther_data = {
            'patientId': patient_id,
            'type': therapy_data.get('therapyType') or therapy_data.get('type') or therapy_data.get('therapy_type'),
            'description': therapy_data.get('description'),
            'startDate': therapy_data.get('startDate'),
            'endDate': therapy_data.get('endDate'),
            'frequency': therapy_data.get('frequency'),
            'duration': therapy_data.get('duration'),
            'prescribedBy': therapy_data.get('prescribedBy', performedBy),
            'notes': therapy_data.get('notes'),
            'status': 'active'
        }

        columns = list(ther_data.keys())
        quoted_columns = [f'"{col}"' if any(c.isupper() for c in col) else col for col in columns]
        placeholders = [f'${i+1}' for i in range(len(columns))]
        values = list(ther_data.values())

        query = f"""
            INSERT INTO therapy ({', '.join(quoted_columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """

        result = await conn.fetchrow(query, *values)
        return dict(result)

    async def _create_note(
        self,
        conn: asyncpg.Connection,
        patient_id: str,
        note_data: Dict[str, Any],
        performedBy: str
    ) -> Dict[str, Any]:
        """Create patient note atomically"""

        # Handle both 'comment' and 'content' field names for compatibility
        content = note_data.get('comment') or note_data.get('content')

        note_record = {
            'patientId': patient_id,
            'content': content,
            'createdBy': performedBy
            # timestamp is auto-generated by database DEFAULT NOW()
            # authorName is resolved via JOIN when fetching notes
        }

        columns = list(note_record.keys())
        quoted_columns = [f'"{col}"' if any(c.isupper() for c in col) else col for col in columns]
        placeholders = [f'${i+1}' for i in range(len(columns))]
        values = list(note_record.values())

        query = f"""
            INSERT INTO patientnotes ({', '.join(quoted_columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """

        result = await conn.fetchrow(query, *values)
        return dict(result)

    async def _record_medication_administration(
        self,
        conn: asyncpg.Connection,
        patient_id: str,
        administration_data: Dict[str, Any],
        performedBy: str
    ) -> Dict[str, Any]:
        """Record medication administration atomically with database persistence"""

        # Create administration record in medicationadministrations table
        # Get medication details to fill in proper name, dosage and route
        medication_id_value = int(administration_data.get('medication_id'))  # INTEGER for INTEGER column
        medication_details = await conn.fetchrow(
            'SELECT name, dosage, route FROM medications WHERE id = $1',
            medication_id_value  # medications.id is INTEGER
        )

        administered_at = datetime.now()

        administration_record = {
            'id': str(uuid.uuid4()),
            'medicationId': medication_id_value,  # INTEGER to match INTEGER column
            'patientId': patient_id,
            'scheduledTime': administered_at,  # Required field - use current time
            'performedAt': administered_at,
            'performedBy': performedBy,  # Medical staff who administered (required)
            # Note: createdBy removed - redundant with performedBy in our immediate-recording system
            'dosageGiven': medication_details['dosage'] if medication_details else 'Unknown',
            'route': medication_details['route'] if medication_details else 'Unknown',
            'status': 'completed',
            'notes': administration_data.get('notes', ''),
            'createdAt': administered_at,
            'updatedAt': administered_at
        }

        # Insert into medicationadministrations table
        columns = list(administration_record.keys())
        quoted_columns = [f'"{col}"' if any(c.isupper() for c in col) else col for col in columns]
        placeholders = [f'${i+1}' for i in range(len(columns))]

        # Build values list with explicit type safety for INTEGER columns
        values = []
        for key, value in administration_record.items():
            if key == 'medicationId':
                # Ensure INTEGER type for database column (medicationId is INTEGER NOT NULL)
                values.append(int(value))
            else:
                values.append(value)

        query = f"""
            INSERT INTO medicationadministrations ({', '.join(quoted_columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """

        result = await conn.fetchrow(query, *values)

        # Also update the medication status to show it was administered
        medication_id = administration_data.get('medication_id')
        if medication_id:
            try:
                await conn.execute(
                    'UPDATE medications SET "updatedAt" = $1 WHERE id = $2',
                    datetime.now(), int(medication_id)
                )
            except Exception as e:
                self.logger.warning(f"Could not update medication {medication_id} status: {e}")

        return dict(result)

    async def _record_therapy_session(
        self,
        conn: asyncpg.Connection,
        patient_id: str,
        session_data: Dict[str, Any],
        performedBy: str
    ) -> Dict[str, Any]:
        """Record therapy session completion atomically with database persistence"""

        # Get therapy details to fill in proper therapy information
        therapy_details = await conn.fetchrow(
            'SELECT description, type FROM therapy WHERE id = $1',
            session_data.get('therapy_id')
        )

        completed_at = datetime.now()

        # Get next session number for this therapy
        last_session = await conn.fetchrow(
            'SELECT MAX("sessionNumber") as max_session FROM therapysessions WHERE "therapyId" = $1',
            session_data.get('therapy_id')
        )
        next_session_number = (last_session['max_session'] or 0) + 1

        session_record = {
            'id': str(uuid.uuid4()),
            'therapyId': session_data.get('therapy_id'),
            'patientId': patient_id,
            'sessionNumber': next_session_number,
            'scheduledDate': completed_at,  # Use current time as scheduled
            'completedAt': completed_at,
            'performedBy': performedBy,
            'sessionNotes': session_data.get('notes', ''),
            'status': 'completed',
            'duration': str(session_data.get('duration', 0)) + ' minutes',
            'createdAt': completed_at,
            'updatedAt': completed_at
        }

        # Insert into therapysessions table
        columns = list(session_record.keys())
        quoted_columns = [f'"{col}"' if any(c.isupper() for c in col) else col for col in columns]
        placeholders = [f'${i+1}' for i in range(len(columns))]
        values = list(session_record.values())

        query = f"""
            INSERT INTO therapysessions ({', '.join(quoted_columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """

        result = await conn.fetchrow(query, *values)

        # Also update the therapy status to show it has sessions
        therapy_id = session_data.get('therapy_id')
        if therapy_id:
            try:
                await conn.execute(
                    'UPDATE therapies SET "updatedAt" = $1 WHERE id = $2',
                    datetime.now(), therapy_id
                )
            except Exception as e:
                self.logger.warning(f"Could not update therapy {therapy_id} status: {e}")

        return dict(result)

    async def _record_alert_acknowledgment(
        self,
        conn: asyncpg.Connection,
        patient_id: str,
        acknowledgment_data: Dict[str, Any],
        performedBy: str
    ) -> Dict[str, Any]:
        """Record alert acknowledgment atomically with database persistence"""

        alert_id = acknowledgment_data.get('alert_id')
        acknowledged_at = datetime.now()

        if not alert_id:
            raise ValueError("alert_id is required for alert acknowledgment")

        # Get alert details first
        alert_details = await conn.fetchrow(
            'SELECT * FROM patient_alerts WHERE id = $1 AND "patientId" = $2',
            alert_id, patient_id
        )

        if not alert_details:
            raise ValueError(f"Alert {alert_id} not found for patient {patient_id}")

        # Update alert with acknowledgment
        await conn.execute('''
            UPDATE patient_alerts
            SET status = 'acknowledged',
                "acknowledgedBy" = $1,
                "acknowledgedAt" = $2
            WHERE id = $3 AND "patientId" = $4
        ''', performedBy, acknowledged_at, alert_id, patient_id)

        # Return the acknowledgment record for case entry creation
        acknowledgment_record = {
            'id': alert_id,
            'alertId': alert_id,
            'patientId': patient_id,
            'performedBy': performedBy,
            'performedAt': acknowledged_at,
            'alertType': alert_details['type'],
            'alertMessage': alert_details['message'],
            'alertSeverity': alert_details['severity'],
            'createdAt': acknowledged_at,
            'updatedAt': acknowledged_at
        }

        self.logger.info(f"Alert {alert_id} acknowledged by {performedBy} for patient {patient_id}")

        return acknowledgment_record

    async def _record_investigation_completion(
        self,
        conn: asyncpg.Connection,
        patient_id: str,
        completion_data: Dict[str, Any],
        performedBy: str
    ) -> Dict[str, Any]:
        """Record investigation completion atomically with database persistence"""

        investigation_id = completion_data.get('investigation_id')
        results = completion_data.get('results', '')
        completed_at = datetime.now()

        if not investigation_id:
            raise ValueError("investigation_id is required for investigation completion")

        # Get investigation details first
        investigation_details = await conn.fetchrow(
            'SELECT * FROM investigations WHERE id = $1 AND "patientId" = $2',
            int(investigation_id), patient_id
        )

        if not investigation_details:
            raise ValueError(f"Investigation {investigation_id} not found for patient {patient_id}")

        # Update investigation with completion data
        await conn.execute('''
            UPDATE investigations
            SET status = 'completed',
                results = $1,
                "completedAt" = $2,
                "updatedAt" = $2
            WHERE id = $3 AND "patientId" = $4
        ''', results, completed_at, int(investigation_id), patient_id)

        # Return the completion record for case entry creation
        completion_record = {
            'id': investigation_id,
            'investigationId': investigation_id,
            'patientId': patient_id,
            'completedBy': performedBy,
            'completedAt': completed_at,
            'results': results,
            'investigationName': investigation_details['name'],
            'investigationType': investigation_details['type'],
            'createdAt': completed_at,
            'updatedAt': completed_at
        }

        self.logger.info(f"Investigation {investigation_id} completed by {performedBy} for patient {patient_id}")

        return completion_record

    async def _record_medication_status_change(
        self,
        conn: asyncpg.Connection,
        patient_id: str,
        status_change_data: Dict[str, Any],
        performedBy: str
    ) -> Dict[str, Any]:
        """Record medication status change atomically with database persistence"""

        medication_id = status_change_data.get('medication_id')
        new_status = status_change_data.get('status')
        changed_at = datetime.now()

        if not medication_id:
            raise ValueError("medication_id is required for medication status change")
        if not new_status:
            raise ValueError("status is required for medication status change")

        # Get medication details first
        medication_details = await conn.fetchrow(
            'SELECT * FROM medications WHERE id = $1 AND "patientId" = $2',
            int(medication_id), patient_id
        )

        if not medication_details:
            raise ValueError(f"Medication {medication_id} not found for patient {patient_id}")

        # Update medication status
        await conn.execute('''
            UPDATE medications
            SET status = $1,
                "modifiedBy" = $2,
                "updatedAt" = $3
            WHERE id = $4 AND "patientId" = $5
        ''', new_status, performedBy, changed_at, int(medication_id), patient_id)

        # Return the status change record for case entry creation
        status_change_record = {
            'id': medication_id,
            'medicationId': medication_id,
            'patientId': patient_id,
            'changedBy': performedBy,
            'changedAt': changed_at,
            'oldStatus': medication_details['status'],
            'newStatus': new_status,
            'medicationName': medication_details['name'],
            'medicationDosage': medication_details['dosage'],
            'createdAt': changed_at,
            'updatedAt': changed_at
        }

        self.logger.info(f"Medication {medication_id} status changed from {medication_details['status']} to {new_status} by {performedBy} for patient {patient_id}")

        return status_change_record

    async def _create_case_entry(
        self,
        conn: asyncpg.Connection,
        patient_id: str,
        action_type: str,
        medical_record: Dict[str, Any],
        performedBy: str
    ) -> Dict[str, Any]:
        """Create case entry automatically for medical action"""

        description = await self._build_case_entry_description(conn, action_type, medical_record)

        # Use the database function for atomic case entry creation
        result = await conn.fetchrow(
            'SELECT create_atomic_case_entry($1, $2, $3, $4) as id',
            patient_id, action_type, description, performedBy
        )

        # Fetch the complete case entry record
        case_entry = await conn.fetchrow(
            'SELECT * FROM "caseEntries" WHERE id = $1',
            result['id']
        )

        # Convert UUID to string for JSON serialization
        entry_dict = dict(case_entry)
        entry_dict['id'] = str(entry_dict['id'])

        # Resolve staff names using middleware (uses transaction connection)
        entry_dict = await resolve_staff_in_response(entry_dict, conn)

        return entry_dict

    async def _build_case_entry_description(self, conn: asyncpg.Connection, action_type: str, medical_record: Dict[str, Any]) -> str:
        """Build descriptive case entry description"""

        if action_type == 'medication':
            name = medical_record.get('name', 'Unknown medication')
            dosage = medical_record.get('dosage', '')
            frequency = medical_record.get('frequency', '')
            return f"Medication prescribed: {name} {dosage} {frequency}".strip()

        elif action_type == 'investigation':
            name = medical_record.get('name', 'Unknown investigation')
            type_val = medical_record.get('type', '')
            urgency = medical_record.get('urgency', '')
            return f"Investigation ordered: {type_val} {name} ({urgency})".strip()

        elif action_type == 'therapy':
            type_val = medical_record.get('type', 'Unknown therapy')
            description = medical_record.get('description', '')
            return f"Therapy prescribed: {type_val} - {description}".strip()

        elif action_type == 'note':
            content = medical_record.get('content', 'Patient note added')
            return f"Clinical note: {content[:100]}{'...' if len(content) > 100 else ''}"

        elif action_type == 'medication_administration':
            # Fetch medication name from database using medicationId
            medication_id = medical_record.get('medicationId')
            medication_name = 'Unknown medication'
            if medication_id:
                medication_details = await conn.fetchrow(
                    'SELECT name FROM medications WHERE id = $1',
                    int(medication_id)
                )
                if medication_details:
                    medication_name = medication_details['name']

            dosage = medical_record.get('dosageGiven', '')
            route = medical_record.get('route', '')
            return f"Medication administered: {medication_name} {dosage} via {route}".strip()

        elif action_type == 'therapy_session':
            therapy_id = medical_record.get('therapyId', 'Unknown therapy')
            session_number = medical_record.get('sessionNumber', '')
            duration = medical_record.get('duration', '')
            notes = medical_record.get('sessionNotes', '')
            return f"Therapy session #{session_number} completed ({duration}) - {notes[:50]}{'...' if len(notes) > 50 else ''}".strip()

        elif action_type == 'alert_acknowledgment':
            alert_type = medical_record.get('alertType', 'Unknown alert')
            alert_message = medical_record.get('alertMessage', '')
            alert_severity = medical_record.get('alertSeverity', '')
            return f"Alert acknowledged: {alert_severity} {alert_type} - {alert_message[:50]}{'...' if len(alert_message) > 50 else ''}".strip()

        elif action_type == 'investigation_completion':
            investigation_name = medical_record.get('investigationName', 'Unknown investigation')
            investigation_type = medical_record.get('investigationType', '')
            results = medical_record.get('results', '')
            return f"Investigation completed: {investigation_type} {investigation_name} - Results: {results[:50]}{'...' if len(results) > 50 else ''}".strip()

        elif action_type == 'medication_status_change':
            medication_name = medical_record.get('medicationName', 'Unknown medication')
            medication_dosage = medical_record.get('medicationDosage', '')
            old_status = medical_record.get('oldStatus', '')
            new_status = medical_record.get('newStatus', '')

            return f"Medication status changed: {medication_name} {medication_dosage} from {old_status} to {new_status}".strip()

        else:
            return f"Medical action: {action_type}"

    # Idempotency and transaction tracking methods

    async def _check_existing_operation(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        """Check if operation already completed (idempotency)"""
        async with getDbConnection() as conn:
            result = await conn.fetchrow(
                'SELECT result FROM medical_operations WHERE "idempotencyKey" = $1 AND status = \'completed\'',
                idempotency_key
            )

            if result:
                return json.loads(result['result'])
            return None

    async def _store_operation_result(
        self,
        conn: asyncpg.Connection,
        idempotency_key: str,
        result: Dict[str, Any]
    ):
        """Store operation result for idempotency"""
        await conn.execute("""
            INSERT INTO medical_operations (
                "idempotencyKey", "operationType", "patientId", result, status, "completedAt"
            ) VALUES ($1, $2, $3, $4, 'completed', NOW())
        """, idempotency_key, result['action_type'],
             result['medical_record']['patientId'], json.dumps(result))

    async def _start_transaction_tracking(
        self,
        conn: asyncpg.Connection,
        transaction_id: str,
        patient_id: str,
        operation_type: str,
        operation_data: Dict[str, Any]
    ):
        """Start transaction tracking"""
        # Convert datetime objects to ISO strings for JSON serialization
        def datetime_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        await conn.execute("""
            INSERT INTO atomic_transactions (
                "transactionId", "patientId", "operationType", "operationData", status
            ) VALUES ($1, $2, $3, $4, 'in_progress')
        """, transaction_id, patient_id, operation_type, json.dumps(operation_data, default=datetime_serializer))

    async def _complete_transaction_tracking(
        self,
        conn: asyncpg.Connection,
        transaction_id: str,
        result: Dict[str, Any]
    ):
        """Complete transaction tracking"""
        await conn.execute("""
            UPDATE atomic_transactions
            SET status = 'completed', "completedAt" = NOW()
            WHERE "transactionId" = $1
        """, transaction_id)

    async def _fail_transaction_tracking(
        self,
        conn: asyncpg.Connection,
        transaction_id: str,
        error_message: str
    ):
        """Mark transaction as failed"""
        await conn.execute("""
            UPDATE atomic_transactions
            SET status = 'failed', "errorMessage" = $2, "completedAt" = NOW()
            WHERE "transactionId" = $1
        """, transaction_id, error_message)

    def _transform_to_camel_case(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform database record to camelCase for frontend"""
        if not record:
            return record

        # Convert keys to camelCase
        camel_record = {}
        for key, value in record.items():
            if isinstance(value, datetime):
                value = value.isoformat()
            camel_record[key] = value

        return camel_record


# Singleton instance
medical_action_service = MedicalActionService()


# Convenience functions for easy usage
async def add_medication_atomic(patient_id: str, medication_data: Dict[str, Any], performedBy: str) -> Dict[str, Any]:
    """Add medication atomically with auto case entry"""
    return await medical_action_service.execute_medical_action(
        'medication', patient_id, medication_data, performedBy
    )


async def add_investigation_atomic(patient_id: str, investigation_data: Dict[str, Any], performedBy: str) -> Dict[str, Any]:
    """Add investigation atomically with auto case entry"""
    return await medical_action_service.execute_medical_action(
        'investigation', patient_id, investigation_data, performedBy
    )


async def add_therapy_atomic(patient_id: str, therapy_data: Dict[str, Any], performedBy: str) -> Dict[str, Any]:
    """Add therapy atomically with auto case entry"""
    return await medical_action_service.execute_medical_action(
        'therapy', patient_id, therapy_data, performedBy
    )


async def add_note_atomic(patient_id: str, note_data: Dict[str, Any], performedBy: str) -> Dict[str, Any]:
    """Add patient note atomically with auto case entry"""
    return await medical_action_service.execute_medical_action(
        'note', patient_id, note_data, performedBy
    )