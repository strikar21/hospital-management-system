import asyncio
import json
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime
import paho.mqtt.client as mqtt
from threading import Thread

from app.core.config import settings
from app.schemas.device import VitalReadingCreate, DoorScanEventCreate, DeviceHealth
from app.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

class MQTTService:
    """MQTT service for IoT device communication"""
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.websocket_manager: Optional[WebSocketManager] = None
        self.is_connected = False
        self.message_handlers: Dict[str, Callable] = {}
        
        # MQTT topics
        self.topics = {
            "vitals": "hospital/devices/+/vitals",
            "door_events": "hospital/devices/+/door",
            "heartbeat": "hospital/devices/+/heartbeat",
            "alerts": "hospital/devices/+/alerts",
            "commands": "hospital/devices/+/commands"
        }
    
    def set_websocket_manager(self, websocket_manager: WebSocketManager):
        """Set WebSocket manager for broadcasting"""
        self.websocket_manager = websocket_manager
    
    async def start(self):
        """Start MQTT service"""
        try:
            self.client = mqtt.Client()
            
            # Set up callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            
            # Authentication if configured
            if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
                self.client.username_pw_set(
                    settings.MQTT_USERNAME, 
                    settings.MQTT_PASSWORD
                )
            
            # Connect to broker
            self.client.connect(
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
                60
            )
            
            # Start the network loop in a separate thread
            self.client.loop_start()
            
            logger.info(f"MQTT service started - connecting to {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
            
        except Exception as e:
            logger.error(f"Failed to start MQTT service: {e}")
            raise
    
    async def stop(self):
        """Stop MQTT service"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT service stopped")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            self.is_connected = True
            logger.info("Connected to MQTT broker")
            
            # Subscribe to all topics
            for topic_name, topic_pattern in self.topics.items():
                client.subscribe(topic_pattern)
                logger.info(f"Subscribed to {topic_pattern}")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        self.is_connected = False
        logger.warning(f"Disconnected from MQTT broker: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.debug(f"Received MQTT message on {topic}: {payload}")
            
            # Route message based on topic
            asyncio.create_task(self._route_message(topic, payload))
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    async def _route_message(self, topic: str, payload: Dict[str, Any]):
        """Route MQTT message to appropriate handler"""
        try:
            topic_parts = topic.split('/')
            if len(topic_parts) < 4:
                logger.warning(f"Invalid topic format: {topic}")
                return
            
            device_id = topic_parts[2]
            message_type = topic_parts[3]
            
            if message_type == "vitals":
                await self._handle_vitals_message(device_id, payload)
            elif message_type == "door":
                await self._handle_door_message(device_id, payload)
            elif message_type == "heartbeat":
                await self._handle_heartbeat_message(device_id, payload)
            elif message_type == "alerts":
                await self._handle_alert_message(device_id, payload)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error routing MQTT message: {e}")
    
    async def _handle_vitals_message(self, device_id: str, payload: Dict[str, Any]):
        """Handle vital signs data from MQTT"""
        try:
            # Convert MQTT payload to VitalReadingCreate
            vital_data = VitalReadingCreate(
                device_id=device_id,
                patient_id=payload.get("patient_id"),
                heart_rate=payload.get("heart_rate"),
                blood_pressure_systolic=payload.get("blood_pressure_systolic"),
                blood_pressure_diastolic=payload.get("blood_pressure_diastolic"),
                temperature=payload.get("temperature"),
                oxygen_saturation=payload.get("oxygen_saturation"),
                respiratory_rate=payload.get("respiratory_rate"),
                ecg_data=payload.get("ecg_data"),
                eeg_data=payload.get("eeg_data"),
                movement_data=payload.get("movement_data"),
                location_data=payload.get("location_data"),
                raw_data=payload.get("raw_data"),
                signal_quality=payload.get("signal_quality"),
                reading_timestamp=datetime.fromisoformat(payload.get("timestamp", datetime.utcnow().isoformat()))
            )
            
            # Store in database (would need database connection here)
            # For now, just broadcast via WebSocket
            if self.websocket_manager:
                streaming_data = {
                    "device_id": device_id,
                    "patient_id": vital_data.patient_id,
                    "vitals": {
                        "heart_rate": vital_data.heart_rate,
                        "blood_pressure_systolic": vital_data.blood_pressure_systolic,
                        "blood_pressure_diastolic": vital_data.blood_pressure_diastolic,
                        "temperature": vital_data.temperature,
                        "oxygen_saturation": vital_data.oxygen_saturation,
                        "respiratory_rate": vital_data.respiratory_rate
                    },
                    "reading_timestamp": vital_data.reading_timestamp.isoformat(),
                    "signal_quality": vital_data.signal_quality,
                    "source": "mqtt"
                }
                
                await self.websocket_manager.broadcast_vitals_data(streaming_data)
            
            logger.debug(f"Processed vitals from device {device_id}")
            
        except Exception as e:
            logger.error(f"Error handling vitals message: {e}")
    
    async def _handle_door_message(self, device_id: str, payload: Dict[str, Any]):
        """Handle door scanner events from MQTT"""
        try:
            door_event = DoorScanEventCreate(
                device_id=device_id,
                card_id=payload.get("card_id"),
                user_id=payload.get("user_id"),
                access_granted=payload.get("access_granted", False),
                door_location=payload.get("door_location", "unknown"),
                scan_timestamp=datetime.fromisoformat(payload.get("timestamp", datetime.utcnow().isoformat())),
                event_data=payload.get("event_data")
            )
            
            # Broadcast door event
            if self.websocket_manager:
                door_event_data = {
                    "device_id": device_id,
                    "card_id": door_event.card_id,
                    "user_id": door_event.user_id,
                    "access_granted": door_event.access_granted,
                    "door_location": door_event.door_location,
                    "scan_timestamp": door_event.scan_timestamp.isoformat(),
                    "event_data": door_event.event_data,
                    "source": "mqtt"
                }
                
                await self.websocket_manager.broadcast_door_event(door_event_data)
            
            logger.debug(f"Processed door event from device {device_id}")
            
        except Exception as e:
            logger.error(f"Error handling door message: {e}")
    
    async def _handle_heartbeat_message(self, device_id: str, payload: Dict[str, Any]):
        """Handle device heartbeat from MQTT"""
        try:
            # Update device status and broadcast health update
            device_status = {
                "device_id": device_id,
                "status": payload.get("status", "online"),
                "battery_level": payload.get("battery_level"),
                "signal_strength": payload.get("signal_strength"),
                "last_heartbeat": datetime.utcnow().isoformat(),
                "system_info": payload.get("system_info"),
                "source": "mqtt"
            }
            
            if self.websocket_manager:
                await self.websocket_manager.broadcast_device_status(device_status)
            
            logger.debug(f"Processed heartbeat from device {device_id}")
            
        except Exception as e:
            logger.error(f"Error handling heartbeat message: {e}")
    
    async def _handle_alert_message(self, device_id: str, payload: Dict[str, Any]):
        """Handle device alerts from MQTT"""
        try:
            alert_data = {
                "device_id": device_id,
                "alert_type": payload.get("alert_type", "unknown"),
                "severity": payload.get("severity", "medium"),
                "message": payload.get("message", "Device alert"),
                "timestamp": payload.get("timestamp", datetime.utcnow().isoformat()),
                "metadata": payload.get("metadata"),
                "source": "mqtt"
            }
            
            if self.websocket_manager:
                await self.websocket_manager.broadcast_alert(alert_data)
            
            logger.info(f"Processed alert from device {device_id}: {alert_data['alert_type']}")
            
        except Exception as e:
            logger.error(f"Error handling alert message: {e}")
    
    def publish_command(self, device_id: str, command: Dict[str, Any]) -> bool:
        """Send command to device via MQTT"""
        if not self.is_connected:
            logger.warning("MQTT not connected, cannot send command")
            return False
        
        try:
            topic = f"hospital/devices/{device_id}/commands"
            payload = json.dumps({
                **command,
                "timestamp": datetime.utcnow().isoformat(),
                "command_id": f"cmd_{int(datetime.utcnow().timestamp())}"
            })
            
            result = self.client.publish(topic, payload)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Command sent to device {device_id}: {command.get('action', 'unknown')}")
                return True
            else:
                logger.error(f"Failed to send command to device {device_id}: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get MQTT service status"""
        return {
            "is_connected": self.is_connected,
            "broker_host": settings.MQTT_BROKER_HOST,
            "broker_port": settings.MQTT_BROKER_PORT,
            "subscribed_topics": list(self.topics.values()),
            "timestamp": datetime.utcnow().isoformat()
        }