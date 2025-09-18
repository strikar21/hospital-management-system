"""
MQTT Service for ESP32 Hospital Watches
Handles direct ESP32 → MQTT → Backend communication when no display is nearby
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Callable, Optional
import ssl

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    
from ..core.database import get_db_connection, get_timescale_connection
from .websocket_manager import connection_manager

logger = logging.getLogger(__name__)

class MQTTService:
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.config = {
            'host': '127.0.0.1',  # MQTT broker host
            'port': 1883,
            'username': 'hospital_esp32',
            'password': 'esp32_secure',
            'keepalive': 60,
            'client_id': 'hospital_backend'
        }
        self.subscribed_topics = set()
        self.message_handlers: Dict[str, Callable] = {}
        self.is_running = False

    async def start(self, config: Dict[str, Any] = None) -> bool:
        """Start MQTT service and connect to broker"""
        if not MQTT_AVAILABLE:
            logger.warning("🚫 MQTT not available - install paho-mqtt: pip install paho-mqtt")
            return False

        if config:
            self.config.update(config)

        try:
            # Create MQTT client
            self.client = mqtt.Client(client_id=self.config['client_id'])
            
            # Set credentials
            if self.config.get('username') and self.config.get('password'):
                self.client.username_pw_set(
                    self.config['username'], 
                    self.config['password']
                )

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_subscribe = self._on_subscribe

            # Configure TLS if needed
            if self.config.get('use_tls'):
                self.client.tls_set(ca_certs=None, certfile=None, keyfile=None, 
                                  cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS,
                                  ciphers=None)

            # Connect to broker
            logger.info(f"📡 Connecting to MQTT broker: {self.config['host']}:{self.config['port']}")
            self.client.connect(
                self.config['host'],
                self.config['port'],
                self.config['keepalive']
            )

            # Start network loop in background
            self.client.loop_start()
            self.is_running = True

            # Wait for connection (up to 10 seconds)
            for _ in range(100):
                if self.connected:
                    break
                await asyncio.sleep(0.1)

            if self.connected:
                await self._setup_hospital_subscriptions()
                logger.info("✅ MQTT service started successfully")
                return True
            else:
                logger.error("❌ MQTT connection timeout")
                return False

        except Exception as e:
            logger.error(f"❌ MQTT startup failed: {e}")
            return False

    async def stop(self):
        """Stop MQTT service"""
        self.is_running = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            
        logger.info("🛑 MQTT service stopped")

    async def _setup_hospital_subscriptions(self):
        """Subscribe to hospital device topics"""
        hospital_topics = [
            "hospital/devices/+/vitals",     # All device vitals
            "hospital/devices/+/heartbeat",  # All device heartbeats
            "hospital/devices/+/alerts",     # All device alerts
            "hospital/devices/+/status",     # All device status
            "hospital/system/+",             # System messages
        ]

        for topic in hospital_topics:
            await self._subscribe_topic(topic)

    async def _subscribe_topic(self, topic: str):
        """Subscribe to MQTT topic"""
        if self.client and self.connected:
            result, mid = self.client.subscribe(topic)
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.subscribed_topics.add(topic)
                logger.info(f"📡 Subscribed to: {topic}")
            else:
                logger.error(f"❌ Failed to subscribe to: {topic}")

    async def publish_command(self, device_id: str, command: Dict[str, Any]) -> bool:
        """Send command to specific ESP32 device"""
        if not self.client or not self.connected:
            logger.warning("⚠️ MQTT not connected - cannot send command")
            return False

        topic = f"hospital/devices/{device_id}/commands"
        payload = json.dumps(command)

        try:
            result = self.client.publish(topic, payload, qos=1)  # QoS 1 for reliability
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📤 Command sent to {device_id}: {command}")
                return True
            else:
                logger.error(f"❌ Failed to send command to {device_id}")
                return False
        except Exception as e:
            logger.error(f"❌ MQTT publish error: {e}")
            return False

    async def assign_patient_to_device(self, device_id: str, patient_id: str) -> bool:
        """Assign patient to ESP32 watch via MQTT"""
        command = {
            "command": "assign_patient",
            "patient_id": patient_id,
            "timestamp": datetime.now().isoformat()
        }
        return await self.publish_command(device_id, command)

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.connected = True
            logger.info("✅ MQTT broker connected")
        else:
            self.connected = False
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            logger.error(f"❌ MQTT connection failed: {error_messages.get(rc, f'Unknown error {rc}')}")

    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.connected = False
        if rc == 0:
            logger.info("📡 MQTT disconnected (clean)")
        else:
            logger.warning(f"⚠️ MQTT disconnected unexpectedly (rc={rc})")

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """MQTT subscription callback"""
        logger.debug(f"📡 MQTT subscription confirmed (mid={mid}, qos={granted_qos})")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.debug(f"📨 MQTT message: {topic} -> {payload}")
            
            # Route message to appropriate handler
            asyncio.create_task(self._route_message(topic, payload))
            
        except Exception as e:
            logger.error(f"❌ MQTT message processing error: {e}")

    async def _route_message(self, topic: str, payload: Dict[str, Any]):
        """Route MQTT messages to appropriate handlers"""
        try:
            topic_parts = topic.split('/')
            
            if len(topic_parts) >= 4 and topic_parts[0] == 'hospital' and topic_parts[1] == 'devices':
                device_id = topic_parts[2]
                message_type = topic_parts[3]
                
                if message_type == 'vitals':
                    await self._handle_vitals_message(device_id, payload)
                elif message_type == 'heartbeat':
                    await self._handle_heartbeat_message(device_id, payload)
                elif message_type == 'alerts':
                    await self._handle_alert_message(device_id, payload)
                elif message_type == 'status':
                    await self._handle_status_message(device_id, payload)
                    
        except Exception as e:
            logger.error(f"❌ Message routing error: {e}")

    async def _handle_vitals_message(self, device_id: str, payload: Dict[str, Any]):
        """Handle vitals data from ESP32 watch"""
        try:
            patient_id = payload.get('patient_id')
            if not patient_id:
                logger.warning(f"⚠️ Vitals from {device_id} without patient assignment")
                return

            # Validate device assignment
            async with get_db_connection() as conn:
                patient = await conn.fetchrow(
                    "SELECT id, assignedDeviceId FROM patients WHERE id = $1",
                    patient_id
                )
                
                if not patient or patient['assigneddeviceid'] != device_id:
                    logger.warning(f"⚠️ Device {device_id} not assigned to patient {patient_id}")
                    return

            # Store vitals in TimescaleDB
            vitals_data = payload.get('vitals', {})
            await self._store_vitals_in_timescale(device_id, patient_id, vitals_data)

            # Update device last seen
            async with get_db_connection() as conn:
                await conn.execute(
                    "UPDATE devices SET lastSeen = NOW(), batteryLevel = $2 WHERE id = $1",
                    device_id, payload.get('battery', 100)
                )

            # Convert MQTT format to frontend format and broadcast via WebSocket
            frontend_vitals = self._convert_mqtt_to_frontend_format(vitals_data)
            await connection_manager.send_vitals_update(patient_id, device_id, frontend_vitals)

            logger.info(f"📊 MQTT Vitals processed for patient {patient_id} from device {device_id}")

        except Exception as e:
            logger.error(f"❌ Vitals processing error: {e}")

    async def _handle_heartbeat_message(self, device_id: str, payload: Dict[str, Any]):
        """Handle heartbeat from ESP32 watch"""
        try:
            # Update device status in database
            async with get_db_connection() as conn:
                await conn.execute("""
                    UPDATE devices 
                    SET lastSeen = NOW(), batteryLevel = $2, status = 'active'
                    WHERE id = $1
                """, device_id, payload.get('battery', 100))

            logger.debug(f"💓 MQTT Heartbeat from {device_id}: Battery {payload.get('battery')}%")

        except Exception as e:
            logger.error(f"❌ Heartbeat processing error: {e}")

    async def _handle_alert_message(self, device_id: str, payload: Dict[str, Any]):
        """Handle emergency alert from ESP32 watch"""
        try:
            patient_id = payload.get('patient_id')
            severity = payload.get('severity', 'high')
            message = payload.get('message', 'Device emergency alert')

            # Broadcast alert via WebSocket
            alert_payload = {
                'severity': severity,
                'message': message,
                'source': f'Device {device_id} (MQTT)',
                'deviceId': device_id
            }

            await connection_manager.send_alert(patient_id, alert_payload)
            logger.warning(f"🚨 MQTT Emergency alert from {device_id}: {message}")

        except Exception as e:
            logger.error(f"❌ Alert processing error: {e}")

    async def _handle_status_message(self, device_id: str, payload: Dict[str, Any]):
        """Handle status update from ESP32 watch"""
        logger.info(f"📋 MQTT Status from {device_id}: {payload.get('event', 'unknown')}")

    async def _store_vitals_in_timescale(self, device_id: str, patient_id: str, vitals: Dict[str, Any]):
        """Store vitals data in TimescaleDB"""
        try:
            async with get_timescale_connection() as ts_conn:
                timestamp = datetime.now()
                
                # Map MQTT vitals format to TimescaleDB format (ESP32 sends full names)
                vital_mappings = {
                    'heartRate': ('heartRate', 'bpm'),
                    'temperature': ('temperature', 'F'),
                    'oxygenSat': ('oxygenSaturation', '%'),
                    'respiratoryRate': ('respiratoryRate', '/min'),
                    'bloodPressureValue': ('bloodPressureSystolic', 'mmHg'),
                    'ecg': ('ecg', 'mV'),
                    'eeg': ('eeg', 'μV'),
                    'bioimpedance': ('bioimpedance', 'Ω'),
                    'tremor': ('tremor', 'scale')
                }
                
                for mqtt_key, (vital_type, unit) in vital_mappings.items():
                    value = vitals.get(mqtt_key)
                    if value is not None:
                        await ts_conn.execute("""
                            INSERT INTO vitals_timeseries (patientid, deviceid, vitaltype, value, unit, time, quality)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """, patient_id, device_id, vital_type, float(value), unit, timestamp, 95)

        except Exception as e:
            logger.warning(f"⚠️ TimescaleDB storage failed: {e}")

    def _convert_mqtt_to_frontend_format(self, mqtt_vitals: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MQTT vitals format to frontend format"""
        return {
            'heartRate': mqtt_vitals.get('heartRate'),
            'bloodPressure': mqtt_vitals.get('bloodPressure'),
            'bloodPressureValue': mqtt_vitals.get('bloodPressureValue'),
            'respiratoryRate': mqtt_vitals.get('respiratoryRate'),
            'oxygenSat': mqtt_vitals.get('oxygenSat'),
            'temperature': mqtt_vitals.get('temperature'),
            'ecg': mqtt_vitals.get('ecg'),
            'eeg': mqtt_vitals.get('eeg'),
            'bioimpedance': mqtt_vitals.get('bioimpedance'),
            'tremor': mqtt_vitals.get('tremor'),
            'lastUpdated': datetime.now().isoformat(),
            'lastSync': datetime.now().isoformat()
        }

    def get_status(self) -> Dict[str, Any]:
        """Get MQTT service status"""
        return {
            'connected': self.connected,
            'running': self.is_running,
            'broker': f"{self.config['host']}:{self.config['port']}",
            'subscribed_topics': list(self.subscribed_topics),
            'available': MQTT_AVAILABLE
        }

# Global MQTT service instance
mqtt_service = MQTTService()