"""
Patient Clinical Context Service
Manages cached patient clinical data for AI vitals analysis
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, date
import logging

from .fhir_base_service import FhirBaseService


class PatientClinicalContextService(FhirBaseService):
    """
    Service for managing patient clinical context
    Caches minimal patient data from external HMS for AI analysis
    """

    def __init__(self):
        super().__init__(table_name='patient_clinical_context', use_timescale=False)
        self.logger = logging.getLogger(__name__)

    # ================================
    # CREATE / UPDATE OPERATIONS
    # ================================

    async def create_or_update_from_hms(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update patient clinical context from HMS data

        Args:
            context_data: {
                "abhaNumber": "91-1234-5678-9012",
                "mrn": "MRN001",
                "externalPatientUrl": "https://hms.hospital.com/fhir/Patient/123",
                "birthDate": "1985-06-15",
                "gender": "male",
                "weight": 75.5,
                "height": 175,
                "isPregnant": false,
                "comorbidities": {"diabetes": true},
                "roomNumber": "201",
                "bedNumber": "A",
                "admissionDate": "2025-11-18T10:00:00Z"
            }

        Returns:
            Created or updated patient context
        """
        try:
            # Check if patient exists (by ABHA or MRN)
            existing = None
            if context_data.get('abhaNumber'):
                existing = await self.get_by_abha_number(context_data['abhaNumber'])
            elif context_data.get('mrn'):
                existing = await self.get_by_mrn(context_data['mrn'])

            # Add sync metadata
            context_data['lastSyncedFromHms'] = datetime.utcnow()
            context_data['syncSource'] = context_data.get('syncSource', 'hms_push')

            if existing:
                # Update existing
                return await self.update_context(existing['id'], context_data)
            else:
                # Create new
                return await self.create_context(context_data)

        except Exception as e:
            self.logger.error(f"Error creating/updating patient context from HMS: {e}")
            raise

    async def create_context(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new patient clinical context"""
        try:
            # Build FHIR-style resource (minimal, just for consistency)
            resource = {
                "resourceType": "PatientClinicalContext",  # Custom resource type
                "identifier": [],
                "meta": {
                    "source": context_data.get('syncSource', 'manual_entry')
                }
            }

            if context_data.get('abhaNumber'):
                resource['identifier'].append({
                    "system": "https://healthid.ndhm.gov.in",
                    "value": context_data['abhaNumber']
                })

            if context_data.get('mrn'):
                resource['identifier'].append({
                    "system": "https://hospital.local/mrn",
                    "value": context_data['mrn']
                })

            # Extract fields for table columns
            extracted = self.extract_searchable_fields(context_data)

            # Create with JSONB + extracted fields
            return await self.create(resource=resource, **extracted)

        except Exception as e:
            self.logger.error(f"Error creating patient context: {e}")
            raise

    async def update_context(self, context_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update patient clinical context"""
        try:
            # Remove fields that shouldn't be updated directly
            updates_copy = {k: v for k, v in updates.items() if k not in ['id', 'createdAt', 'updatedAt']}

            return await self.update(context_id, updates_copy)

        except Exception as e:
            self.logger.error(f"Error updating patient context: {e}")
            raise

    # ================================
    # QUERY OPERATIONS
    # ================================

    async def get_by_abha_number(self, abha_number: str) -> Optional[Dict[str, Any]]:
        """Get patient context by ABHA number"""
        try:
            results = await self.search(filters={'abhaNumber': abha_number}, limit=1)
            return results[0] if results else None

        except Exception as e:
            self.logger.error(f"Error getting patient by ABHA: {e}")
            raise

    async def get_by_mrn(self, mrn: str) -> Optional[Dict[str, Any]]:
        """Get patient context by Medical Record Number"""
        try:
            results = await self.search(filters={'mrn': mrn}, limit=1)
            return results[0] if results else None

        except Exception as e:
            self.logger.error(f"Error getting patient by MRN: {e}")
            raise

    async def get_by_room_bed(self, room_number: str, bed_number: str) -> Optional[Dict[str, Any]]:
        """Get patient by room and bed assignment"""
        try:
            results = await self.search(
                filters={'roomNumber': room_number, 'bedNumber': bed_number, 'admissionStatus': 'admitted'},
                limit=1
            )
            return results[0] if results else None

        except Exception as e:
            self.logger.error(f"Error getting patient by room/bed: {e}")
            raise

    async def get_active_patients(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get all currently admitted patients"""
        try:
            return await self.search(
                filters={'active': True, 'admissionStatus': 'admitted'},
                limit=limit,
                offset=offset
            )

        except Exception as e:
            self.logger.error(f"Error getting active patients: {e}")
            raise

    async def get_clinical_context_for_ai(self, patient_id: str) -> Dict[str, Any]:
        """
        Get clinical context optimized for AI vitals analysis

        Returns:
            {
                "age": 40,
                "gender": "male",
                "weight": 75.5,
                "height": 175,
                "bmi": 24.7,
                "isPregnant": false,
                "comorbidities": {"hypertension": true}
            }
        """
        try:
            context = await self.get_by_id(patient_id)
            if not context:
                raise ValueError(f"Patient context not found: {patient_id}")

            # Calculate age from birthDate
            birth_date = context.get('birthDate')
            age = self._calculate_age(birth_date) if birth_date else None

            return {
                "age": age,
                "gender": context.get('gender'),
                "weight": float(context.get('weight')) if context.get('weight') else None,
                "height": float(context.get('height')) if context.get('height') else None,
                "bmi": float(context.get('bmi')) if context.get('bmi') else None,
                "isPregnant": context.get('isPregnant', False),
                "comorbidities": context.get('comorbidities', {}),
                "currentMedications": context.get('currentMedications', []),
                "allergies": context.get('allergies', [])
            }

        except Exception as e:
            self.logger.error(f"Error getting AI context: {e}")
            raise

    # ================================
    # ADMISSION MANAGEMENT
    # ================================

    async def admit_patient(self, patient_id: str, room_number: str, bed_number: str,
                           admission_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Admit patient to room/bed"""
        try:
            updates = {
                'roomNumber': room_number,
                'bedNumber': bed_number,
                'admissionDate': admission_date or datetime.utcnow(),
                'admissionStatus': 'admitted',
                'active': True
            }

            return await self.update(patient_id, updates)

        except Exception as e:
            self.logger.error(f"Error admitting patient: {e}")
            raise

    async def discharge_patient(self, patient_id: str) -> Dict[str, Any]:
        """Discharge patient"""
        try:
            updates = {
                'admissionStatus': 'discharged',
                'active': False
            }

            return await self.update(patient_id, updates)

        except Exception as e:
            self.logger.error(f"Error discharging patient: {e}")
            raise

    # ================================
    # VALIDATION & EXTRACTION
    # ================================

    async def validate_resource(self, resource: Dict[str, Any]) -> None:
        """Validate patient context resource"""
        if resource.get('resourceType') != 'PatientClinicalContext':
            raise ValueError("Resource type must be PatientClinicalContext")

        # Basic validation - at least one identifier required
        if not resource.get('identifier') or len(resource['identifier']) == 0:
            raise ValueError("At least one identifier (ABHA or MRN) is required")

    def extract_searchable_fields(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields from context data for table columns"""
        extracted = {}

        # Identifiers
        if 'abhaNumber' in context_data:
            extracted['abhaNumber'] = context_data['abhaNumber']
        if 'mrn' in context_data:
            extracted['mrn'] = context_data['mrn']
        if 'externalPatientUrl' in context_data:
            extracted['externalPatientUrl'] = context_data['externalPatientUrl']
        if 'externalEncounterUrl' in context_data:
            extracted['externalEncounterUrl'] = context_data['externalEncounterUrl']

        # Demographics
        if 'birthDate' in context_data:
            extracted['birthDate'] = context_data['birthDate'] if isinstance(context_data['birthDate'], date) else datetime.fromisoformat(context_data['birthDate'].replace('Z', '+00:00')).date()
        if 'gender' in context_data:
            extracted['gender'] = context_data['gender']

        # Physical measurements
        if 'weight' in context_data:
            extracted['weight'] = float(context_data['weight'])
        if 'height' in context_data:
            extracted['height'] = float(context_data['height'])

        # Clinical context
        if 'isPregnant' in context_data:
            extracted['isPregnant'] = bool(context_data['isPregnant'])
        if 'comorbidities' in context_data:
            extracted['comorbidities'] = context_data['comorbidities']
        if 'currentMedications' in context_data:
            extracted['currentMedications'] = context_data['currentMedications']
        if 'allergies' in context_data:
            extracted['allergies'] = context_data['allergies']

        # Admission details
        if 'roomNumber' in context_data:
            extracted['roomNumber'] = context_data['roomNumber']
        if 'bedNumber' in context_data:
            extracted['bedNumber'] = context_data['bedNumber']
        if 'admissionDate' in context_data:
            extracted['admissionDate'] = context_data['admissionDate'] if isinstance(context_data['admissionDate'], datetime) else datetime.fromisoformat(context_data['admissionDate'].replace('Z', '+00:00'))
        if 'expectedDischargeDate' in context_data:
            extracted['expectedDischargeDate'] = context_data['expectedDischargeDate'] if isinstance(context_data['expectedDischargeDate'], datetime) else datetime.fromisoformat(context_data['expectedDischargeDate'].replace('Z', '+00:00'))
        if 'admissionStatus' in context_data:
            extracted['admissionStatus'] = context_data['admissionStatus']

        # Sync metadata
        if 'lastSyncedFromHms' in context_data:
            extracted['lastSyncedFromHms'] = context_data['lastSyncedFromHms']
        if 'syncSource' in context_data:
            extracted['syncSource'] = context_data['syncSource']

        # Active status
        if 'active' in context_data:
            extracted['active'] = bool(context_data['active'])

        return extracted

    # ================================
    # UTILITY METHODS
    # ================================

    def _calculate_age(self, birth_date: date) -> int:
        """Calculate age from birth date"""
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        return age
