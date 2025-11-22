"""
FHIR Device Service
Manages FHIR R5 Device, DeviceMetric, and DeviceAssociation resources
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
from uuid import UUID

from .fhir_base_service import FhirBaseService


class FhirDeviceService(FhirBaseService):
    """
    Service for managing FHIR R5 Device resources (IoT devices)
    Handles watches, tablets, door scanners
    """

    def __init__(self):
        super().__init__(table_name='fhir_devices', use_timescale=False)
        self.logger = logging.getLogger(__name__)

    # ================================
    # DEVICE CRUD OPERATIONS
    # ================================

    async def create_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create FHIR R5 Device resource

        Args:
            device_data: {
                "deviceId": "fit-00001",
                "deviceType": "watch",
                "displayName": "Fit Watch 00001",
                "manufacturer": "Custom ESP32",
                "modelNumber": "ESP32-WATCH-V2",
                "serialNumber": "ESP32-SN-00001",
                "macAddress": "AA:BB:CC:DD:EE:FF",
                "firmwareVersion": "v2.1.3",
                "batteryLevel": 85,
                "status": "active"
            }

        Returns:
            Created Device resource
        """
        try:
            # Build FHIR R5 Device resource
            resource = self._build_device_resource(device_data)

            # Extract searchable fields
            extracted = self.extract_searchable_fields(device_data)

            # Create with JSONB + extracted fields
            return await self.create(resource=resource, **extracted)

        except Exception as e:
            self.logger.error(f"Error creating device: {e}")
            raise

    async def update_device(self, device_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update device (both FHIR resource and extracted fields)"""
        try:
            # Get existing device
            existing = await self.get_by_id(device_id)
            if not existing:
                raise ValueError(f"Device not found: {device_id}")

            # Update FHIR resource
            updated_resource = existing['resource'].copy()

            # Update properties if changed
            if 'batteryLevel' in updates or 'firmwareVersion' in updates:
                if 'property' not in updated_resource:
                    updated_resource['property'] = []

                # Update battery level
                if 'batteryLevel' in updates:
                    battery_prop = next((p for p in updated_resource['property'] if p.get('type', {}).get('text') == 'Battery Level'), None)
                    if battery_prop:
                        battery_prop['valueQuantity'] = {"value": updates['batteryLevel'], "unit": "%"}
                    else:
                        updated_resource['property'].append({
                            "type": {"text": "Battery Level"},
                            "valueQuantity": {"value": updates['batteryLevel'], "unit": "%"}
                        })

                # Update firmware
                if 'firmwareVersion' in updates:
                    firmware_prop = next((p for p in updated_resource['property'] if p.get('type', {}).get('text') == 'Firmware Version'), None)
                    if firmware_prop:
                        firmware_prop['valueString'] = updates['firmwareVersion']
                    else:
                        updated_resource['property'].append({
                            "type": {"text": "Firmware Version"},
                            "valueString": updates['firmwareVersion']
                        })

            # Update status
            if 'status' in updates:
                updated_resource['status'] = updates['status']

            # Prepare update payload
            update_payload = {'resource': updated_resource}

            # Add extracted field updates
            for key in ['batteryLevel', 'firmwareVersion', 'status', 'lastSeen', 'maintenanceStatus', 'calibrationDueDate']:
                if key in updates:
                    update_payload[key] = updates[key]

            return await self.update(device_id, update_payload)

        except Exception as e:
            self.logger.error(f"Error updating device: {e}")
            raise

    async def get_device_by_device_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device by deviceId (fit-00001, ESP32_WATCH_002, etc.)"""
        try:
            results = await self.search(filters={'deviceId': device_id}, limit=1)
            return results[0] if results else None

        except Exception as e:
            self.logger.error(f"Error getting device by deviceId: {e}")
            raise

    async def get_device_by_mac(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Get device by MAC address"""
        try:
            results = await self.search(filters={'macAddress': mac_address}, limit=1)
            return results[0] if results else None

        except Exception as e:
            self.logger.error(f"Error getting device by MAC: {e}")
            raise

    async def get_devices_by_type(self, device_type: str, status: str = 'active',
                                  limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get devices by type (watch, tablet, doorScanner)"""
        try:
            return await self.search(
                filters={'deviceType': device_type, 'status': status},
                limit=limit,
                offset=offset
            )

        except Exception as e:
            self.logger.error(f"Error getting devices by type: {e}")
            raise

    async def get_available_devices(self, device_type: Optional[str] = None,
                                   limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get available devices (not currently assigned)
        Uses device_availability view
        """
        try:
            async with self.get_connection() as conn:
                where_clauses = ["assignmentStatus = 'available'", "status = 'active'"]
                values = []
                param_count = 1

                if device_type:
                    where_clauses.append(f'"deviceType" = ${param_count}')
                    values.append(device_type)
                    param_count += 1

                where_sql = " AND ".join(where_clauses)

                query = f"""
                    SELECT * FROM device_availability
                    WHERE {where_sql}
                    ORDER BY "lastSeen" DESC
                    LIMIT ${param_count} OFFSET ${param_count + 1}
                """

                values.extend([limit, offset])

                results = await conn.fetch(query, *values)
                return [dict(row) for row in results]

        except Exception as e:
            self.logger.error(f"Error getting available devices: {e}")
            raise

    async def update_device_health(self, device_id: str, battery_level: int,
                                  last_seen: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Update device health metrics (battery, last seen)"""
        try:
            updates = {
                'batteryLevel': battery_level,
                'lastSeen': last_seen or datetime.utcnow()
            }

            return await self.update_device(device_id, updates)

        except Exception as e:
            self.logger.error(f"Error updating device health: {e}")
            raise

    # ================================
    # DEVICE ASSOCIATION (Assignment)
    # ================================

    async def assign_device_to_patient(self, device_id: str, patient_context_id: str,
                                      operator_reference: Optional[str] = None,
                                      assignment_reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Assign device to patient (create DeviceAssociation)

        Args:
            device_id: UUID of fhir_devices
            patient_context_id: UUID of patient_clinical_context
            operator_reference: HMS Practitioner URL who assigned it
            assignment_reason: Reason for assignment

        Returns:
            Created DeviceAssociation
        """
        try:
            # Build FHIR R5 DeviceAssociation resource
            association_resource = {
                "resourceType": "DeviceAssociation",
                "subject": {"reference": f"PatientClinicalContext/{patient_context_id}"},
                "device": {"reference": f"Device/{device_id}"},
                "status": {"coding": [{"code": "attached"}]},
                "period": {
                    "start": datetime.utcnow().isoformat() + 'Z'
                }
            }

            if operator_reference:
                association_resource['operator'] = [{"reference": operator_reference}]

            # Create in fhir_device_associations table
            async with self.get_connection() as conn:
                query = """
                    INSERT INTO fhir_device_associations
                    (resource, "patientContextId", "deviceId", status, "periodStart", "operatorReference", "assignmentReason")
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id, resource, "patientContextId", "deviceId", status, "periodStart", "createdAt"
                """

                import json
                result = await conn.fetchrow(
                    query,
                    json.dumps(association_resource),
                    UUID(patient_context_id),
                    UUID(device_id),
                    'attached',
                    datetime.utcnow(),
                    operator_reference,
                    assignment_reason
                )

                result_dict = dict(result)
                result_dict['resource'] = json.loads(result_dict['resource']) if isinstance(result_dict['resource'], str) else result_dict['resource']

                self.logger.info(f"Assigned device {device_id} to patient {patient_context_id}")
                return result_dict

        except Exception as e:
            self.logger.error(f"Error assigning device: {e}")
            raise

    async def unassign_device(self, association_id: str) -> Dict[str, Any]:
        """Unassign device from patient (end DeviceAssociation period)"""
        try:
            async with self.get_connection() as conn:
                query = """
                    UPDATE fhir_device_associations
                    SET "periodEnd" = $1, status = 'entered-in-error'
                    WHERE id = $2
                    RETURNING *
                """

                result = await conn.fetchrow(query, datetime.utcnow(), UUID(association_id))

                if not result:
                    raise ValueError(f"Device association not found: {association_id}")

                result_dict = dict(result)
                import json
                result_dict['resource'] = json.loads(result_dict['resource']) if isinstance(result_dict['resource'], str) else result_dict['resource']

                self.logger.info(f"Unassigned device association: {association_id}")
                return result_dict

        except Exception as e:
            self.logger.error(f"Error unassigning device: {e}")
            raise

    async def get_device_assignment(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current active assignment for a device"""
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT * FROM fhir_device_associations
                    WHERE "deviceId" = $1
                      AND "periodEnd" IS NULL
                      AND status = 'attached'
                    ORDER BY "periodStart" DESC
                    LIMIT 1
                """

                result = await conn.fetchrow(query, UUID(device_id))

                if not result:
                    return None

                result_dict = dict(result)
                import json
                result_dict['resource'] = json.loads(result_dict['resource']) if isinstance(result_dict['resource'], str) else result_dict['resource']
                return result_dict

        except Exception as e:
            self.logger.error(f"Error getting device assignment: {e}")
            raise

    async def get_patient_devices(self, patient_context_id: str) -> List[Dict[str, Any]]:
        """Get all currently assigned devices for a patient"""
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT da.*, d.resource as device_resource, d."deviceId", d."deviceType", d."displayName", d."batteryLevel"
                    FROM fhir_device_associations da
                    JOIN fhir_devices d ON da."deviceId" = d.id
                    WHERE da."patientContextId" = $1
                      AND da."periodEnd" IS NULL
                      AND da.status = 'attached'
                    ORDER BY da."periodStart" DESC
                """

                results = await conn.fetch(query, UUID(patient_context_id))

                import json
                result_list = []
                for row in results:
                    row_dict = dict(row)
                    row_dict['resource'] = json.loads(row_dict['resource']) if isinstance(row_dict['resource'], str) else row_dict['resource']
                    row_dict['device_resource'] = json.loads(row_dict['device_resource']) if isinstance(row_dict['device_resource'], str) else row_dict['device_resource']
                    result_list.append(row_dict)

                return result_list

        except Exception as e:
            self.logger.error(f"Error getting patient devices: {e}")
            raise

    # ================================
    # VALIDATION & EXTRACTION
    # ================================

    async def validate_resource(self, resource: Dict[str, Any]) -> None:
        """Validate FHIR Device resource"""
        if resource.get('resourceType') != 'Device':
            raise ValueError("Resource type must be Device")

        # Must have at least one identifier
        if not resource.get('identifier') or len(resource['identifier']) == 0:
            raise ValueError("Device must have at least one identifier")

    def extract_searchable_fields(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fields from device data for table columns"""
        extracted = {}

        # Required fields
        if 'deviceId' in device_data:
            extracted['deviceId'] = device_data['deviceId']
        if 'deviceType' in device_data:
            extracted['deviceType'] = device_data['deviceType']

        # Optional fields
        for key in ['macAddress', 'displayName', 'manufacturer', 'modelNumber', 'serialNumber',
                   'status', 'batteryLevel', 'firmwareVersion', 'lastSeen',
                   'lastCalibrationDate', 'calibrationDueDate', 'maintenanceStatus']:
            if key in device_data:
                extracted[key] = device_data[key]

        return extracted

    def _build_device_resource(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build FHIR R5 Device resource from device data"""
        resource = {
            "resourceType": "Device",
            "identifier": [
                {
                    "system": "https://hospital.local/devices",
                    "value": device_data['deviceId']
                }
            ],
            "displayName": device_data.get('displayName', device_data['deviceId']),
            "type": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": self._get_snomed_code_for_type(device_data.get('deviceType', 'other')),
                    "display": device_data.get('deviceType', 'other').title()
                }]
            },
            "status": device_data.get('status', 'active')
        }

        # Add MAC address as identifier
        if device_data.get('macAddress'):
            resource['identifier'].append({
                "type": {"text": "MAC Address"},
                "value": device_data['macAddress']
            })

        # Add manufacturer details
        if device_data.get('manufacturer'):
            resource['manufacturer'] = device_data['manufacturer']
        if device_data.get('modelNumber'):
            resource['modelNumber'] = device_data['modelNumber']
        if device_data.get('serialNumber'):
            resource['serialNumber'] = device_data['serialNumber']

        # Add properties (battery, firmware)
        resource['property'] = []

        if device_data.get('batteryLevel') is not None:
            resource['property'].append({
                "type": {"text": "Battery Level"},
                "valueQuantity": {"value": device_data['batteryLevel'], "unit": "%"}
            })

        if device_data.get('firmwareVersion'):
            resource['property'].append({
                "type": {"text": "Firmware Version"},
                "valueString": device_data['firmwareVersion']
            })

        # Add owner (hospital organization)
        resource['owner'] = {"reference": "Organization/hospital"}

        return resource

    def _get_snomed_code_for_type(self, device_type: str) -> str:
        """Map device type to SNOMED CT code"""
        type_map = {
            'watch': '706767009',  # Patient monitoring system
            'tablet': '469824003',  # Display device
            'doorScanner': '706689003',  # Monitoring equipment
            'sensor': '706767009',  # Patient monitoring system
            'other': '462242008'  # Medical device
        }
        return type_map.get(device_type, type_map['other'])
