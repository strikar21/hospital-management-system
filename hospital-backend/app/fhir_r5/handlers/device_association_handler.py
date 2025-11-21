"""
DeviceAssociation Handler - FHIR R5
Manages device-to-patient assignments
Supports: GET, POST, PATCH
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from ..repository import FHIRResourceRepository


class DeviceAssociationHandler:
    """Handle FHIR DeviceAssociation resources"""

    def __init__(self, repository: FHIRResourceRepository):
        self.repository = repository

    async def create_association(self, association: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new device-patient association

        Args:
            association: FHIR R5 DeviceAssociation resource

        Returns:
            Created association resource
        """
        # Validate required fields
        if 'resourceType' not in association or association['resourceType'] != 'DeviceAssociation':
            raise ValueError("Invalid resource type. Must be 'DeviceAssociation'")

        if 'id' not in association:
            raise ValueError("Association ID is required")

        if 'subject' not in association:
            raise ValueError("Patient reference (subject) is required")

        if 'device' not in association:
            raise ValueError("Device reference is required")

        # Set default status if not provided
        if 'status' not in association:
            association['status'] = {'coding': [{'code': 'active'}]}

        # Set period start if not provided
        if 'period' not in association:
            association['period'] = {}

        if 'start' not in association['period']:
            association['period']['start'] = datetime.now(timezone.utc).isoformat()

        # Add metadata
        if 'meta' not in association:
            association['meta'] = {}

        association['meta']['versionId'] = '1'
        association['meta']['lastUpdated'] = datetime.now(timezone.utc).isoformat()

        # Extract subject for indexing
        subject = association['subject'].get('reference', '')

        # Extract status code
        status_code = association['status'].get('coding', [{}])[0].get('code', 'active')

        # Create in database
        result = await self.repository.create(
            resource_type='DeviceAssociation',
            resource_id=association['id'],
            resource=association,
            status=status_code,
            subject=subject
        )

        return result['resource']

    async def get_association(self, association_id: str) -> Optional[Dict[str, Any]]:
        """
        Get association by ID

        Args:
            association_id: Association ID

        Returns:
            Association resource or None
        """
        result = await self.repository.read('DeviceAssociation', association_id)
        return result['resource'] if result else None

    async def update_association(
        self,
        association_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update association (PATCH operation)

        Args:
            association_id: Association ID
            updates: Fields to update

        Returns:
            Updated association resource
        """
        # Get current association
        current = await self.repository.read('DeviceAssociation', association_id)

        if not current:
            raise ValueError(f"Association {association_id} not found")

        # Merge updates
        association = current['resource']
        association.update(updates)

        # Update metadata
        if 'meta' not in association:
            association['meta'] = {}

        association['meta']['lastUpdated'] = datetime.now(timezone.utc).isoformat()

        # Extract updated values
        subject = association['subject'].get('reference', '')
        status_code = association['status'].get('coding', [{}])[0].get('code', 'active')

        # Update in database
        result = await self.repository.update(
            resource_type='DeviceAssociation',
            resource_id=association_id,
            resource=association,
            status=status_code,
            subject=subject
        )

        return result['resource']

    async def search_associations(
        self,
        patient_id: Optional[str] = None,
        device_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search device associations

        Args:
            patient_id: Filter by patient
            device_id: Filter by device
            status: Filter by status (active, inactive, etc.)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of association resources
        """
        filters = {}

        if patient_id:
            filters['subject'] = f'Patient/{patient_id}'

        if status:
            filters['status'] = status

        # Search in database
        results = await self.repository.search(
            resource_type='DeviceAssociation',
            filters=filters,
            limit=limit,
            offset=offset
        )

        associations = [r['resource'] for r in results]

        # Filter by device if specified
        # (device is a reference, so we filter in memory)
        if device_id:
            associations = [
                a for a in associations
                if a.get('device', {}).get('reference', '').endswith(device_id)
            ]

        return associations

    async def end_association(
        self,
        association_id: str,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        End a device association

        Args:
            association_id: Association ID
            end_time: End time (defaults to now)

        Returns:
            Updated association resource
        """
        if not end_time:
            end_time = datetime.now(timezone.utc)

        updates = {
            'status': {'coding': [{'code': 'completed'}]},
            'period': {}
        }

        # Get current association to preserve period.start
        current = await self.repository.read('DeviceAssociation', association_id)

        if current and 'period' in current['resource']:
            updates['period'] = current['resource']['period']

        updates['period']['end'] = end_time.isoformat()

        return await self.update_association(association_id, updates)

    async def get_active_device_for_patient(
        self,
        patient_id: str,
        device_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the active device association for a patient

        Args:
            patient_id: Patient ID
            device_type: Optional device type filter

        Returns:
            Active association or None
        """
        associations = await self.search_associations(
            patient_id=patient_id,
            status='active',
            limit=10
        )

        # Filter associations without end date
        active = [
            a for a in associations
            if not a.get('period', {}).get('end')
        ]

        if active:
            return active[0]

        return None
