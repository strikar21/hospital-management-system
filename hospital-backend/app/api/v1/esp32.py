"""
ESP32 Device API endpoints for hospital watches
"""

from fastapi import APIRouter, HTTPException, Body, Header, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from ...core.database import getDbConnection, getTimescaleConnection
from ...core.auth_dependencies import verify_device_key
from ...services.websocket_manager import connectionManager
from ...services.audit import logAuditEvent
from ...services.vital_alert_service import vital_alert_service
from ...services.arrhythmia_detection_service import arrhythmia_detection_service

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()
logger = logging.getLogger(__name__)

# Device ID counter for auto-assignment
deviceCounter = 1

@router.post("/provision")
async def provisionEsp32Device(provisionData: Dict[str, Any]):
    """
    Provision new ESP32 device with automatic serial assignment
    Validates provisioner credentials and assigns device ID/serial
    """
    try:
        macAddress = provisionData.get('macAddress')
        deviceType = provisionData.get('deviceType', 'esp32Watch')
        provisionerId = provisionData.get('provisionerId')
        provisionerPassword = provisionData.get('provisionerPassword')
        firmwareVersion = provisionData.get('firmwareVersion', '3.0.0')
        
        if not macAddress or not provisionerId or not provisionerPassword:
            raise HTTPException(status_code=400, detail="MAC address and provisioner credentials required")
        
        async with getDbConnection() as conn:
            # Validate provisioner credentials
            provisioner = await conn.fetchrow(
                "SELECT id, name, role, password FROM staff WHERE id = $1 AND role = 'Provisioner'",
                provisionerId
            )
            
            if not provisioner:
                logger.warning(f"❌ Invalid provisioner ID: {provisionerId}")
                raise HTTPException(status_code=403, detail="Invalid provisioner credentials")
            
            # Validate provisioner password
            if provisioner['password'] != provisionerPassword:
                logger.warning(f"❌ Invalid provisioner password for ID: {provisionerId}")
                raise HTTPException(status_code=403, detail="Invalid provisioner credentials")
            
            # Check if device already exists by MAC address
            existingDevice = await conn.fetchrow(
                'SELECT id, serialNumber FROM devices WHERE macAddress = $1',
                macAddress
            )

            if existingDevice:
                logger.info(f"📱 Device with MAC {macAddress} already provisioned as {existingDevice['id']}")
                return JSONResponse({
                    "success": True,
                    "message": "Device already provisioned",
                    "deviceId": existingDevice['id'],
                    "serialNumber": existingDevice['serialNumber'],
                    "status": "existing"
                })
            
            # Generate new device ID and serial number
            deviceCount = await conn.fetchval('SELECT COUNT(*) FROM devices WHERE deviceType = $1', deviceType)
            newDeviceNumber = deviceCount + 1
            
            deviceId = f"ESP32_WATCH_{newDeviceNumber:03d}"  # ESP32_WATCH_001, ESP32_WATCH_002, etc.
            serialNumber = f"SN_W{newDeviceNumber:03d}"     # SN_W001, SN_W002, etc.
            
            # Create new device record
            await conn.execute("""
                INSERT INTO devices (id, deviceType, serialNumber, macAddress,
                                   firmwareVersion, batteryLevel, status, location,
                                   lastSeen, createdAt, updatedAt)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW(), NOW())
            """, deviceId, deviceType, serialNumber, macAddress,
                 firmwareVersion, 100, 'available', 'Device Pool')
            
            # Log provisioning action
            await logAuditEvent(
                conn, provisionerId, 'provisionDevice', 'device', deviceId,
                f"Provisioned new {deviceType} with serial {serialNumber}"
            )
            
            logger.info(f"✅ New ESP32 device provisioned: {deviceId} (Serial: {serialNumber}) by {provisioner['name']}")
        
        return JSONResponse({
            "success": True,
            "message": "Device provisioned successfully",
            "deviceId": deviceId,
            "serialNumber": serialNumber,
            "provisionedby": provisioner['name'],
            "status": "new"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ESP32 provisioning error: {e}")
        raise HTTPException(status_code=500, detail="Device provisioning failed")

@router.post("/online")
async def deviceOnline(statusData: Dict[str, Any]):
    """
    Mark device as online after successful provisioning
    """
    try:
        deviceId = statusData.get('deviceId')
        serialNumber = statusData.get('serialNumber')
        batteryLevel = statusData.get('batteryLevel', 100)
        
        if not deviceId:
            raise HTTPException(status_code=400, detail="Device ID required")
        
        async with getDbConnection() as conn:
            # Update device status
            await conn.execute("""
                UPDATE devices
                SET status = 'available', batteryLevel = $2, lastSeen = NOW(), updatedAt = NOW()
                WHERE id = $1
            """, deviceId, batteryLevel)
            
            logger.info(f"📱 Device {deviceId} marked as online")
        
        return JSONResponse({
            "success": True,
            "message": "Device marked as online",
            "deviceId": deviceId
        })
        
    except Exception as e:
        logger.error(f"❌ Device online update error: {e}")
        raise HTTPException(status_code=500, detail="Device status update failed")

@router.post("/register")
async def registerEsp32Device(deviceData: Dict[str, Any]):
    """
    Register ESP32 device in the system
    Called by ESP32 on startup
    """
    try:
        deviceId = deviceData.get('deviceId')
        deviceType = deviceData.get('deviceType', 'esp32Watch')
        macAddress = deviceData.get('macAddress')
        firmwareVersion = deviceData.get('firmwareVersion', '1.0.0')
        batteryLevel = deviceData.get('batteryLevel', 100)
        location = deviceData.get('location', 'Mobile')
        
        if not deviceId or not macAddress:
            raise HTTPException(status_code=400, detail="Device ID and MAC address required")
        
        async with getDbConnection() as conn:
            # Check if device already exists
            existingDevice = await conn.fetchrow(
                'SELECT id FROM devices WHERE id = $1 OR macAddress = $2',
                deviceId, macAddress
            )

            if existingDevice:
                # Update existing device
                await conn.execute("""
                    UPDATE devices
                    SET deviceType = $2, batteryLevel = $3, firmwareVersion = $4,
                        lastSeen = NOW(), updatedAt = NOW(), status = 'available'
                    WHERE id = $1
                """, deviceId, deviceType, batteryLevel, firmwareVersion)
                
                logger.info(f"📱 ESP32 device updated: {deviceId}")
            else:
                # Create new device
                await conn.execute("""
                    INSERT INTO devices (id, deviceType, serialNumber, macAddress,
                                       batteryLevel, firmwareVersion, location, status,
                                       lastSeen, createdAt, updatedAt)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW(), NOW())
                """, deviceId, deviceType, f"ESP32_{deviceId[-4:]}", macAddress,
                     batteryLevel, firmwareVersion, location, 'available')
                
                logger.info(f"✅ New ESP32 device registered: {deviceId}")
        
        return JSONResponse({
            "success": True,
            "deviceId": deviceId,
            "message": "Device registered successfully",
            "servertime": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ ESP32 registration error: {e}")
        raise HTTPException(status_code=500, detail="Device registration failed")

@router.post("/{deviceId}/heartbeat")
async def deviceHeartbeat(
    deviceId: str,
    heartbeatData: Dict[str, Any]
):
    """
    Receive heartbeat from ESP32 device
    Updates device status and battery level
    """
    try:
        batteryLevel = heartbeatData.get('batteryLevel', 100)
        signalStrength = heartbeatData.get('signalstrength', -50)
        deviceStatus = heartbeatData.get('status', 'active')
        
        async with getDbConnection() as conn:
            # Update device status
            await conn.execute("""
                UPDATE devices
                SET batteryLevel = $2, status = $3, lastSeen = NOW(), updatedAt = NOW()
                WHERE id = $1
            """, deviceId, batteryLevel, deviceStatus)
            
            # Check if device exists
            device = await conn.fetchrow('SELECT id, "assignedPatientId" FROM devices WHERE id = $1', deviceId)
            if not device:
                raise HTTPException(status_code=404, detail="Device not found")
        
        logger.info(f"💓 Heartbeat from {deviceId}: Battery {batteryLevel}%, Signal {signalStrength}dBm")
        
        return JSONResponse({
            "success": True,
            "message": "Heartbeat received",
            "servertime": datetime.now().isoformat(),
            "batteryLevel": batteryLevel
        })
        
    except Exception as e:
        logger.error(f"❌ ESP32 heartbeat error: {e}")
        raise HTTPException(status_code=500, detail="Heartbeat processing failed")

@router.post("/{deviceId}/vitals/{patientId}")
@limiter.limit("100/minute")  # Allow 100 vitals updates per minute per device
async def receiveVitalsData(
    request: Request,
    deviceId: str,
    patientId: str,
    vitalsData: Dict[str, Any],
    device_key: str = Header(None, alias="X-Device-Key")
):
    """
    Receive vitals data from ESP32 device
    Stores in TimescaleDB and broadcasts to WebSocket subscribers

    Security:
    - Requires X-Device-Key header for device authentication
    - Rate limited to 100 requests per minute per device
    - Validates device is assigned to patient
    """
    try:
        # Verify device authentication
        device = await verify_device_key(device_key)

        # Verify device ID matches authenticated device
        if device["id"] != deviceId:
            logger.warning(f"⚠️ Device {device['id']} attempted to send vitals as {deviceId}")
            raise HTTPException(status_code=403, detail="Device ID mismatch")
        # Validate that device is assigned to this patient
        async with getDbConnection() as conn:
            patient = await conn.fetchrow(
                'SELECT id, "assignedDeviceId" FROM patients WHERE id = $1',
                patientId
            )

            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")

            if patient['assignedDeviceId'] != deviceId:
                logger.warning(f"⚠️ Device {deviceId} sent vitals for patient {patientId} but not assigned")
                raise HTTPException(status_code=403, detail="Device not assigned to this patient")
        
        # Store vitals in TimescaleDB
        try:
            async with getTimescaleConnection() as tsConn:
                timestamp = datetime.now()
                
                # Store each vital type (optimized for frontend format)
                vitalTypes = {
                    'heartrate': vitalsData.get('heartrate'),
                    'temperature': vitalsData.get('temperature'),
                    'oxygensaturation': vitalsData.get('oxygensat'),  # ESP32 sends 'oxygenSat'
                    'respiratoryrate': vitalsData.get('respiratoryrate'),
                    'bloodpressuresystolic': vitalsData.get('bloodpressurevalue'),
                    'ecg': vitalsData.get('ecg'),
                    'eeg': vitalsData.get('eeg'),
                    'bioimpedance': vitalsData.get('bioimpedance'),
                    'tremor': vitalsData.get('tremor')
                }
                
                for vitalType, value in vitalTypes.items():
                    if value is not None:
                        await tsConn.execute("""
                            INSERT INTO vitals_timeseries ("patientId", "deviceId", vitaltype, value, unit, time, quality)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """, patientId, deviceId, vitalType, float(value),
                             getUnitForVitalFix(vitalType), timestamp,
                             vitalsData.get('quality', 95))
                
                logger.info(f"📊 Vitals stored for patient {patientId} from device {deviceId}")
        
        except Exception as e:
            logger.warning(f"⚠️ TimescaleDB storage failed: {e}, continuing with broadcast")
        
        # Update device last seen
        async with getDbConnection() as conn:
            await conn.execute(
                'UPDATE devices SET "lastSeen" = NOW(), "batteryLevel" = $2 WHERE id = $1',
                deviceId, vitalsData.get('devicebattery', 100)
            )

        # ============================================
        # PHASE 2: GENERATE ALERTS (BEST EFFORT)
        # ============================================
        alerts = []
        try:
            async with getDbConnection() as conn:
                # Vital threshold alerts (existing)
                alerts = await vital_alert_service.check_vitals_and_generate_alerts(
                    patientId, deviceId, vitalsData, conn
                )

                # NEW: Arrhythmia detection
                if vitalsData.get('heartrate'):
                    logger.info(f"🔬 CALLING ARRHYTHMIA DETECTION for patient {patientId}, HR: {vitalsData.get('heartrate')}")
                    arrhythmia_alert = await arrhythmia_detection_service.detect_arrhythmia(
                        patientId, deviceId, int(vitalsData['heartrate']), conn
                    )
                    logger.info(f"🔬 ARRHYTHMIA DETECTION RETURNED: {arrhythmia_alert}")
                    if arrhythmia_alert:
                        alerts.append(arrhythmia_alert)
                        logger.info(f"🔬 ARRHYTHMIA ALERT APPENDED TO LIST")
                else:
                    logger.warning(f"⚠️ NO HEARTRATE IN VITALS DATA - arrhythmia detection skipped")

            if alerts:
                logger.warning(f"🚨 Generated {len(alerts)} alert(s) for patient {patientId}")
                # Broadcast alerts via WebSocket
                for alert in alerts:
                    alert_type = 'arrhythmia_alert' if alert.get('alertType') else 'vital_threshold_alert'
                    await connectionManager.sendAlert(patientId, {
                        'type': alert_type,
                        'alert': alert
                    })

        except Exception as e:
            logger.error(f"⚠️ Alert generation failed (vitals already stored): {e}")
            # DON'T raise - vitals are already stored, alert failure is non-critical

        # ============================================
        # PHASE 3: BROADCAST VITALS (BEST EFFORT)
        # ============================================
        # Broadcast to WebSocket subscribers with frontend-compatible format
        frontendVitals = {
            'heartrate': vitalsData.get('heartrate'),
            'bloodpressure': vitalsData.get('bloodpressure'),
            'bloodpressurevalue': vitalsData.get('bloodpressurevalue'),
            'respiratoryrate': vitalsData.get('respiratoryrate'),
            'oxygensat': vitalsData.get('oxygensat'),
            'temperature': vitalsData.get('temperature'),
            'ecg': vitalsData.get('ecg'),
            'eeg': vitalsData.get('eeg'),
            'bioimpedance': vitalsData.get('bioimpedance'),
            'tremor': vitalsData.get('tremor'),
            'lastupdated': datetime.now().isoformat(),
            'lastsync': datetime.now().isoformat()
        }
        await connectionManager.sendVitalsUpdate(patientId, deviceId, frontendVitals)
        
        return JSONResponse({
            "success": True,
            "message": "Vitals received and processed",
            "patientId": patientId,
            "deviceId": deviceId,
            "timestamp": datetime.now().isoformat(),
            "alertsGenerated": len(alerts),
            "alerts": [{'severity': a['severity'], 'message': a['message']} for a in alerts]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ESP32 vitals error: {e}")
        raise HTTPException(status_code=500, detail="Vitals processing failed")

@router.post("/{deviceId}/alert")
async def receiveEmergencyAlert(
    deviceId: str,
    alertData: Dict[str, Any]
):
    """
    Receive emergency alert from ESP32 device
    """
    try:
        patientId = alertData.get('patientId')
        alertType = alertData.get('alerttype', 'warning')
        message = alertData.get('message', 'Device alert')
        vitals = alertData.get('vitals', {})
        
        # Broadcast emergency alert
        alertPayload = {
            'severity': alertType,
            'message': message,
            'source': f'Device {deviceId}',
            'vitals': vitals,
            'deviceId': deviceId
        }
        
        await connectionManager.sendAlert(patientId, alertPayload)
        
        logger.warning(f"🚨 Emergency alert from {deviceId} for patient {patientId}: {message}")
        
        return JSONResponse({
            "success": True,
            "message": "Emergency alert broadcasted",
            "alertid": str(uuid.uuid4())
        })
        
    except Exception as e:
        logger.error(f"❌ ESP32 alert error: {e}")
        raise HTTPException(status_code=500, detail="Alert processing failed")

@staticmethod
def getUnitForVital(vitalType: str) -> str:
    """Get the unit for a given vital type"""
    units = {
        'heartrate': 'bpm',
        'temperature': 'F',
        'oxygensaturation': '%',
        'respiratoryrate': '/min',
        'bloodpressuresystolic': 'mmHg',
        'bloodpressurediastolic': 'mmHg'
    }
    return units.get(vitalType, '')

# Fix the self reference in the static method
def getUnitForVitalFix(vitalType: str) -> str:
    """Get the unit for a given vital type"""
    units = {
        'heartrate': 'bpm',
        'temperature': 'F', 
        'oxygensaturation': '%',
        'respiratoryrate': '/min',
        'bloodpressuresystolic': 'mmHg',
        'bloodpressurediastolic': 'mmHg'
    }
    return units.get(vitalType, '')

# Door Scanner ESP32 endpoints
@router.post("/door-scanner/{scannerId}/scan")
async def doorScannerDetection(
    scannerId: str,
    scanData: Dict[str, Any]
):
    """
    Receive BLE device detection from door scanner ESP32
    Tracks which devices (watches/tablets) are in which rooms
    """
    try:
        detectedDevices = scanData.get('detecteddevices', [])
        roomId = scanData.get('roomid')
        scannerLocation = scanData.get('location')
        
        if not roomId:
            raise HTTPException(status_code=400, detail="Room ID required")
        
        async with getDbConnection() as conn:
            # Update scanner heartbeat
            await conn.execute("""
                UPDATE devices
                SET lastSeen = NOW(), status = 'active'
                WHERE id = $1 AND deviceType = 'doorScanner'
            """, scannerId)
            
            # Process detected devices
            for deviceInfo in detectedDevices:
                deviceId = deviceInfo.get('deviceId')
                rssi = deviceInfo.get('rssi', -50)
                
                if deviceId:
                    # Update device location based on door scanner detection
                    await conn.execute("""
                        UPDATE devices
                        SET location = $2, lastSeen = NOW()
                        WHERE id = $1
                    """, deviceId, roomId)
                    
                    # Find patient assigned to this device
                    patient = await conn.fetchrow("""
                        SELECT id, "firstName", "lastName"
                        FROM patients
                        WHERE "assignedDeviceId" = $1 AND status = 'active'
                    """, deviceId)
                    
                    if patient:
                        logger.info(f"🚪 Door scanner {scannerId}: Patient {patient['firstName']} {patient['lastName']} detected in {roomId}")
        
        return JSONResponse({
            "success": True,
            "scannerid": scannerId,
            "roomid": roomId,
            "devicesdetected": len(detectedDevices),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Door scanner error: {e}")
        raise HTTPException(status_code=500, detail="Door scanner processing failed") 
