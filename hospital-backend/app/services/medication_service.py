"""
Medication Service - Business logic layer for medication operations
"""

from typing import Dict, List, Optional, Any
import asyncpg

from .base_service import BaseService
from ..repositories.medication_repository import MedicationRepository


class MedicationService(BaseService):
    """Medication service handling all medication business logic"""

    def __init__(self):
        self.medication_repository = MedicationRepository()
        super().__init__(self.medication_repository)

    async def get_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get medications by patient ID"""
        results = await self.medication_repository.get_by_patient_id(patient_id)
        return [self.repository.transform_to_camel_case(item) for item in results]

    async def add_medication(self, patient_id: str, medication_data: Dict[str, Any], created_by: str) -> Dict[str, Any]:
        """Add medication with validation and FK constraint handling"""
        try:
            # Validate required fields
            required_fields = ['medicationName', 'dosage', 'frequency']
            for field in required_fields:
                if not medication_data.get(field):
                    raise ValueError(f"Field '{field}' is required")

            # Transform from camelCase to snake_case
            snake_data = self.repository.transform_from_camel_case(medication_data)

            result = await self.medication_repository.add_medication(patient_id, snake_data, created_by)

            if result:
                return self.repository.transform_to_camel_case(result)
            return None

        except asyncpg.exceptions.ForeignKeyViolationError as e:
            # Parse which FK constraint was violated
            error_msg = str(e)

            if 'fk_medications_patient' in error_msg:
                self.logger.error(f"Patient FK violation: patient {patient_id} not found")
                raise ValueError(f"Patient {patient_id} not found. Cannot create medication for non-existent patient.")
            elif 'fk_medications_prescriber' in error_msg:
                prescriber = medication_data.get('prescribedBy', 'unknown')
                self.logger.error(f"Prescriber FK violation: {prescriber} not found in staff")
                raise ValueError(f"Prescriber {prescriber} not found in staff directory. Please verify the staff ID.")
            elif 'fk_medications_creator' in error_msg:
                self.logger.error(f"Creator FK violation: {created_by} not found in staff")
                raise ValueError(f"Creator {created_by} not found in system.")
            else:
                self.logger.error(f"Unknown FK violation in add_medication: {e}")
                raise ValueError("Referenced record not found. Please check all IDs are valid.")

        except asyncpg.exceptions.UniqueViolationError as e:
            self.logger.error(f"Unique violation in add_medication: {e}")
            raise ValueError("Duplicate medication record. This medication may already exist for this patient.")

        except ValueError as e:
            # Re-raise validation errors
            raise

        except Exception as e:
            self.logger.error(f"Unexpected error in add_medication: {e}", exc_info=True)
            raise RuntimeError("Failed to create medication due to database error.")

    async def update_medication(self, patient_id: str, medication_id: str, status: str, updated_by: str) -> bool:
        """Update medication status"""
        valid_statuses = ['active', 'stopped', 'held', 'completed']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        return await self.medication_repository.update_medication_status(
            patient_id, medication_id, status, updated_by
        )

    async def get_medications_with_schedule(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get medications with their next scheduled dose times"""
        import json

        results = await self.medication_repository.get_medications_with_schedule(patient_id)
        medications_with_schedule = []

        for medication in results:
            # Transform medication data to camelCase
            med_data = self.repository.transform_to_camel_case(medication)

            # Handle next administration data (it gets transformed to nextAdministration)
            next_admin_raw = med_data.get('nextAdministration')

            if next_admin_raw:
                # Parse JSON string if it's a string
                if isinstance(next_admin_raw, str):
                    try:
                        next_admin = json.loads(next_admin_raw)
                    except (json.JSONDecodeError, TypeError):
                        next_admin = None
                else:
                    next_admin = next_admin_raw

                if next_admin and isinstance(next_admin, dict):
                    next_dose = next_admin.get('nextDose')
                    if next_dose:
                        med_data['nextDoseTime'] = next_dose
                        med_data['nextDoseStatus'] = next_admin.get('status', 'scheduled')
                        if next_admin.get('notes'):
                            med_data['nextDoseNotes'] = next_admin.get('notes')
                    else:
                        med_data['nextDoseTime'] = None
                        med_data['nextDoseStatus'] = None
                else:
                    med_data['nextDoseTime'] = None
                    med_data['nextDoseStatus'] = None
            else:
                med_data['nextDoseTime'] = None
                med_data['nextDoseStatus'] = None

            # Remove the raw nextAdministration field
            med_data.pop('nextAdministration', None)
            medications_with_schedule.append(med_data)

        return medications_with_schedule