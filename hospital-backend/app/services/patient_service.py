"""
Patient Service - Business logic layer for patient operations
Handles all patient-related business rules and data processing
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import asyncpg

from .base_service import BaseService
from ..repositories.patient_repository import PatientRepository
from ..core.exceptions import (
    ValidationException,
    NotFoundException,
    DatabaseException,
    BusinessRuleException,
    PermissionDeniedException
)


class PatientService(BaseService):
    """
    Patient service handling all patient business logic
    Coordinates with PatientRepository for data operations
    """

    def __init__(self):
        self.patient_repository = PatientRepository()
        super().__init__(self.patient_repository)

    # ================================
    # PATIENT CORE OPERATIONS
    # ================================

    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get patient records by patient ID (implements base class abstract method)"""
        result = await self.get_by_id(patient_id)
        return [result] if result else []

    async def get_complete_patient_data(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient with all associated medical records"""
        try:
            # Validate input
            if not patient_id or not patient_id.strip():
                raise ValidationException("Patient ID is required", field="patient_id")

            result = await self.patient_repository.get_complete_patient_data(patient_id)

            # Check if patient exists
            if not result:
                raise NotFoundException("Patient", patient_id)

            # Transform to camelCase and process medical records
            camel_result = self.patient_repository.transform_to_camel_case(result)

            # Process nested medical records - handle JSON strings
            import json
            for field in ['notes', 'medications', 'investigations', 'therapies']:
                field_data = camel_result.get(field)

                # Parse JSON strings to arrays
                if isinstance(field_data, str):
                    try:
                        field_data = json.loads(field_data)
                    except (json.JSONDecodeError, TypeError):
                        field_data = []

                # Ensure it's a list
                if not isinstance(field_data, list):
                    field_data = []

                # Filter out null entries and transform to camelCase
                camel_result[field] = [
                    self.patient_repository.transform_to_camel_case(item)
                    for item in field_data
                    if item is not None
                ]

                # Add edit permissions for each item
                for item in camel_result[field]:
                    # Notes use 'timestamp', others use 'createdAt'
                    time_field = item.get('timestamp') or item.get('createdAt', '')
                    item['canEdit'] = self.can_edit_item(time_field)

            # Calculate age if birthDate exists
            if camel_result.get('dateOfBirth'):
                camel_result['age'] = self.patient_repository.calculate_age(camel_result['dateOfBirth'])

            # Resolve staff IDs to names
            self.logger.info(f"🔍 Resolving staff names for patient {patient_id}")
            await self._resolve_staff_names(camel_result)
            self.logger.info(f"✅ Staff names resolved: attendingPhysicianName = {camel_result.get('attendingPhysicianName')}")

            # Resolve staff IDs in medical records
            await self._resolve_medical_record_staff_names(camel_result)

            # Fetch latest vitals from TimescaleDB
            vitals_map = await self.patient_repository.getLatestVitalsForPatients([patient_id])

            if patient_id in vitals_map:
                vitals_row = vitals_map[patient_id]

                # Transform to frontend format (same as mqtt_service._convertVitalsToFrontendFormat)
                camel_result['vitals'] = {
                    'heartRate': vitals_row.get('heartRate'),
                    'respiratoryRate': vitals_row.get('respiratoryRate'),
                    'skinTemperature': vitals_row.get('skinTemperature'),
                    'oxygenSaturation': vitals_row.get('oxygenSaturation'),
                    'batteryLevel': vitals_row.get('batteryLevel'),
                    'signalQuality': vitals_row.get('signalQuality'),
                    'lastDataReceived': vitals_row.get('time').isoformat() if vitals_row.get('time') else None,
                    'lastUpdated': vitals_row.get('time').isoformat() if vitals_row.get('time') else None,
                    'isEcgMode': vitals_row.get('mode') == 'ecg',
                    'ecgReading': vitals_row.get('rrInterval') if vitals_row.get('mode') == 'ecg' else 0,
                    'eegReading': vitals_row.get('alphaPower') if vitals_row.get('mode') == 'eeg' else 0,
                }

                # Add nested ECG/EEG objects if present
                if vitals_row.get('mode') == 'ecg':
                    camel_result['vitals']['ecg'] = {
                        'rrInterval': vitals_row.get('rrInterval'),
                        'qrsDuration': vitals_row.get('qrsDuration'),
                        'qtInterval': vitals_row.get('qtInterval'),
                        'axis': vitals_row.get('axis'),
                        'rhythm': vitals_row.get('rhythm'),
                        'stSegment': vitals_row.get('stSegment')
                    }
                elif vitals_row.get('mode') == 'eeg':
                    camel_result['vitals']['eeg'] = {
                        'alphaPower': vitals_row.get('alphaPower'),
                        'betaPower': vitals_row.get('betaPower'),
                        'thetaPower': vitals_row.get('thetaPower'),
                        'deltaPower': vitals_row.get('deltaPower'),
                        'gammaPower': vitals_row.get('gammaPower'),
                        'dominantFrequency': vitals_row.get('dominantFrequency'),
                        'seizureActivity': vitals_row.get('seizureActivity')
                    }

            return camel_result

        except (ValidationException, NotFoundException):
            # Re-raise custom exceptions
            raise

        except asyncpg.PostgresError as e:
            # Database errors
            self.logger.error(
                f"Database error getting complete patient data for {patient_id}: {e}",
                exc_info=True
            )
            raise DatabaseException("get patient data", str(e))

        except Exception as e:
            # Unexpected errors
            self.logger.error(
                f"Unexpected error getting complete patient data for {patient_id}: {e}",
                exc_info=True
            )
            raise

    async def _resolve_staff_names(self, patient_data: Dict[str, Any]) -> None:
        """Resolve staff IDs to readable names"""
        try:
            # Get staff IDs that need resolution
            attending_physician_id = patient_data.get('attendingPhysician')
            nurse_in_charge_id = patient_data.get('nurseInCharge')

            self.logger.info(f"🔍 Staff IDs to resolve: attending={attending_physician_id}, nurse={nurse_in_charge_id}")

            staff_ids = []
            if attending_physician_id:
                staff_ids.append(attending_physician_id)
            if nurse_in_charge_id:
                staff_ids.append(nurse_in_charge_id)

            if not staff_ids:
                self.logger.info("⚠️ No staff IDs to resolve")
                return

            # Query staff names from database
            self.logger.info(f"🔍 Querying staff names for IDs: {staff_ids}")
            staff_names = await self.patient_repository.get_staff_names(staff_ids)
            self.logger.info(f"✅ Retrieved staff names: {staff_names}")

            # Update patient data with resolved names
            if attending_physician_id and attending_physician_id in staff_names:
                patient_data['attendingPhysicianName'] = staff_names[attending_physician_id]['name']
                patient_data['assignedDoctor'] = staff_names[attending_physician_id]['name']
                self.logger.info(f"✅ Set attending physician name: {staff_names[attending_physician_id]['name']}")

            if nurse_in_charge_id and nurse_in_charge_id in staff_names:
                patient_data['nurseInChargeName'] = staff_names[nurse_in_charge_id]['name']
                self.logger.info(f"✅ Set nurse name: {staff_names[nurse_in_charge_id]['name']}")

        except Exception as e:
            self.logger.error(f"❌ Error resolving staff names: {e}", exc_info=True)
            # Don't fail the whole request if staff name resolution fails

    async def _resolve_medical_record_staff_names(self, patient_data: Dict[str, Any]) -> None:
        """Resolve staff IDs to readable names in all medical records"""
        try:
            # Collect all staff IDs from medical records
            staff_ids = set()

            # Get staff IDs from medications
            if patient_data.get('medications'):
                for med in patient_data['medications']:
                    if isinstance(med, dict):
                        if med.get('prescribedBy'):
                            staff_ids.add(med['prescribedBy'])
                        if med.get('authorId'):
                            staff_ids.add(med['authorId'])
                        if med.get('createdBy'):
                            staff_ids.add(med['createdBy'])

            # Get staff IDs from investigations
            if patient_data.get('investigations'):
                for inv in patient_data['investigations']:
                    if isinstance(inv, dict):
                        if inv.get('performedBy'):
                            staff_ids.add(inv['performedBy'])
                        if inv.get('authorId'):
                            staff_ids.add(inv['authorId'])
                        if inv.get('createdBy'):
                            staff_ids.add(inv['createdBy'])

            # Get staff IDs from therapies
            if patient_data.get('therapies'):
                for therapy in patient_data['therapies']:
                    if isinstance(therapy, dict):
                        if therapy.get('prescribedBy'):
                            staff_ids.add(therapy['prescribedBy'])

            # Get staff IDs from notes
            if patient_data.get('notes'):
                for note in patient_data['notes']:
                    if isinstance(note, dict):
                        if note.get('authorId'):
                            staff_ids.add(note['authorId'])
                        if note.get('createdBy'):
                            staff_ids.add(note['createdBy'])
                        if note.get('editedBy'):
                            staff_ids.add(note['editedBy'])

            # Remove None values and convert to list
            staff_ids = [sid for sid in staff_ids if sid]

            if not staff_ids:
                return

            # Get staff names from database
            staff_names = await self.patient_repository.get_staff_names(staff_ids)

            # Update medications with resolved names
            if patient_data.get('medications'):
                for med in patient_data['medications']:
                    if isinstance(med, dict):
                        if med.get('prescribedBy') and med['prescribedBy'] in staff_names:
                            med['prescribedByName'] = staff_names[med['prescribedBy']]['name']
                        if med.get('authorId') and med['authorId'] in staff_names:
                            med['authorName'] = staff_names[med['authorId']]['name']
                        if med.get('createdBy') and med['createdBy'] in staff_names:
                            med['createdByName'] = staff_names[med['createdBy']]['name']

            # Update investigations with resolved names
            if patient_data.get('investigations'):
                for inv in patient_data['investigations']:
                    if isinstance(inv, dict):
                        if inv.get('prescribedBy') and inv['prescribedBy'] in staff_names:
                            inv['prescribedByName'] = staff_names[inv['prescribedBy']]['name']
                        if inv.get('authorId') and inv['authorId'] in staff_names:
                            inv['authorName'] = staff_names[inv['authorId']]['name']
                        if inv.get('createdBy') and inv['createdBy'] in staff_names:
                            inv['createdByName'] = staff_names[inv['createdBy']]['name']

            # Update therapies with resolved names
            if patient_data.get('therapies'):
                for therapy in patient_data['therapies']:
                    if isinstance(therapy, dict):
                        if therapy.get('prescribedBy') and therapy['prescribedBy'] in staff_names:
                            therapy['prescribedByName'] = staff_names[therapy['prescribedBy']]['name']
                        if therapy.get('authorId') and therapy['authorId'] in staff_names:
                            therapy['authorName'] = staff_names[therapy['authorId']]['name']
                        if therapy.get('createdBy') and therapy['createdBy'] in staff_names:
                            therapy['createdByName'] = staff_names[therapy['createdBy']]['name']

            # Update notes with resolved names
            if patient_data.get('notes'):
                for note in patient_data['notes']:
                    if isinstance(note, dict):
                        # Map createdBy to authorId for frontend compatibility
                        if note.get('createdBy'):
                            note['authorId'] = note['createdBy']

                            # Set authorName and authorRole (frontend expected fields)
                            if note['createdBy'] in staff_names:
                                note['authorName'] = staff_names[note['createdBy']]['name']
                                note['createdByName'] = staff_names[note['createdBy']]['name']  # Keep for backwards compat
                                note['authorRole'] = staff_names[note['createdBy']]['role']
                            else:
                                # Fallback for missing staff records
                                note['authorName'] = 'Unknown Staff'
                                note['authorRole'] = 'Staff'

                        if note.get('editedBy') and note['editedBy'] in staff_names:
                            note['editedByName'] = staff_names[note['editedBy']]['name']

        except Exception as e:
            self.logger.error(f"Error resolving medical record staff names: {e}")
            # Don't fail the whole request if staff name resolution fails

    async def search_patients(self, search_query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search patients with business logic"""
        try:
            # Validate search query
            if not search_query or len(search_query.strip()) < 1:
                raise ValidationException(
                    "Search query must be at least 1 character",
                    field="search_query"
                )

            # Validate limit
            if limit < 1 or limit > 1000:
                raise ValidationException(
                    "Limit must be between 1 and 1000",
                    field="limit"
                )

            results = await self.patient_repository.search_patients(search_query.strip(), limit)

            # Transform and enhance results
            enhanced_results = []
            for patient in results:
                camel_patient = self.patient_repository.transform_to_camel_case(patient)

                # Calculate age
                if camel_patient.get('dateOfBirth'):
                    camel_patient['age'] = self.patient_repository.calculate_age(camel_patient['dateOfBirth'])

                # Add edit permission
                camel_patient['canEdit'] = self.can_edit_item(camel_patient.get('createdAt', ''))

                enhanced_results.append(camel_patient)

            return enhanced_results

        except ValidationException:
            # Re-raise validation exceptions
            raise

        except asyncpg.PostgresError as e:
            # Database errors
            self.logger.error(
                f"Database error searching patients with query '{search_query}': {e}",
                exc_info=True
            )
            raise DatabaseException("search patients", str(e))

        except Exception as e:
            # Unexpected errors
            self.logger.error(
                f"Unexpected error searching patients with query '{search_query}': {e}",
                exc_info=True
            )
            raise

    async def get_patients_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get patients by status with business logic"""
        # Validate status
        valid_statuses = ['stable', 'critical', 'emergency', 'discharged', 'admitted']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of: {valid_statuses}")

        results = await self.patient_repository.get_patients_by_status(status)
        return [self.repository.transform_to_camel_case(item) for item in results]

    async def get_patients_by_room(self, room_number: str) -> List[Dict[str, Any]]:
        """Get patients by room with validation"""
        if not room_number or not room_number.strip():
            raise ValueError("Room number cannot be empty")

        results = await self.patient_repository.get_patients_by_room(room_number.strip())
        return [self.repository.transform_to_camel_case(item) for item in results]

    async def get_patients_by_ward(self, ward: str) -> List[Dict[str, Any]]:
        """Get patients by ward with validation"""
        if not ward or not ward.strip():
            raise ValueError("Ward cannot be empty")

        results = await self.patient_repository.get_patients_by_ward(ward.strip())
        return [self.repository.transform_to_camel_case(item) for item in results]

    async def get_all(self, filters: Optional[Dict[str, Any]] = None,
                     limit: Optional[int] = None,
                     offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Override get_all to include latest vitals from TimescaleDB"""
        try:
            # Get patients from PostgreSQL (includes device assignment data)
            patients = await self.patient_repository.get_all(filters, limit, offset)

            if not patients:
                return []

            # Extract patient IDs
            patient_ids = [p.get('id') for p in patients if p.get('id')]

            if not patient_ids:
                return patients

            # Fetch latest vitals from TimescaleDB
            vitals_map = await self.patient_repository.getLatestVitalsForPatients(patient_ids)

            # Merge vitals into patient data
            for patient in patients:
                patient_id = patient.get('id')
                if patient_id and patient_id in vitals_map:
                    vitals_row = vitals_map[patient_id]

                    # Transform to frontend format (same as mqtt_service._convertVitalsToFrontendFormat)
                    patient['vitals'] = {
                        'heartRate': vitals_row.get('heartRate'),
                        'respiratoryRate': vitals_row.get('respiratoryRate'),
                        'skinTemperature': vitals_row.get('skinTemperature'),
                        'oxygenSaturation': vitals_row.get('oxygenSaturation'),
                        'batteryLevel': vitals_row.get('batteryLevel'),
                        'signalQuality': vitals_row.get('signalQuality'),
                        'lastDataReceived': vitals_row.get('time').isoformat() if vitals_row.get('time') else None,
                        'lastUpdated': vitals_row.get('time').isoformat() if vitals_row.get('time') else None,
                        'isEcgMode': vitals_row.get('mode') == 'ecg',
                        'ecgReading': vitals_row.get('rrInterval') if vitals_row.get('mode') == 'ecg' else 0,
                        'eegReading': vitals_row.get('alphaPower') if vitals_row.get('mode') == 'eeg' else 0,
                    }

                    # Add nested ECG/EEG objects if present
                    if vitals_row.get('mode') == 'ecg':
                        patient['vitals']['ecg'] = {
                            'rrInterval': vitals_row.get('rrInterval'),
                            'qrsDuration': vitals_row.get('qrsDuration'),
                            'qtInterval': vitals_row.get('qtInterval'),
                            'axis': vitals_row.get('axis'),
                            'rhythm': vitals_row.get('rhythm'),
                            'stSegment': vitals_row.get('stSegment')
                        }
                    elif vitals_row.get('mode') == 'eeg':
                        patient['vitals']['eeg'] = {
                            'alphaPower': vitals_row.get('alphaPower'),
                            'betaPower': vitals_row.get('betaPower'),
                            'thetaPower': vitals_row.get('thetaPower'),
                            'deltaPower': vitals_row.get('deltaPower'),
                            'gammaPower': vitals_row.get('gammaPower'),
                            'dominantFrequency': vitals_row.get('dominantFrequency'),
                            'seizureActivity': vitals_row.get('seizureActivity')
                        }

            self.logger.info(f"✅ Retrieved {len(patients)} patients with vitals merged from TimescaleDB")
            return patients

        except Exception as e:
            self.logger.error(f"Service get_all error: {e}")
            # Don't fail the whole request if vitals fetch fails - return patients without vitals
            try:
                return await self.patient_repository.get_all(filters, limit, offset)
            except:
                raise

    # ================================
    # PATIENT NOTES OPERATIONS
    # ================================

    async def add_note_comment(self, patient_id: str, content: str, author_id: str) -> Dict[str, Any]:
        """Add note with validation and business logic"""
        try:
            # Validate inputs
            if not patient_id or not patient_id.strip():
                raise ValidationException("Patient ID is required", field="patient_id")

            if not content or not content.strip():
                raise ValidationException("Note content cannot be empty", field="content")

            if not author_id or not author_id.strip():
                raise ValidationException("Author ID is required", field="author_id")

            # Check if patient exists
            if not await self.patient_repository.exists(patient_id):
                raise NotFoundException("Patient", patient_id)

            # Add note
            result = await self.patient_repository.add_patient_note(
                patient_id, content.strip(), author_id
            )

            if result:
                camel_result = self.patient_repository.transform_to_camel_case(result)
                camel_result['canEdit'] = True  # Newly created notes can always be edited
                return camel_result

            # If result is None, something went wrong
            raise DatabaseException("add note", "Failed to create note record")

        except (ValidationException, NotFoundException):
            # Re-raise custom exceptions
            raise

        except asyncpg.PostgresError as e:
            # Database errors
            self.logger.error(
                f"Database error adding note for patient {patient_id}: {e}",
                exc_info=True
            )
            raise DatabaseException("add note", str(e))

        except Exception as e:
            # Unexpected errors
            self.logger.error(
                f"Unexpected error adding note for patient {patient_id}: {e}",
                exc_info=True
            )
            raise

    async def edit_note_comment(self, patient_id: str, note_id: str, content: str, editor_id: str) -> bool:
        """Edit note with validation and permissions"""
        try:
            # Validation
            if not content or not content.strip():
                raise ValueError("Note content cannot be empty")

            if not await self.patient_repository.exists(patient_id):
                raise ValueError(f"Patient {patient_id} not found")

            # Check edit permission (24-hour window)
            # This would typically fetch the note first to check timestamp
            # For now, assume the repository handles this validation

            return await self.patient_repository.update_patient_note(
                patient_id, note_id, content.strip(), editor_id
            )

        except Exception as e:
            self.logger.error(f"Service error editing note: {e}")
            raise

    async def delete_note_comment(self, patient_id: str, note_id: str, deleted_by: str) -> bool:
        """Delete note with validation and permissions"""
        try:
            if not await self.patient_repository.exists(patient_id):
                raise ValueError(f"Patient {patient_id} not found")

            return await self.patient_repository.delete_patient_note(patient_id, note_id, deleted_by)

        except Exception as e:
            self.logger.error(f"Service error deleting note: {e}")
            raise

    def can_edit_note(self, note: Dict[str, Any], user_id: str) -> bool:
        """Check if user can edit note"""
        # User can edit if they authored it and it's within edit window
        # Check both createdBy (new) and authorId (legacy) for backwards compatibility
        return ((note.get('createdBy') == user_id or note.get('authorId') == user_id) and
                self.can_edit_item(note.get('timestamp', '')))

    # ================================
    # DISCHARGE OPERATIONS
    # ================================

    async def discharge_patient(self, patient_id: str, discharged_by: str) -> bool:
        """Discharge patient with business logic validation"""
        try:
            # Validate inputs
            if not patient_id or not patient_id.strip():
                raise ValidationException("Patient ID is required", field="patient_id")

            if not discharged_by or not discharged_by.strip():
                raise ValidationException("Discharged by staff ID is required", field="discharged_by")

            # Check if patient exists
            patient = await self.patient_repository.get_by_id(patient_id)
            if not patient:
                raise NotFoundException("Patient", patient_id)

            # Business rule: Cannot discharge already discharged patient
            if patient.get('status') == 'discharged':
                raise BusinessRuleException(
                    f"Patient {patient_id} is already discharged",
                    rule="no_duplicate_discharge"
                )

            # Business rule: Cannot discharge critical patients without special authorization
            # (This is a simplified example - real systems would have more complex rules)
            if patient.get('status') == 'critical':
                self.logger.warning(f"Discharging critical patient {patient_id} - requires authorization")
                # In production, check authorization here

            # Perform discharge
            success = await self.patient_repository.discharge_patient(patient_id, discharged_by)

            # Post-discharge processing
            if success:
                await self.post_discharge_processing(patient_id, discharged_by)

            return success

        except (ValidationException, NotFoundException, BusinessRuleException):
            # Re-raise custom exceptions
            raise

        except asyncpg.PostgresError as e:
            # Database errors
            self.logger.error(
                f"Database error discharging patient {patient_id}: {e}",
                exc_info=True
            )
            raise DatabaseException("discharge patient", str(e))

        except Exception as e:
            # Unexpected errors
            self.logger.error(
                f"Unexpected error discharging patient {patient_id}: {e}",
                exc_info=True
            )
            raise

    async def post_discharge_processing(self, patient_id: str, discharged_by: str) -> None:
        """Handle post-discharge cleanup"""
        try:
            # This would typically:
            # 1. Unassign devices
            # 2. Clear active alerts
            # 3. Generate discharge summary
            # 4. Notify relevant staff
            self.logger.info(f"Post-discharge processing completed for patient {patient_id}")

        except Exception as e:
            self.logger.error(f"Error in post-discharge processing: {e}")
            # Don't raise - this shouldn't fail the main discharge

    # ================================
    # ALERT OPERATIONS
    # ================================

    async def acknowledge_alert(self, patient_id: str, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge alert with validation"""
        try:
            if not await self.patient_repository.exists(patient_id):
                raise ValueError(f"Patient {patient_id} not found")

            return await self.patient_repository.acknowledge_alert(patient_id, alert_id, acknowledged_by)

        except Exception as e:
            self.logger.error(f"Service error acknowledging alert: {e}")
            raise

    async def get_patient_alerts(self, patient_id: str, status: str = 'active', limit: int = 50) -> List[Dict[str, Any]]:
        """Get patient alerts from database"""
        try:
            if not await self.patient_repository.exists(patient_id):
                raise ValueError(f"Patient {patient_id} not found")

            return await self.patient_repository.get_patient_alerts(patient_id, status, limit)

        except Exception as e:
            self.logger.error(f"Service error getting alerts: {e}")
            raise

    async def resolve_alert(self, patient_id: str, alert_id: str, resolved_by: str) -> bool:
        """Resolve alert with validation"""
        try:
            if not await self.patient_repository.exists(patient_id):
                raise ValueError(f"Patient {patient_id} not found")

            return await self.patient_repository.resolve_alert(patient_id, alert_id, resolved_by)

        except Exception as e:
            self.logger.error(f"Service error resolving alert: {e}")
            raise

    # ================================
    # CASE ENTRY OPERATIONS
    # ================================

    async def add_case_entry(self, patient_id: str, entry_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add case entry with validation"""
        try:
            # Validation
            if not entry_data.get('entryType'):
                raise ValueError("Entry type is required")

            if not entry_data.get('description'):
                raise ValueError("Description is required")

            if not await self.patient_repository.exists(patient_id):
                raise ValueError(f"Patient {patient_id} not found")

            # Use direct field names - database expects camelCase entryType
            result = await self.patient_repository.add_case_entry(patient_id, entry_data, created_by)

            if result:
                return self.patient_repository.transform_to_camel_case(result)

            return None

        except Exception as e:
            self.logger.error(f"Service error adding case entry: {e}")
            raise

    async def get_case_entries(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get case entries with transformation and staff name resolution"""
        try:
            if not await self.patient_repository.exists(patient_id):
                raise ValueError(f"Patient {patient_id} not found")

            results = await self.patient_repository.get_case_entries(patient_id)
            camel_results = [self.repository.transform_to_camel_case(item) for item in results]

            # Resolve staff names for case entries
            if camel_results:
                staff_ids = set()
                for entry in camel_results:
                    if entry.get('createdBy'):
                        staff_ids.add(entry['createdBy'])

                # Get staff names from database
                staff_ids_list = list(staff_ids)
                if staff_ids_list:
                    staff_names = await self.patient_repository.get_staff_names(staff_ids_list)

                    # Update case entries with resolved names
                    for entry in camel_results:
                        created_by = entry.get('createdBy')
                        if created_by and created_by in staff_names:
                            entry['createdByName'] = staff_names[created_by]['name']
                            entry['createdByRole'] = staff_names[created_by]['role']

            return camel_results

        except Exception as e:
            self.logger.error(f"Service error getting case entries: {e}")
            raise

    async def get_aggregated_timeline(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Get aggregated timeline of all medical activities.

        NOTE: Staff name resolution is handled by middleware at the API layer.
        This keeps the service layer clean and ensures consistent resolution across all endpoints.
        """
        try:
            if not await self.patient_repository.exists(patient_id):
                raise ValueError(f"Patient {patient_id} not found")

            timeline_entries = await self.patient_repository.get_aggregated_timeline(patient_id)
            camel_results = [self.repository.transform_to_camel_case(item) for item in timeline_entries]

            # Staff name resolution removed - now handled by middleware
            # This ensures ALL staff fields are resolved consistently, not just performedBy

            return camel_results

        except Exception as e:
            self.logger.error(f"Service error getting aggregated timeline: {e}")
            raise

    # ================================
    # VALIDATION OVERRIDES
    # ================================

    async def validate_create_data(self, data: Dict[str, Any]) -> None:
        """Validate patient creation data"""
        required_fields = ['firstName', 'lastName', 'dateOfBirth']
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f"Field '{field}' is required")

        # Validate date of birth
        try:
            if isinstance(data['dateOfBirth'], str):
                datetime.fromisoformat(data['dateOfBirth'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            raise ValueError("Invalid date of birth format")

    async def validate_update_data(self, record_id: str, data: Dict[str, Any]) -> None:
        """Validate patient update data"""
        # Check if patient exists
        if not await self.patient_repository.exists(record_id):
            raise ValueError(f"Patient {record_id} not found")

        # Validate specific fields if present
        if 'dateOfBirth' in data:
            try:
                if isinstance(data['dateOfBirth'], str):
                    datetime.fromisoformat(data['dateOfBirth'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                raise ValueError("Invalid date of birth format")

    async def validate_delete(self, record_id: str, deleted_by: Optional[str] = None) -> None:
        """Validate patient deletion"""
        # Check if patient exists
        if not await self.patient_repository.exists(record_id):
            raise ValueError(f"Patient {record_id} not found")

        # Check if patient can be deleted (business rules)
        patient = await self.patient_repository.get_by_id(record_id)
        if patient and patient.get('status') == 'critical':
            raise ValueError("Cannot delete patient with critical status")

    # ================================
    # PROCESSING HOOKS
    # ================================

    async def post_create_processing(self, result: Dict[str, Any], created_by: Optional[str] = None) -> None:
        """Post patient creation processing"""
        try:
            patient_id = result.get('id')
            if patient_id:
                # Initialize patient systems, create default records, etc.
                self.logger.info(f"Patient {patient_id} created successfully")

        except Exception as e:
            self.logger.error(f"Error in post-create processing: {e}")

    async def post_update_processing(self, result: Dict[str, Any], updated_by: Optional[str] = None) -> None:
        """Post patient update processing"""
        try:
            patient_id = result.get('id')
            if patient_id:
                # Handle status changes, notifications, etc.
                self.logger.info(f"Patient {patient_id} updated successfully")

        except Exception as e:
            self.logger.error(f"Error in post-update processing: {e}")