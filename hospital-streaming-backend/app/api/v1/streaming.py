from fastapi import APIRouter, Request, HTTPException, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.schemas.device import StreamingVitalData, StreamingAlertData
from app.services.websocket_manager import WebSocketManager

router = APIRouter(prefix="/streaming")

@router.get("/stats")
async def get_streaming_stats(request: Request):
    """Get WebSocket connection statistics"""
    websocket_manager: WebSocketManager = request.app.state.websocket_manager
    return websocket_manager.get_connection_stats()

@router.get("/channels")
async def get_channels(request: Request):
    """Get available streaming channels"""
    websocket_manager: WebSocketManager = request.app.state.websocket_manager
    
    channels = {}
    for channel, clients in websocket_manager.channels.items():
        channels[channel] = {
            "name": channel,
            "client_count": len(clients),
            "description": get_channel_description(channel)
        }
    
    return {"channels": channels}

@router.get("/channels/{channel}/clients")
async def get_channel_clients(channel: str, request: Request):
    """Get clients connected to specific channel"""
    websocket_manager: WebSocketManager = request.app.state.websocket_manager
    
    if channel not in websocket_manager.channels:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    clients = websocket_manager.get_channel_clients(channel)
    client_details = []
    
    for client_id in clients:
        if client_id in websocket_manager.client_metadata:
            metadata = websocket_manager.client_metadata[client_id]
            client_details.append({
                "clientId": client_id,
                "connectedAt": metadata.get("connectedAt"),
                "lastPing": metadata.get("lastPing"),
                "channels": websocket_manager.get_client_channels(client_id)
            })
    
    return {
        "channel": channel,
        "client_count": len(clients),
        "clients": client_details
    }

@router.post("/broadcast/system")
async def broadcast_system_message(
    message: str,
    severity: str = "info",
    request: Request = None
):
    """Broadcast system message to all connected clients"""
    websocket_manager: WebSocketManager = request.app.state.websocket_manager
    
    await websocket_manager.broadcast_system_message(message, severity)
    
    return {
        "status": "message_broadcasted",
        "message": message,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/test/vitals")
async def test_vitals_broadcast(request: Request):
    """Test endpoint to broadcast sample vitals data"""
    websocket_manager: WebSocketManager = request.app.state.websocket_manager
    
    # Sample vital data
    vital_data = {
        "deviceId": "TEST_DEVICE_001",
        "patientId": "PATIENT_123",
        "heartRate": 75,
        "bloodPressureSystolic": 120,
        "bloodPressureDiastolic": 80,
        "temperature": 98.6,
        "oxygenSaturation": 98.5,
        "respiratoryRate": 16,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await websocket_manager.broadcast_vitals_data(vital_data)
    
    return {
        "status": "test_vitals_broadcasted",
        "data": vital_data
    }

@router.post("/test/alert")
async def test_alert_broadcast(request: Request):
    """Test endpoint to broadcast sample alert"""
    websocket_manager: WebSocketManager = request.app.state.websocket_manager
    
    # Sample alert data
    alert_data = {
        "alertId": 999,
        "deviceId": "TEST_DEVICE_001",
        "patientId": "PATIENT_123",
        "alertType": "test_alert",
        "severity": "medium",
        "message": "This is a test alert for demonstration",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await websocket_manager.broadcast_alert(alert_data)
    
    return {
        "status": "test_alert_broadcasted",
        "data": alert_data
    }

def get_channel_description(channel: str) -> str:
    """Get description for streaming channel"""
    descriptions = {
        "vitals": "Real-time vital signs data from all monitoring devices",
        "alerts": "Critical alerts and notifications from devices and patients",
        "doorEvents": "Door scanner access events and security notifications",
        "deviceStatus": "Device health status and connectivity updates"
    }
    return descriptions.get(channel, "Custom streaming channel")