from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import logging

from app.db.database import database
from app.schemas.device_assignment import DeviceAssignmentCreate, DeviceAssignmentResponse, DeviceAssignmentUpdate

logger = logging.getLogger(__name__)

class DeviceAssignmentService:
    @staticmethod
    async def get_free_devices(device_type: str = None, location: str = None) -> List[Dict[str, Any]]:
        """Get list of available devices from free pool"""
        try:
            where_conditions = ['"isActive" = true', '"assignmentStatus" = \'free\'']
            params = {}
            
            if device_type:
                where_conditions.append('"deviceType" = :device_type')
                params["device_type"] = device_type
                
            if location:
                where_conditions.append("location = :location")
                params["location"] = location
                
            where_clause = " AND ".join(where_conditions)
            
            query = f"""
                SELECT "deviceId", name, "deviceType", location, status, "batteryLevel", 
                       "lastHeartbeat", "createdAt"
                FROM devices
                WHERE {where_clause}
                ORDER BY "batteryLevel" DESC, "lastHeartbeat" DESC
            """
            
            results = await database.fetch_all(query, params)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting free devices: {e}")
            return []
    
    @staticmethod
    async def assign_device_to_patient(
        device_id: str, 
        patient_id: str,
        assigned_by: str,
        assignment_reason: str = "patient_admission"
    ) -> Optional[DeviceAssignmentResponse]:
        """Assign a device to a patient"""
        try:
            # Check if device is available
            device_check_query = """
                SELECT "deviceId", name, "assignmentStatus", status
                FROM devices 
                WHERE "deviceId" = :device_id AND "isActive" = true
            """
            device = await database.fetch_one(device_check_query, {"device_id": device_id})
            
            if not device:
                raise ValueError("Device not found or inactive")
                
            if device["assignmentStatus"] != "free":
                raise ValueError(f"Device is not available (status: {device['assignmentStatus']})")
                
            if device["status"] == "offline":
                raise ValueError("Cannot assign offline device")
            
            # Start transaction
            async with database.transaction():
                # Update device assignment status
                update_device_query = """
                    UPDATE devices 
                    SET "assignmentStatus" = 'assigned', "assignedTo" = :patient_id, 
                        "assignedAt" = NOW(), "updatedAt" = NOW()
                    WHERE "deviceId" = :device_id
                """
                await database.execute(update_device_query, {
                    "device_id": device_id,
                    "patient_id": patient_id
                })
                
                # Create assignment record
                assignment_query = """
                    INSERT INTO device_assignments 
                    ("deviceId", "patientId", "assignedBy", "assignmentReason", "assignedAt", status)
                    VALUES (:device_id, :patient_id, :assigned_by, :assignment_reason, NOW(), 'active')
                    RETURNING id, "deviceId", "patientId", "assignedBy", "assignmentReason", 
                             "assignedAt", "unassignedAt", status, "createdAt"
                """
                
                result = await database.fetch_one(assignment_query, {
                    "device_id": device_id,
                    "patient_id": patient_id,
                    "assigned_by": assigned_by,
                    "assignment_reason": assignment_reason
                })
                
                if result:
                    logger.info(f"Assigned device {device_id} to patient {patient_id}")
                    
                    # Start vitals simulation for this patient-device pair
                    try:
                        from app.services.vitals_simulator import vitals_simulator
                        await vitals_simulator.start_simulation_for_patient(patient_id, device_id)
                        logger.info(f"Started vitals simulation for patient {patient_id} on device {device_id}")
                    except Exception as e:
                        logger.error(f"Failed to start vitals simulation: {e}")
                        # Don't fail the assignment if simulation fails to start
                    
                    return DeviceAssignmentResponse(**dict(result))
                    
                return None
                
        except ValueError as e:
            logger.warning(f"Assignment validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error assigning device: {e}")
            raise
    
    @staticmethod
    async def unassign_device(
        device_id: str,
        unassigned_by: str,
        unassignment_reason: str = "patient_discharge",
        new_device_id: str = None
    ) -> bool:
        """Unassign device from patient and return to free pool"""
        try:
            # Get current assignment
            current_assignment_query = """
                SELECT id, "deviceId", "patientId", status
                FROM device_assignments
                WHERE "deviceId" = :device_id AND status = 'active'
                ORDER BY "assignedAt" DESC
                LIMIT 1
            """
            
            assignment = await database.fetch_one(current_assignment_query, {"device_id": device_id})
            
            if not assignment:
                raise ValueError("No active assignment found for this device")
            
            async with database.transaction():
                # Update assignment record
                update_assignment_query = """
                    UPDATE device_assignments 
                    SET status = 'completed', "unassignedAt" = NOW(), 
                        "unassignedBy" = :unassigned_by, "unassignmentReason" = :unassignment_reason,
                        "newDeviceId" = :new_device_id
                    WHERE id = :assignment_id
                """
                
                await database.execute(update_assignment_query, {
                    "assignment_id": assignment["id"],
                    "unassigned_by": unassigned_by,
                    "unassignment_reason": unassignment_reason,
                    "new_device_id": new_device_id
                })
                
                # Return device to free pool
                update_device_query = """
                    UPDATE devices 
                    SET "assignmentStatus" = 'free', "assignedTo" = NULL, 
                        "assignedAt" = NULL, "updatedAt" = NOW()
                    WHERE "deviceId" = :device_id
                """
                await database.execute(update_device_query, {"device_id": device_id})
                
                # Stop vitals simulation for this patient
                try:
                    from app.services.vitals_simulator import vitals_simulator
                    await vitals_simulator.stop_simulation_for_patient(assignment["patientId"])
                    logger.info(f"Stopped vitals simulation for patient {assignment['patientId']}")
                except Exception as e:
                    logger.error(f"Failed to stop vitals simulation: {e}")
                    # Don't fail the unassignment if simulation fails to stop
                
                logger.info(f"Unassigned device {device_id} - reason: {unassignment_reason}")
                return True
                
        except ValueError as e:
            logger.warning(f"Unassignment validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error unassigning device: {e}")
            raise
    
    @staticmethod
    async def reassign_device(
        old_device_id: str,
        new_device_id: str,
        reassigned_by: str,
        reassignment_reason: str = "device_malfunction"
    ) -> Optional[DeviceAssignmentResponse]:
        """Reassign patient from one device to another"""
        try:
            # Get current assignment
            current_assignment_query = """
                SELECT id, "deviceId", "patientId", status
                FROM device_assignments
                WHERE "deviceId" = :device_id AND status = 'active'
                ORDER BY "assignedAt" DESC
                LIMIT 1
            """
            
            assignment = await database.fetch_one(current_assignment_query, {"device_id": old_device_id})
            
            if not assignment:
                raise ValueError("No active assignment found for old device")
            
            patient_id = assignment["patientId"]
            
            # Unassign old device
            await DeviceAssignmentService.unassign_device(
                old_device_id, reassigned_by, reassignment_reason, new_device_id
            )
            
            # Assign new device
            new_assignment = await DeviceAssignmentService.assign_device_to_patient(
                new_device_id, patient_id, reassigned_by, "device_reassignment"
            )
            
            logger.info(f"Reassigned patient {patient_id} from device {old_device_id} to {new_device_id}")
            return new_assignment
            
        except Exception as e:
            logger.error(f"Error reassigning device: {e}")
            raise
    
    @staticmethod
    async def get_patient_device(patient_id: str) -> Optional[Dict[str, Any]]:
        """Get currently assigned device for a patient"""
        try:
            query = """
                SELECT d."deviceId", d.name, d."deviceType", d.status, d."batteryLevel",
                       da."assignedAt", da."assignedBy", da."assignmentReason"
                FROM devices d
                JOIN device_assignments da ON d."deviceId" = da."deviceId"
                WHERE da."patientId" = :patient_id AND da.status = 'active' AND d."isActive" = true
                ORDER BY da."assignedAt" DESC
                LIMIT 1
            """
            
            result = await database.fetch_one(query, {"patient_id": patient_id})
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Error getting patient device: {e}")
            return None
    
    @staticmethod
    async def get_assignment_history(
        patient_id: str = None,
        device_id: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get assignment history for patient or device"""
        try:
            where_conditions = []
            params = {"limit": limit}
            
            if patient_id:
                where_conditions.append('da."patientId" = :patient_id')
                params["patient_id"] = patient_id
                
            if device_id:
                where_conditions.append('da."deviceId" = :device_id')
                params["device_id"] = device_id
                
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            query = f"""
                SELECT da.id, da."deviceId", da."patientId", da."assignedBy", da."assignmentReason",
                       da."assignedAt", da."unassignedAt", da."unassignedBy", da."unassignmentReason",
                       da."newDeviceId", da.status, d.name as "deviceName", d."deviceType"
                FROM device_assignments da
                JOIN devices d ON da."deviceId" = d."deviceId"
                WHERE {where_clause}
                ORDER BY da."assignedAt" DESC
                LIMIT :limit
            """
            
            results = await database.fetch_all(query, params)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Error getting assignment history: {e}")
            return []
    
    @staticmethod
    async def get_device_pool_status() -> Dict[str, Any]:
        """Get overview of device pool status"""
        try:
            stats_query = """
                SELECT 
                    "deviceType",
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE "assignmentStatus" = 'free') as available,
                    COUNT(*) FILTER (WHERE "assignmentStatus" = 'assigned') as assigned,
                    COUNT(*) FILTER (WHERE status = 'offline') as offline,
                    COUNT(*) FILTER (WHERE "batteryLevel" IS NOT NULL AND "batteryLevel" < 20) as "lowBattery"
                FROM devices
                WHERE "isActive" = true
                GROUP BY "deviceType"
                ORDER BY "deviceType"
            """
            
            results = await database.fetch_all(stats_query)
            
            pool_status = {
                "by_type": {},
                "summary": {
                    "total_devices": 0,
                    "available_devices": 0,
                    "assigned_devices": 0,
                    "offline_devices": 0,
                    "low_battery_devices": 0
                }
            }
            
            for row in results:
                pool_status["by_type"][row["deviceType"]] = {
                    "total": row["total"],
                    "available": row["available"],
                    "assigned": row["assigned"],
                    "offline": row["offline"],
                    "low_battery": row["lowBattery"]
                }
                
                # Update summary
                pool_status["summary"]["total_devices"] += row["total"]
                pool_status["summary"]["available_devices"] += row["available"]
                pool_status["summary"]["assigned_devices"] += row["assigned"]
                pool_status["summary"]["offline_devices"] += row["offline"]
                pool_status["summary"]["low_battery_devices"] += row["lowBattery"]
            
            return pool_status
            
        except Exception as e:
            logger.error(f"Error getting device pool status: {e}")
            return {"error": "Failed to get device pool status"}