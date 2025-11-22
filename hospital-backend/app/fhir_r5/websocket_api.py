"""
WebSocket API for Real-Time Streaming

Provides WebSocket endpoints for streaming vitals and alerts
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json

from app.services.websocket_service import vitals_streaming


# Router for WebSocket endpoints
ws_router = APIRouter(prefix="/ws", tags=["WebSocket"])


@ws_router.websocket("/vitals")
async def websocket_vitals_all(websocket: WebSocket):
    """
    WebSocket endpoint for streaming all patient vitals

    Connect to: ws://localhost:8000/ws/vitals

    Messages sent:
    - observation: FHIR Observation resources
    - alert: FHIR Flag resources (alerts)
    - audit: FHIR AuditEvent resources
    - device_status: Device status updates
    """
    await vitals_streaming.manager.connect(websocket)

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to vitals stream (all patients)",
            "stats": vitals_streaming.get_stats()
        })

        # Keep connection alive and receive messages
        while True:
            # Receive messages (for future two-way communication)
            data = await websocket.receive_text()

            # Echo back (for testing)
            await websocket.send_json({
                "type": "echo",
                "message": f"Received: {data}"
            })

    except WebSocketDisconnect:
        vitals_streaming.manager.disconnect(websocket)


@ws_router.websocket("/vitals/{patient_id}")
async def websocket_vitals_patient(
    websocket: WebSocket,
    patient_id: str
):
    """
    WebSocket endpoint for streaming specific patient vitals

    Connect to: ws://localhost:8000/ws/vitals/PAT000001

    Args:
        patient_id: Patient ID to subscribe to

    Messages sent:
    - observation: FHIR Observation resources for this patient
    - alert: FHIR Flag resources (alerts) for this patient
    """
    await vitals_streaming.manager.connect(websocket, patient_id)

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": f"Connected to vitals stream for patient {patient_id}",
            "patientId": patient_id,
            "stats": vitals_streaming.get_stats()
        })

        # Keep connection alive
        while True:
            data = await websocket.receive_text()

            # Handle commands
            try:
                command = json.loads(data)

                if command.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": command.get("timestamp")
                    })
                elif command.get("type") == "stats":
                    await websocket.send_json({
                        "type": "stats",
                        "data": vitals_streaming.get_stats()
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown command: {command.get('type')}"
                    })
            except json.JSONDecodeError:
                # Plain text message
                await websocket.send_json({
                    "type": "echo",
                    "message": data
                })

    except WebSocketDisconnect:
        vitals_streaming.manager.disconnect(websocket, patient_id)


@ws_router.get("/stats")
async def get_websocket_stats():
    """
    Get WebSocket streaming statistics

    Returns connection counts and uptime
    """
    return vitals_streaming.get_stats()
