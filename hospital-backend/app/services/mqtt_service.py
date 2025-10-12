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
    
from ..core.database import getDbConnection, getTimescaleConnection
from .websocket_manager import connectionManager

logger = logging.getLogger(__name__)

class MQTTService:
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.config = {
            'host': '127.0.0.1',  # MQTT broker host
            'port': 1883,
            'username': 'hospitalEsp32',
            'password': 'esp32Secure',
            'keepalive': 60,
            'clientId': 'hospitalBackend'
        }
        self.subscribedTopics = set()
        self.messageHandlers: Dict[str, Callable] = {}
        self.isRunning = False

    async def start(self, config: Dict[str, Any] = None) -> bool:
        """Start MQTT service and connect to broker"""
        if not MQTT_AVAILABLE:
            logger.warning("🚫 MQTT not available - install paho-mqtt: pip install paho-mqtt")
            return False

        if config:
            self.config.update(config)

        try:
            # Create MQTT client
            self.client = mqtt.Client(client_id=self.config["clientId"])
            
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
            self.isRunning = True

            # Wait for connection (up to 10 seconds with timeout)
            try:
                await asyncio.wait_for(self._wait_for_connection(), timeout=10.0)
                await self._setupHospitalSubscriptions()
                logger.info("✅ MQTT service started successfully")
                return True
            except asyncio.TimeoutError:
                logger.error("❌ MQTT connection timeout after 10 seconds")
                return False

        except Exception as e:
            logger.error(f"❌ MQTT startup failed: {e}")
            return False

    async def _wait_for_connection(self):
        """Wait for MQTT connection to be established"""
        while not self.connected:
            await asyncio.sleep(0.1)

    async def stop(self):
        """Stop MQTT service"""
        self.isRunning = False
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            
        logger.info("🛑 MQTT service stopped")

    async def _setupHospitalSubscriptions(self):
        """Subscribe to hospital device topics"""
        hospitalTopics = [
            "hospital/devices/+/vitals",     # All device vitals
            "hospital/devices/+/heartbeat",  # All device heartbeats
            "hospital/devices/+/alerts",     # All device alerts
            "hospital/devices/+/status",     # All device status
            "hospital/system/+",             # System messages
        ]

        for topic in hospitalTopics:
            await self._subscribeTopic(topic)

    async def _subscribeTopic(self, topic: str):
        """Subscribe to MQTT topic"""
        if self.client and self.connected:
            result, mid = self.client.subscribe(topic)
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.subscribedTopics.add(topic)
                logger.info(f"📡 Subscribed to: {topic}")
            else:
                logger.error(f"❌ Failed to subscribe to: {topic}")

    async def publishCommand(self, deviceId: str, command: Dict[str, Any]) -> bool:
        """Send command to specific ESP32 device"""
        if not self.client or not self.connected:
            logger.warning("⚠️ MQTT not connected - cannot send command")
            return False

        topic = f"hospital/devices/{deviceId}/commands"
        payload = json.dumps(command)

        try:
            result = self.client.publish(topic, payload, qos=1)  # QoS 1 for reliability
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📤 Command sent to {deviceId}: {command}")
                return True
            else:
                logger.error(f"❌ Failed to send command to {deviceId}")
                return False
        except Exception as e:
            logger.error(f"❌ MQTT publish error: {e}")
            return False

    async def assignPatientToDevice(self, deviceId: str, patientId: str) -> bool:
        """Assign patient to ESP32 watch via MQTT"""
        command = {
            "command": "assignPatient",
            "patientId": patientId,
            "timestamp": datetime.now().isoformat()
        }
        return await self.publishCommand(deviceId, command)

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.connected = True
            logger.info("✅ MQTT broker connected")
        else:
            self.connected = False
            errorMessages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            logger.error(f"❌ MQTT connection failed: {errorMessages.get(rc, f'Unknown error {rc}')}")

    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.connected = False
        if rc == 0:
            logger.info("📡 MQTT disconnected (clean)")
        else:
            logger.warning(f"⚠️ MQTT disconnected unexpectedly (rc={rc})")

    def _on_subscribe(self, client, userdata, mid, grantedQos):
        """MQTT subscription callback"""
        logger.debug(f"📡 MQTT subscription confirmed (mid={mid}, qos={grantedQos})")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.debug(f"📨 MQTT message: {topic} -> {payload}")
            
            # Route message to appropriate handler
            asyncio.create_task(self._routeMessage(topic, payload))
            
        except Exception as e:
            logger.error(f"❌ MQTT message processing error: {e}")

    async def _routeMessage(self, topic: str, payload: Dict[str, Any]):
        """Route MQTT messages to appropriate handlers"""
        try:
            topicParts = topic.split('/')
            
            if len(topicParts) >= 4 and topicParts[0] == 'hospital' and topicParts[1] == 'devices':
                deviceId = topicParts[2]
                messageType = topicParts[3]
                
                if messageType == 'vitals':
                    await self._handleVitalsMessage(deviceId, payload)
                elif messageType == 'heartbeat':
                    await self._handleHeartbeatMessage(deviceId, payload)
                elif messageType == 'alerts':
                    await self._handleAlertMessage(deviceId, payload)
                elif messageType == 'status':
                    await self._handleStatusMessage(deviceId, payload)
                    
        except Exception as e:
            logger.error(f"❌ Message routing error: {e}")

    async def _handleVitalsMessage(self, deviceId: str, payload: Dict[str, Any]):
        """Handle vitals data from ESP32 watch"""
        try:
            patientId = payload.get('patientId')
            if not patientId:
                logger.warning(f"⚠️ Vitals from {deviceId} without patient assignment")
                return

            # Validate device assignment
            async with getDbConnection() as conn:
                patient = await conn.fetchrow(
                    "SELECT id, \"assignedDeviceId\" FROM patients WHERE id = $1",
                    patientId
                )
                
                if not patient or patient['assignedDeviceId'] != deviceId:
                    logger.warning(f"⚠️ Device {deviceId} not assigned to patient {patientId}")
                    return

            # Store vitals in TimescaleDB
            vitalsData = payload.get('vitals', {})
            await self._storeVitalsInTimescale(deviceId, patientId, vitalsData)

            # Update device last seen
            async with getDbConnection() as conn:
                await conn.execute(
                    'UPDATE devices SET "lastSeen" = NOW(), "batteryLevel" = $2 WHERE id = $1',
                    deviceId, payload.get('battery', 100)
                )

            # Convert MQTT format to frontend format and broadcast via WebSocket
            frontendVitals = self._convertMqttToFrontendFormat(vitalsData)
            await connectionManager.sendVitalsUpdate(patientId, deviceId, frontendVitals)

            logger.info(f"📊 MQTT Vitals processed for patient {patientId} from device {deviceId}")

        except Exception as e:
            logger.error(f"❌ Vitals processing error: {e}")

    async def _handleHeartbeatMessage(self, deviceId: str, payload: Dict[str, Any]):
        """Handle heartbeat from ESP32 watch"""
        try:
            # Update device status in database
            async with getDbConnection() as conn:
                await conn.execute("""
                    UPDATE devices
                    SET "lastSeen" = NOW(), "batteryLevel" = $2, status = 'active'
                    WHERE id = $1
                """, deviceId, payload.get('battery', 100))

            logger.debug(f"💓 MQTT Heartbeat from {deviceId}: Battery {payload.get('battery')}%")

        except Exception as e:
            logger.error(f"❌ Heartbeat processing error: {e}")

    async def _handleAlertMessage(self, deviceId: str, payload: Dict[str, Any]):
        """Handle emergency alert from ESP32 watch"""
        try:
            patientId = payload.get('patientId')
            severity = payload.get('severity', 'high')
            message = payload.get('message', 'Device emergency alert')

            # Broadcast alert via WebSocket
            alertPayload = {
                'severity': severity,
                'message': message,
                'source': f'Device {deviceId} (MQTT)',
                'deviceId': deviceId
            }

            await connectionManager.sendAlert(patientId, alertPayload)
            logger.warning(f"🚨 MQTT Emergency alert from {deviceId}: {message}")

        except Exception as e:
            logger.error(f"❌ Alert processing error: {e}")

    async def _handleStatusMessage(self, deviceId: str, payload: Dict[str, Any]):
        """Handle status update from ESP32 watch"""
        logger.info(f"📋 MQTT Status from {deviceId}: {payload.get('event', 'unknown')}")

    async def _storeVitalsInTimescale(self, deviceId: str, patientId: str, vitals: Dict[str, Any]):
        """Store vitals data in TimescaleDB"""
        try:
            async with getTimescaleConnection() as tsConn:
                timestamp = datetime.now()
                
                # Map MQTT vitals format to TimescaleDB format (ESP32 sends full names)
                vitalMappings = {
                    'heartrate': ('heartrate', 'bpm'),
                    'temperature': ('temperature', 'F'),
                    'oxygensat': ('oxygensaturation', '%'),
                    'respiratoryrate': ('respiratoryrate', '/min'),
                    'bloodpressurevalue': ('bloodpressuresystolic', 'mmHg'),
                    'ecg': ('ecg', 'mV'),
                    'eeg': ('eeg', 'μV'),
                    'bioimpedance': ('bioimpedance', 'Ω'),
                    'tremor': ('tremor', 'scale')
                }
                
                for mqttKey, (vitalType, unit) in vitalMappings.items():
                    value = vitals.get(mqttKey)
                    if value is not None:
                        await tsConn.execute("""
                            INSERT INTO vitals_timeseries ("patientId", "deviceId", "vitalType", value, unit, time, quality)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """, patientId, deviceId, vitalType, float(value), unit, timestamp, 95)

        except Exception as e:
            logger.warning(f"⚠️ TimescaleDB storage failed: {e}")

    def _convertMqttToFrontendFormat(self, mqttVitals: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MQTT vitals format to frontend format"""
        return {
            'heartrate': mqttVitals.get('heartrate'),
            'bloodpressure': mqttVitals.get('bloodpressure'),
            'bloodpressurevalue': mqttVitals.get('bloodpressurevalue'),
            'respiratoryrate': mqttVitals.get('respiratoryrate'),
            'oxygensat': mqttVitals.get('oxygensat'),
            'temperature': mqttVitals.get('temperature'),
            'ecg': mqttVitals.get('ecg'),
            'eeg': mqttVitals.get('eeg'),
            'bioimpedance': mqttVitals.get('bioimpedance'),
            'tremor': mqttVitals.get('tremor'),
            'lastUpdated': datetime.now().isoformat(),
            'lastSync': datetime.now().isoformat()
        }

    def getStatus(self) -> Dict[str, Any]:
        """Get MQTT service status"""
        return {
            'connected': self.connected,
            'running': self.isRunning,
            'broker': f"{self.config['host']}:{self.config['port']}",
            'subscribedTopics': list(self.subscribedTopics),
            'available': MQTT_AVAILABLE
        }

# Global MQTT service instance
mqttService = MQTTService()