"""
Device Handler - FHIR R5
Manages medical devices (ESP32 watches, door scanners, etc.)
Supports: GET, POST, PATCH
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from ..repository import FHIRResourceRepository


class DeviceHandler:
    """Handle FHIR Device resources"""

    def __init__(self, repository: FHIRResourceRepository):
        self.repository = repository

    async def create_device(self, device: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new device

        Args:
            device: FHIR R5 Device resource

        Returns:
            Created device resource
        """
        # Validate required fields
        if 'resourceType' not in device or device['resourceType'] != 'Device':
            raise ValueError("Invalid resource type. Must be 'Device'")

        if 'id' not in device:
            raise ValueError("Device ID is required")

        if 'status' not in device:
            device['status'] = 'active'

        # Extract identifier for easier access
        identifier = device.get('identifier', [{}])[0].get('value', device['id'])

        # Add metadata
        if 'meta' not in device:
            device['meta'] = {}

        device['meta']['versionId'] = '1'
        device['meta']['lastUpdated'] = datetime.now(timezone.utc).isoformat()

        # Create in database
        result = await self.repository.create(
            resource_type='Device',
            resource_id=device['id'],
            resource=device,
            status=device['status']
        )

        return result['resource']

    async def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device by ID

        Args:
            device_id: Device ID

        Returns:
            Device resource or None
        """
        result = await self.repository.read('Device', device_id)
        return result['resource'] if result else None

    async def update_device(
        self,
        device_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update device (PATCH operation)

        Args:
            device_id: Device ID
            updates: Fields to update

        Returns:
            Updated device resource
        """
        # Get current device
        current = await self.repository.read('Device', device_id)

        if not current:
            raise ValueError(f"Device {device_id} not found")

        # Merge updates
        device = current['resource']
        device.update(updates)

        # Update metadata
        if 'meta' not in device:
            device['meta'] = {}

        device['meta']['lastUpdated'] = datetime.now(timezone.utc).isoformat()

        # Update in database
        result = await self.repository.update(
            resource_type='Device',
            resource_id=device_id,
            resource=device,
            status=device.get('status')
        )

        return result['resource']

    async def search_devices(
        self,
        status: Optional[str] = None,
        device_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search devices with filters

        Args:
            status: Device status (active, inactive, etc.)
            device_type: Type of device (watch, door_scanner, etc.)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of device resources
        """
        filters = {}

        if status:
            filters['status'] = status

        # Search in database
        results = await self.repository.search(
            resource_type='Device',
            filters=filters,
            limit=limit,
            offset=offset
        )

        devices = [r['resource'] for r in results]

        # Filter by device type if specified
        # (device type is in property array, so we filter in memory)
        if device_type:
            devices = [
                d for d in devices
                if self._get_device_type(d) == device_type
            ]

        return devices

    async def deactivate_device(self, device_id: str) -> Dict[str, Any]:
        """
        Deactivate a device (set status to inactive)

        Args:
            device_id: Device ID

        Returns:
            Updated device resource
        """
        return await self.update_device(device_id, {'status': 'inactive'})

    def _get_device_type(self, device: Dict[str, Any]) -> Optional[str]:
        """Extract device type from property array"""
        properties = device.get('property', [])

        for prop in properties:
            if prop.get('type', {}).get('text') == 'deviceType':
                value = prop.get('valueCodeableConcept', [{}])[0].get('text')
                if value:
                    return value

        return None
