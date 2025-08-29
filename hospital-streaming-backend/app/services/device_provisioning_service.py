from typing import List, Optional, Dict, Any
from sqlalchemy.exc import IntegrityError
import uuid
import secrets
import logging
import json
from datetime import datetime

from app.db.database import database
from app.schemas.devices import DeviceProvisionRequest, DeviceResponse, DeviceUpdate, DeviceStatusUpdate

logger = logging.getLogger(__name__)

class DeviceProvisioningService:
    @staticmethod
    def _parse_device_result(result) -> Dict[str, Any]:
        """Parse database result and convert JSON strings back to dicts"""
        if not result:
            return None
        
        result_dict = dict(result)
        
        # Parse JSON fields
        for field in ['capabilities', 'configuration']:
            if result_dict.get(field) and isinstance(result_dict[field], str):
                try:
                    result_dict[field] = json.loads(result_dict[field])
                except (json.JSONDecodeError, TypeError):
                    result_dict[field] = {}
        
        return result_dict
    @staticmethod
    def generate_device_token() -> str:
        """Generate a secure device token for authentication"""
        return f"dt_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key for device communication"""
        return f"ak_{secrets.token_urlsafe(24)}"
    
    @staticmethod
    async def provision_device(device_data: DeviceProvisionRequest, provisioned_by: str) -> Optional[DeviceResponse]:
        """Provision a new device in the system"""
        try:
            # Check if device_id already exists
            query = "SELECT COUNT(*) FROM devices WHERE device_id = :device_id"
            result = await database.fetch_val(query, {"device_id": device_data.device_id})
            if result > 0:
                raise ValueError(f"Device ID {device_data.device_id} already exists")
            
            # Check if MAC address already exists (if provided)
            if device_data.mac_address:
                query = "SELECT COUNT(*) FROM devices WHERE mac_address = :mac_address"
                result = await database.fetch_val(query, {"mac_address": device_data.mac_address})
                if result > 0:
                    raise ValueError(f"MAC address {device_data.mac_address} already exists")
            
            # Generate security credentials
            device_token = DeviceProvisioningService.generate_device_token()
            api_key = DeviceProvisioningService.generate_api_key()
            
            # Set default capabilities based on device type
            default_capabilities = DeviceProvisioningService._get_default_capabilities(device_data.device_type)
            capabilities = {**default_capabilities, **(device_data.capabilities or {})}
            
            # Set default configuration
            default_config = DeviceProvisioningService._get_default_config(device_data.device_type)
            configuration = {**default_config, **(device_data.initial_config or {})}
            
            # Insert device
            query = """
                INSERT INTO devices (
                    device_id, name, device_type, status, location, mac_address, 
                    capabilities, configuration, firmware_version, device_token, 
                    api_key, is_active
                )
                VALUES (
                    :device_id, :name, :device_type, 'provisioning', :location, 
                    :mac_address, :capabilities, :configuration, :firmware_version, 
                    :device_token, :api_key, true
                )
                RETURNING id, device_id, name, device_type, status, location, mac_address,
                         ip_address, capabilities, configuration, firmware_version,
                         device_token, api_key, last_seen, last_heartbeat, battery_level,
                         signal_strength, created_at, updated_at, is_active
            """
            
            result = await database.fetch_one(
                query,
                {
                    "device_id": device_data.device_id,
                    "name": device_data.name,
                    "device_type": device_data.device_type,
                    "location": device_data.location,
                    "mac_address": device_data.mac_address,
                    "capabilities": json.dumps(capabilities),
                    "configuration": json.dumps(configuration),
                    "firmware_version": device_data.firmware_version,
                    "device_token": device_token,
                    "api_key": api_key
                }
            )
            
            if result:
                logger.info(f"Provisioned device: {device_data.device_id} by {provisioned_by}")
                
                # Log provisioning action
                await DeviceProvisioningService._log_device_action(
                    device_data.device_id, 
                    "provisioned", 
                    provisioned_by,
                    {"device_type": device_data.device_type, "location": device_data.location}
                )
                
                result_dict = DeviceProvisioningService._parse_device_result(result)
                return DeviceResponse(**result_dict)
            
            return None
            
        except IntegrityError as e:
            logger.error(f"Integrity error provisioning device: {e}")
            if "device_id" in str(e):
                raise ValueError("Device ID already exists")
            elif "mac_address" in str(e):
                raise ValueError("MAC address already exists")
            else:
                raise ValueError("Error provisioning device")
        except Exception as e:
            logger.error(f"Error provisioning device: {e}")
            raise
    
    @staticmethod
    async def get_device(device_id: str) -> Optional[DeviceResponse]:
        """Get device by device ID"""
        try:
            query = """
                SELECT id, device_id, name, device_type, status, location, mac_address,
                       ip_address, capabilities, configuration, firmware_version,
                       device_token, api_key, last_seen, last_heartbeat, battery_level,
                       signal_strength, created_at, updated_at, is_active
                FROM devices
                WHERE device_id = :device_id
            """
            
            result = await database.fetch_one(query, {"device_id": device_id})
            
            if result:
                result_dict = DeviceProvisioningService._parse_device_result(result)
                return DeviceResponse(**result_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting device: {e}")
            return None
    
    @staticmethod
    async def list_devices(
        page: int = 1,
        page_size: int = 50,
        device_type: str = None,
        status: str = None,
        location: str = None,
        is_active: bool = True
    ) -> dict:
        """List devices with filtering and pagination"""
        try:
            offset = (page - 1) * page_size
            
            # Build WHERE clause
            where_conditions = []
            params = {"offset": offset, "limit": page_size}
            
            if is_active is not None:
                where_conditions.append("is_active = :is_active")
                params["is_active"] = is_active
            
            if device_type:
                where_conditions.append("device_type = :device_type")
                params["device_type"] = device_type
            
            if status:
                where_conditions.append("status = :status")
                params["status"] = status
                
            if location:
                where_conditions.append("location ILIKE :location")
                params["location"] = f"%{location}%"
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM devices WHERE {where_clause}"
            count_params = {k: v for k, v in params.items() if k not in ['offset', 'limit']}
            total_count = await database.fetch_val(count_query, count_params)
            
            # Get device list
            list_query = f"""
                SELECT id, device_id, name, device_type, status, location, mac_address,
                       ip_address, capabilities, configuration, firmware_version,
                       device_token, api_key, last_seen, last_heartbeat, battery_level,
                       signal_strength, created_at, updated_at, is_active
                FROM devices
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """
            
            results = await database.fetch_all(list_query, params)
            
            device_list = [DeviceResponse(**dict(row)) for row in results]
            
            return {
                "devices": device_list,
                "total_count": total_count,
                "page": page,
                "page_size": page_size
            }
            
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            return {
                "devices": [],
                "total_count": 0,
                "page": page,
                "page_size": page_size
            }
    
    @staticmethod
    async def update_device(device_id: str, update_data: DeviceUpdate) -> Optional[DeviceResponse]:
        """Update device information"""
        try:
            # Build update query dynamically
            update_fields = []
            params = {"device_id": device_id}
            
            for field, value in update_data.dict(exclude_unset=True).items():
                if value is not None:
                    update_fields.append(f"{field} = :{field}")
                    params[field] = value
            
            if not update_fields:
                return await DeviceProvisioningService.get_device(device_id)
            
            update_fields.append("updated_at = NOW()")
            
            query = f"""
                UPDATE devices
                SET {", ".join(update_fields)}
                WHERE device_id = :device_id
                RETURNING id, device_id, name, device_type, status, location, mac_address,
                         ip_address, capabilities, configuration, firmware_version,
                         device_token, api_key, last_seen, last_heartbeat, battery_level,
                         signal_strength, created_at, updated_at, is_active
            """
            
            result = await database.fetch_one(query, params)
            
            if result:
                logger.info(f"Updated device: {device_id}")
                return DeviceResponse(**dict(result))
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating device: {e}")
            raise
    
    @staticmethod
    async def update_device_status(device_id: str, status_data: DeviceStatusUpdate) -> Optional[DeviceResponse]:
        """Update device status and operational data"""
        try:
            update_fields = ["last_heartbeat = NOW()", "updated_at = NOW()"]
            params = {"device_id": device_id}
            
            if status_data.status:
                update_fields.append("status = :status")
                params["status"] = status_data.status
            
            if status_data.battery_level is not None:
                update_fields.append("battery_level = :battery_level")
                params["battery_level"] = status_data.battery_level
            
            if status_data.signal_strength is not None:
                update_fields.append("signal_strength = :signal_strength")
                params["signal_strength"] = status_data.signal_strength
                
            if status_data.location:
                update_fields.append("location = :location")
                params["location"] = status_data.location
            
            query = f"""
                UPDATE devices
                SET {", ".join(update_fields)}
                WHERE device_id = :device_id
                RETURNING id, device_id, name, device_type, status, location, mac_address,
                         ip_address, capabilities, configuration, firmware_version,
                         device_token, api_key, last_seen, last_heartbeat, battery_level,
                         signal_strength, created_at, updated_at, is_active
            """
            
            result = await database.fetch_one(query, params)
            
            if result:
                return DeviceResponse(**dict(result))
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating device status: {e}")
            raise
    
    @staticmethod
    async def deactivate_device(device_id: str, deactivated_by: str) -> bool:
        """Deactivate a device (soft delete)"""
        try:
            query = """
                UPDATE devices
                SET is_active = false, status = 'offline', updated_at = NOW()
                WHERE device_id = :device_id
            """
            
            await database.execute(query, {"device_id": device_id})
            
            # Log deactivation
            await DeviceProvisioningService._log_device_action(
                device_id, "deactivated", deactivated_by
            )
            
            logger.info(f"Deactivated device: {device_id} by {deactivated_by}")
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating device: {e}")
            return False
    
    @staticmethod
    def _get_default_capabilities(device_type: str) -> Dict[str, Any]:
        """Get default capabilities based on device type"""
        capabilities_map = {
            'watch': {"vitals": True, "location": True, "battery": True, "fall_detection": True},
            'vital_monitor': {"ecg": True, "vitals": True, "alarms": True, "display": True},
            'door_scanner': {"nfc": True, "rfid": True, "access_control": True, "logging": True},
            'bed_sensor': {"pressure": True, "movement": True, "presence": True},
            'iv_pump': {"infusion": True, "alarms": True, "dosage_control": True},
            'ventilator': {"breathing_support": True, "pressure_control": True, "alarms": True},
            'ecg_monitor': {"ecg": True, "heart_rate": True, "arrhythmia_detection": True},
            'pulse_oximeter': {"oxygen_saturation": True, "pulse_rate": True, "perfusion": True},
            'blood_pressure_monitor': {"blood_pressure": True, "pulse": True, "cuff_control": True},
            'temperature_sensor': {"temperature": True, "ambient": True, "alerts": True},
            'camera': {"video": True, "audio": True, "recording": True, "streaming": True},
            'access_control': {"card_reader": True, "biometric": True, "logging": True},
            'emergency_button': {"panic": True, "location": True, "audio": True},
            'tablet': {"display": True, "touch": True, "wifi": True, "apps": True},
            'smartphone': {"calls": True, "data": True, "gps": True, "apps": True}
        }
        return capabilities_map.get(device_type, {})
    
    @staticmethod
    def _get_default_config(device_type: str) -> Dict[str, Any]:
        """Get default configuration based on device type"""
        config_map = {
            'watch': {"sampling_rate": 1, "battery_alert": 20, "sync_interval": 300},
            'vital_monitor': {"refresh_rate": 2, "alarm_volume": 80, "display_brightness": 75},
            'door_scanner': {"timeout": 30, "retry_attempts": 3, "log_level": "info"},
            'bed_sensor': {"sensitivity": 50, "movement_threshold": 10, "reporting_interval": 60},
            'iv_pump': {"max_rate": 999, "pressure_limit": 15, "alarm_delay": 5},
            'ventilator': {"tidal_volume": 500, "respiratory_rate": 12, "peep": 5},
            'ecg_monitor': {"lead_count": 12, "sampling_frequency": 250, "filter_mode": "adaptive"},
            'pulse_oximeter': {"averaging_time": 8, "sensitivity": "normal", "alarm_limits": {"spo2": 90}},
            'blood_pressure_monitor': {"cuff_pressure": 180, "measurement_interval": 300, "units": "mmHg"},
            'temperature_sensor': {"units": "celsius", "precision": 0.1, "calibration_offset": 0},
            'camera': {"resolution": "1080p", "fps": 30, "compression": "h264", "storage_days": 7},
            'access_control': {"max_attempts": 3, "lockout_duration": 300, "audit_enabled": True},
            'emergency_button': {"response_timeout": 30, "escalation_levels": 3, "location_accuracy": "high"},
            'tablet': {"screen_timeout": 300, "auto_update": True, "kiosk_mode": False},
            'smartphone': {"data_limit": 1000, "roaming": False, "hotspot": False}
        }
        return config_map.get(device_type, {})
    
    @staticmethod
    async def _log_device_action(device_id: str, action: str, performed_by: str, metadata: Dict[str, Any] = None):
        """Log device provisioning/management actions"""
        try:
            query = """
                INSERT INTO audit_logs (id, user_id, user_role, action, entity_type, entity_id, changes, device_info)
                VALUES (:id, :user_id, 'Provisioner', :action, 'device', :entity_id, :changes, 'Device Management System')
            """
            
            await database.execute(
                query,
                {
                    "id": str(uuid.uuid4()),
                    "user_id": performed_by,
                    "action": f"DEVICE_{action.upper()}",
                    "entity_id": device_id,
                    "changes": metadata or {}
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log device action: {e}")
            # Don't fail the main operation if logging fails