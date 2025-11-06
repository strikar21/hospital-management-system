"""
MQTT Service for ESP32 Hospital Watches
Handles direct ESP32 → MQTT → Backend communication when no display is nearby
"""

import asyncio
import json
import logging
import time
import uuid
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
from ..models.neural_vitals import (
    VitalsRealtimeMessage,
    WaveformSnapshotMessage,
    NeuralEventMessage,
    VitalsRealtimeDB,
    WaveformSnapshotDB,
    NeuralEventDB
)
from .ecg_analysis_service import ecgAnalysisService
from .eeg_analysis_service import eegAnalysisService
from .alert_detection_service import completeAlertDetectionService as alertDetectionService

logger = logging.getLogger(__name__)

class MQTTService:
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False

        # Build relative paths to certificates
        import os
        base_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "mosquitto", "certs")
        ca_cert_path = os.path.join(base_path, "hospital_ca.crt")
        client_cert_path = os.path.join(base_path, "backend.crt")
        client_key_path = os.path.join(base_path, "backend.key")

        self.config = {
            'host': os.getenv('MQTT_HOST', '127.0.0.1'),  # MQTT broker host
            'port': int(os.getenv('MQTT_PORT', '8883')),  # TLS port
            'username': 'hospitalEsp32',
            'password': 'ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=',
            'keepalive': 60,
            'clientId': 'hospitalBackend',
            'use_tls': True,
            'ca_certs': ca_cert_path,  # Hospital CA certificate
            'certfile': client_cert_path,  # Backend client certificate
            'keyfile': client_key_path  # Backend client private key
        }
        self.subscribedTopics = set()
        self.messageHandlers: Dict[str, Callable] = {}
        self.isRunning = False
        self.deviceLastMessage: Dict[str, float] = {}  # Rate limiting tracker

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

            # Configure TLS with client certificate (mTLS)
            if self.config.get('use_tls'):
                self.client.tls_set(
                    ca_certs=self.config.get('ca_certs'),
                    certfile=self.config.get('certfile'),  # Backend client certificate
                    keyfile=self.config.get('keyfile'),    # Backend client private key
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLSv1_2,
                    ciphers=None
                )
                # Allow hostname mismatch for development (localhost vs 127.0.0.1)
                self.client.tls_insecure_set(True)

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

            # Store event loop for thread-safe async task scheduling from MQTT callbacks
            self.eventLoop = asyncio.get_running_loop()

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
            await asyncio.sleep(0.01)  # Reduced from 0.1s to 0.01s for lower latency

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
            "hospital/devices/+/vitals",     # Real-time vitals (1 sec updates)
            "hospital/devices/+/waveform",   # Waveform snapshots (10 sec updates)
            "hospital/devices/+/stream",     # Real-time waveform streaming (100ms packets, 10 msg/sec)
            "hospital/devices/+/event",      # Neural events (arrhythmia, seizure)
            "hospital/devices/+/heartbeat",  # Device heartbeats
            "hospital/devices/+/alerts",     # Legacy alerts
            "hospital/devices/+/status",     # Device status
            "hospital/system/+",             # System messages
            "hospital/provisioning/request", # Device provisioning requests (NEW)
        ]

        for topic in hospitalTopics:
            await self._subscribeTopic(topic)

    async def _subscribeTopic(self, topic: str):
        """Subscribe to MQTT topic"""
        if self.client and self.connected:
            result, mid = self.client.subscribe(topic, qos=1)  # QoS 1 for end-to-end reliability with ESP32
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.subscribedTopics.add(topic)
                logger.info(f"📡 Subscribed to: {topic} (QoS 1)")
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

    async def publishAssignment(self, deviceId: str, patientId: str) -> bool:
        """
        Send patient assignment notification to ESP32 watch via MQTT
        Uses /assign topic that ESP32 subscribes to
        """
        if not self.client or not self.connected:
            logger.warning("⚠️ MQTT not connected - cannot send assignment")
            return False

        topic = f"hospital/devices/{deviceId}/assign"
        payload = json.dumps({
            "patientId": patientId,
            "timestamp": datetime.now().isoformat()
        })

        try:
            result = self.client.publish(topic, payload, qos=1)  # QoS 1 for reliability
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📤 Assignment notification sent to {deviceId}: patient {patientId}")
                return True
            else:
                logger.error(f"❌ Failed to send assignment to {deviceId}")
                return False
        except Exception as e:
            logger.error(f"❌ MQTT publish error: {e}")
            return False

    async def publishDeassignment(self, deviceId: str) -> bool:
        """
        Send deassignment notification to ESP32 watch via MQTT
        Clears patient assignment and stops vitals transmission
        Uses /unassign topic that ESP32 will subscribe to
        """
        if not self.client or not self.connected:
            logger.warning("⚠️ MQTT not connected - cannot send deassignment")
            return False

        topic = f"hospital/devices/{deviceId}/unassign"
        payload = json.dumps({
            "command": "unassign",
            "timestamp": datetime.now().isoformat()
        })

        try:
            result = self.client.publish(topic, payload, qos=1)  # QoS 1 for reliability
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📤 Deassignment notification sent to {deviceId}")
                return True
            else:
                logger.error(f"❌ Failed to send deassignment to {deviceId}")
                return False
        except Exception as e:
            logger.error(f"❌ MQTT publish error: {e}")
            return False

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

            # Log ALL incoming messages at INFO level to diagnose waveform stream issue
            if '/stream' in topic:
                logger.info(f"📨 MQTT STREAM MESSAGE RECEIVED: {topic}")
                logger.info(f"   Payload keys: {list(payload.keys())}")
                logger.info(f"   Has ecgWaveform: {'ecgWaveform' in payload}")
                logger.info(f"   Has eegWaveform: {'eegWaveform' in payload}")
            else:
                logger.debug(f"📨 MQTT message: {topic} -> {payload}")

            # Schedule coroutine in main event loop (thread-safe from MQTT callback thread)
            asyncio.run_coroutine_threadsafe(
                self._routeMessage(topic, payload),
                self.eventLoop
            )

        except Exception as e:
            logger.error(f"❌ MQTT message processing error: {e}")

    async def _routeMessage(self, topic: str, payload: Dict[str, Any]):
        """Route MQTT messages to appropriate handlers with security validation"""
        try:
            topicParts = topic.split('/')

            # DEBUG: Log routing for stream messages
            if '/stream' in topic:
                logger.info(f"🔀 ROUTING stream message: topic={topic}, topicParts={topicParts}")

            # Handle provisioning requests (no authentication needed yet)
            if topic == 'hospital/provisioning/request':
                await self._handleProvisioningRequest(payload)
                return

            if len(topicParts) >= 4 and topicParts[0] == 'hospital' and topicParts[1] == 'devices':
                deviceId = topicParts[2]
                messageType = topicParts[3]

                # DEBUG: Log stream message routing
                if messageType == 'stream':
                    logger.info(f"🔀 Stream message identified: deviceId={deviceId}, messageType={messageType}")

                # ========================================
                # SECURITY VALIDATION LAYER
                # ========================================

                # Validate device exists and is active
                async with getDbConnection() as conn:
                    device = await conn.fetchrow(
                        'SELECT id, status FROM devices WHERE id = $1',
                        deviceId
                    )
                    if not device:
                        logger.warning(f"🚨 SECURITY: Message from unknown device {deviceId}")
                        return

                    # Allow messages from devices in normal operation (available or assigned to patients)
                    ALLOWED_STATUSES = ['available', 'assigned']
                    if device['status'] not in ALLOWED_STATUSES:
                        logger.warning(f"🚨 SECURITY: Message from {device['status']} device {deviceId}")
                        return

                    # DEBUG: Log security validation for stream messages
                    if messageType == 'stream':
                        logger.info(f"✅ Security validation passed for stream: deviceId={deviceId}, status={device['status']}")

                # Rate limiting: Max 1 message per second per device per topic (except 'stream' which sends 10/sec)
                if messageType != 'stream':  # Waveform streaming sends 10 msg/sec, skip rate limit
                    # DETECT OFFLINE QUEUE: If message timestamp is > 5 seconds old, it's from offline buffer
                    # ESP32 offline queue sends old messages in batch after reconnection
                    now = time.time()
                    messageTimestamp = payload.get('timestamp')

                    # Convert ISO timestamp to Unix epoch if needed
                    if messageTimestamp:
                        try:
                            from datetime import datetime
                            if isinstance(messageTimestamp, str):
                                messageTimestamp = datetime.fromisoformat(messageTimestamp.replace('Z', '+00:00')).timestamp()
                            elif isinstance(messageTimestamp, datetime):
                                messageTimestamp = messageTimestamp.timestamp()
                        except Exception:
                            messageTimestamp = now  # Fallback to current time if parsing fails
                    else:
                        messageTimestamp = now  # No timestamp = treat as real-time

                    messageAge = now - messageTimestamp

                    # Only rate-limit REAL-TIME messages (< 5 seconds old)
                    if messageAge < 5.0:  # Real-time message
                        rateLimitKey = f"{deviceId}:{messageType}"
                        lastMsg = self.deviceLastMessage.get(rateLimitKey, 0)

                        if (now - lastMsg) < 1.0:  # Less than 1 second
                            logger.warning(f"🚨 SECURITY: Rate limit exceeded for {deviceId}/{messageType}")
                            return

                        self.deviceLastMessage[rateLimitKey] = now
                    else:
                        # Offline queue message - accept without rate limiting
                        logger.info(f"📦 OFFLINE QUEUE: Accepting old message from {deviceId}/{messageType} (age: {messageAge:.1f}s)")

                # Validate data ranges for vitals
                if messageType == 'vitals':
                    if not self._validateVitalsRanges(payload):
                        logger.warning(f"🚨 SECURITY: Invalid vitals data from {deviceId}")
                        return

                # Route to handler
                if messageType == 'vitals':
                    await self._handleVitalsMessageNew(deviceId, payload)
                elif messageType == 'waveform':
                    await self._handleWaveformMessage(deviceId, payload)
                elif messageType == 'stream':
                    await self._handleWaveformStream(deviceId, payload)
                elif messageType == 'event':
                    await self._handleNeuralEventMessage(deviceId, payload)
                elif messageType == 'heartbeat':
                    await self._handleHeartbeatMessage(deviceId, payload)
                elif messageType == 'alerts':
                    await self._handleAlertMessage(deviceId, payload)
                elif messageType == 'status':
                    await self._handleStatusMessage(deviceId, payload)

        except Exception as e:
            logger.error(f"❌ Message routing error: {e}")

    def _validateVitalsRanges(self, payload: Dict[str, Any]) -> bool:
        """Validate vitals are within physiologically possible ranges"""
        try:
            hr = payload.get('heartRate', 0)
            spo2 = payload.get('oxygenSaturation', 0)
            temp = payload.get('skinTemperature', 0)
            rr = payload.get('respiratoryRate', 0)

            # Physiologically possible ranges
            if hr and not (20 <= hr <= 300):
                logger.warning(f"Invalid heart rate: {hr}")
                return False

            if spo2 and not (50 <= spo2 <= 100):
                logger.warning(f"Invalid SpO2: {spo2}")
                return False

            if temp and not (30.0 <= temp <= 45.0):
                logger.warning(f"Invalid temperature: {temp}°C (expected Celsius range: 30.0-45.0)")
                return False

            if rr and not (4 <= rr <= 60):
                logger.warning(f"Invalid respiratory rate: {rr}")
                return False

            return True
        except Exception as e:
            logger.error(f"Vitals validation error: {e}")
            return False

    async def _handleVitalsMessageNew(self, deviceId: str, payload: Dict[str, Any]):
        """Handle 8-channel vitals data from ESP32 watch"""
        try:
            # Parse and validate using Pydantic model
            try:
                vitalsMsg = VitalsRealtimeMessage(**payload)
            except Exception as e:
                logger.error(f"❌ Invalid vitals message from {deviceId}: {e}")
                return

            patientId = vitalsMsg.patientId

            # Validate device assignment
            async with getDbConnection() as conn:
                patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1", patientId)
                if not patient:
                    logger.warning(f"⚠️ Patient {patientId} not found")
                    return

                assignment = await conn.fetchrow(
                    'SELECT "deviceId" FROM deviceassignments WHERE "patientId" = $1 AND status = \'active\'',
                    patientId
                )
                if not assignment or assignment['deviceId'] != deviceId:
                    logger.warning(f"⚠️ Device {deviceId} not assigned to patient {patientId}")
                    return

            # Store in TimescaleDB vitals_realtime table
            await self._storeVitalsRealtime(vitalsMsg)

            # ========================================
            # STORE WAVEFORM DATA (if present in combined message)
            # ========================================
            # If ESP32 sent waveform data in the combined message, store it separately
            if (vitalsMsg.sampleRate and vitalsMsg.duration and
                (vitalsMsg.ecgWaveform or vitalsMsg.eegWaveform)):

                # Create a WaveformSnapshotMessage from the vitals message
                waveformData = {
                    'deviceId': vitalsMsg.deviceId,
                    'patientId': vitalsMsg.patientId,
                    'timestamp': vitalsMsg.timestamp,
                    'mode': vitalsMsg.mode,
                    'sampleRate': vitalsMsg.sampleRate,
                    'duration': vitalsMsg.duration,
                    'compression': vitalsMsg.compression,
                    'quality': vitalsMsg.quality.dict() if vitalsMsg.quality else None,
                    'sequence': vitalsMsg.sequence,
                    'metadata': vitalsMsg.metadata
                }

                if vitalsMsg.mode == 'ecg' and vitalsMsg.ecgWaveform:
                    waveformData['ecgWaveform'] = vitalsMsg.ecgWaveform.dict()
                elif vitalsMsg.mode == 'eeg' and vitalsMsg.eegWaveform:
                    waveformData['eegWaveform'] = vitalsMsg.eegWaveform.dict()

                try:
                    waveformMsg = WaveformSnapshotMessage(**waveformData)
                    await self._storeWaveformSnapshot(waveformMsg)

                    # ========================================
                    # BACKEND ECG/EEG ANALYSIS ON WAVEFORM
                    # ========================================
                    # Run backend analysis on the waveform data
                    analysisResult = None

                    if waveformMsg.mode == 'ecg' and waveformMsg.ecgWaveform:
                        logger.info(f"🧠 Running ECG analysis for patient {patientId}...")
                        analysisResult = ecgAnalysisService.analyzeECG(waveformMsg.ecgWaveform.dict(), mode='ecg')

                        if analysisResult and analysisResult.confidence and analysisResult.confidence > 0.5:
                            logger.info(f"✅ ECG Analysis: HR={analysisResult.heartRate} BPM, "
                                      f"Rhythm={analysisResult.rhythm}")

                    elif waveformMsg.mode == 'eeg' and waveformMsg.eegWaveform:
                        logger.info(f"🧠 Running EEG analysis for patient {patientId}...")
                        analysisResult = eegAnalysisService.analyzeEEG(waveformMsg.eegWaveform.dict(), mode='eeg')

                        if analysisResult and analysisResult.confidence and analysisResult.confidence > 0.5:
                            logger.info(f"✅ EEG Analysis: Alpha={analysisResult.alphaPower:.1f} μV²")

                            # Critical: Seizure detection
                            if analysisResult.seizureActivity and analysisResult.seizureConfidence and analysisResult.seizureConfidence > 0.7:
                                await self._createSeizureAlert(patientId, deviceId, analysisResult)

                    logger.debug(f"📈 Waveform stored from combined message (1-sec snapshot)")

                except Exception as e:
                    logger.warning(f"⚠️ Could not process waveform data from combined message: {e}")

            # Update PostgreSQL patients table with latest vitals (for quick access)
            await self._updatePatientLatestVitals(vitalsMsg)

            # Update device last seen
            async with getDbConnection() as conn:
                await conn.execute(
                    'UPDATE devices SET "lastSeen" = NOW(), "batteryLevel" = $2 WHERE id = $1',
                    deviceId, vitalsMsg.batteryLevel or 100
                )

            # ========================================
            # STORE IMPEDANCE READINGS (Component 3)
            # ========================================
            # If impedance data is present, store it for electrode quality tracking
            if vitalsMsg.signalQuality is not None:
                try:
                    # Calculate approximate impedance from signal quality (inverse relationship)
                    # Signal quality 0.0-1.0 maps to impedance 10-1 kOhm
                    approximateImpedance = 10.0 - (vitalsMsg.signalQuality * 9.0)

                    async with getDbConnection() as conn:
                        await conn.execute("""
                            INSERT INTO impedanceReadings (patientId, deviceId, impedance, timestamp)
                            VALUES ($1, $2, $3, NOW())
                        """, patientId, deviceId, approximateImpedance)

                    logger.debug(f"💾 Impedance reading stored: {approximateImpedance:.2f} kΩ (from signal quality)")
                except Exception as e:
                    logger.debug(f"Could not store impedance reading: {e}")

            # ========================================
            # ALERT DETECTION (Complete System - Components 1 & 3)
            # ========================================
            # Detect alerts from vitals data
            vitalsDict = {
                'heartRate': vitalsMsg.heartRate,
                'oxygenSaturation': vitalsMsg.oxygenSaturation,
                'respiratoryRate': vitalsMsg.respiratoryRate,
                'temperature': vitalsMsg.skinTemperature,
                'batteryLevel': vitalsMsg.batteryLevel,
                'signalQuality': vitalsMsg.signalQuality,
                'impedance': approximateImpedance if vitalsMsg.signalQuality is not None else None
            }

            alerts = await alertDetectionService.detectAlerts(vitalsDict, patientId, deviceId)

            # Store alerts in database and broadcast via WebSocket
            async with getDbConnection() as conn:
                for alert in alerts:
                    # Generate unique alert ID
                    alert_id = str(uuid.uuid4())

                    # Store alert in patient_alerts table
                    await conn.execute('''
                        INSERT INTO patient_alerts
                        (id, "patientId", "deviceId", type, severity, message, source, "alertTimestamp", status, "createdAt", "updatedAt")
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active', NOW(), NOW())
                    ''', alert_id, patientId, deviceId, alert.alertType, alert.severity, alert.message, alert.source, datetime.now())

                    # Broadcast with ID for frontend acknowledgment tracking
                    alertPayload = alertDetectionService.createAlertPayload(alert)
                    alertPayload['id'] = alert_id
                    await connectionManager.sendAlert(patientId, alertPayload)

                    logger.debug(f"Alert stored: {alert.alertType} (ID: {alert_id}) for patient {patientId}")

            # Broadcast to frontend via WebSocket
            frontendVitals = self._convertVitalsToFrontendFormat(vitalsMsg)
            await connectionManager.sendVitalsUpdate(patientId, deviceId, frontendVitals)

            logger.info(f"📊 8CH Vitals processed for patient {patientId} from device {deviceId} (mode: {vitalsMsg.mode})")

        except Exception as e:
            logger.error(f"❌ Vitals processing error: {e}", exc_info=True)

    async def _handleWaveformMessage(self, deviceId: str, payload: Dict[str, Any]):
        """Handle 8-channel waveform snapshot from ESP32 watch with automatic analysis"""
        try:
            # Parse and validate using Pydantic model
            try:
                waveformMsg = WaveformSnapshotMessage(**payload)
            except Exception as e:
                logger.error(f"❌ Invalid waveform message from {deviceId}: {e}")
                return

            patientId = waveformMsg.patientId

            # Validate device assignment
            async with getDbConnection() as conn:
                assignment = await conn.fetchrow(
                    'SELECT "deviceId" FROM deviceassignments WHERE "patientId" = $1 AND status = \'active\'',
                    patientId
                )
                if not assignment or assignment['deviceId'] != deviceId:
                    logger.warning(f"⚠️ Device {deviceId} not assigned to patient {patientId}")
                    return

            # ========================================
            # BACKEND ECG/EEG ANALYSIS
            # ========================================
            # If ESP32 didn't send analysis, backend calculates it
            analysisResult = None

            if waveformMsg.mode == 'ecg' and waveformMsg.ecgWaveform:
                # Extract waveform data for analysis
                waveformData = waveformMsg.ecgWaveform.dict()

                # Run ECG analysis service
                logger.info(f"🧠 Running ECG analysis for patient {patientId}...")
                analysisResult = ecgAnalysisService.analyzeECG(waveformData, mode='ecg')

                if analysisResult and analysisResult.confidence and analysisResult.confidence > 0.5:
                    logger.info(f"✅ ECG Analysis: HR={analysisResult.heartRate} BPM, "
                              f"Rhythm={analysisResult.rhythm}, "
                              f"QRS={analysisResult.qrsDuration}ms, "
                              f"Confidence={analysisResult.confidence:.2f}")

                    # Store analysis results in vitals_realtime for trend tracking
                    await self._storeAnalysisAsVitals(patientId, deviceId, analysisResult, 'ecg')
                else:
                    logger.warning(f"⚠️ ECG analysis low confidence or failed")

            elif waveformMsg.mode == 'eeg' and waveformMsg.eegWaveform:
                # Extract waveform data for analysis
                waveformData = waveformMsg.eegWaveform.dict()

                # Run EEG analysis service
                logger.info(f"🧠 Running EEG analysis for patient {patientId}...")
                analysisResult = eegAnalysisService.analyzeEEG(waveformData, mode='eeg')

                if analysisResult and analysisResult.confidence and analysisResult.confidence > 0.5:
                    logger.info(f"✅ EEG Analysis: Alpha={analysisResult.alphaPower:.1f} μV², "
                              f"Seizure={'YES' if analysisResult.seizureActivity else 'NO'}, "
                              f"Confidence={analysisResult.confidence:.2f}")

                    # Store analysis results in vitals_realtime for trend tracking
                    await self._storeAnalysisAsVitals(patientId, deviceId, analysisResult, 'eeg')

                    # If seizure detected, create critical alert
                    if analysisResult.seizureActivity and analysisResult.seizureConfidence and analysisResult.seizureConfidence > 0.7:
                        await self._createSeizureAlert(patientId, deviceId, analysisResult)
                else:
                    logger.warning(f"⚠️ EEG analysis low confidence or failed")

            # Store in TimescaleDB waveform_snapshots table
            await self._storeWaveformSnapshot(waveformMsg)

            logger.info(f"📈 Waveform snapshot stored for patient {patientId} (mode: {waveformMsg.mode}, {waveformMsg.sampleRate}Hz, {waveformMsg.duration}s)")

        except Exception as e:
            logger.error(f"❌ Waveform processing error: {e}", exc_info=True)

    async def _handleWaveformStream(self, deviceId: str, payload: Dict[str, Any]):
        """
        Handle real-time waveform streaming packets (100ms batches, 10 msg/sec)
        MQTT Topic: hospital/devices/{deviceId}/stream

        This is EPHEMERAL streaming - NOT stored in database, only broadcast to WebSocket
        """
        try:
            # Basic validation
            if not all(k in payload for k in ['deviceId', 'patientId', 'timestamp', 'mode']):
                logger.warning(f"⚠️ Incomplete waveform stream message from {deviceId}")
                return

            # Must have waveform data (either ECG or EEG)
            if 'ecgWaveform' not in payload and 'eegWaveform' not in payload:
                logger.warning(f"⚠️ Waveform stream from {deviceId} missing waveform data")
                return

            patientId = payload.get('patientId')

            # Validate device assignment
            async with getDbConnection() as conn:
                assignment = await conn.fetchrow(
                    'SELECT "deviceId" FROM deviceassignments WHERE "patientId" = $1 AND status = \'active\'',
                    patientId
                )
                if not assignment or assignment['deviceId'] != deviceId:
                    logger.warning(f"⚠️ Waveform stream from unassigned device {deviceId}")
                    return

            # Broadcast to WebSocket subscribers (ephemeral - NOT stored)
            await connectionManager.sendWaveformStream(
                patientId=patientId,
                deviceId=deviceId,
                waveformData=payload
            )

            # ✅ NEW: Store stream packet to database for historical analysis
            try:
                # Prepare waveform data for storage
                # ESP32 stream format is compatible with WaveformSnapshotMessage schema
                # Set duration to 0.1 seconds (100ms packet = 0.1s)
                payload['duration'] = 0.1

                # Parse timestamp if needed
                if 'timestamp' in payload:
                    timestampStr = payload['timestamp']
                    if isinstance(timestampStr, str):
                        if timestampStr.endswith('Z'):
                            timestampStr = timestampStr.replace('Z', '+00:00')
                        payload['timestamp'] = datetime.fromisoformat(timestampStr)

                # Create WaveformSnapshotMessage and store using existing function
                waveformMsg = WaveformSnapshotMessage(**payload)
                await self._storeWaveformSnapshot(waveformMsg)

                # Log storage success (every 10th packet to avoid spam)
                sequence = payload.get('sequence', 0)
                if sequence % 10 == 0:
                    logger.debug(f"💾 Stream packet #{sequence} stored to database")

            except Exception as e:
                # Don't fail WebSocket broadcast if storage fails
                logger.error(f"Stream packet storage failed (non-critical): {e}", exc_info=True)

            # Stream packets logged at DEBUG level only

        except Exception as e:
            logger.error(f"❌ Waveform stream processing error: {e}", exc_info=True)

    async def _handleNeuralEventMessage(self, deviceId: str, payload: Dict[str, Any]):
        """Handle neural event (arrhythmia/seizure) from ESP32 watch"""
        try:
            # Parse and validate using Pydantic model
            try:
                eventMsg = NeuralEventMessage(**payload)
            except Exception as e:
                logger.error(f"❌ Invalid neural event message from {deviceId}: {e}")
                return

            patientId = eventMsg.patientId

            # Validate device assignment
            async with getDbConnection() as conn:
                assignment = await conn.fetchrow(
                    'SELECT "deviceId" FROM deviceassignments WHERE "patientId" = $1 AND status = \'active\'',
                    patientId
                )
                if not assignment or assignment['deviceId'] != deviceId:
                    logger.warning(f"⚠️ Device {deviceId} not assigned to patient {patientId}")
                    return

            # Store in TimescaleDB neural_events table
            await self._storeNeuralEvent(eventMsg)

            # Create alert in PostgreSQL alerts table (for staff notification)
            await self._createAlertForEvent(eventMsg)

            # Broadcast critical alert via WebSocket
            alertPayload = {
                'severity': eventMsg.severity,
                'message': f"{eventMsg.eventType.upper()} detected (confidence: {eventMsg.confidence:.0%})",
                'source': f'Device {deviceId} ({eventMsg.mode.upper()})',
                'deviceId': deviceId,
                'eventType': eventMsg.eventType,
                'confidence': eventMsg.confidence
            }
            await connectionManager.sendAlert(patientId, alertPayload)

            logger.warning(f"🚨 Neural event: {eventMsg.eventType} for patient {patientId} (severity: {eventMsg.severity}, confidence: {eventMsg.confidence:.0%})")

        except Exception as e:
            logger.error(f"❌ Neural event processing error: {e}", exc_info=True)

    async def _handleVitalsMessage(self, deviceId: str, payload: Dict[str, Any]):
        """Handle vitals data from ESP32 watch"""
        try:
            patientId = payload.get('patientId')
            if not patientId:
                logger.warning(f"⚠️ Vitals from {deviceId} without patient assignment")
                return

            # Validate device assignment via deviceassignments table
            async with getDbConnection() as conn:
                patient = await conn.fetchrow("SELECT id FROM patients WHERE id = $1", patientId)
                if not patient:
                    logger.warning(f"⚠️ Patient {patientId} not found")
                    return

                # Check device assignment via deviceassignments table
                assignment = await conn.fetchrow(
                    'SELECT "deviceId" FROM deviceassignments WHERE "patientId" = $1 AND status = \'active\'',
                    patientId
                )
                if not assignment or assignment['deviceId'] != deviceId:
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
        """Handle heartbeat from ESP32 watch via MQTT"""
        try:
            # Support both field names for backward compatibility
            batteryLevel = payload.get('batteryLevel', payload.get('battery', 100))
            signalStrength = payload.get('signalStrength', -50)

            # Update device status in database
            async with getDbConnection() as conn:
                await conn.execute("""
                    UPDATE devices
                    SET "lastSeen" = NOW(), "batteryLevel" = $2,
                        status = CASE WHEN status = 'offline' THEN 'available' ELSE status END,
                        "updatedAt" = NOW()
                    WHERE id = $1
                """, deviceId, batteryLevel)

            logger.info(f"💓 MQTT Heartbeat: {deviceId} Battery {batteryLevel}% Signal {signalStrength}dBm")

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

    # ============================================
    # MQTT PROVISIONING HANDLER (NEW)
    # ============================================

    async def _handleProvisioningRequest(self, payload: Dict[str, Any]):
        """
        Handle device provisioning request via MQTT
        This replaces HTTP provisioning for ESP32 devices
        """
        try:
            macAddress = payload.get('macAddress')
            deviceType = payload.get('deviceType', 'watch')
            firmwareVersion = payload.get('firmwareVersion', '4.2.0')
            provisionerId = payload.get('provisionerId')
            provisionerPassword = payload.get('provisionerPassword')

            logger.info(f"🔄 MQTT Provisioning request from MAC: {macAddress}")

            # Validate required fields
            if not macAddress or not provisionerId or not provisionerPassword:
                await self._publishProvisioningResponse(macAddress, {
                    "success": False,
                    "message": "MAC address and provisioner credentials required"
                })
                return

            async with getDbConnection() as conn:
                # Validate provisioner credentials
                import bcrypt
                provisioner = await conn.fetchrow(
                    "SELECT id, \"firstName\", \"lastName\", role, password FROM staff WHERE id = $1 AND role IN ('Provisioner', 'Technician')",
                    provisionerId
                )

                if not provisioner:
                    logger.warning(f"❌ Invalid provisioner ID or role: {provisionerId}")
                    await self._publishProvisioningResponse(macAddress, {
                        "success": False,
                        "message": "Invalid provisioner credentials or insufficient role"
                    })
                    return

                # Validate provisioner password
                passwordValid = bcrypt.checkpw(
                    provisionerPassword.encode('utf-8'),
                    provisioner['password'].encode('utf-8')
                )
                if not passwordValid:
                    logger.warning(f"❌ Invalid provisioner password for ID: {provisionerId}")
                    await self._publishProvisioningResponse(macAddress, {
                        "success": False,
                        "message": "Invalid provisioner credentials"
                    })
                    return

                # Check if device already exists (MAC address = hardware identity)
                existingDevice = await conn.fetchrow(
                    'SELECT id, "serialNumber", "deviceType" FROM devices WHERE "macAddress" = $1',
                    macAddress
                )

                if existingDevice:
                    # ========================================
                    # RE-PROVISIONING EXISTING DEVICE
                    # Device flash may have been erased, firmware upgraded, etc.
                    # Return SAME device ID to preserve patient assignments and history
                    # ========================================
                    deviceId = existingDevice['id']
                    serialNumber = existingDevice['serialNumber']

                    logger.warning(f"🔄 RE-PROVISIONING existing device: {deviceId} (MAC: {macAddress})")

                    # Generate NEW MQTT credentials (old ones may be lost/compromised)
                    mqttUsername = f"{deviceId}_mqtt"
                    mqttPassword = self._generateDevicePassword(deviceId)

                    # Update device record with new firmware version
                    await conn.execute('''
                        UPDATE devices
                        SET "firmwareVersion" = $1,
                            "updatedAt" = NOW(),
                            "lastSeen" = NOW()
                        WHERE id = $2
                    ''', firmwareVersion, deviceId)

                    # Log re-provisioning event for audit trail
                    from ..services.audit import logAuditEvent
                    await logAuditEvent(
                        conn, provisionerId, 'reprovisionDevice', 'device', deviceId,
                        f"Re-provisioned {deviceId} (MAC: {macAddress}, firmware: {firmwareVersion})"
                    )

                    provisionerName = f"{provisioner['firstName']} {provisioner['lastName']}"
                    logger.info(f"✅ Device {deviceId} re-provisioned with new credentials by {provisionerName}")

                    # Send response with EXISTING device info + NEW credentials
                    await self._publishProvisioningResponse(macAddress, {
                        "success": True,
                        "message": f"Device {deviceId} re-provisioned successfully",
                        "deviceId": deviceId,
                        "serialNumber": serialNumber,
                        "mqttUsername": mqttUsername,
                        "mqttPassword": mqttPassword,
                        "provisionedBy": provisionerName,
                        "status": "reprovisioned"  # Flag to indicate re-provisioning
                    })
                    return

                # Generate new device ID and serial number
                deviceCount = await conn.fetchval('SELECT COUNT(*) FROM devices WHERE "deviceType" = $1', deviceType)
                newDeviceNumber = deviceCount + 1

                deviceId = f"ESP32_WATCH_{newDeviceNumber:03d}"
                serialNumber = f"SN_W{newDeviceNumber:03d}"
                deviceName = f"ESP32 Watch #{newDeviceNumber:03d}"

                # Generate per-device MQTT credentials
                mqttUsername = f"{deviceId}_mqtt"
                mqttPassword = self._generateDevicePassword(deviceId)

                # Create new device record
                await conn.execute("""
                    INSERT INTO devices (id, "deviceType", name, "serialNumber", "macAddress",
                                       "firmwareVersion", "batteryLevel", status, location,
                                       "lastSeen", "createdAt", "updatedAt")
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW(), NOW())
                """, deviceId, deviceType, deviceName, serialNumber, macAddress,
                     firmwareVersion, 100, 'available', 'Device Pool')

                # Log provisioning action
                from ..services.audit import logAuditEvent
                await logAuditEvent(
                    conn, provisionerId, 'provisionDevice', 'device', deviceId,
                    f"Provisioned new {deviceType} with serial {serialNumber} via MQTT"
                )

                provisionerName = f"{provisioner['firstName']} {provisioner['lastName']}"
                logger.info(f"✅ New ESP32 device provisioned via MQTT: {deviceId} (Serial: {serialNumber}) by {provisionerName}")

                # Publish provisioning response with MQTT credentials
                await self._publishProvisioningResponse(macAddress, {
                    "success": True,
                    "message": "Device provisioned successfully",
                    "deviceId": deviceId,
                    "serialNumber": serialNumber,
                    "mqttUsername": mqttUsername,
                    "mqttPassword": mqttPassword,
                    "provisionedBy": provisionerName,
                    "status": "new"
                })

        except Exception as e:
            logger.error(f"❌ MQTT provisioning error: {e}")
            if 'macAddress' in locals():
                await self._publishProvisioningResponse(macAddress, {
                    "success": False,
                    "message": "Device provisioning failed"
                })

    async def _publishProvisioningResponse(self, macAddress: str, response: Dict[str, Any]):
        """Publish provisioning response to device-specific topic"""
        if not self.client or not self.connected:
            logger.error("⚠️ MQTT not connected - cannot send provisioning response")
            return

        topic = f"hospital/provisioning/response/{macAddress}"
        payload = json.dumps(response)

        try:
            result = self.client.publish(topic, payload, qos=1)  # QoS 1 for reliability
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📤 Provisioning response sent to {macAddress}")
            else:
                logger.error(f"❌ Failed to send provisioning response to {macAddress}")
        except Exception as e:
            logger.error(f"❌ MQTT publish error: {e}")

    def _generateDevicePassword(self, deviceId: str) -> str:
        """Generate unique MQTT password for device"""
        import hashlib
        import secrets

        # Use device ID + factory secret to generate deterministic password
        from ..core.config import settings
        secret = settings.esp32FactorySecret if hasattr(settings, 'esp32FactorySecret') else "hospital_default_secret"

        # Generate password: HMAC(deviceId, secret)
        password_bytes = f"{deviceId}:{secret}".encode('utf-8')
        hashed = hashlib.sha256(password_bytes).digest()

        # Convert to base64 for readability (URL-safe)
        import base64
        password = base64.urlsafe_b64encode(hashed[:24]).decode('utf-8')  # 24 bytes = 32 chars base64

        return password

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

    # ============================================
    # 8-CHANNEL ECG/EEG HELPER METHODS
    # ============================================

    async def _storeVitalsRealtime(self, vitalsMsg: VitalsRealtimeMessage):
        """Store vitals in TimescaleDB vitals_realtime table"""
        try:
            async with getTimescaleConnection() as tsConn:
                # Build nested ECG/EEG analysis JSON
                ecgAnalysisJson = None
                if vitalsMsg.ecgAnalysis:
                    ecgAnalysisJson = vitalsMsg.ecgAnalysis.dict()

                eegAnalysisJson = None
                if vitalsMsg.eegAnalysis:
                    eegAnalysisJson = vitalsMsg.eegAnalysis.dict()

                qualityJson = None
                if vitalsMsg.quality:
                    qualityJson = vitalsMsg.quality.dict()

                # Insert into vitals_realtime table
                await tsConn.execute("""
                    INSERT INTO vitals_realtime (
                        time, "patientId", "deviceId", mode,
                        "heartRate", "respiratoryRate", "skinTemperature",
                        "oxygenSaturation", "batteryLevel", "signalQuality",
                        "systolicPressure", "diastolicPressure",
                        "rrInterval", "qrsDuration", "qtInterval", axis, rhythm, "stSegment",
                        "alphaPower", "betaPower", "thetaPower", "deltaPower", "gammaPower",
                        "dominantFrequency", "seizureActivity",
                        tremor, bioimpedance, "imuFallRisk", "perfusionIndex", "stepCount", "watchWorn", "lastMovementTime",
                        quality, sequence, metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18,
                        $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35
                    )
                """,
                    vitalsMsg.timestamp, vitalsMsg.patientId, vitalsMsg.deviceId, vitalsMsg.mode,
                    vitalsMsg.heartRate, vitalsMsg.respiratoryRate, vitalsMsg.skinTemperature,
                    vitalsMsg.oxygenSaturation, vitalsMsg.batteryLevel, vitalsMsg.signalQuality,
                    vitalsMsg.bloodPressureSystolic, vitalsMsg.bloodPressureDiastolic,
                    vitalsMsg.ecgAnalysis.rrInterval if vitalsMsg.ecgAnalysis else None,
                    vitalsMsg.ecgAnalysis.qrsDuration if vitalsMsg.ecgAnalysis else None,
                    vitalsMsg.ecgAnalysis.qtInterval if vitalsMsg.ecgAnalysis else None,
                    vitalsMsg.ecgAnalysis.axis if vitalsMsg.ecgAnalysis else None,
                    vitalsMsg.ecgAnalysis.rhythm if vitalsMsg.ecgAnalysis else None,
                    vitalsMsg.ecgAnalysis.stSegment if vitalsMsg.ecgAnalysis else None,
                    vitalsMsg.eegAnalysis.bandPowers.alpha if vitalsMsg.eegAnalysis else None,
                    vitalsMsg.eegAnalysis.bandPowers.beta if vitalsMsg.eegAnalysis else None,
                    vitalsMsg.eegAnalysis.bandPowers.theta if vitalsMsg.eegAnalysis else None,
                    vitalsMsg.eegAnalysis.bandPowers.delta if vitalsMsg.eegAnalysis else None,
                    vitalsMsg.eegAnalysis.bandPowers.gamma if vitalsMsg.eegAnalysis else None,
                    vitalsMsg.eegAnalysis.dominantFrequency if vitalsMsg.eegAnalysis else None,
                    vitalsMsg.eegAnalysis.seizureActivity if vitalsMsg.eegAnalysis else None,
                    vitalsMsg.tremor,
                    vitalsMsg.bioimpedance,
                    vitalsMsg.imuFallRisk,
                    vitalsMsg.perfusionIndex,
                    vitalsMsg.stepCount,
                    vitalsMsg.watchWorn,
                    vitalsMsg.lastMovementTime,
                    json.dumps(qualityJson) if qualityJson else None,
                    vitalsMsg.sequence,
                    json.dumps(vitalsMsg.metadata) if vitalsMsg.metadata else None
                )
        except Exception as e:
            logger.error(f"❌ Failed to store vitals in TimescaleDB: {e}", exc_info=True)

    async def _updatePatientLatestVitals(self, vitalsMsg: VitalsRealtimeMessage):
        """Update PostgreSQL patients table with latest vitals (stub for now)"""
        # TODO: Update patients.vitals JSONB column with latest values
        # This allows quick access to current vitals without querying TimescaleDB
        pass

    def _convertVitalsToFrontendFormat(self, vitalsMsg: VitalsRealtimeMessage) -> Dict[str, Any]:
        """Convert VitalsRealtimeMessage to frontend format with all fields"""

        # Calculate fallRisk from imuFallRisk (0-10 scale → low/medium/high)
        fallRisk = 'low'
        if vitalsMsg.imuFallRisk is not None:
            if vitalsMsg.imuFallRisk > 6:
                fallRisk = 'high'
            elif vitalsMsg.imuFallRisk > 3:
                fallRisk = 'medium'

        result = {
            # Basic vitals - frontend field names
            'heartRate': vitalsMsg.heartRate,
            'respiratoryRate': vitalsMsg.respiratoryRate,
            'skinTemperature': vitalsMsg.skinTemperature,  # Celsius from backend
            'oxygenSaturation': vitalsMsg.oxygenSaturation,

            # Blood pressure - frontend field names
            'systolicPressure': vitalsMsg.bloodPressureSystolic,
            'diastolicPressure': vitalsMsg.bloodPressureDiastolic,

            # Advanced monitoring - frontend field names
            'bioelectricalImpedance': vitalsMsg.bioimpedance if vitalsMsg.bioimpedance is not None else 0,
            'tremorIntensity': vitalsMsg.tremor if vitalsMsg.tremor is not None else 0,
            'fallRisk': fallRisk,

            # ECG/EEG single readings - frontend field names
            'ecgReading': vitalsMsg.ecgReading if vitalsMsg.ecgReading is not None else 0,
            'eegReading': vitalsMsg.eegReading if vitalsMsg.eegReading is not None else 0,
            'isEcgMode': vitalsMsg.mode == 'ecg',

            # Device status
            'batteryLevel': vitalsMsg.batteryLevel,
            'signalQuality': vitalsMsg.signalQuality,
            'dataQualityScore': vitalsMsg.signalQuality,  # Alias for compatibility

            # Timestamps
            'lastDataReceived': vitalsMsg.timestamp.isoformat(),
            'lastUpdated': vitalsMsg.timestamp.isoformat(),
            'lastSync': datetime.now().isoformat(),
            'timestamp': vitalsMsg.timestamp.isoformat()
        }

        # Add nested ECG object if in ECG mode
        if vitalsMsg.mode == 'ecg' and vitalsMsg.ecgAnalysis:
            result['ecg'] = {
                'rrInterval': vitalsMsg.ecgAnalysis.rrInterval,
                'qrsDuration': vitalsMsg.ecgAnalysis.qrsDuration,
                'qtInterval': vitalsMsg.ecgAnalysis.qtInterval,
                'axis': vitalsMsg.ecgAnalysis.axis,
                'rhythm': vitalsMsg.ecgAnalysis.rhythm,
                'stSegment': vitalsMsg.ecgAnalysis.stSegment
            }

        # Add nested EEG object if in EEG mode
        if vitalsMsg.mode == 'eeg' and vitalsMsg.eegAnalysis:
            result['eeg'] = {
                'alphaPower': vitalsMsg.eegAnalysis.bandPowers.alpha,
                'betaPower': vitalsMsg.eegAnalysis.bandPowers.beta,
                'thetaPower': vitalsMsg.eegAnalysis.bandPowers.theta,
                'deltaPower': vitalsMsg.eegAnalysis.bandPowers.delta,
                'gammaPower': vitalsMsg.eegAnalysis.bandPowers.gamma,
                'dominantFrequency': vitalsMsg.eegAnalysis.dominantFrequency,
                'seizureActivity': vitalsMsg.eegAnalysis.seizureActivity
            }

        return result

    async def _storeWaveformSnapshot(self, waveformMsg: WaveformSnapshotMessage):
        """Store waveform snapshot in TimescaleDB waveform_snapshots table"""
        try:
            async with getTimescaleConnection() as tsConn:
                # Convert waveform data to JSON
                ecgLimbJson = None
                ecgPrecordialJson = None
                ecgDerivedJson = None
                ecgEventsJson = None
                eegFrontalJson = None
                eegCentralJson = None
                eegOccipitalJson = None
                eegAnalysisJson = None

                if waveformMsg.mode == 'ecg' and waveformMsg.ecgWaveform:
                    ecgLimbJson = json.dumps(waveformMsg.ecgWaveform.limb.dict())
                    if waveformMsg.ecgWaveform.precordial:
                        ecgPrecordialJson = json.dumps(waveformMsg.ecgWaveform.precordial.dict())
                    if waveformMsg.ecgWaveform.derived:
                        ecgDerivedJson = json.dumps(waveformMsg.ecgWaveform.derived.dict())
                    if waveformMsg.ecgWaveform.events:
                        ecgEventsJson = json.dumps([e.dict() for e in waveformMsg.ecgWaveform.events])

                if waveformMsg.mode == 'eeg' and waveformMsg.eegWaveform:
                    eegFrontalJson = json.dumps(waveformMsg.eegWaveform.frontal.dict())
                    eegCentralJson = json.dumps(waveformMsg.eegWaveform.central.dict())
                    eegOccipitalJson = json.dumps(waveformMsg.eegWaveform.occipital.dict())
                    if waveformMsg.eegWaveform.analysis:
                        eegAnalysisJson = json.dumps(waveformMsg.eegWaveform.analysis.dict())

                qualityJson = json.dumps(waveformMsg.quality.dict()) if waveformMsg.quality else None

                # Insert into waveform_snapshots table
                await tsConn.execute("""
                    INSERT INTO waveform_snapshots (
                        time, "patientId", "deviceId", mode, "sampleRate", duration,
                        "ecgLimbLeads", "ecgPrecordialLeads", "ecgDerivedLeads", "ecgEvents",
                        "eegFrontalChannels", "eegCentralChannels", "eegOccipitalChannels", "eegAnalysis",
                        quality, sequence, compression, metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
                    )
                """,
                    waveformMsg.timestamp, waveformMsg.patientId, waveformMsg.deviceId,
                    waveformMsg.mode, waveformMsg.sampleRate, waveformMsg.duration,
                    ecgLimbJson, ecgPrecordialJson, ecgDerivedJson, ecgEventsJson,
                    eegFrontalJson, eegCentralJson, eegOccipitalJson, eegAnalysisJson,
                    qualityJson, waveformMsg.sequence, waveformMsg.compression,
                    json.dumps(waveformMsg.metadata) if waveformMsg.metadata else None
                )
        except Exception as e:
            logger.error(f"❌ Failed to store waveform in TimescaleDB: {e}", exc_info=True)

    async def _storeNeuralEvent(self, eventMsg: NeuralEventMessage):
        """Store neural event in TimescaleDB neural_events table"""
        try:
            async with getTimescaleConnection() as tsConn:
                await tsConn.execute("""
                    INSERT INTO neural_events (
                        time, "patientId", "deviceId", "eventType", severity, confidence, mode,
                        "sampleRate", duration, context, waveform, actions, metadata
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
                    )
                """,
                    eventMsg.timestamp, eventMsg.patientId, eventMsg.deviceId,
                    eventMsg.eventType, eventMsg.severity, eventMsg.confidence, eventMsg.mode,
                    eventMsg.sampleRate, eventMsg.duration,
                    json.dumps(eventMsg.context) if eventMsg.context else None,
                    json.dumps(eventMsg.waveform) if eventMsg.waveform else None,
                    json.dumps(eventMsg.actions) if eventMsg.actions else None,
                    json.dumps(eventMsg.metadata) if eventMsg.metadata else None
                )
        except Exception as e:
            logger.error(f"❌ Failed to store neural event in TimescaleDB: {e}", exc_info=True)

    async def _createAlertForEvent(self, eventMsg: NeuralEventMessage):
        """Create alert in PostgreSQL alerts table (stub for now)"""
        # TODO: Insert into alerts table for staff notification
        # This creates a persistent alert that nurses/doctors can acknowledge
        pass

    async def _storeAnalysisAsVitals(self, patientId: str, deviceId: str, analysisResult: any, mode: str):
        """
        Store ECG/EEG analysis results in vitals_realtime table for trend tracking
        This allows frontend to query and display analysis trends over time
        """
        try:
            from .ecg_analysis_service import ECGAnalysisResult
            from .eeg_analysis_service import EEGAnalysisResult

            async with getTimescaleConnection() as tsConn:
                timestamp = datetime.now()

                if mode == 'ecg' and isinstance(analysisResult, ECGAnalysisResult):
                    # Store ECG analysis results
                    await tsConn.execute("""
                        INSERT INTO vitals_realtime (
                            time, "patientId", "deviceId", mode,
                            "heartRate", "signalQuality",
                            "rrInterval", "qrsDuration", "qtInterval", axis, rhythm, "stSegment"
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                        timestamp, patientId, deviceId, mode,
                        analysisResult.heartRate,
                        analysisResult.signalQuality,
                        analysisResult.rrInterval,
                        analysisResult.qrsDuration,
                        analysisResult.qtInterval,
                        analysisResult.axis,
                        analysisResult.rhythm,
                        analysisResult.stSegment
                    )

                elif mode == 'eeg' and isinstance(analysisResult, EEGAnalysisResult):
                    # Store EEG analysis results
                    await tsConn.execute("""
                        INSERT INTO vitals_realtime (
                            time, "patientId", "deviceId", mode, "signalQuality",
                            "alphaPower", "betaPower", "thetaPower", "deltaPower", "gammaPower",
                            "dominantFrequency", "seizureActivity"
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    """,
                        timestamp, patientId, deviceId, mode,
                        analysisResult.signalQuality,
                        analysisResult.alphaPower,
                        analysisResult.betaPower,
                        analysisResult.thetaPower,
                        analysisResult.deltaPower,
                        analysisResult.gammaPower,
                        analysisResult.dominantFrequency,
                        analysisResult.seizureActivity
                    )

                logger.debug(f"💾 Analysis results stored in vitals_realtime for {patientId}")

        except Exception as e:
            logger.error(f"❌ Failed to store analysis results: {e}", exc_info=True)

    async def _createSeizureAlert(self, patientId: str, deviceId: str, analysisResult: any):
        """Create critical alert for seizure detection"""
        try:
            # Broadcast critical alert via WebSocket
            alertPayload = {
                'severity': 'critical',
                'message': f'SEIZURE ACTIVITY DETECTED (Confidence: {analysisResult.seizureConfidence:.0%})',
                'source': f'Backend EEG Analysis (Device {deviceId})',
                'deviceId': deviceId,
                'eventType': 'seizure',
                'confidence': analysisResult.seizureConfidence,
                'alphaPower': analysisResult.alphaPower,
                'dominantFrequency': analysisResult.dominantFrequency
            }

            await connectionManager.sendAlert(patientId, alertPayload)

            logger.critical(f"🚨🚨🚨 SEIZURE ALERT for patient {patientId} (Confidence: {analysisResult.seizureConfidence:.0%})")

        except Exception as e:
            logger.error(f"❌ Failed to create seizure alert: {e}", exc_info=True)

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
mqtt_service = mqttService  # Alias for snake_case import compatibility