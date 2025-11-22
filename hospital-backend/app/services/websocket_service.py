"""
WebSocket Service for Real-Time Vitals Streaming

Broadcasts FHIR Observations and Alerts to connected clients
"""

from typing import Dict, Any, Set, List
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from datetime import datetime


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""

    def __init__(self):
        # Active connections by patient ID
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Global connections (all patients)
        self.global_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, patient_id: str = None):
        """
        Accept a WebSocket connection

        Args:
            websocket: WebSocket connection
            patient_id: Optional patient ID to subscribe to specific patient
        """
        await websocket.accept()

        if patient_id:
            # Subscribe to specific patient
            if patient_id not in self.active_connections:
                self.active_connections[patient_id] = set()
            self.active_connections[patient_id].add(websocket)
        else:
            # Subscribe to all patients
            self.global_connections.add(websocket)

    def disconnect(self, websocket: WebSocket, patient_id: str = None):
        """
        Remove a WebSocket connection

        Args:
            websocket: WebSocket connection to remove
            patient_id: Patient ID if subscribed to specific patient
        """
        if patient_id and patient_id in self.active_connections:
            self.active_connections[patient_id].discard(websocket)
            if not self.active_connections[patient_id]:
                del self.active_connections[patient_id]
        else:
            self.global_connections.discard(websocket)

    async def broadcast_to_patient(self, patient_id: str, message: Dict[str, Any]):
        """
        Broadcast message to all connections subscribed to a patient

        Args:
            patient_id: Patient ID
            message: Message to broadcast
        """
        # Send to patient-specific connections
        if patient_id in self.active_connections:
            dead_connections = set()
            for connection in self.active_connections[patient_id]:
                try:
                    await connection.send_json(message)
                except:
                    dead_connections.add(connection)

            # Remove dead connections
            for connection in dead_connections:
                self.active_connections[patient_id].discard(connection)

        # Send to global connections
        await self.broadcast_global(message)

    async def broadcast_global(self, message: Dict[str, Any]):
        """
        Broadcast message to all global connections

        Args:
            message: Message to broadcast
        """
        dead_connections = set()
        for connection in self.global_connections:
            try:
                await connection.send_json(message)
            except:
                dead_connections.add(connection)

        # Remove dead connections
        for connection in dead_connections:
            self.global_connections.discard(connection)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific connection"""
        await websocket.send_text(message)

    def get_connection_count(self) -> Dict[str, int]:
        """Get count of active connections"""
        patient_counts = {
            patient_id: len(connections)
            for patient_id, connections in self.active_connections.items()
        }

        return {
            "global": len(self.global_connections),
            "patients": patient_counts,
            "total": len(self.global_connections) + sum(patient_counts.values())
        }


class VitalsStreamingService:
    """Service for streaming vitals and alerts via WebSocket"""

    def __init__(self):
        self.manager = ConnectionManager()

    async def stream_observation(self, observation: Dict[str, Any]):
        """
        Stream a FHIR Observation to connected clients

        Args:
            observation: FHIR R5 Observation resource
        """
        # Extract patient ID
        patient_ref = observation.get("subject", {}).get("reference", "")
        patient_id = patient_ref.replace("Patient/", "")

        # Create message
        message = {
            "type": "observation",
            "timestamp": datetime.now().isoformat(),
            "data": observation
        }

        # Broadcast
        if patient_id:
            await self.manager.broadcast_to_patient(patient_id, message)
        else:
            await self.manager.broadcast_global(message)

    async def stream_alert(self, alert: Dict[str, Any]):
        """
        Stream a FHIR Flag (alert) to connected clients

        Args:
            alert: FHIR R5 Flag resource
        """
        # Extract patient ID
        patient_ref = alert.get("subject", {}).get("reference", "")
        patient_id = patient_ref.replace("Patient/", "")

        # Create message
        message = {
            "type": "alert",
            "timestamp": datetime.now().isoformat(),
            "severity": alert.get("_internal", {}).get("severity", "warning"),
            "data": alert
        }

        # Broadcast
        if patient_id:
            await self.manager.broadcast_to_patient(patient_id, message)
        else:
            await self.manager.broadcast_global(message)

    async def stream_audit_event(self, audit_event: Dict[str, Any]):
        """
        Stream a FHIR AuditEvent to connected clients

        Args:
            audit_event: FHIR R5 AuditEvent resource
        """
        # Create message
        message = {
            "type": "audit",
            "timestamp": datetime.now().isoformat(),
            "data": audit_event
        }

        # Broadcast globally (audit events are for all)
        await self.manager.broadcast_global(message)

    async def stream_device_status(self, device_id: str, status: Dict[str, Any]):
        """
        Stream device status update

        Args:
            device_id: Device ID
            status: Status information (battery, connectivity, etc.)
        """
        message = {
            "type": "device_status",
            "timestamp": datetime.now().isoformat(),
            "deviceId": device_id,
            "data": status
        }

        await self.manager.broadcast_global(message)

    def get_stats(self) -> Dict[str, Any]:
        """Get streaming service statistics"""
        return {
            "connections": self.manager.get_connection_count(),
            "uptime": datetime.now().isoformat()
        }


# Global instance
vitals_streaming = VitalsStreamingService()
