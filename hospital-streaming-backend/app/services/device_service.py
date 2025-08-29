import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, insert
from sqlalchemy.exc import IntegrityError

from app.db.database import database
from app.models.device import Device, DeviceAlert, VitalReading
from app.schemas.device import (
    DeviceCreate, DeviceUpdate, DeviceResponse, DeviceHealth, 
    DeviceAlertCreate, VitalReadingCreate
)
from app.services.websocket_manager import WebSocketManager
import logging

logger = logging.getLogger(__name__)

class DeviceService:
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
    
    async def register_device(self, device_data: DeviceCreate) -> DeviceResponse:
        """Register a new device in the system"""
        
        # Check if device already exists
        existing_query = select(Device).where(Device.deviceId == device_data.device_id)
        existing_device = await database.fetch_one(existing_query)
        
        if existing_device:
            raise ValueError(f"Device with ID {device_data.device_id} already exists")
        
        # Generate authentication tokens
        device_token = secrets.token_urlsafe(32)
        api_key = secrets.token_urlsafe(24)
        
        # Create device record
        device_dict = device_data.dict()
        device_dict.update({
            "deviceToken": device_token,
            "apiKey": api_key,
            "status": "offline",
            "createdAt": datetime.utcnow(),
            "isActive": True
        })
        
        try:
            query = insert(Device).values(**device_dict)
            device_id_db = await database.execute(query)
            
            # Fetch the created device
            fetch_query = select(Device).where(Device.id == device_id_db)
            device = await database.fetch_one(fetch_query)
            
            logger.info(f"Device registered successfully: {device_data.device_id}")
            
            return DeviceResponse.from_orm(device)
            
        except IntegrityError as e:
            logger.error(f"Device registration failed: {e}")
            raise ValueError("Device registration failed due to constraint violation")
    
    async def update_device(self, device_id: str, device_update: DeviceUpdate) -> DeviceResponse:
        """Update device information"""
        
        # Check if device exists
        check_query = select(Device).where(
            Device.deviceId == device_id, 
            Device.isActive == True
        )
        existing_device = await database.fetch_one(check_query)
        
        if not existing_device:
            raise ValueError(f"Device {device_id} not found")
        
        # Update device
        update_data = device_update.dict(exclude_unset=True)
        update_data["updatedAt"] = datetime.utcnow()
        
        query = update(Device).where(
            Device.deviceId == device_id
        ).values(**update_data)
        
        await database.execute(query)
        
        # Fetch updated device
        fetch_query = select(Device).where(Device.deviceId == device_id)
        updated_device = await database.fetch_one(fetch_query)
        
        logger.info(f"Device updated: {device_id}")
        
        return DeviceResponse.from_orm(updated_device)
    
    async def update_device_heartbeat(self, device_id: str, health_data: DeviceHealth):
        """Update device heartbeat and health status"""
        
        # Update device last_seen and health data
        update_data = {
            "lastHeartbeat": health_data.last_heartbeat,
            "lastSeen": datetime.utcnow(),
            "status": health_data.status.value,
            "updatedAt": datetime.utcnow()
        }
        
        if health_data.battery_level is not None:
            update_data["batteryLevel"] = health_data.battery_level
        
        if health_data.signal_strength is not None:
            update_data["signalStrength"] = health_data.signal_strength
        
        query = update(Device).where(
            Device.deviceId == device_id,
            Device.isActive == True
        ).values(**update_data)
        
        result = await database.execute(query)
        
        if result == 0:
            raise ValueError(f"Device {device_id} not found")
        
        # Check for alert conditions
        await self._check_device_health_alerts(device_id, health_data)
        
        logger.debug(f"Heartbeat received from device: {device_id}")
    
    async def create_device_alert(self, alert_data: DeviceAlertCreate) -> int:
        """Create a new device alert"""
        
        alert_dict = alert_data.dict()
        alert_dict.update({
            "createdAt": datetime.utcnow(),
            "isActive": True,
            "isAcknowledged": False
        })
        
        query = insert(DeviceAlert).values(**alert_dict)
        alert_id = await database.execute(query)
        
        # Broadcast alert via WebSocket
        await self._broadcast_alert(alert_id, alert_data)
        
        logger.info(f"Alert created for device {alert_data.device_id}: {alert_data.alert_type}")
        
        return alert_id
    
    async def get_offline_devices(self, threshold_minutes: int = 5) -> List[DeviceResponse]:
        """Get devices that haven't sent heartbeat within threshold"""
        
        threshold_time = datetime.utcnow() - timedelta(minutes=threshold_minutes)
        
        query = select(Device).where(
            Device.isActive == True,
            Device.lastHeartbeat < threshold_time,
            Device.status != "offline"
        )
        
        devices = await database.fetch_all(query)
        
        return [DeviceResponse.from_orm(device) for device in devices]
    
    async def mark_devices_offline(self, threshold_minutes: int = 5):
        """Mark devices as offline if they haven't sent heartbeat"""
        
        threshold_time = datetime.utcnow() - timedelta(minutes=threshold_minutes)
        
        query = update(Device).where(
            Device.isActive == True,
            Device.lastHeartbeat < threshold_time,
            Device.status != "offline"
        ).values(
            status="offline",
            updatedAt=datetime.utcnow()
        )
        
        result = await database.execute(query)
        
        if result > 0:
            logger.info(f"Marked {result} devices as offline")
        
        return result
    
    async def _check_device_health_alerts(self, device_id: str, health_data: DeviceHealth):
        """Check device health and create alerts if needed"""
        
        alerts_to_create = []
        
        # Battery low alert
        if health_data.battery_level is not None and health_data.battery_level < 20:
            severity = "critical" if health_data.battery_level < 10 else "high"
            alerts_to_create.append(DeviceAlertCreate(
                device_id=device_id,
                alert_type="battery_low",
                severity=severity,
                message=f"Battery level is {health_data.battery_level}%",
                alert_data={"battery_level": health_data.battery_level}
            ))
        
        # Signal strength alert
        if health_data.signal_strength is not None and health_data.signal_strength < -80:
            alerts_to_create.append(DeviceAlertCreate(
                device_id=device_id,
                alert_type="weak_signal",
                severity="medium",
                message=f"Weak signal strength: {health_data.signal_strength} dBm",
                alert_data={"signal_strength": health_data.signal_strength}
            ))
        
        # Create alerts
        for alert_data in alerts_to_create:
            # Check if similar alert already exists
            existing_query = select(DeviceAlert).where(
                DeviceAlert.deviceId == device_id,
                DeviceAlert.alertType == alert_data.alert_type,
                DeviceAlert.isActive == True,
                DeviceAlert.isAcknowledged == False
            )
            existing_alert = await database.fetch_one(existing_query)
            
            if not existing_alert:
                await self.create_device_alert(alert_data)
    
    async def _broadcast_alert(self, alert_id: int, alert_data: DeviceAlertCreate):
        """Broadcast alert to connected WebSocket clients"""
        
        alert_message = {
            "type": "device_alert",
            "alert_id": alert_id,
            "device_id": alert_data.device_id,
            "alert_type": alert_data.alert_type,
            "severity": alert_data.severity,
            "message": alert_data.message,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": alert_data.alert_data
        }
        
        # Broadcast to all clients subscribed to alerts
        await self.websocket_manager.broadcast_to_channel("alerts", alert_message)
    
    async def authenticate_device(self, device_token: str) -> Optional[DeviceResponse]:
        """Authenticate device using token"""
        
        query = select(Device).where(
            Device.deviceToken == device_token,
            Device.isActive == True
        )
        device = await database.fetch_one(query)
        
        if device:
            return DeviceResponse.from_orm(device)
        
        return None
    
    async def get_device_capabilities(self, device_id: str) -> Dict[str, Any]:
        """Get device capabilities"""
        
        query = select(Device.capabilities).where(
            Device.deviceId == device_id,
            Device.isActive == True
        )
        result = await database.fetch_one(query)
        
        return result["capabilities"] if result and result["capabilities"] else {}
    
    async def update_device_configuration(self, device_id: str, config: Dict[str, Any]) -> bool:
        """Update device configuration"""
        
        query = update(Device).where(
            Device.deviceId == device_id,
            Device.isActive == True
        ).values(
            configuration=config,
            updatedAt=datetime.utcnow()
        )
        
        result = await database.execute(query)
        return result > 0