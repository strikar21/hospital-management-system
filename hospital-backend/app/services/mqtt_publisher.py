"""
MQTT Publisher Service

Publishes commands and assignments to IoT devices via MQTT
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional
import paho.mqtt.client as mqtt
from datetime import datetime

logger = logging.getLogger(__name__)


class MQTTPublisherService:
    """
    MQTT Publisher Service

    Publishes commands to devices via MQTT topics
    """

    def __init__(
        self,
        mqtt_broker: str = "localhost",
        mqtt_port: int = 1883,
        mqtt_username: Optional[str] = None,
        mqtt_password: Optional[str] = None
    ):
        """
        Initialize MQTT publisher

        Args:
            mqtt_broker: MQTT broker hostname
            mqtt_port: MQTT broker port
            mqtt_username: MQTT username (optional)
            mqtt_password: MQTT password (optional)
        """
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password

        # MQTT client
        self.client = mqtt.Client(client_id="hospital-backend-publisher")

        # Set authentication if provided
        if self.mqtt_username and self.mqtt_password:
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)

        # Connect to broker
        self._connect()

    def _connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.client.loop_start()  # Start background thread
            logger.info(f"✅ MQTT Publisher connected to {self.mqtt_broker}:{self.mqtt_port}")
        except Exception as e:
            logger.error(f"❌ Failed to connect MQTT publisher: {e}")

    def assign_device_to_patient(
        self,
        device_id: str,
        patient_id: str
    ) -> bool:
        """
        Assign device to patient

        Args:
            device_id: Device ID (e.g., "DEV000001")
            patient_id: Patient ID (e.g., "PAT000001")

        Returns:
            True if published successfully
        """
        try:
            topic = f"hospital/devices/{device_id}/assign"

            payload = {
                "patientId": patient_id,
                "timestamp": datetime.now().isoformat()
            }

            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=1,  # QoS 1 - at least once delivery
                retain=True  # Retain message so device gets it on reconnect
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Assigned {device_id} to patient {patient_id}")
                return True
            else:
                logger.error(f"❌ Failed to assign device: {result.rc}")
                return False

        except Exception as e:
            logger.error(f"❌ Error assigning device: {e}")
            return False

    def send_ping_command(
        self,
        device_id: str
    ) -> str:
        """
        Send ping command to device

        Args:
            device_id: Device ID

        Returns:
            Command ID (for tracking acknowledgment)
        """
        command_id = str(uuid.uuid4())

        try:
            topic = f"hospital/devices/{device_id}/commands"

            payload = {
                "command": "ping",
                "commandId": command_id,
                "timestamp": datetime.now().isoformat()
            }

            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=1  # QoS 1 - at least once delivery
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Sent ping command to {device_id} (commandId: {command_id})")
                return command_id
            else:
                logger.error(f"❌ Failed to send ping: {result.rc}")
                return ""

        except Exception as e:
            logger.error(f"❌ Error sending ping: {e}")
            return ""

    def send_waveform_calibrate_command(
        self,
        device_id: str
    ) -> str:
        """
        Send waveform calibration command to device

        Args:
            device_id: Device ID

        Returns:
            Command ID (for tracking acknowledgment)
        """
        command_id = str(uuid.uuid4())

        try:
            topic = f"hospital/devices/{device_id}/commands"

            payload = {
                "command": "waveformCalibrate",
                "commandId": command_id,
                "timestamp": datetime.now().isoformat()
            }

            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=1  # QoS 1 - at least once delivery
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Sent waveform calibration command to {device_id} (commandId: {command_id})")
                return command_id
            else:
                logger.error(f"❌ Failed to send calibration command: {result.rc}")
                return ""

        except Exception as e:
            logger.error(f"❌ Error sending calibration command: {e}")
            return ""

    def send_custom_command(
        self,
        device_id: str,
        command_type: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send custom command to device

        Args:
            device_id: Device ID
            command_type: Command type string
            parameters: Optional command parameters

        Returns:
            Command ID (for tracking acknowledgment)
        """
        command_id = str(uuid.uuid4())

        try:
            topic = f"hospital/devices/{device_id}/commands"

            payload = {
                "command": command_type,
                "commandId": command_id,
                "timestamp": datetime.now().isoformat()
            }

            if parameters:
                payload.update(parameters)

            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=1  # QoS 1 - at least once delivery
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Sent {command_type} command to {device_id} (commandId: {command_id})")
                return command_id
            else:
                logger.error(f"❌ Failed to send command: {result.rc}")
                return ""

        except Exception as e:
            logger.error(f"❌ Error sending command: {e}")
            return ""

    def unassign_device(
        self,
        device_id: str
    ) -> bool:
        """
        Unassign device from patient

        Args:
            device_id: Device ID

        Returns:
            True if published successfully
        """
        try:
            topic = f"hospital/devices/{device_id}/assign"

            payload = {
                "patientId": "",  # Empty string to unassign
                "timestamp": datetime.now().isoformat()
            }

            result = self.client.publish(
                topic,
                json.dumps(payload),
                qos=1,  # QoS 1 - at least once delivery
                retain=True  # Retain message
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"✅ Unassigned {device_id} from patient")
                return True
            else:
                logger.error(f"❌ Failed to unassign device: {result.rc}")
                return False

        except Exception as e:
            logger.error(f"❌ Error unassigning device: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("✅ MQTT Publisher disconnected")

    # ====================================
    # ADDITIONAL DEVICE COMMANDS
    # ====================================

    def set_display_brightness(self, device_id: str, brightness: int) -> str:
        """Set display brightness (0-100%)"""
        return self.send_custom_command(device_id, "setDisplayBrightness", {"brightness": brightness})

    def enable_waveform_streaming(self, device_id: str) -> str:
        """Enable waveform streaming (ECG/EEG 500Hz)"""
        return self.send_custom_command(device_id, "enableWaveformStreaming", {"enabled": True})

    def disable_waveform_streaming(self, device_id: str) -> str:
        """Disable waveform streaming"""
        return self.send_custom_command(device_id, "enableWaveformStreaming", {"enabled": False})

    def set_sampling_rate(self, device_id: str, sampling_rate_hz: int) -> str:
        """Set waveform sampling rate (100, 250, 500, 1000 Hz)"""
        return self.send_custom_command(device_id, "setSamplingRate", {"samplingRateHz": sampling_rate_hz})

    def set_vitals_interval(self, device_id: str, interval_seconds: int) -> str:
        """Set vitals transmission interval (1-60 seconds)"""
        return self.send_custom_command(device_id, "setVitalsInterval", {"intervalSeconds": interval_seconds})

    def enable_debug_mode(self, device_id: str) -> str:
        """Enable debug logging on device"""
        return self.send_custom_command(device_id, "setDebugMode", {"enabled": True})

    def disable_debug_mode(self, device_id: str) -> str:
        """Disable debug logging on device"""
        return self.send_custom_command(device_id, "setDebugMode", {"enabled": False})

    def reboot_device(self, device_id: str) -> str:
        """Reboot device (ESP32 restart)"""
        return self.send_custom_command(device_id, "reboot", {})

    def get_device_status(self, device_id: str) -> str:
        """Request full device status (battery, memory, uptime, etc.)"""
        return self.send_custom_command(device_id, "getStatus", {})

    def set_alert_threshold(self, device_id: str, vital_type: str, threshold_high: float, threshold_low: float) -> str:
        """Set alert thresholds for vital signs"""
        return self.send_custom_command(device_id, "setAlertThreshold", {
            "vitalType": vital_type,
            "thresholdHigh": threshold_high,
            "thresholdLow": threshold_low
        })

    def enable_led_alerts(self, device_id: str) -> str:
        """Enable LED alert flashing"""
        return self.send_custom_command(device_id, "setLEDAlerts", {"enabled": True})

    def disable_led_alerts(self, device_id: str) -> str:
        """Disable LED alert flashing"""
        return self.send_custom_command(device_id, "setLEDAlerts", {"enabled": False})

    def clear_offline_queue(self, device_id: str) -> str:
        """Clear offline message queue (SPIFFS)"""
        return self.send_custom_command(device_id, "clearOfflineQueue", {})

    def sync_time(self, device_id: str) -> str:
        """Force NTP time synchronization"""
        return self.send_custom_command(device_id, "syncTime", {})

    def set_ecg_mode(self, device_id: str) -> str:
        """Set device to ECG mode (12-lead)"""
        return self.send_custom_command(device_id, "setWaveformMode", {"mode": "ECG"})

    def set_eeg_mode(self, device_id: str) -> str:
        """Set device to EEG mode (8-channel)"""
        return self.send_custom_command(device_id, "setWaveformMode", {"mode": "EEG"})


# Global MQTT publisher instance
_mqtt_publisher: Optional[MQTTPublisherService] = None


def get_mqtt_publisher() -> MQTTPublisherService:
    """
    Get global MQTT publisher instance (singleton)

    Returns:
        MQTTPublisherService instance
    """
    global _mqtt_publisher

    if _mqtt_publisher is None:
        import os
        from dotenv import load_dotenv

        load_dotenv()

        mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
        mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        mqtt_username = os.getenv("MQTT_USERNAME")
        mqtt_password = os.getenv("MQTT_PASSWORD")

        _mqtt_publisher = MQTTPublisherService(
            mqtt_broker=mqtt_broker,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password
        )

    return _mqtt_publisher
