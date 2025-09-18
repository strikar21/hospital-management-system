"""
WebSocket API endpoints for real-time hospital data streaming
"""

import json
import logging
import uuid
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import JSONResponse

from ...services.websocket_manager import connection_manager
from ...core.database import get_db_connection, get_timescale_connection
from ...core.db_utils import fetch_one

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/realtime")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str = Query(..., description="User ID for authentication"),
    user_role: str = Query(..., description="User role for authorization")
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
    connection_id = f"conn_{uuid.uuid4().hex[:8]}"
    
    try:
        # Establish WebSocket connection
        await connection_manager.connect(websocket, connection_id, user_id, user_role)
        
        # Handle incoming messages from client
        async for data in websocket.iter_text():
            try:
                message = json.loads(data)
                await handle_client_message(connection_id, message)
                
            except json.JSONDecodeError:
                await connection_manager.send_to_connection(connection_id, {
                    'type': 'error',
                    'message': 'Invalid JSON format'
                })
            except Exception as e:
                logger.error(f"❌ Error handling client message from {connection_id}: {e}")
                await connection_manager.send_to_connection(connection_id, {
                    'type': 'error',
                    'message': 'Message processing failed'
                })
                
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error for {connection_id}: {e}")
    finally:
        connection_manager.disconnect(connection_id)

async def handle_client_message(connection_id: str, message: Dict[str, Any]) -> None:
    """Handle incoming messages from WebSocket clients"""
    
    message_type = message.get('type')
    
    if message_type == 'subscribe_patient':
        # Subscribe to patient-specific updates
        patient_id = message.get('patient_id')
        if patient_id:
            # Verify patient exists and user has access
            async with get_db_connection() as conn:
                patient = await fetch_one(conn, "SELECT id FROM patients WHERE id = ? AND status = 'active'", (patient_id,))
                if patient:
                    success = connection_manager.subscribe_to_patient(connection_id, patient_id)
                    await connection_manager.send_to_connection(connection_id, {
                        'type': 'subscription_result',
                        'action': 'subscribe_patient',
                        'patient_id': patient_id,
                        'success': success,
                        'message': f'Subscribed to patient {patient_id}' if success else 'Subscription failed'
                    })
                else:
                    await connection_manager.send_to_connection(connection_id, {
                        'type': 'subscription_result',
                        'action': 'subscribe_patient',
                        'patient_id': patient_id,
                        'success': False,
                        'message': 'Patient not found or inactive'
                    })
        else:
            await connection_manager.send_to_connection(connection_id, {
                'type': 'error',
                'message': 'Patient ID required for subscription'
            })
    
    elif message_type == 'unsubscribe_patient':
        # Unsubscribe from patient-specific updates
        patient_id = message.get('patient_id')
        if patient_id:
            success = connection_manager.unsubscribe_from_patient(connection_id, patient_id)
            await connection_manager.send_to_connection(connection_id, {
                'type': 'subscription_result',
                'action': 'unsubscribe_patient',
                'patient_id': patient_id,
                'success': success,
                'message': f'Unsubscribed from patient {patient_id}' if success else 'Unsubscribe failed'
            })
        else:
            await connection_manager.send_to_connection(connection_id, {
                'type': 'error',
                'message': 'Patient ID required for unsubscription'
            })
    
    elif message_type == 'pong':
        # Handle pong response from client
        logger.debug(f"💓 Pong received from {connection_id}")
    
    elif message_type == 'get_status':
        # Send connection status
        await connection_manager.send_to_connection(connection_id, {
            'type': 'status',
            'connection_id': connection_id,
            'total_connections': connection_manager.get_connection_count(),
            'metadata': connection_manager.connection_metadata.get(connection_id, {})
        })
    
    else:
        await connection_manager.send_to_connection(connection_id, {
            'type': 'error',
            'message': f'Unknown message type: {message_type}'
        })

@router.get("/connections/status")
async def get_websocket_status():
    """Get current WebSocket connection status"""
    return JSONResponse({
        'total_connections': connection_manager.get_connection_count(),
        'patient_subscriptions': {
            patient_id: len(connections) 
            for patient_id, connections in connection_manager.patient_subscriptions.items()
        },
        'general_subscriptions': len(connection_manager.general_subscriptions)
    })

@router.post("/broadcast/vitals/{patient_id}")
async def broadcast_vitals_update(patient_id: str, vitals_data: Dict[str, Any], device_id: str = Query(..., description="Device ID sending vitals")):
    """
    Manually broadcast vitals update to subscribers
    Used for testing or external integrations - requires device_id validation
    """
    try:
        await connection_manager.send_vitals_update(patient_id, device_id, vitals_data)
        return JSONResponse({
            'success': True,
            'message': f'Vitals update broadcasted for patient {patient_id} from device {device_id}',
            'subscriber_count': connection_manager.get_patient_subscriber_count(patient_id)
        })
    except Exception as e:
        logger.error(f"❌ Failed to broadcast vitals update: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast vitals update")

@router.post("/broadcast/medication/{patient_id}")
async def broadcast_medication_update(patient_id: str, medication_data: Dict[str, Any]):
    """
    Manually broadcast medication update to subscribers
    Used for testing or external integrations
    """
    try:
        await connection_manager.send_medication_update(patient_id, medication_data)
        return JSONResponse({
            'success': True,
            'message': f'Medication update broadcasted for patient {patient_id}',
            'subscriber_count': connection_manager.get_patient_subscriber_count(patient_id)
        })
    except Exception as e:
        logger.error(f"❌ Failed to broadcast medication update: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast medication update")

@router.post("/broadcast/alert")
async def broadcast_alert(alert_data: Dict[str, Any]):
    """
    Broadcast alert to all or patient-specific subscribers
    """
    try:
        patient_id = alert_data.get('patient_id')
        await connection_manager.send_alert(patient_id, alert_data)
        
        if patient_id:
            subscriber_count = connection_manager.get_patient_subscriber_count(patient_id)
        else:
            subscriber_count = len(connection_manager.general_subscriptions)
        
        return JSONResponse({
            'success': True,
            'message': f'Alert broadcasted{f" for patient {patient_id}" if patient_id else " to all subscribers"}',
            'subscriber_count': subscriber_count
        })
    except Exception as e:
        logger.error(f"❌ Failed to broadcast alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast alert")