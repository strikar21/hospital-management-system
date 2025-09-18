"""
ESP32 Device API endpoints for hospital watches
"""

from fastapi import APIRouter, HTTPException, Body, Header
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from ...core.database import get_db_connection, get_timescale_connection
from ...services.websocket_manager import connection_manager
from ...services.audit import log_audit_event

router = APIRouter()
logger = logging.getLogger(__name__)

# Device ID counter for auto-assignment
device_counter = 1

@router.post("/provision")
async def provision_esp32_device(provision_data: Dict[str, Any]):
    """
    Provision new ESP32 device with automatic serial assignment
    Validates provisioner credentials and assigns device ID/serial
    """
    try:
        mac_address = provision_data.get('macAddress')
        device_type = provision_data.get('deviceType', 'esp32_watch')
        provisioner_id = provision_data.get('provisioner_id')
        provisioner_password = provision_data.get('provisioner_password')
        firmware_version = provision_data.get('firmwareVersion', '3.0.0')
        
        if not mac_address or not provisioner_id or not provisioner_password:
            raise HTTPException(status_code=400, detail="MAC address and provisioner credentials required")
        
        async with get_db_connection() as conn:
            # Validate provisioner credentials
            provisioner = await conn.fetchrow(
                "SELECT id, name, role, password FROM staff WHERE id = $1 AND role = 'Provisioner'",
                provisioner_id
            )
            
            if not provisioner:
                logger.warning(f"❌ Invalid provisioner ID: {provisioner_id}")
                raise HTTPException(status_code=403, detail="Invalid provisioner credentials")
            
            # Validate provisioner password
            if provisioner['password'] != provisioner_password:
                logger.warning(f"❌ Invalid provisioner password for ID: {provisioner_id}")
                raise HTTPException(status_code=403, detail="Invalid provisioner credentials")
            
            # Check if device already exists by MAC address
            existing_device = await conn.fetchrow(
                "SELECT id, serialNumber FROM devices WHERE macAddress = $1",
                mac_address
            )
            
            if existing_device:
                logger.info(f"📱 Device with MAC {mac_address} already provisioned as {existing_device['id']}")
                return JSONResponse({
                    "success": True,
                    "message": "Device already provisioned",
                    "deviceId": existing_device['id'],
                    "serialNumber": existing_device['serialnumber'],
                    "status": "existing"
                })
            
            # Generate new device ID and serial number
            device_count = await conn.fetchval("SELECT COUNT(*) FROM devices WHERE devicetype = $1", device_type)
            new_device_number = device_count + 1
            
            device_id = f"ESP32_WATCH_{new_device_number:03d}"  # ESP32_WATCH_001, ESP32_WATCH_002, etc.
            serial_number = f"SN_W{new_device_number:03d}"     # SN_W001, SN_W002, etc.
            
            # Create new device record
            await conn.execute("""
                INSERT INTO devices (id, devicetype, serialnumber, macaddress, 
                                   firmwareversion, batterylevel, status, location, 
                                   lastseen, createdat, updatedat)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW(), NOW())
            """, device_id, device_type, serial_number, mac_address,
                 firmware_version, 100, 'available', 'Device Pool')
            
            # Log provisioning action
            await log_audit_event(
                conn, provisioner_id, 'provision_device', 'device', device_id,
                f"Provisioned new {device_type} with serial {serial_number}"
            )
            
            logger.info(f"✅ New ESP32 device provisioned: {device_id} (Serial: {serial_number}) by {provisioner['name']}")
        
        return JSONResponse({
            "success": True,
            "message": "Device provisioned successfully",
            "deviceId": device_id,
            "serialNumber": serial_number,
            "provisionedBy": provisioner['name'],
            "status": "new"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ESP32 provisioning error: {e}")
        raise HTTPException(status_code=500, detail="Device provisioning failed")

@router.post("/online")
async def device_online(status_data: Dict[str, Any]):
    """
    Mark device as online after successful provisioning
    """
    try:
        device_id = status_data.get('deviceId')
        serial_number = status_data.get('serialNumber')
        battery_level = status_data.get('batteryLevel', 100)
        
        if not device_id:
            raise HTTPException(status_code=400, detail="Device ID required")
        
        async with get_db_connection() as conn:
            # Update device status
            await conn.execute("""
                UPDATE devices 
                SET status = 'available', batterylevel = $2, lastseen = NOW(), updatedat = NOW()
                WHERE id = $1
            """, device_id, battery_level)
            
            logger.info(f"📱 Device {device_id} marked as online")
        
        return JSONResponse({
            "success": True,
            "message": "Device marked as online",
            "deviceId": device_id
        })
        
    except Exception as e:
        logger.error(f"❌ Device online update error: {e}")
        raise HTTPException(status_code=500, detail="Device status update failed")

@router.post("/register")
async def register_esp32_device(device_data: Dict[str, Any]):
    """
    Register ESP32 device in the system
    Called by ESP32 on startup
    """
    try:
        device_id = device_data.get('deviceId')
        device_type = device_data.get('deviceType', 'esp32_watch')
        mac_address = device_data.get('macAddress')
        firmware_version = device_data.get('firmwareVersion', '1.0.0')
        battery_level = device_data.get('batteryLevel', 100)
        location = device_data.get('location', 'Mobile')
        
        if not device_id or not mac_address:
            raise HTTPException(status_code=400, detail="Device ID and MAC address required")
        
        async with get_db_connection() as conn:
            # Check if device already exists
            existing_device = await conn.fetchrow(
                "SELECT id FROM devices WHERE id = $1 OR macAddress = $2",
                device_id, mac_address
            )
            
            if existing_device:
                # Update existing device
                await conn.execute("""
                    UPDATE devices 
                    SET devicetype = $2, batterylevel = $3, firmwareversion = $4,
                        lastseen = NOW(), updatedat = NOW(), status = 'available'
                    WHERE id = $1
                """, device_id, device_type, battery_level, firmware_version)
                
                logger.info(f"📱 ESP32 device updated: {device_id}")
            else:
                # Create new device
                await conn.execute("""
                    INSERT INTO devices (id, devicetype, serialnumber, macaddress, 
                                       batterylevel, firmwareversion, location, status, 
                                       lastseen, createdat, updatedat)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW(), NOW())
                """, device_id, device_type, f"ESP32_{device_id[-4:]}", mac_address,
                     battery_level, firmware_version, location, 'available')
                
                logger.info(f"✅ New ESP32 device registered: {device_id}")
        
        return JSONResponse({
            "success": True,
            "deviceId": device_id,
            "message": "Device registered successfully",
            "serverTime": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ ESP32 registration error: {e}")
        raise HTTPException(status_code=500, detail="Device registration failed")

@router.post("/{device_id}/heartbeat")
async def device_heartbeat(
    device_id: str,
    heartbeat_data: Dict[str, Any]
):
    """
    Receive heartbeat from ESP32 device
    Updates device status and battery level
    """
    try:
        battery_level = heartbeat_data.get('batteryLevel', 100)
        signal_strength = heartbeat_data.get('signalStrength', -50)
        device_status = heartbeat_data.get('status', 'active')
        
        async with get_db_connection() as conn:
            # Update device status
            await conn.execute("""
                UPDATE devices 
                SET batterylevel = $2, status = $3, lastseen = NOW(), updatedat = NOW()
                WHERE id = $1
            """, device_id, battery_level, device_status)
            
            # Check if device exists
            device = await conn.fetchrow("SELECT id, assignedpatientid FROM devices WHERE id = $1", device_id)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")
        
        logger.info(f"💓 Heartbeat from {device_id}: Battery {battery_level}%, Signal {signal_strength}dBm")
        
        return JSONResponse({
            "success": True,
            "message": "Heartbeat received",
            "serverTime": datetime.now().isoformat(),
            "batteryLevel": battery_level
        })
        
    except Exception as e:
        logger.error(f"❌ ESP32 heartbeat error: {e}")
        raise HTTPException(status_code=500, detail="Heartbeat processing failed")

@router.post("/{device_id}/vitals/{patient_id}")
async def receive_vitals_data(
    device_id: str,
    patient_id: str,
    vitals_data: Dict[str, Any]
):
    """
    Receive vitals data from ESP32 device
    Stores in TimescaleDB and broadcasts to WebSocket subscribers
    """
    try:
        # Validate that device is assigned to this patient
        async with get_db_connection() as conn:
            patient = await conn.fetchrow(
                "SELECT id, assigneddeviceid FROM patients WHERE id = $1",
                patient_id
            )
            
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")
            
            if patient['assigneddeviceid'] != device_id:
                logger.warning(f"⚠️ Device {device_id} sent vitals for patient {patient_id} but not assigned")
                raise HTTPException(status_code=403, detail="Device not assigned to this patient")
        
        # Store vitals in TimescaleDB
        try:
            async with get_timescale_connection() as ts_conn:
                timestamp = datetime.now()
                
                # Store each vital type (optimized for frontend format)
                vital_types = {
                    'heartRate': vitals_data.get('heartRate'),
                    'temperature': vitals_data.get('temperature'),
                    'oxygenSaturation': vitals_data.get('oxygenSat'),  # ESP32 sends 'oxygenSat'
                    'respiratoryRate': vitals_data.get('respiratoryRate'),
                    'bloodPressureSystolic': vitals_data.get('bloodPressureValue'),
                    'ecg': vitals_data.get('ecg'),
                    'eeg': vitals_data.get('eeg'),
                    'bioimpedance': vitals_data.get('bioimpedance'),
                    'tremor': vitals_data.get('tremor')
                }
                
                for vital_type, value in vital_types.items():
                    if value is not None:
                        await ts_conn.execute("""
                            INSERT INTO vitals_timeseries (patientid, deviceid, vitaltype, value, unit, time, quality)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """, patient_id, device_id, vital_type, float(value), 
                             get_unit_for_vital_fix(vital_type), timestamp, 
                             vitals_data.get('quality', 95))
                
                logger.info(f"📊 Vitals stored for patient {patient_id} from device {device_id}")
        
        except Exception as e:
            logger.warning(f"⚠️ TimescaleDB storage failed: {e}, continuing with broadcast")
        
        # Update device last seen
        async with get_db_connection() as conn:
            await conn.execute(
                "UPDATE devices SET lastseen = NOW(), batterylevel = $2 WHERE id = $1",
                device_id, vitals_data.get('deviceBattery', 100)
            )
        
        # Broadcast to WebSocket subscribers with frontend-compatible format
        frontend_vitals = {
            'heartRate': vitals_data.get('heartRate'),
            'bloodPressure': vitals_data.get('bloodPressure'),
            'bloodPressureValue': vitals_data.get('bloodPressureValue'),
            'respiratoryRate': vitals_data.get('respiratoryRate'),
            'oxygenSat': vitals_data.get('oxygenSat'),
            'temperature': vitals_data.get('temperature'),
            'ecg': vitals_data.get('ecg'),
            'eeg': vitals_data.get('eeg'),
            'bioimpedance': vitals_data.get('bioimpedance'),
            'tremor': vitals_data.get('tremor'),
            'lastUpdated': datetime.now().isoformat(),
            'lastSync': datetime.now().isoformat()
        }
        await connection_manager.send_vitals_update(patient_id, device_id, frontend_vitals)
        
        return JSONResponse({
            "success": True,
            "message": "Vitals received and broadcasted",
            "patientId": patient_id,
            "deviceId": device_id,
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ESP32 vitals error: {e}")
        raise HTTPException(status_code=500, detail="Vitals processing failed")

@router.post("/{device_id}/alert")
async def receive_emergency_alert(
    device_id: str,
    alert_data: Dict[str, Any]
):
    """
    Receive emergency alert from ESP32 device
    """
    try:
        patient_id = alert_data.get('patientId')
        alert_type = alert_data.get('alertType', 'warning')
        message = alert_data.get('message', 'Device alert')
        vitals = alert_data.get('vitals', {})
        
        # Broadcast emergency alert
        alert_payload = {
            'severity': alert_type,
            'message': message,
            'source': f'Device {device_id}',
            'vitals': vitals,
            'deviceId': device_id
        }
        
        await connection_manager.send_alert(patient_id, alert_payload)
        
        logger.warning(f"🚨 Emergency alert from {device_id} for patient {patient_id}: {message}")
        
        return JSONResponse({
            "success": True,
            "message": "Emergency alert broadcasted",
            "alertId": str(uuid.uuid4())
        })
        
    except Exception as e:
        logger.error(f"❌ ESP32 alert error: {e}")
        raise HTTPException(status_code=500, detail="Alert processing failed")

@staticmethod
def get_unit_for_vital(vital_type: str) -> str:
    """Get the unit for a given vital type"""
    units = {
        'heartRate': 'bpm',
        'temperature': 'F',
        'oxygenSaturation': '%',
        'respiratoryRate': '/min',
        'bloodPressureSystolic': 'mmHg',
        'bloodPressureDiastolic': 'mmHg'
    }
    return units.get(vital_type, '')

# Fix the self reference in the static method
def get_unit_for_vital_fix(vital_type: str) -> str:
    """Get the unit for a given vital type"""
    units = {
        'heartRate': 'bpm',
        'temperature': 'F', 
        'oxygenSaturation': '%',
        'respiratoryRate': '/min',
        'bloodPressureSystolic': 'mmHg',
        'bloodPressureDiastolic': 'mmHg'
    }
    return units.get(vital_type, '')

# Door Scanner ESP32 endpoints
@router.post("/door-scanner/{scanner_id}/scan")
async def door_scanner_detection(
    scanner_id: str,
    scan_data: Dict[str, Any]
):
    """
    Receive BLE device detection from door scanner ESP32
    Tracks which devices (watches/tablets) are in which rooms
    """
    try:
        detected_devices = scan_data.get('detectedDevices', [])
        room_id = scan_data.get('roomId')
        scanner_location = scan_data.get('location')
        
        if not room_id:
            raise HTTPException(status_code=400, detail="Room ID required")
        
        async with get_db_connection() as conn:
            # Update scanner heartbeat
            await conn.execute("""
                UPDATE devices 
                SET lastseen = NOW(), status = 'active'
                WHERE id = $1 AND devicetype = 'door_scanner'
            """, scanner_id)
            
            # Process detected devices
            for device_info in detected_devices:
                device_id = device_info.get('deviceId')
                rssi = device_info.get('rssi', -50)
                
                if device_id:
                    # Update device location based on door scanner detection
                    await conn.execute("""
                        UPDATE devices 
                        SET location = $2, lastseen = NOW()
                        WHERE id = $1
                    """, device_id, room_id)
                    
                    # Find patient assigned to this device
                    patient = await conn.fetchrow("""
                        SELECT id, firstname, lastname 
                        FROM patients 
                        WHERE assigneddeviceid = $1 AND status = 'active'
                    """, device_id)
                    
                    if patient:
                        logger.info(f"🚪 Door scanner {scanner_id}: Patient {patient['firstname']} {patient['lastname']} detected in {room_id}")
        
        return JSONResponse({
            "success": True,
            "scannerId": scanner_id,
            "roomId": room_id,
            "devicesDetected": len(detected_devices),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Door scanner error: {e}")
        raise HTTPException(status_code=500, detail="Door scanner processing failed")