"""
MQTT Consumer Service

Listens to MQTT topics for device messages and processes them through device adapters
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
import paho.mqtt.client as mqtt
import httpx
from datetime import datetime

# Import device adapters
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from device_modules.esp32_watch.adapter import ESP32WatchAdapter
from device_modules.door_scanner.adapter import DoorScannerAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MQTTConsumerService:
    """
    MQTT Consumer Service

    Subscribes to device MQTT topics and processes messages through device adapters
    """

    def __init__(
        self,
        mqtt_broker: str = "localhost",
        mqtt_port: int = 1883,
        mqtt_username: Optional[str] = None,
        mqtt_password: Optional[str] = None,
        fhir_api_base: str = "http://localhost:8000",
        auth_token: Optional[str] = None
    ):
        """
        Initialize MQTT consumer

        Args:
            mqtt_broker: MQTT broker hostname
            mqtt_port: MQTT broker port
            mqtt_username: MQTT username (optional)
            mqtt_password: MQTT password (optional)
            fhir_api_base: Base URL for FHIR API
            auth_token: JWT token for FHIR API authentication
        """
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.fhir_api_base = fhir_api_base
        self.auth_token = auth_token

        # Initialize device adapters
        self.esp32_watch_adapter = ESP32WatchAdapter()
        self.door_scanner_adapter = DoorScannerAdapter()

        # MQTT client
        self.client = mqtt.Client(client_id="hospital-backend-consumer")

        # Setup callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # Set authentication if provided
        if self.mqtt_username and self.mqtt_password:
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)

        # HTTP client for FHIR API
        self.http_client = httpx.AsyncClient(
            base_url=self.fhir_api_base,
            timeout=30.0
        )

        # Statistics
        self.stats = {
            "messages_received": 0,
            "vitals_processed": 0,
            "nfc_events_processed": 0,
            "errors": 0,
            "last_message_time": None
        }

    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            logger.info(f"✅ Connected to MQTT broker at {self.mqtt_broker}:{self.mqtt_port}")

            # Subscribe to topics
            topics = [
                ("hospital/devices/+/vitals", 1),      # ESP32 watch vitals (QoS 1)
                ("hospital/devices/+/nfc", 1),         # Door scanner NFC events (QoS 1)
                ("hospital/devices/+/stream", 0),      # Waveform streaming (QoS 0 - high frequency)
                ("hospital/devices/+/heartbeat", 0),   # Device heartbeats (QoS 0)
            ]

            for topic, qos in topics:
                client.subscribe(topic, qos)
                logger.info(f"📡 Subscribed to: {topic} (QoS {qos})")
        else:
            logger.error(f"❌ Failed to connect to MQTT broker, return code: {rc}")

    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        if rc != 0:
            logger.warning(f"⚠️  Unexpected MQTT disconnection, return code: {rc}")
            logger.info("🔄 Attempting to reconnect...")

    def on_message(self, client, userdata, msg):
        """Callback when message received from MQTT broker"""
        try:
            self.stats["messages_received"] += 1
            self.stats["last_message_time"] = datetime.now().isoformat()

            topic = msg.topic
            payload_str = msg.payload.decode('utf-8')

            logger.debug(f"📨 Received message on topic: {topic}")

            # Parse JSON payload
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON payload: {e}")
                self.stats["errors"] += 1
                return

            # Route to appropriate handler
            if "/vitals" in topic:
                asyncio.run(self.handle_vitals_message(payload))
            elif "/nfc" in topic:
                asyncio.run(self.handle_nfc_message(payload))
            elif "/stream" in topic:
                asyncio.run(self.handle_waveform_stream(payload))
            elif "/heartbeat" in topic:
                asyncio.run(self.handle_heartbeat(payload))
            else:
                logger.warning(f"⚠️  Unknown topic: {topic}")

        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)
            self.stats["errors"] += 1

    async def handle_vitals_message(self, payload: Dict[str, Any]):
        """
        Handle vitals message from ESP32 watch

        Args:
            payload: MQTT vitals payload
        """
        try:
            logger.info(f"💓 Processing vitals from device: {payload.get('deviceId')}")

            # Validate payload
            is_valid, error = self.esp32_watch_adapter.validate_mqtt_payload(payload)
            if not is_valid:
                logger.error(f"❌ Invalid vitals payload: {error}")
                self.stats["errors"] += 1
                return

            # Transform to FHIR Observations
            observations = self.esp32_watch_adapter.transform_to_fhir_observations(payload)
            logger.info(f"✅ Created {len(observations)} FHIR Observations")

            # Detect alerts
            alerts = self.esp32_watch_adapter.detect_alerts(payload)
            if alerts:
                logger.warning(f"🚨 Detected {len(alerts)} alerts!")

            # Send observations to FHIR API
            for obs in observations:
                await self.post_observation(obs)

            # Send alerts to FHIR API (as Flag resources)
            for alert in alerts:
                await self.post_flag(alert)

            self.stats["vitals_processed"] += 1

        except Exception as e:
            logger.error(f"❌ Error handling vitals message: {e}", exc_info=True)
            self.stats["errors"] += 1

    async def handle_nfc_message(self, payload: Dict[str, Any]):
        """
        Handle NFC event from door scanner

        Args:
            payload: MQTT NFC payload
        """
        try:
            logger.info(f"🚪 Processing NFC event: {payload.get('staffId')} → {payload.get('location')}")

            # Validate payload
            is_valid, error = self.door_scanner_adapter.validate_nfc_payload(payload)
            if not is_valid:
                logger.error(f"❌ Invalid NFC payload: {error}")
                self.stats["errors"] += 1
                return

            # Transform to FHIR AuditEvent
            audit_event = self.door_scanner_adapter.transform_to_fhir_audit_event(payload)
            logger.info(f"✅ Created FHIR AuditEvent")

            # Transform to FHIR Observation (optional - for room occupancy tracking)
            observation = self.door_scanner_adapter.transform_to_fhir_observation(payload)

            # Send audit event to FHIR API
            await self.post_audit_event(audit_event)

            # Send observation if patient present
            if observation:
                await self.post_observation(observation)

            self.stats["nfc_events_processed"] += 1

        except Exception as e:
            logger.error(f"❌ Error handling NFC message: {e}", exc_info=True)
            self.stats["errors"] += 1

    async def handle_waveform_stream(self, payload: Dict[str, Any]):
        """
        Handle waveform stream data (ECG/EEG)

        Args:
            payload: MQTT waveform payload
        """
        # For now, just log (can be extended to store waveforms)
        logger.debug(f"📊 Received waveform stream from device: {payload.get('deviceId')}")

    async def handle_heartbeat(self, payload: Dict[str, Any]):
        """
        Handle device heartbeat

        Args:
            payload: MQTT heartbeat payload
        """
        logger.debug(f"💗 Heartbeat from device: {payload.get('deviceId')}")

    async def post_observation(self, observation: Dict[str, Any]):
        """
        Post FHIR Observation to API

        Args:
            observation: FHIR Observation resource
        """
        try:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            response = await self.http_client.post(
                "/fhir/Observation",
                json=observation,
                headers=headers
            )

            if response.status_code == 201:
                logger.info(f"✅ Posted Observation: {observation['id']}")
            else:
                logger.error(f"❌ Failed to post Observation: {response.status_code} - {response.text}")
                self.stats["errors"] += 1

        except Exception as e:
            logger.error(f"❌ Error posting Observation: {e}")
            self.stats["errors"] += 1

    async def post_audit_event(self, audit_event: Dict[str, Any]):
        """
        Post FHIR AuditEvent to API

        Args:
            audit_event: FHIR AuditEvent resource
        """
        try:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            response = await self.http_client.post(
                "/fhir/AuditEvent",
                json=audit_event,
                headers=headers
            )

            if response.status_code == 201:
                logger.info(f"✅ Posted AuditEvent: {audit_event['id']}")
            else:
                logger.error(f"❌ Failed to post AuditEvent: {response.status_code} - {response.text}")
                self.stats["errors"] += 1

        except Exception as e:
            logger.error(f"❌ Error posting AuditEvent: {e}")
            self.stats["errors"] += 1

    async def post_flag(self, flag: Dict[str, Any]):
        """
        Post FHIR Flag (alert) to API

        Args:
            flag: FHIR Flag resource
        """
        try:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            # For now, log the alert (Flag resource endpoint not yet implemented)
            logger.warning(f"🚨 ALERT: {flag.get('code', {}).get('text', 'Unknown alert')}")

            # TODO: Implement POST /fhir/Flag endpoint in FHIR API
            # response = await self.http_client.post(
            #     "/fhir/Flag",
            #     json=flag,
            #     headers=headers
            # )

        except Exception as e:
            logger.error(f"❌ Error posting Flag: {e}")
            self.stats["errors"] += 1

    def start(self):
        """Start the MQTT consumer"""
        try:
            logger.info(f"🚀 Starting MQTT Consumer Service")
            logger.info(f"   MQTT Broker: {self.mqtt_broker}:{self.mqtt_port}")
            logger.info(f"   FHIR API: {self.fhir_api_base}")

            # Connect to MQTT broker
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)

            # Start loop (blocking)
            self.client.loop_forever()

        except KeyboardInterrupt:
            logger.info("⏹️  Shutting down MQTT Consumer Service...")
            self.stop()

        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
            self.stop()

    def stop(self):
        """Stop the MQTT consumer"""
        logger.info("🛑 Stopping MQTT Consumer Service...")

        # Disconnect from MQTT broker
        self.client.disconnect()

        # Close HTTP client
        asyncio.run(self.http_client.aclose())

        # Print statistics
        logger.info("📊 Statistics:")
        logger.info(f"   Messages Received: {self.stats['messages_received']}")
        logger.info(f"   Vitals Processed: {self.stats['vitals_processed']}")
        logger.info(f"   NFC Events Processed: {self.stats['nfc_events_processed']}")
        logger.info(f"   Errors: {self.stats['errors']}")

        logger.info("✅ MQTT Consumer Service stopped")


if __name__ == "__main__":
    # Example usage
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Get configuration from environment
    mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    fhir_api_base = os.getenv("FHIR_API_BASE", "http://localhost:8000")
    auth_token = os.getenv("AUTH_TOKEN")

    # Create and start consumer
    consumer = MQTTConsumerService(
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        fhir_api_base=fhir_api_base,
        auth_token=auth_token
    )

    consumer.start()
