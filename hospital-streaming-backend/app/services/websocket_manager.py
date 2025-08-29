from fastapi import WebSocket
from typing import Dict, List, Set, Optional, Any
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections for real-time streaming"""
    
    def __init__(self):
        # Store active connections by client_id
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Store connections by channel (vitals, alerts, etc.)
        self.channels: Dict[str, Set[str]] = {
            "vitals": set(),
            "alerts": set(),
            "door_events": set(),
            "device_status": set()
        }
        
        # Store client metadata
        self.client_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str, channel: str = "general"):
        """Accept a WebSocket connection and add to channel"""
        await websocket.accept()
        
        self.active_connections[client_id] = websocket
        
        # Add to channel
        if channel not in self.channels:
            self.channels[channel] = set()
        self.channels[channel].add(client_id)
        
        # Store metadata
        self.client_metadata[client_id] = {
            "channel": channel,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        logger.info(f"Client {client_id} connected to channel {channel}")
        
        # Send welcome message
        await self.send_personal_message(client_id, {
            "type": "connection_established",
            "client_id": client_id,
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def disconnect(self, client_id: str):
        """Remove client from all connections and channels"""
        if client_id in self.active_connections:
            # Remove from all channels
            for channel_clients in self.channels.values():
                channel_clients.discard(client_id)
            
            # Remove connection and metadata
            del self.active_connections[client_id]
            if client_id in self.client_metadata:
                del self.client_metadata[client_id]
            
            logger.info(f"Client {client_id} disconnected")
    
    async def send_personal_message(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                await self.disconnect(client_id)
    
    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]):
        """Broadcast message to all clients in a channel"""
        if channel not in self.channels:
            logger.warning(f"Channel {channel} does not exist")
            return
        
        message["channel"] = channel
        message["broadcast_timestamp"] = datetime.utcnow().isoformat()
        
        # Get list of clients to avoid modification during iteration
        client_ids = list(self.channels[channel])
        
        for client_id in client_ids:
            await self.send_personal_message(client_id, message)
        
        logger.debug(f"Broadcasted message to {len(client_ids)} clients in channel {channel}")
    
    async def broadcast_vitals_data(self, vital_data: Dict[str, Any]):
        """Broadcast vital signs data to vitals channel"""
        message = {
            "type": "vital_update",
            "data": vital_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_channel("vitals", message)
    
    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """Broadcast alert to alerts channel"""
        message = {
            "type": "new_alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_channel("alerts", message)
    
    async def broadcast_door_event(self, door_event: Dict[str, Any]):
        """Broadcast door scanner event"""
        message = {
            "type": "door_event",
            "data": door_event,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_channel("door_events", message)
    
    async def broadcast_device_status(self, device_status: Dict[str, Any]):
        """Broadcast device status update"""
        message = {
            "type": "device_status_update",
            "data": device_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_channel("device_status", message)
    
    async def add_client_to_channel(self, client_id: str, channel: str):
        """Add existing client to additional channel"""
        if client_id not in self.active_connections:
            logger.warning(f"Client {client_id} not found")
            return False
        
        if channel not in self.channels:
            self.channels[channel] = set()
        
        self.channels[channel].add(client_id)
        
        # Update metadata
        if client_id in self.client_metadata:
            if "channels" not in self.client_metadata[client_id]:
                self.client_metadata[client_id]["channels"] = []
            self.client_metadata[client_id]["channels"].append(channel)
        
        await self.send_personal_message(client_id, {
            "type": "channel_joined",
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return True
    
    async def remove_client_from_channel(self, client_id: str, channel: str):
        """Remove client from specific channel"""
        if channel in self.channels:
            self.channels[channel].discard(client_id)
        
        # Update metadata
        if client_id in self.client_metadata:
            if "channels" in self.client_metadata[client_id]:
                try:
                    self.client_metadata[client_id]["channels"].remove(channel)
                except ValueError:
                    pass
        
        await self.send_personal_message(client_id, {
            "type": "channel_left",
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_channel_clients(self, channel: str) -> List[str]:
        """Get list of client IDs in a channel"""
        return list(self.channels.get(channel, set()))
    
    def get_client_channels(self, client_id: str) -> List[str]:
        """Get list of channels a client is subscribed to"""
        channels = []
        for channel, clients in self.channels.items():
            if client_id in clients:
                channels.append(channel)
        return channels
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "channels": {
                channel: len(clients) 
                for channel, clients in self.channels.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def ping_all_clients(self):
        """Send ping to all connected clients to keep connections alive"""
        ping_message = {
            "type": "ping",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        client_ids = list(self.active_connections.keys())
        for client_id in client_ids:
            await self.send_personal_message(client_id, ping_message)
    
    async def start_keepalive_task(self):
        """Start background task to keep connections alive"""
        while True:
            await asyncio.sleep(30)  # Ping every 30 seconds
            await self.ping_all_clients()
    
    async def broadcast_system_message(self, message: str, severity: str = "info"):
        """Broadcast system-wide message to all clients"""
        system_message = {
            "type": "system_message",
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to all channels
        for channel in self.channels.keys():
            await self.broadcast_to_channel(channel, system_message)