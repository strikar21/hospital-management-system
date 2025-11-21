"""
Patient Handler - FHIR R5
GET only - Patients come from HMS (Hospital Management System)
"""

from typing import Optional, Dict, Any, List
from ..repository import FHIRResourceRepository
import httpx


class PatientHandler:
    """
    Handle FHIR Patient resources
    Note: Patients are cached from HMS, not created in this system
    """

    def __init__(self, repository: FHIRResourceRepository, hms_base_url: Optional[str] = None):
        self.repository = repository
        self.hms_base_url = hms_base_url or "http://localhost:8001"  # Mock HMS server

    async def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Get patient by ID
        First checks local cache, then fetches from HMS if not found
        """
        # Try local cache first
        cached = await self.repository.read('Patient', patient_id)

        if cached:
            return cached['resource']

        # Fetch from HMS
        patient = await self._fetch_from_hms(patient_id)

        if patient:
            # Cache in local database
            await self.repository.create(
                resource_type='Patient',
                resource_id=patient_id,
                resource=patient,
                status=patient.get('active', True) and 'active' or 'inactive'
            )

        return patient

    async def search_patients(
        self,
        identifier: Optional[str] = None,
        name: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search patients
        Searches local cache only (HMS integration would search HMS)
        """
        filters = {}

        # For now, we'll search the cached patients
        # In production, this would also query HMS

        resources = await self.repository.search(
            resource_type='Patient',
            filters=filters,
            limit=limit
        )

        return [r['resource'] for r in resources]

    async def _fetch_from_hms(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch patient from HMS
        Calls HMS API to get patient data in FHIR R5 format
        """
        try:
            async with httpx.AsyncClient() as client:
                # Try FHIR endpoint first
                response = await client.get(
                    f"{self.hms_base_url}/api/patients/{patient_id}/fhir",
                    timeout=5.0
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    # Try standard HMS endpoint and transform
                    hms_response = await client.get(
                        f"{self.hms_base_url}/api/patients/{patient_id}",
                        timeout=5.0
                    )

                    if hms_response.status_code == 200:
                        return self._transform_to_fhir_r5(hms_response.json())

                    return None

        except httpx.TimeoutException:
            print(f"[WARNING] HMS API timeout for patient {patient_id}")
            return None
        except httpx.ConnectError:
            print(f"[WARNING] HMS API connection failed - is HMS server running?")
            return None
        except Exception as e:
            print(f"[ERROR] Failed to fetch patient from HMS: {e}")
            return None

    def _transform_to_fhir_r5(self, hms_patient: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform HMS patient format to FHIR R5 Patient resource
        """
        # This will be implemented when we connect to real HMS
        return {
            "resourceType": "Patient",
            "id": hms_patient.get('id'),
            "identifier": [
                {
                    "system": "http://hospital.example.com/mrn",
                    "value": hms_patient.get('mrn')
                }
            ],
            "name": [
                {
                    "family": hms_patient.get('lastName'),
                    "given": [hms_patient.get('firstName')]
                }
            ],
            "gender": hms_patient.get('gender'),
            "birthDate": hms_patient.get('birthDate')
        }
