"""
ESP32 Device API endpoints for hospital watches
"""

from fastapi import APIRouter, HTTPException, Body, Header, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import uuid
import bcrypt

from ...core.database import getDbConnection, getTimescaleConnection
from ...core.auth_dependencies import verify_device_key
from ...services.websocket_manager import connectionManager
from ...services.audit import logAuditEvent
from ...services.vital_alert_service import vital_alert_service
from ...services.arrhythmia_detection_service import arrhythmia_detection_service
from ...middleware.esp32_field_mapper import ESP32FieldMapper
from ...middleware.esp32_hmac_auth import ESP32HMACAuth
from ...core.config import settings

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

router = APIRouter()
logger = logging.getLogger(__name__)

# Device ID counter for auto-assignment
deviceCounter = 1

# Initialize HMAC authenticator for runtime device authentication
hmac_auth = ESP32HMACAuth(
    factory_secret=settings.esp32FactorySecret,
    timestamp_window=settings.esp32TimestampWindow
)
logger.info("✅ ESP32 HMAC authenticator initialized")

@router.post("/provision")
async def provisionEsp32Device(provisionData: Dict[str, Any]):
    """
    Provision new ESP32 device with automatic serial assignment
    Validates provisioner credentials and assigns device ID/serial
    """
    try:
        # Transform ESP32 lowercase fields to backend camelCase
        provisionData = ESP32FieldMapper.transform_request(provisionData)

        macAddress = provisionData.get('macAddress')
        deviceType = provisionData.get('deviceType', 'watch')  # Default to 'watch' (valid enum value)
        provisionerId = provisionData.get('provisionerId')
        provisionerPassword = provisionData.get('provisionerPassword')
        firmwareVersion = provisionData.get('firmwareVersion', '3.0.0')
        
        if not macAddress or not provisionerId or not provisionerPassword:
            raise HTTPException(status_code=400, detail="MAC address and provisioner credentials required")
        
        async with getDbConnection() as conn:
            # Validate provisioner credentials (allow Technician or Provisioner roles)
            provisioner = await conn.fetchrow(
                "SELECT id, \"firstName\", \"lastName\", role, password FROM staff WHERE id = $1 AND role IN ('Provisioner', 'Technician')",
                provisionerId
            )

            if not provisioner:
                logger.warning(f"❌ Invalid provisioner ID or role: {provisionerId}")
                raise HTTPException(status_code=403, detail="Invalid provisioner credentials or insufficient role")

            # Validate provisioner password using bcrypt
            passwordValid = bcrypt.checkpw(
                provisionerPassword.encode('utf-8'),
                provisioner['password'].encode('utf-8')
            )
            if not passwordValid:
                logger.warning(f"❌ Invalid provisioner password for ID: {provisionerId}")
                raise HTTPException(status_code=403, detail="Invalid provisioner credentials")
            
            # Check if device already exists by MAC address
            existingDevice = await conn.fetchrow(
                'SELECT id, "serialNumber" FROM devices WHERE "macAddress" = $1',
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
            deviceCount = await conn.fetchval('SELECT COUNT(*) FROM devices WHERE "deviceType" = $1', deviceType)
            newDeviceNumber = deviceCount + 1

            deviceId = f"ESP32_WATCH_{newDeviceNumber:03d}"  # ESP32_WATCH_001, ESP32_WATCH_002, etc.
            serialNumber = f"SN_W{newDeviceNumber:03d}"     # SN_W001, SN_W002, etc.
            deviceName = f"ESP32 Watch #{newDeviceNumber:03d}"  # ESP32 Watch #001, #002, etc.

            # Create new device record (HMAC authentication - no deviceKey needed)
            await conn.execute("""
                INSERT INTO devices (id, "deviceType", name, "serialNumber", "macAddress",
                                   "firmwareVersion", "batteryLevel", status, location,
                                   "lastSeen", "createdAt", "updatedAt")
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW(), NOW())
            """, deviceId, deviceType, deviceName, serialNumber, macAddress,
                 firmwareVersion, 100, 'available', 'Device Pool')
            
            # Log provisioning action
            await logAuditEvent(
                conn, provisionerId, 'provisionDevice', 'device', deviceId,
                f"Provisioned new {deviceType} with serial {serialNumber}"
            )
            
            provisionerName = f"{provisioner['firstName']} {provisioner['lastName']}"
            logger.info(f"✅ New ESP32 device provisioned: {deviceId} (Serial: {serialNumber}) by {provisionerName}")

        return JSONResponse({
            "success": True,
            "message": "Device provisioned successfully (HMAC authentication)",
            "deviceId": deviceId,
            "serialNumber": serialNumber,
            "macAddress": macAddress,
            "provisionedBy": provisionerName,
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
        # Transform ESP32 lowercase fields to backend camelCase
        statusData = ESP32FieldMapper.transform_request(statusData)

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
async def registerEsp32Device(
    request: Request,
    deviceData: Dict[str, Any],
    device_mac: str = Header(None, alias="X-Device-MAC"),
    device_signature: str = Header(None, alias="X-Device-Signature"),
    device_timestamp: str = Header(None, alias="X-Timestamp")
):
    """
    Register ESP32 device in the system
    Called by ESP32 after provisioning

    Security: Requires HMAC-SHA256 authentication
    """
    try:
        deviceData = ESP32FieldMapper.transform_request(deviceData)
        macAddress = deviceData.get('macAddress')
        firmwareVersion = deviceData.get('firmwareVersion', '3.0.0')
        batteryLevel = deviceData.get('batteryLevel', 100)

        if not macAddress:
            raise HTTPException(status_code=400, detail="MAC address required")

        # HMAC Authentication
        endpoint = "/api/v1/esp32/register"
        is_valid, validated_mac, error_msg = hmac_auth.authenticate_device(
            device_mac, device_signature, device_timestamp, endpoint
        )

        if not is_valid:
            logger.warning(f"❌ Registration failed: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        if macAddress != validated_mac:
            raise HTTPException(status_code=403, detail="MAC address mismatch")

        async with getDbConnection() as conn:
            device = await conn.fetchrow(
                'SELECT id, "serialNumber" FROM devices WHERE "macAddress" = $1',
                validated_mac
            )

            if not device:
                raise HTTPException(status_code=404, detail="Device not provisioned")

            deviceId = device['id']

            await conn.execute("""
                UPDATE devices
                SET "batteryLevel" = $2, "firmwareVersion" = $3,
                    "lastSeen" = NOW(), "updatedAt" = NOW(), status = 'available'
                WHERE id = $1
            """, deviceId, batteryLevel, firmwareVersion)

            logger.info(f"✅ ESP32 registered: {deviceId} (HMAC auth)")

        return JSONResponse({
            "success": True,
            "deviceId": deviceId,
            "serialNumber": device['serialNumber'],
            "message": "Device registered",
            "servertime": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/{deviceId}/heartbeat")
async def deviceHeartbeat(
    request: Request,
    deviceId: str,
    heartbeatData: Dict[str, Any],
    device_mac: str = Header(None, alias="X-Device-MAC"),
    device_signature: str = Header(None, alias="X-Device-Signature"),
    device_timestamp: str = Header(None, alias="X-Timestamp")
):
    """
    Receive heartbeat from ESP32 device

    Security: Requires HMAC-SHA256 authentication
    """
    try:
        heartbeatData = ESP32FieldMapper.transform_request(heartbeatData)
        batteryLevel = heartbeatData.get('batteryLevel', 100)
        signalStrength = heartbeatData.get('signalStrength', -50)

        # HMAC Authentication
        endpoint = f"/api/v1/esp32/{deviceId}/heartbeat"
        is_valid, validated_mac, error_msg = hmac_auth.authenticate_device(
            device_mac, device_signature, device_timestamp, endpoint
        )

        if not is_valid:
            raise HTTPException(status_code=401, detail=error_msg)

        async with getDbConnection() as conn:
            device = await conn.fetchrow(
                'SELECT "macAddress" FROM devices WHERE id = $1',
                deviceId
            )

            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            if device['macAddress'] != validated_mac:
                raise HTTPException(status_code=403, detail="MAC mismatch")

            await conn.execute("""
                UPDATE devices
                SET "batteryLevel" = $2, "lastSeen" = NOW(), "updatedAt" = NOW(),
                    status = CASE WHEN status = 'offline' THEN 'available' ELSE status END
                WHERE id = $1
            """, deviceId, batteryLevel)

        logger.info(f"💓 Heartbeat: {deviceId} Battery {batteryLevel}%")

        return JSONResponse({
            "success": True,
            "message": "Heartbeat received",
            "servertime": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Heartbeat error: {e}")
        raise HTTPException(status_code=500, detail="Heartbeat failed")

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
        # Transform ESP32 lowercase fields to backend camelCase
        vitalsData = ESP32FieldMapper.transform_request(vitalsData)
        logger.debug(f"🔄 Transformed ESP32 vitals data to camelCase for device {deviceId}")

        # Verify device authentication
        device = await verify_device_key(device_key)

        # Verify device ID matches authenticated device
        if device["id"] != deviceId:
            logger.warning(f"⚠️ Device {device['id']} attempted to send vitals as {deviceId}")
            raise HTTPException(status_code=403, detail="Device ID mismatch")
        # Validate that device is assigned to this patient
        async with getDbConnection() as conn:
            patient = await conn.fetchrow('SELECT id FROM patients WHERE id = $1', patientId)

            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")

            # Check device assignment via deviceassignments table
            assignment = await conn.fetchrow(
                'SELECT "deviceId" FROM deviceassignments WHERE "patientId" = $1 AND status = \'active\'',
                patientId
            )
            if not assignment or assignment['deviceId'] != deviceId:
                logger.warning(f"⚠️ Device {deviceId} sent vitals for patient {patientId} but not assigned")
                raise HTTPException(status_code=403, detail="Device not assigned to this patient")
        
        # Store vitals in TimescaleDB
        try:
            async with getTimescaleConnection() as tsConn:
                timestamp = datetime.now()
                
                # Store each vital type (using camelCase after transformation)
                vitalTypes = {
                    'heartrate': vitalsData.get('heartRate'),
                    'temperature': vitalsData.get('bodyTemperature'),
                    'oxygensaturation': vitalsData.get('oxygenSaturation'),
                    'respiratoryrate': vitalsData.get('respiratoryRate'),
                    'bloodpressuresystolic': vitalsData.get('bloodPressureSystolic'),
                    'ecg': vitalsData.get('ecg'),
                    'eeg': vitalsData.get('eeg'),
                    'bioimpedance': vitalsData.get('bioImpedance'),
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
                deviceId, vitalsData.get('deviceBattery', 100)
            )

        # ============================================
        # PHASE 2: GENERATE ALERTS (BEST EFFORT)
        # ============================================
        # DEPRECATED: This HTTP endpoint alert generation is legacy.
        # ESP32 devices should use MQTT (hospital/devices/{deviceId}/vitals) instead.
        # MQTT path uses AlertPipeline from domain layer for proper alert generation.
        # This code path is kept for backwards compatibility only.
        alerts = []
        try:
            logger.warning(f"⚠️ DEPRECATED: Device {deviceId} using HTTP endpoint for vitals. Please migrate to MQTT.")
            async with getDbConnection() as conn:
                # Vital threshold alerts (existing)
                alerts = await vital_alert_service.check_vitals_and_generate_alerts(
                    patientId, deviceId, vitalsData, conn
                )

                # NEW: Arrhythmia detection
                if vitalsData.get('heartRate'):
                    logger.info(f"🔬 CALLING ARRHYTHMIA DETECTION for patient {patientId}, HR: {vitalsData.get('heartRate')}")
                    arrhythmia_alert = await arrhythmia_detection_service.detect_arrhythmia(
                        patientId, deviceId, int(vitalsData['heartRate']), conn
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
        # Transform camelCase vitals back to lowercase for frontend/ESP32 compatibility
        frontendVitals = ESP32FieldMapper.transform_response({
            'heartRate': vitalsData.get('heartRate'),
            'bloodPressure': vitalsData.get('bloodPressure'),
            'bloodPressureSystolic': vitalsData.get('bloodPressureSystolic'),
            'respiratoryRate': vitalsData.get('respiratoryRate'),
            'oxygenSaturation': vitalsData.get('oxygenSaturation'),
            'bodyTemperature': vitalsData.get('bodyTemperature'),
            'ecg': vitalsData.get('ecg'),
            'eeg': vitalsData.get('eeg'),
            'bioImpedance': vitalsData.get('bioImpedance'),
            'tremor': vitalsData.get('tremor'),
            'lastUpdated': datetime.now().isoformat(),
            'lastSync': datetime.now().isoformat()
        })
        logger.debug(f"🔄 Transformed vitals to lowercase for frontend broadcast")
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
    request: Request,
    deviceId: str,
    alertData: Dict[str, Any],
    device_mac: str = Header(None, alias="X-Device-MAC"),
    device_signature: str = Header(None, alias="X-Device-Signature"),
    device_timestamp: str = Header(None, alias="X-Timestamp")
):
    """
    Receive emergency alert from ESP32 device

    Security: Requires HMAC-SHA256 authentication
    """
    try:
        # HMAC Authentication
        endpoint = f"/api/v1/esp32/{deviceId}/alert"
        is_valid, validated_mac, error_msg = hmac_auth.authenticate_device(
            device_mac, device_signature, device_timestamp, endpoint
        )

        if not is_valid:
            raise HTTPException(status_code=401, detail=error_msg)

        async with getDbConnection() as conn:
            device = await conn.fetchrow(
                'SELECT "macAddress" FROM devices WHERE id = $1',
                deviceId
            )

            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            if device['macAddress'] != validated_mac:
                raise HTTPException(status_code=403, detail="MAC mismatch")

        alertData = ESP32FieldMapper.transform_request(alertData)
        patientId = alertData.get('patientId')
        alertType = alertData.get('alertType', 'emergency')
        message = alertData.get('message', 'Emergency button pressed')
        vitals = alertData.get('vitals', {})

        await connectionManager.sendAlert(patientId, {
            'severity': alertType,
            'message': message,
            'source': f'Device {deviceId}',
            'vitals': vitals,
            'deviceId': deviceId
        })

        logger.warning(f"🚨 Alert: {deviceId} for {patientId}: {message}")

        return JSONResponse({
            "success": True,
            "message": "Alert broadcasted",
            "alertid": str(uuid.uuid4())
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Alert error: {e}")
        raise HTTPException(status_code=500, detail="Alert failed")

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
        # Transform ESP32 lowercase fields to backend camelCase
        scanData = ESP32FieldMapper.transform_request(scanData)

        detectedDevices = scanData.get('detectedDevices', [])
        roomId = scanData.get('roomId')
        scannerLocation = scanData.get('location')
        
        if not roomId:
            raise HTTPException(status_code=400, detail="Room ID required")
        
        async with getDbConnection() as conn:
            # Update scanner heartbeat
            await conn.execute("""
                UPDATE devices
                SET "lastSeen" = NOW(), status = 'active'
                WHERE id = $1 AND "deviceType" = 'doorScanner'
            """, scannerId)
            
            # Process detected devices
            for deviceInfo in detectedDevices:
                deviceId = deviceInfo.get('deviceId')
                rssi = deviceInfo.get('rssi', -50)
                
                if deviceId:
                    # Update device location based on door scanner detection
                    await conn.execute("""
                        UPDATE devices
                        SET location = $2, "lastSeen" = NOW()
                        WHERE id = $1
                    """, deviceId, roomId)
                    
                    # Find patient assigned to this device (via deviceassignments JOIN)
                    patient = await conn.fetchrow("""
                        SELECT p.id, p."firstName", p."lastName"
                        FROM patients p
                        JOIN deviceassignments da ON p.id = da."patientId"
                        WHERE da."deviceId" = $1 AND da.status = 'active' AND p.status = 'active'
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
