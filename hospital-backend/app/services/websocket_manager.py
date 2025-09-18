"""
WebSocket manager for real-time hospital data streaming
"""

import json
import asyncio
import logging
from typing import Dict, Set, Any, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Active connections by connection ID
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Connections subscribed to specific patients
        self.patient_subscriptions: Dict[str, Set[str]] = {}  # patient_id -> set of connection_ids
        
        # Connections subscribed to general hospital updates
        self.general_subscriptions: Set[str] = set()
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str, user_role: str) -> None:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            'user_id': user_id,
            'user_role': user_role,
            'connected_at': datetime.now().isoformat(),
            'last_ping': datetime.now().isoformat()
        }
        
        # Auto-subscribe to general updates
        self.general_subscriptions.add(connection_id)
        
        logger.info(f"🔌 WebSocket connection established: {connection_id} (User: {user_id}, Role: {user_role})")
        
        # Send connection confirmation
        await self.send_to_connection(connection_id, {
            'type': 'connection_established',
            'connection_id': connection_id,
            'timestamp': datetime.now().isoformat(),
            'message': 'Real-time updates enabled'
        })
    
    def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        # Remove from all subscriptions
        self.general_subscriptions.discard(connection_id)
        
        for patient_id in self.patient_subscriptions:
            self.patient_subscriptions[patient_id].discard(connection_id)
        
        # Clean up empty patient subscriptions
        empty_patients = [pid for pid, conns in self.patient_subscriptions.items() if not conns]
        for pid in empty_patients:
            del self.patient_subscriptions[pid]
        
        logger.info(f"🔌 WebSocket connection closed: {connection_id}")
    
    async def send_to_connection(self, connection_id: str, data: Dict[str, Any]) -> bool:
        """Send data to a specific connection"""
        if connection_id not in self.active_connections:
            return False
        
        try:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send to connection {connection_id}: {e}")
            # Remove broken connection
            self.disconnect(connection_id)
            return False
    
    async def broadcast_to_patient_subscribers(self, patient_id: str, data: Dict[str, Any]) -> int:
        """Send data to all connections subscribed to a specific patient"""
        if patient_id not in self.patient_subscriptions:
            return 0
        
        sent_count = 0
        failed_connections = []
        
        for connection_id in self.patient_subscriptions[patient_id].copy():
            success = await self.send_to_connection(connection_id, data)
            if success:
                sent_count += 1
            else:
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        for conn_id in failed_connections:
            self.patient_subscriptions[patient_id].discard(conn_id)
        
        return sent_count
    
    async def broadcast_general(self, data: Dict[str, Any]) -> int:
        """Send data to all general subscribers"""
        sent_count = 0
        failed_connections = []
        
        for connection_id in self.general_subscriptions.copy():
            success = await self.send_to_connection(connection_id, data)
            if success:
                sent_count += 1
            else:
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        for conn_id in failed_connections:
            self.general_subscriptions.discard(conn_id)
        
        return sent_count
    
    def subscribe_to_patient(self, connection_id: str, patient_id: str) -> bool:
        """Subscribe a connection to patient-specific updates"""
        if connection_id not in self.active_connections:
            return False
        
        if patient_id not in self.patient_subscriptions:
            self.patient_subscriptions[patient_id] = set()
        
        self.patient_subscriptions[patient_id].add(connection_id)
        logger.info(f"📡 Connection {connection_id} subscribed to patient {patient_id}")
        return True
    
    def unsubscribe_from_patient(self, connection_id: str, patient_id: str) -> bool:
        """Unsubscribe a connection from patient-specific updates"""
        if patient_id in self.patient_subscriptions:
            self.patient_subscriptions[patient_id].discard(connection_id)
            
            # Clean up empty subscriptions
            if not self.patient_subscriptions[patient_id]:
                del self.patient_subscriptions[patient_id]
            
            logger.info(f"📡 Connection {connection_id} unsubscribed from patient {patient_id}")
            return True
        return False
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    def get_patient_subscriber_count(self, patient_id: str) -> int:
        """Get number of connections subscribed to a specific patient"""
        return len(self.patient_subscriptions.get(patient_id, set()))
    
    async def send_vitals_update(self, patient_id: str, device_id: str, vitals_data: Dict[str, Any]) -> None:
        """Send vitals update to patient subscribers - only if device is assigned and connected"""
        from ..core.database import get_db_connection
        
        try:
            # Check if patient has this device assigned and device is connected
            async with get_db_connection() as conn:
                # Check device assignment
                result = await conn.fetchrow(
                    "SELECT assignedDeviceId FROM patients WHERE id = $1",
                    patient_id
                )
                
                if not result or not result['assigneddeviceid']:
                    logger.warning(f"⚠️ Vitals update ignored - no device assigned to patient {patient_id}")
                    return
                
                if result['assigneddeviceid'] != device_id:
                    logger.warning(f"⚠️ Vitals update ignored - device mismatch. Patient {patient_id} assigned to {result['assigneddeviceid']}, got update from {device_id}")
                    return
                
                # Check device status
                device_result = await conn.fetchrow(
                    "SELECT status, lastSeen FROM devices WHERE id = $1",
                    device_id
                )
                
                if not device_result or device_result['status'] not in ['active', 'connected']:
                    logger.warning(f"⚠️ Vitals update ignored - device {device_id} status is {device_result['status'] if device_result else 'not found'}")
                    return
        
            # Device validation passed - send vitals update
            data = {
                'type': 'vitals_update',
                'patient_id': patient_id,
                'device_id': device_id,
                'timestamp': datetime.now().isoformat(),
                'vitals': vitals_data
            }
            
            sent_count = await self.broadcast_to_patient_subscribers(patient_id, data)
            if sent_count > 0:
                logger.info(f"📊 Vitals update sent to {sent_count} subscribers for patient {patient_id} from device {device_id}")
        
        except Exception as e:
            logger.error(f"❌ Error validating device assignment for vitals update: {e}")
    
    async def send_medication_update(self, patient_id: str, medication_data: Dict[str, Any]) -> None:
        """Send medication update to patient subscribers"""
        data = {
            'type': 'medication_update',
            'patient_id': patient_id,
            'timestamp': datetime.now().isoformat(),
            'medication': medication_data
        }
        
        sent_count = await self.broadcast_to_patient_subscribers(patient_id, data)
        if sent_count > 0:
            logger.info(f"💊 Medication update sent to {sent_count} subscribers for patient {patient_id}")
    
    async def send_alert(self, patient_id: Optional[str], alert_data: Dict[str, Any]) -> None:
        """Send alert to relevant subscribers"""
        data = {
            'type': 'alert',
            'patient_id': patient_id,
            'timestamp': datetime.now().isoformat(),
            'alert': alert_data
        }
        
        if patient_id:
            # Send to patient-specific subscribers
            sent_count = await self.broadcast_to_patient_subscribers(patient_id, data)
        else:
            # Send to all general subscribers
            sent_count = await self.broadcast_general(data)
        
        if sent_count > 0:
            logger.info(f"🚨 Alert sent to {sent_count} subscribers{f' for patient {patient_id}' if patient_id else ' (general)'}")
    
    async def keepalive(self) -> None:
        """Send keepalive pings to all connections"""
        ping_data = {
            'type': 'ping',
            'timestamp': datetime.now().isoformat()
        }
        
        sent_count = await self.broadcast_general(ping_data)
        if sent_count > 0:
            logger.debug(f"💓 Keepalive sent to {sent_count} connections")

# Global connection manager instance
connection_manager = ConnectionManager()

# Background task for keepalive pings
async def keepalive_task():
    """Background task to send periodic keepalive pings"""
    while True:
        try:
            await connection_manager.keepalive()
            await asyncio.sleep(30)  # Send keepalive every 30 seconds
        except Exception as e:
            logger.error(f"❌ Keepalive task error: {e}")
            await asyncio.sleep(5)

# The keepalive task will be started when the FastAPI app starts
keepalive_task_instance = None

def start_keepalive_task():
    """Start the keepalive background task"""
    global keepalive_task_instance
    if keepalive_task_instance is None:
        keepalive_task_instance = asyncio.create_task(keepalive_task())
        logger.info("💓 WebSocket keepalive task started")

def stop_keepalive_task():
    """Stop the keepalive background task"""
    global keepalive_task_instance
    if keepalive_task_instance is not None:
        keepalive_task_instance.cancel()
        keepalive_task_instance = None
        logger.info("💓 WebSocket keepalive task stopped")