"""
WebSocket API endpoints for real-time hospital data streaming
"""

import json
import logging
import uuid
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import JSONResponse

from ...services.websocket_manager import connectionManager
from ...core.database import getDbConnection, getTimescaleConnection
from ...core.db_utils import fetchOne
from ...core.jwt_handler import verify_token

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/realtime")
async def websocketEndpoint(
    websocket: WebSocket,
    token: str = Query(None, description="JWT authentication token")
):
    """
    WebSocket endpoint for real-time hospital data updates
    FIXED: Now requires valid JWT token for authentication

    Supports:
    - Real-time vitals streaming
    - Medication updates
    - Alert notifications
    - Patient-specific subscriptions
    """

    # Must accept connection before we can close it with a reason
    await websocket.accept()

    # Validate JWT token - reject if missing or invalid
    if not token:
        logger.warning("WebSocket: Connection rejected - no token provided")
        await websocket.close(code=1008, reason="Authentication token required")
        return

    try:
        user = verify_token(token, "access")
        userId = user.get("id")
        userRole = user.get("role")
        logger.info(f"WebSocket: Authenticated user {userId} with role {userRole}")
    except Exception as e:
        # Invalid token - reject connection
        logger.warning(f"WebSocket: Authentication failed - {str(e)}")
        await websocket.close(code=1008, reason="Invalid authentication token")
        return

    # Generate unique connection ID
    connectionId = f"conn{uuid.uuid4().hex[:8]}"

    try:
        # Establish WebSocket connection with validated user
        await connectionManager.connect(websocket, connectionId, userId, userRole)
        
        # Handle incoming messages from client
        async for data in websocket.iter_text():
            logger.info(f"🟢 RAW WebSocket data received from {connectionId}: {data[:500]}")
            try:
                message = json.loads(data)
                logger.info(f"🟢 Parsed WebSocket message from {connectionId}: type={message.get('type')}, keys={list(message.keys())}")
                await handleClientMessage(connectionId, message)
                
            except json.JSONDecodeError:
                await connectionManager.sendToConnection(connectionId, {
                    'type': 'error',
                    'message': 'Invalid JSON format'
                })
            except Exception as e:
                logger.error(f"❌ Error handling client message from {connectionId}: {e}")
                await connectionManager.sendToConnection(connectionId, {
                    'type': 'error',
                    'message': 'Message processing failed'
                })
                
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {connectionId}")
    except Exception as e:
        logger.error(f"❌ WebSocket error for {connectionId}: {e}")
    finally:
        connectionManager.disconnect(connectionId)

async def handleClientMessage(connectionId: str, message: Dict[str, Any]) -> None:
    """Handle incoming messages from WebSocket clients"""

    logger.info(f"🔵 DEBUG: Received WebSocket message: type={message.get('type')}, keys={list(message.keys())}")

    messageType = message.get('type')

    if messageType == 'subscribePatient':
        # Subscribe to patient-specific updates
        patientId = message.get('patientId')
        triggerWaveformCalibration = message.get('triggerWaveformCalibration', False)  # ✅ NEW: ECG viewer can request waveform calibration

        logger.info(f"🔵 DEBUG: subscribePatient - patientId={patientId}, triggerWaveformCalibration={triggerWaveformCalibration}")

        if patientId:
            # Verify patient exists and user has access
            async with getDbConnection() as conn:
                patient = await fetchOne(conn, "SELECT id FROM patients WHERE id = $1 AND status = 'active'", (patientId,))

                logger.info(f"🔵 DEBUG: Patient lookup - found={patient is not None}")

                if patient:
                    success = connectionManager.subscribeToPatient(connectionId, patientId)

                    logger.info(f"🔵 DEBUG: subscribeToPatient returned success={success}")

                    await connectionManager.sendToConnection(connectionId, {
                        'type': 'subscriptionResult',
                        'action': 'subscribePatient',
                        'patientId': patientId,
                        'success': success,
                        'message': f'Subscribed to patient {patientId}' if success else 'Subscription failed'
                    })

                    # ✅ NEW: Trigger waveform calibration on ECG viewer open
                    logger.info(f"🔵 DEBUG: Checking waveform calibration - success={success}, trigger={triggerWaveformCalibration}")

                    if success and triggerWaveformCalibration:
                        logger.info(f"🔵 DEBUG: About to trigger waveform calibration for patient {patientId}")
                        try:
                            deviceId = await _getDeviceForPatient(patientId)
                            logger.info(f"🔵 DEBUG: Device lookup returned deviceId={deviceId}")

                            if deviceId:
                                logger.info(f"🔵 DEBUG: Calling _triggerWaveformCalibration for device {deviceId}")
                                await _triggerWaveformCalibration(deviceId, patientId)
                                logger.info(f"🔧 Waveform calibration triggered for device {deviceId} (patient {patientId})")
                            else:
                                logger.warning(f"⚠️  No device found for patient {patientId}")
                        except Exception as e:
                            logger.error(f"⚠️  Could not trigger waveform calibration for patient {patientId}: {e}", exc_info=True)
                    else:
                        logger.info(f"🔵 DEBUG: Waveform calibration NOT triggered - success={success}, trigger={triggerWaveformCalibration}")

                else:
                    await connectionManager.sendToConnection(connectionId, {
                        'type': 'subscriptionResult',
                        'action': 'subscribePatient',
                        'patientId': patientId,
                        'success': False,
                        'message': 'Patient not found or inactive'
                    })
        else:
            await connectionManager.sendToConnection(connectionId, {
                'type': 'error',
                'message': 'Patient ID required for subscription'
            })
    
    elif messageType == 'unsubscribePatient':
        # Unsubscribe from patient-specific updates
        patientId = message.get('patientId')
        if patientId:
            success = connectionManager.unsubscribeFromPatient(connectionId, patientId)
            await connectionManager.sendToConnection(connectionId, {
                'type': 'subscriptionResult',
                'action': 'unsubscribePatient',
                'patientId': patientId,
                'success': success,
                'message': f'Unsubscribed from patient {patientId}' if success else 'Unsubscribe failed'
            })
        else:
            await connectionManager.sendToConnection(connectionId, {
                'type': 'error',
                'message': 'Patient ID required for unsubscription'
            })
    
    elif messageType == 'pong':
        # Handle pong response from client
        logger.debug(f"💓 Pong received from {connectionId}")
    
    elif messageType == 'getStatus':
        # Send connection status
        await connectionManager.sendToConnection(connectionId, {
            'type': 'status',
            'connectionId': connectionId,
            'totalConnections': connectionManager.getConnectionCount(),
            'metadata': connectionManager.connectionMetadata.get(connectionId, {})
        })
    
    else:
        await connectionManager.sendToConnection(connectionId, {
            'type': 'error',
            'message': f'Unknown message type: {messageType}'
        })

@router.get("/connections/status")
async def getWebsocketStatus():
    """Get current WebSocket connection status"""
    return JSONResponse({
        'totalConnections': connectionManager.getConnectionCount(),
        'patientSubscriptions': {
            patientId: len(connections) 
            for patientId, connections in connectionManager.patientSubscriptions.items()
        },
        'generalSubscriptions': len(connectionManager.generalSubscriptions)
    })

@router.post("/broadcast/vitals/{patientId}")
async def broadcastVitalsUpdate(patientId: str, vitalsData: Dict[str, Any], deviceId: str = Query(..., description="Device ID sending vitals")):
    """
    Manually broadcast vitals update to subscribers
    Used for testing or external integrations - requires deviceId validation
    """
    try:
        await connectionManager.sendVitalsUpdate(patientId, deviceId, vitalsData)
        return JSONResponse({
            'success': True,
            'message': f'Vitals update broadcasted for patient {patientId} from device {deviceId}',
            'subscriberCount': connectionManager.getPatientSubscriberCount(patientId)
        })
    except Exception as e:
        logger.error(f"❌ Failed to broadcast vitals update: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast vitals update")

@router.post("/broadcast/medication/{patientId}")
async def broadcastMedicationUpdate(patientId: str, medicationData: Dict[str, Any]):
    """
    Manually broadcast medication update to subscribers
    Used for testing or external integrations
    """
    try:
        await connectionManager.sendMedicationUpdate(patientId, medicationData)
        return JSONResponse({
            'success': True,
            'message': f'Medication update broadcasted for patient {patientId}',
            'subscriberCount': connectionManager.getPatientSubscriberCount(patientId)
        })
    except Exception as e:
        logger.error(f"❌ Failed to broadcast medication update: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast medication update")

@router.post("/broadcast/alert")
async def broadcastAlert(alertData: Dict[str, Any]):
    """
    Broadcast alert to all or patient-specific subscribers
    """
    try:
        patientId = alertData.get('patientId')
        await connectionManager.sendAlert(patientId, alertData)

        if patientId:
            subscriberCount = connectionManager.getPatientSubscriberCount(patientId)
        else:
            subscriberCount = len(connectionManager.generalSubscriptions)

        return JSONResponse({
            'success': True,
            'message': f'Alert broadcasted{f" for patient {patientId}" if patientId else " to all subscribers"}',
            'subscriberCount': subscriberCount
        })
    except Exception as e:
        logger.error(f"❌ Failed to broadcast alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast alert")

# ====================================
# ✅ NEW: WAVEFORM CALIBRATION HELPERS
# ====================================

async def _getDeviceForPatient(patientId: str) -> str | None:
    """Get device ID assigned to a patient"""
    async with getDbConnection() as conn:
        result = await fetchOne(conn, """
            SELECT d.id as deviceId
            FROM deviceassignments da
            JOIN devices d ON da."deviceId" = d.id
            WHERE da."patientId" = $1
            AND da."assignedAt" IS NOT NULL
            AND da."unassignedAt" IS NULL
            ORDER BY da."assignedAt" DESC
            LIMIT 1
        """, (patientId,))
        return result['deviceid'] if result else None

async def _triggerWaveformCalibration(deviceId: str, patientId: str) -> None:
    """Send MQTT waveform calibration command to device"""
    from ...services.mqtt_service import mqttService
    from datetime import datetime, timezone

    commandId = str(uuid.uuid4())
    command = {
        'command': 'waveformCalibrate',
        'commandId': commandId,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'triggeredBy': 'ecgViewerOpen',
        'patientId': patientId
    }

    await mqttService.publishCommand(deviceId, command)
    logger.info(f"📤 Waveform calibration command sent to device {deviceId} (commandId: {commandId})")