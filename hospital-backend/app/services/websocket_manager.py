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
        self.activeConnections: Dict[str, WebSocket] = {}
        
        # Connections subscribed to specific patients
        self.patientSubscriptions: Dict[str, Set[str]] = {}  # patientId -> set of connectionIds
        
        # Connections subscribed to general hospital updates
        self.generalSubscriptions: Set[str] = set()
        
        # Connection metadata
        self.connectionMetadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connectionId: str, userId: str, userRole: str) -> None:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        self.activeConnections[connectionId] = websocket
        self.connectionMetadata[connectionId] = {
            'userId': userId,
            'userRole': userRole,
            'connectedAt': datetime.now().isoformat(),
            'lastPing': datetime.now().isoformat()
        }
        
        # Auto-subscribe to general updates
        self.generalSubscriptions.add(connectionId)
        
        logger.info(f"🔌 WebSocket connection established: {connectionId} (User: {userId}, Role: {userRole})")
        
        # Send connection confirmation
        await self.sendToConnection(connectionId, {
            'type': 'connectionEstablished',
            'connectionId': connectionId,
            'timestamp': datetime.now().isoformat(),
            'message': 'Real-time updates enabled'
        })
    
    def disconnect(self, connectionId: str) -> None:
        """Remove a WebSocket connection"""
        if connectionId in self.activeConnections:
            del self.activeConnections[connectionId]
        
        if connectionId in self.connectionMetadata:
            del self.connectionMetadata[connectionId]
        
        # Remove from all subscriptions
        self.generalSubscriptions.discard(connectionId)
        
        for patientId in self.patientSubscriptions:
            self.patientSubscriptions[patientId].discard(connectionId)
        
        # Clean up empty patient subscriptions
        emptyPatients = [pid for pid, conns in self.patientSubscriptions.items() if not conns]
        for pid in emptyPatients:
            del self.patientSubscriptions[pid]
        
        logger.info(f"🔌 WebSocket connection closed: {connectionId}")
    
    async def sendToConnection(self, connectionId: str, data: Dict[str, Any]) -> bool:
        """Send data to a specific connection"""
        if connectionId not in self.activeConnections:
            return False
        
        try:
            websocket = self.activeConnections[connectionId]
            await websocket.send_text(json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send to connection {connectionId}: {e}")
            # Remove broken connection
            self.disconnect(connectionId)
            return False
    
    async def broadcastToPatientSubscribers(self, patientId: str, data: Dict[str, Any]) -> int:
        """Send data to all connections subscribed to a specific patient"""
        if patientId not in self.patientSubscriptions:
            return 0
        
        sentCount = 0
        failedConnections = []

        for connectionId in self.patientSubscriptions[patientId].copy():
            success = await self.sendToConnection(connectionId, data)
            if success:
                sentCount += 1
            else:
                failedConnections.append(connectionId)

        # Clean up failed connections
        for connId in failedConnections:
            self.patientSubscriptions[patientId].discard(connId)

        return sentCount
    
    async def broadcastGeneral(self, data: Dict[str, Any]) -> int:
        """Send data to all general subscribers"""
        sentCount = 0
        failedConnections = []

        for connectionId in self.generalSubscriptions.copy():
            success = await self.sendToConnection(connectionId, data)
            if success:
                sentCount += 1
            else:
                failedConnections.append(connectionId)

        # Clean up failed connections
        for connId in failedConnections:
            self.generalSubscriptions.discard(connId)

        return sentCount
    
    def subscribeToPatient(self, connectionId: str, patientId: str) -> bool:
        """Subscribe a connection to patient-specific updates"""
        if connectionId not in self.activeConnections:
            return False
        
        if patientId not in self.patientSubscriptions:
            self.patientSubscriptions[patientId] = set()
        
        self.patientSubscriptions[patientId].add(connectionId)
        logger.info(f"📡 Connection {connectionId} subscribed to patient {patientId}")
        return True
    
    def unsubscribeFromPatient(self, connectionId: str, patientId: str) -> bool:
        """Unsubscribe a connection from patient-specific updates"""
        if patientId in self.patientSubscriptions:
            self.patientSubscriptions[patientId].discard(connectionId)
            
            # Clean up empty subscriptions
            if not self.patientSubscriptions[patientId]:
                del self.patientSubscriptions[patientId]
            
            logger.info(f"📡 Connection {connectionId} unsubscribed from patient {patientId}")
            return True
        return False
    
    def getConnectionCount(self) -> int:
        """Get total number of active connections"""
        return len(self.activeConnections)
    
    def getPatientSubscriberCount(self, patientId: str) -> int:
        """Get number of connections subscribed to a specific patient"""
        return len(self.patientSubscriptions.get(patientId, set()))
    
    async def sendVitalsUpdate(self, patientId: str, deviceId: str, vitalsData: Dict[str, Any]) -> None:
        """Send vitals update to patient subscribers - only if device is assigned and connected"""
        from ..core.database import getDbConnection
        
        try:
            # Check if patient has this device assigned and device is connected
            async with getDbConnection() as conn:
                # Check device assignment
                result = await conn.fetchrow(
                    "SELECT assigneddeviceid FROM patients WHERE id = $1",
                    patientId
                )
                
                if not result or not result['assigneddeviceid']:
                    logger.warning(f"⚠️ Vitals update ignored - no device assigned to patient {patientId}")
                    return
                
                if result['assigneddeviceid'] != deviceId:
                    logger.warning(f"⚠️ Vitals update ignored - device mismatch. Patient {patientId} assigned to {result['assigneddeviceid']}, got update from {deviceId}")
                    return
                
                # Check device status
                deviceResult = await conn.fetchrow(
                    "SELECT status, lastseen FROM devices WHERE id = $1",
                    deviceId
                )
                
                if not deviceResult or deviceResult['status'] not in ['active', 'connected']:
                    logger.warning(f"⚠️ Vitals update ignored - device {deviceId} status is {deviceResult['status'] if deviceResult else 'not found'}")
                    return
        
            # Device validation passed - send vitals update
            data = {
                'type': 'vitalsUpdate',
                'patientId': patientId,
                'deviceId': deviceId,
                'timestamp': datetime.now().isoformat(),
                'vitals': vitalsData
            }
            
            sentCount = await self.broadcastToPatientSubscribers(patientId, data)
            if sentCount > 0:
                logger.info(f"📊 Vitals update sent to {sentCount} subscribers for patient {patientId} from device {deviceId}")
        
        except Exception as e:
            logger.error(f"❌ Error validating device assignment for vitals update: {e}")
    
    async def sendMedicationUpdate(self, patientId: str, medicationData: Dict[str, Any]) -> None:
        """Send medication update to patient subscribers"""
        data = {
            'type': 'medicationUpdate',
            'patientId': patientId,
            'timestamp': datetime.now().isoformat(),
            'medication': medicationData
        }
        
        sentCount = await self.broadcastToPatientSubscribers(patientId, data)
        if sentCount > 0:
            logger.info(f"💊 Medication update sent to {sentCount} subscribers for patient {patientId}")
    
    async def sendAlert(self, patientId: Optional[str], alertData: Dict[str, Any]) -> None:
        """Send alert to relevant subscribers"""
        data = {
            'type': 'alert',
            'patientId': patientId,
            'timestamp': datetime.now().isoformat(),
            'alert': alertData
        }
        
        if patientId:
            # Send to patient-specific subscribers
            sentCount = await self.broadcastToPatientSubscribers(patientId, data)
        else:
            # Send to all general subscribers
            sentCount = await self.broadcastGeneral(data)
        
        if sentCount > 0:
            logger.info(f"🚨 Alert sent to {sentCount} subscribers{f' for patient {patientId}' if patientId else ' (general)'}")
    
    async def keepalive(self) -> None:
        """Send keepalive pings to all connections"""
        pingData = {
            'type': 'ping',
            'timestamp': datetime.now().isoformat()
        }
        
        sentCount = await self.broadcastGeneral(pingData)
        if sentCount > 0:
            logger.debug(f"💓 Keepalive sent to {sentCount} connections")

# Global connection manager instance
connectionManager = ConnectionManager()

# Background task for keepalive pings
async def keepAliveTask():
    """Background task to send periodic keepalive pings"""
    while True:
        try:
            await connectionManager.keepalive()
            await asyncio.sleep(30)  # Send keepalive every 30 seconds
        except Exception as e:
            logger.error(f"❌ Keepalive task error: {e}")
            await asyncio.sleep(5)

# The keepalive task will be started when the FastAPI app starts
keepaliveTaskInstance = None

def startKeepaliveTask():
    """Start the keepalive background task"""
    global keepaliveTaskInstance
    if keepaliveTaskInstance is None:
        keepaliveTaskInstance = asyncio.create_task(keepAliveTask())
        logger.info("💓 WebSocket keepalive task started")

def stopKeepaliveTask():
    """Stop the keepalive background task"""
    global keepaliveTaskInstance
    if keepaliveTaskInstance is not None:
        keepaliveTaskInstance.cancel()
        keepaliveTaskInstance = None
        logger.info("💓 WebSocket keepalive task stopped")