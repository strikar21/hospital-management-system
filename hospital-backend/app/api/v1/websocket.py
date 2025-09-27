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

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/realtime")
async def websocketEndpoint(
    websocket: WebSocket,
    userId: str = Query(..., description="User ID for authentication"),
    userRole: str = Query(..., description="User role for authorization")
):
    """
    WebSocket endpoint for real-time hospital data updates
    
    Supports:
    - Real-time vitals streaming
    - Medication updates
    - Alert notifications
    - Patient-specific subscriptions
    """
    
    # Generate unique connection ID
    connectionId = f"conn{uuid.uuid4().hex[:8]}"
    
    try:
        # Establish WebSocket connection
        await connectionManager.connect(websocket, connectionId, userId, userRole)
        
        # Handle incoming messages from client
        async for data in websocket.iter_text():
            try:
                message = json.loads(data)
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
    
    messageType = message.get('type')
    
    if messageType == 'subscribePatient':
        # Subscribe to patient-specific updates
        patientId = message.get('patientId')
        if patientId:
            # Verify patient exists and user has access
            async with getDbConnection() as conn:
                patient = await fetchOne(conn, "SELECT id FROM patients WHERE id = $1 AND status = 'active'", (patientId,))
                if patient:
                    success = connectionManager.subscribeToPatient(connectionId, patientId)
                    await connectionManager.sendToConnection(connectionId, {
                        'type': 'subscriptionResult',
                        'action': 'subscribePatient',
                        'patientId': patientId,
                        'success': success,
                        'message': f'Subscribed to patient {patientId}' if success else 'Subscription failed'
                    })
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
            success = connectionManager.unsubscribe_from_patient(connectionId, patientId)
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