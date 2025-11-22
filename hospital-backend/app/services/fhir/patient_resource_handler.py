"""
FHIR R5 Patient Resource Handler

Converts between HMS patient table and FHIR R5 Patient resources.
Provides migration utilities and transformation functions.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date
import asyncpg

from .fhir_resource_service import FhirResourceService

logger = logging.getLogger(__name__)


class PatientResourceHandler:
    """
    Patient resource handler for FHIR R5

    Responsibilities:
    - Convert HMS patient data → FHIR R5 Patient resource
    - Convert FHIR R5 Patient resource → HMS patient data
    - Migrate existing patients to fhir_resources table
    - Provide search and query utilities
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize Patient resource handler

        Args:
            pool: PostgreSQL connection pool
        """
        self.pool = pool
        self.fhir_service = FhirResourceService(pool)

    # ========================================================================
    # HMS → FHIR R5 CONVERSION
    # ========================================================================

    def hms_patient_to_fhir(self, hms_patient: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert HMS patient record to FHIR R5 Patient resource

        Args:
            hms_patient: Patient data from HMS patients table

        Returns:
            FHIR R5 Patient resource
        """
        patient_id = hms_patient['id']  # PAT0001
        mrn = hms_patient.get('mrn')  # HMS2024000001

        # Build identifier array
        identifiers = []
        if mrn:
            identifiers.append({
                "system": "http://hospital.example.com/mrn",
                "value": mrn,
                "type": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "MR",
                        "display": "Medical Record Number"
                    }]
                }
            })

        # Add patient ID as identifier
        identifiers.append({
            "system": "http://hospital.example.com/patient-id",
            "value": patient_id,
            "type": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                    "code": "PI",
                    "display": "Patient Identifier"
                }]
            }
        })

        # Build name
        name = []
        if hms_patient.get('firstName') or hms_patient.get('lastName'):
            name.append({
                "use": "official",
                "family": hms_patient.get('lastName', ''),
                "given": [hms_patient.get('firstName', '')] if hms_patient.get('firstName') else [],
                "text": f"{hms_patient.get('firstName', '')} {hms_patient.get('lastName', '')}".strip()
            })

        # Build telecom
        telecom = []
        if hms_patient.get('phoneNumber'):
            telecom.append({
                "system": "phone",
                "value": hms_patient['phoneNumber'],
                "use": "mobile"
            })

        # Gender mapping (HMS → FHIR)
        gender_map = {
            'male': 'male',
            'female': 'female',
            'other': 'other',
            'unknown': 'unknown',
            'M': 'male',
            'F': 'female'
        }
        gender = gender_map.get(hms_patient.get('gender', '').lower(), 'unknown')

        # Birth date
        birth_date = None
        if hms_patient.get('dateOfBirth'):
            dob = hms_patient['dateOfBirth']
            if isinstance(dob, date):
                birth_date = dob.isoformat()
            elif isinstance(dob, str):
                birth_date = dob

        # Build contact (emergency contact)
        contact = []
        if hms_patient.get('emergencyContactName') or hms_patient.get('emergencyContactPhone'):
            emergency_contact = {
                "relationship": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0131",
                        "code": "C",
                        "display": "Emergency Contact"
                    }]
                }]
            }

            if hms_patient.get('emergencyContactName'):
                # Parse name (assume "FirstName LastName" format)
                parts = hms_patient['emergencyContactName'].split(' ', 1)
                emergency_contact['name'] = {
                    "text": hms_patient['emergencyContactName']
                }
                if len(parts) == 2:
                    emergency_contact['name']['given'] = [parts[0]]
                    emergency_contact['name']['family'] = parts[1]

            if hms_patient.get('emergencyContactPhone'):
                emergency_contact['telecom'] = [{
                    "system": "phone",
                    "value": hms_patient['emergencyContactPhone'],
                    "use": "mobile"
                }]

            contact.append(emergency_contact)

        # Build extensions for HMS-specific fields
        extension = []

        # Blood type extension
        if hms_patient.get('bloodType'):
            extension.append({
                "url": "http://hospital.example.com/fhir/StructureDefinition/blood-type",
                "valueString": hms_patient['bloodType']
            })

        # Weight extension
        if hms_patient.get('weight'):
            extension.append({
                "url": "http://hospital.example.com/fhir/StructureDefinition/weight",
                "valueDecimal": float(hms_patient['weight'])
            })

        # Room/Bed extension
        if hms_patient.get('roomNumber') or hms_patient.get('bedNumber'):
            extension.append({
                "url": "http://hospital.example.com/fhir/StructureDefinition/room-bed",
                "extension": [
                    {
                        "url": "roomNumber",
                        "valueString": hms_patient.get('roomNumber', '')
                    },
                    {
                        "url": "bedNumber",
                        "valueString": hms_patient.get('bedNumber', '')
                    }
                ]
            })

        # Status mapping
        active = hms_patient.get('status') == 'active'

        # Build FHIR Patient resource
        fhir_patient = {
            "resourceType": "Patient",
            "id": patient_id,
            "identifier": identifiers,
            "active": active,
            "name": name,
            "telecom": telecom,
            "gender": gender
        }

        if birth_date:
            fhir_patient['birthDate'] = birth_date

        if contact:
            fhir_patient['contact'] = contact

        if extension:
            fhir_patient['extension'] = extension

        return fhir_patient

    # ========================================================================
    # FHIR R5 → HMS CONVERSION
    # ========================================================================

    def fhir_patient_to_hms(self, fhir_patient: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert FHIR R5 Patient resource to HMS patient record

        Args:
            fhir_patient: FHIR R5 Patient resource

        Returns:
            HMS patient data dict
        """
        hms_patient = {
            "id": fhir_patient['id']
        }

        # Extract MRN from identifiers
        identifiers = fhir_patient.get('identifier', [])
        for ident in identifiers:
            if ident.get('system') == 'http://hospital.example.com/mrn':
                hms_patient['mrn'] = ident['value']
                break

        # Extract name
        names = fhir_patient.get('name', [])
        if names:
            name = names[0]  # Use first name
            hms_patient['firstName'] = name.get('given', [''])[0] if name.get('given') else ''
            hms_patient['lastName'] = name.get('family', '')

        # Extract phone
        telecoms = fhir_patient.get('telecom', [])
        for telecom in telecoms:
            if telecom.get('system') == 'phone':
                hms_patient['phoneNumber'] = telecom['value']
                break

        # Gender
        gender_map = {
            'male': 'male',
            'female': 'female',
            'other': 'other',
            'unknown': 'unknown'
        }
        hms_patient['gender'] = gender_map.get(fhir_patient.get('gender', 'unknown'), 'unknown')

        # Birth date
        if fhir_patient.get('birthDate'):
            hms_patient['dateOfBirth'] = fhir_patient['birthDate']

        # Emergency contact
        contacts = fhir_patient.get('contact', [])
        for contact in contacts:
            # Check if emergency contact
            relationships = contact.get('relationship', [])
            is_emergency = False
            for rel in relationships:
                codings = rel.get('coding', [])
                for coding in codings:
                    if coding.get('code') == 'C':  # Emergency contact code
                        is_emergency = True
                        break

            if is_emergency:
                if contact.get('name'):
                    hms_patient['emergencyContactName'] = contact['name'].get('text', '')

                telecoms = contact.get('telecom', [])
                for telecom in telecoms:
                    if telecom.get('system') == 'phone':
                        hms_patient['emergencyContactPhone'] = telecom['value']
                        break
                break

        # Extract extensions
        extensions = fhir_patient.get('extension', [])
        for ext in extensions:
            url = ext.get('url', '')

            if url == 'http://hospital.example.com/fhir/StructureDefinition/blood-type':
                hms_patient['bloodType'] = ext.get('valueString')

            elif url == 'http://hospital.example.com/fhir/StructureDefinition/weight':
                hms_patient['weight'] = ext.get('valueDecimal')

            elif url == 'http://hospital.example.com/fhir/StructureDefinition/room-bed':
                sub_extensions = ext.get('extension', [])
                for sub_ext in sub_extensions:
                    if sub_ext.get('url') == 'roomNumber':
                        hms_patient['roomNumber'] = sub_ext.get('valueString')
                    elif sub_ext.get('url') == 'bedNumber':
                        hms_patient['bedNumber'] = sub_ext.get('valueString')

        # Status
        hms_patient['status'] = 'active' if fhir_patient.get('active', True) else 'inactive'

        return hms_patient

    # ========================================================================
    # MIGRATION UTILITIES
    # ========================================================================

    async def migrate_patient_to_fhir(
        self,
        patient_id: str,
        created_by: Optional[str] = 'migration'
    ) -> Dict[str, Any]:
        """
        Migrate a single patient from patients table to fhir_resources

        Args:
            patient_id: Patient ID (PAT0001)
            created_by: User performing migration

        Returns:
            Created FHIR Patient resource
        """
        logger.info(f"Migrating patient {patient_id} to FHIR resources")

        async with self.pool.acquire() as conn:
            # Get HMS patient data
            hms_patient = await conn.fetchrow(
                "SELECT * FROM patients WHERE id = $1",
                patient_id
            )

            if not hms_patient:
                raise ValueError(f"Patient {patient_id} not found")

            # Convert to FHIR
            fhir_patient = self.hms_patient_to_fhir(dict(hms_patient))

            # Create in fhir_resources
            created_patient = await self.fhir_service.create(fhir_patient, created_by=created_by)

            logger.info(f"Successfully migrated patient {patient_id}")
            return created_patient

    async def migrate_all_patients(
        self,
        batch_size: int = 100,
        created_by: Optional[str] = 'migration'
    ) -> Dict[str, Any]:
        """
        Migrate all patients from patients table to fhir_resources

        Args:
            batch_size: Number of patients to migrate per batch
            created_by: User performing migration

        Returns:
            Migration statistics
        """
        logger.info("Starting migration of all patients to FHIR resources")

        stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "errors": []
        }

        async with self.pool.acquire() as conn:
            # Get all patient IDs
            patient_ids = await conn.fetch(
                "SELECT id FROM patients ORDER BY id"
            )

            stats['total'] = len(patient_ids)
            logger.info(f"Found {stats['total']} patients to migrate")

            # Migrate in batches
            for i in range(0, len(patient_ids), batch_size):
                batch = patient_ids[i:i + batch_size]
                logger.info(f"Migrating batch {i // batch_size + 1} ({len(batch)} patients)")

                for row in batch:
                    patient_id = row['id']
                    try:
                        await self.migrate_patient_to_fhir(patient_id, created_by=created_by)
                        stats['success'] += 1
                    except Exception as e:
                        logger.error(f"Failed to migrate patient {patient_id}: {e}")
                        stats['failed'] += 1
                        stats['errors'].append({
                            "patientId": patient_id,
                            "error": str(e)
                        })

        logger.info(f"Migration complete: {stats['success']} succeeded, {stats['failed']} failed")
        return stats

    # ========================================================================
    # QUERY UTILITIES
    # ========================================================================

    async def get_patient_by_mrn(self, mrn: str) -> Optional[Dict[str, Any]]:
        """
        Get FHIR Patient resource by MRN

        Args:
            mrn: Medical Record Number (HMS2024000001)

        Returns:
            FHIR Patient resource or None
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT resource
                FROM fhir_resources_active
                WHERE resourceType = 'Patient'
                  AND identifiers @> $1::jsonb
            """, [{"system": "http://hospital.example.com/mrn", "value": mrn}])

            if result:
                return dict(result['resource'])
            return None

    async def search_patients_by_name(
        self,
        name: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search patients by name (partial match)

        Args:
            name: Name to search for
            limit: Maximum results

        Returns:
            List of FHIR Patient resources
        """
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT resource
                FROM fhir_resources_active
                WHERE resourceType = 'Patient'
                  AND (
                      resource->'name'->0->>'family' ILIKE $1
                      OR resource->'name'->0->>'text' ILIKE $1
                      OR EXISTS (
                          SELECT 1 FROM jsonb_array_elements_text(resource->'name'->0->'given') AS given
                          WHERE given ILIKE $1
                      )
                  )
                ORDER BY resource->'name'->0->>'family'
                LIMIT $2
            """, f'%{name}%', limit)

            return [dict(row['resource']) for row in results]
