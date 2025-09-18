"""
Device management API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from ...models.device import Device, DeviceCreate, DeviceUpdate, DeviceAssignment, DeviceAssignmentCreate
from ...core.database import get_db_connection
from ...services.audit import log_audit_event

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[Device])
async def get_all_devices(
    status: Optional[str] = Query(None, description="Filter by device status"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    available_only: bool = Query(False, description="Show only available devices")
):
    """
    Get all devices with optional filtering
    """
    try:
        async with get_db_connection() as conn:
            query = "SELECT * FROM devices WHERE 1=1"
            params = []
            
            param_count = 0
            
            if status:
                param_count += 1
                query += f" AND status = ${param_count}"
                params.append(status)
            
            if device_type:
                param_count += 1
                query += f" AND devicetype = ${param_count}"
                params.append(device_type)
                
            if available_only:
                query += " AND status = 'available' AND assignedpatientid IS NULL"
            
            query += " ORDER BY createdat DESC"
            
            rows = await conn.fetch(query, *params)
            
            devices = []
            for row in rows:
                device_dict = dict(row) if hasattr(row, 'keys') else row
                logger.info(f"🔍 Raw device data from DB: {device_dict}")
                
                # Transform database field names to model field names
                field_mapping = {
                    'devicetype': 'deviceType',
                    'serialnumber': 'serialNumber',
                    'macaddress': 'macAddress',
                    'firmwareversion': 'firmwareVersion',
                    'batterylevel': 'batteryLevel',
                    'lastseen': 'lastSeen',
                    'assignedpatientid': 'assignedPatientId',
                    'calibrationdate': 'calibrationDate',
                    'nextmaintenancedate': 'nextMaintenanceDate',
                    'createdat': 'createdAt',
                    'updatedat': 'updatedAt'
                }
                
                # Create transformed dict
                transformed_dict = {}
                for db_key, value in device_dict.items():
                    model_key = field_mapping.get(db_key, db_key)
                    transformed_dict[model_key] = value
                
                logger.info(f"🔄 Transformed device data: {transformed_dict}")
                
                try:
                    devices.append(Device(**transformed_dict))
                except Exception as validation_error:
                    logger.error(f"❌ Device validation error: {validation_error}")
                    logger.error(f"❌ Transformed data keys: {list(transformed_dict.keys())}")
                    raise
            
            logger.info(f"📱 Retrieved {len(devices)} devices")
            return devices
            
    except Exception as e:
        logger.error(f"❌ Get devices error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve devices")

@router.get("/{device_id}", response_model=Device)
async def get_device(device_id: str):
    """
    Get a specific device
    """
    try:
        async with get_db_connection() as conn:
            query = "SELECT * FROM devices WHERE id = $1"
            device_row = await conn.fetchrow(query, device_id)
            
            if not device_row:
                raise HTTPException(status_code=404, detail="Device not found")
            
            device_dict = dict(device_row) if hasattr(device_row, 'keys') else device_row
            try:
                return Device(**device_dict)
            except Exception as validation_error:
                logger.error(f"❌ Device validation error: {validation_error}")
                logger.error(f"❌ Device data: {device_dict}")
                raise
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get device error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve device")

@router.post("/", response_model=Device)
async def create_device(device_data: DeviceCreate, created_by: str):
    """
    Create a new device
    """
    try:
        # Generate clean device serial number: Device type + year + sequential
        year = datetime.now().year
        sequential = str(uuid.uuid4().int)[:4].zfill(4)
        device_id = f"HW{year}{sequential}"
        
        async with get_db_connection() as conn:
            query = """
                INSERT INTO devices (
                    id, devicetype, serialnumber, macaddress, firmwareversion,
                    location, status, createdat, updatedat
                ) VALUES ($1, $2, $3, $4, $5, $6, 'available', $7, $8)
            """
            
            now = datetime.now()
            await conn.execute(query,
                device_id, device_data.deviceType, device_data.serialNumber,
                device_data.macAddress, device_data.firmwareVersion,
                device_data.location, now, now
            )
            
            # Log audit event
            await log_audit_event(
                user_id=created_by,
                action="DEVICE_CREATED",
                resource_type="DEVICE",
                resource_id=device_id,
                details=f"Created device: {device_data.deviceType} - {device_data.serialNumber}"
            )
            
            # Get the created device
            created_row = await conn.fetchrow("SELECT * FROM devices WHERE id = $1", device_id)
            device_dict = dict(created_row) if hasattr(created_row, 'keys') else created_row
            
            logger.info(f"✅ Created device: {device_id} - {device_data.deviceType}")
            return Device(**device_dict)
            
    except Exception as e:
        logger.error(f"❌ Create device error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create device")

@router.put("/{device_id}", response_model=Device)
async def update_device(device_id: str, device_data: DeviceUpdate, updated_by: str):
    """
    Update an existing device
    """
    try:
        async with get_db_connection() as conn:
            # Check if device exists
            existing = await conn.fetchrow("SELECT * FROM devices WHERE id = $1", device_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Device not found")
            
            # Build update query for non-None fields
            update_fields = []
            params = []
            
            param_count = 0
            for field, value in device_data.dict(exclude_unset=True).items():
                if value is not None:
                    param_count += 1
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value)
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")
            
            param_count += 1
            update_fields.append(f"updatedat = ${param_count}")
            params.append(datetime.now())
            param_count += 1
            params.append(device_id)
            
            query = f"UPDATE devices SET {', '.join(update_fields)} WHERE id = ${param_count}"
            await conn.execute(query, *params)
            
            # Log audit event
            await log_audit_event(
                user_id=updated_by,
                action="DEVICE_UPDATED",
                resource_type="DEVICE",
                resource_id=device_id,
                details=f"Updated device fields: {list(device_data.dict(exclude_unset=True).keys())}"
            )
            
            # Get updated device
            updated_row = await conn.fetchrow("SELECT * FROM devices WHERE id = $1", device_id)
            device_dict = dict(updated_row) if hasattr(updated_row, 'keys') else updated_row
            
            logger.info(f"✅ Updated device: {device_id}")
            return Device(**device_dict)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update device error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update device")

@router.post("/assign", response_model=DeviceAssignment)
async def assign_device_to_patient(assignment: DeviceAssignmentCreate):
    """
    Assign a device to a patient
    """
    try:
        async with get_db_connection() as conn:
            # Check if patient exists and is active
            patient = await conn.fetchrow(
                "SELECT id FROM patients WHERE id = $1 AND status = 'active'",
                assignment.patientId
            )
            if not patient:
                raise HTTPException(status_code=404, detail="Active patient not found")
            
            # Check if device exists and is available
            device = await conn.fetchrow(
                "SELECT * FROM devices WHERE id = $1 AND status = 'available'",
                assignment.deviceId
            )
            if not device:
                raise HTTPException(status_code=404, detail="Available device not found")
            
            # Check if device is already assigned
            existing_assignment = await conn.fetchrow(
                "SELECT id FROM deviceassignments WHERE deviceid = $1 AND status = 'active'",
                assignment.deviceId
            )
            if existing_assignment:
                raise HTTPException(status_code=400, detail="Device is already assigned")
            
            now = datetime.now()
            
            # Create device assignment
            assignment_query = """
                INSERT INTO deviceassignments (
                    patientid, deviceid, assignedby, assignedat, status, notes
                ) VALUES ($1, $2, $3, $4, 'active', $5)
            """
            await conn.execute(assignment_query,
                assignment.patientId, assignment.deviceId, assignment.assignedBy,
                now, assignment.notes
            )
            
            # Update device status and assignment
            await conn.execute(
                "UPDATE devices SET status = 'assigned', assignedpatientid = $1, lastseen = $2 WHERE id = $3",
                assignment.patientId, now, assignment.deviceId
            )
            
            # Update patient with assigned device
            await conn.execute(
                "UPDATE patients SET assigneddeviceid = $1, updatedat = $2 WHERE id = $3",
                assignment.deviceId, now, assignment.patientId
            )
            
            
            # Log audit event
            await log_audit_event(
                user_id=assignment.assignedBy,
                action="DEVICE_ASSIGNED",
                resource_type="DEVICE_ASSIGNMENT",
                resource_id=assignment.deviceId,
                details=f"Assigned device {assignment.deviceId} to patient {assignment.patientId}"
            )
            
            # Get the created assignment
            assignment_row = await conn.fetchrow(
                "SELECT * FROM deviceassignments WHERE deviceid = $1 AND status = 'active'",
                assignment.deviceId
            )
            assignment_dict = dict(assignment_row) if hasattr(assignment_row, 'keys') else assignment_row
            
            # Transform assignment field names
            assignment_mapping = {
                'patientid': 'patientId',
                'deviceid': 'deviceId',
                'assignedby': 'assignedBy',
                'assignedat': 'assignedAt',
                'unassignedat': 'unassignedAt'
            }
            
            transformed_assignment = {}
            for db_key, value in assignment_dict.items():
                model_key = assignment_mapping.get(db_key, db_key)
                transformed_assignment[model_key] = value
            
            logger.info(f"✅ Device assigned: {assignment.deviceId} → {assignment.patientId}")
            return DeviceAssignment(**transformed_assignment)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Device assignment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign device")

@router.post("/unassign/{device_id}")
async def unassign_device(device_id: str, unassigned_by: str = Query(..., description="Staff ID performing unassignment")):
    """
    Unassign a device from a patient
    """
    try:
        async with get_db_connection() as conn:
            # Check if device exists and is assigned
            device = await conn.fetchrow(
                "SELECT * FROM devices WHERE id = $1 AND status = 'assigned'",
                device_id
            )
            if not device:
                raise HTTPException(status_code=404, detail="Assigned device not found")
            
            device_dict = dict(device) if hasattr(device, 'keys') else device
            patient_id = device_dict.get('assignedpatientid')
            
            now = datetime.now()
            
            # Update device assignment status
            await conn.execute(
                "UPDATE deviceassignments SET status = 'inactive', unassignedat = $1 WHERE deviceid = $2 AND status = 'active'",
                now, device_id
            )
            
            # Update device status
            await conn.execute(
                "UPDATE devices SET status = 'available', assignedpatientid = NULL, updatedat = $1 WHERE id = $2",
                now, device_id
            )
            
            # Update patient
            if patient_id:
                await conn.execute(
                    "UPDATE patients SET assigneddeviceid = NULL, updatedat = $1 WHERE id = $2",
                    now, patient_id
                )
            
            
            # Log audit event
            await log_audit_event(
                user_id=unassigned_by,
                action="DEVICE_UNASSIGNED",
                resource_type="DEVICE_ASSIGNMENT",
                resource_id=device_id,
                details=f"Unassigned device {device_id} from patient {patient_id}"
            )
            
            logger.info(f"✅ Device unassigned: {device_id} from {patient_id}")
            return {
                "message": "Device unassigned successfully",
                "deviceId": device_id,
                "patientId": patient_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Device unassignment error: {e}")
        raise HTTPException(status_code=500, detail="Failed to unassign device")

@router.get("/assignments/", response_model=List[DeviceAssignment])
async def get_device_assignments(
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    active_only: bool = Query(True, description="Show only active assignments")
):
    """
    Get device assignments with optional filtering
    """
    try:
        async with get_db_connection() as conn:
            query = "SELECT * FROM deviceassignments WHERE 1=1"
            params = []
            
            param_count = 0
            
            if patient_id:
                param_count += 1
                query += f" AND patientid = ${param_count}"
                params.append(patient_id)
            
            if device_id:
                param_count += 1
                query += f" AND deviceid = ${param_count}"
                params.append(device_id)
                
            if active_only:
                query += " AND status = 'active'"
            
            query += " ORDER BY assignedat DESC"
            
            rows = await conn.fetch(query, *params)
            
            assignments = []
            for row in rows:
                assignment_dict = dict(row) if hasattr(row, 'keys') else row
                
                # Transform assignment field names
                assignment_mapping = {
                    'patientid': 'patientId',
                    'deviceid': 'deviceId',
                    'assignedby': 'assignedBy',
                    'assignedat': 'assignedAt',
                    'unassignedat': 'unassignedAt'
                }
                
                transformed_assignment = {}
                for db_key, value in assignment_dict.items():
                    model_key = assignment_mapping.get(db_key, db_key)
                    transformed_assignment[model_key] = value
                
                assignments.append(DeviceAssignment(**transformed_assignment))
            
            logger.info(f"📋 Retrieved {len(assignments)} device assignments")
            return assignments
            
    except Exception as e:
        logger.error(f"❌ Get assignments error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve device assignments")