"""
Device Commands API

REST API endpoints for sending commands to IoT devices via MQTT
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

from app.services.mqtt_publisher import get_mqtt_publisher

router = APIRouter(prefix="/devices", tags=["Device Commands"])


# Request models
class AssignDeviceRequest(BaseModel):
    """Request to assign device to patient"""
    device_id: str
    patient_id: str


class UnassignDeviceRequest(BaseModel):
    """Request to unassign device from patient"""
    device_id: str


class PingDeviceRequest(BaseModel):
    """Request to ping device"""
    device_id: str


class CalibrateDeviceRequest(BaseModel):
    """Request to calibrate device waveforms"""
    device_id: str


class CustomCommandRequest(BaseModel):
    """Request to send custom command"""
    device_id: str
    command_type: str
    parameters: Optional[Dict[str, Any]] = None


class DisplayBrightnessRequest(BaseModel):
    """Request to set display brightness"""
    device_id: str
    brightness: int  # 0-100%


class WaveformStreamingRequest(BaseModel):
    """Request to enable/disable waveform streaming"""
    device_id: str
    enabled: bool


class SamplingRateRequest(BaseModel):
    """Request to set sampling rate"""
    device_id: str
    sampling_rate_hz: int  # 100, 250, 500, 1000 Hz


class VitalsIntervalRequest(BaseModel):
    """Request to set vitals transmission interval"""
    device_id: str
    interval_seconds: int  # 1-60 seconds


class DebugModeRequest(BaseModel):
    """Request to enable/disable debug mode"""
    device_id: str
    enabled: bool


class RebootDeviceRequest(BaseModel):
    """Request to reboot device"""
    device_id: str


class DeviceStatusRequest(BaseModel):
    """Request device status"""
    device_id: str


class AlertThresholdRequest(BaseModel):
    """Request to set alert threshold"""
    device_id: str
    vital_type: str  # "heartRate", "spo2", "temperature", etc.
    threshold_high: float
    threshold_low: float


class LEDAlertsRequest(BaseModel):
    """Request to enable/disable LED alerts"""
    device_id: str
    enabled: bool


class ClearOfflineQueueRequest(BaseModel):
    """Request to clear offline queue"""
    device_id: str


class SyncTimeRequest(BaseModel):
    """Request to sync time"""
    device_id: str


class WaveformModeRequest(BaseModel):
    """Request to set waveform mode"""
    device_id: str
    mode: str  # "ECG" or "EEG"


# Response models
class CommandResponse(BaseModel):
    """Response from command"""
    success: bool
    command_id: Optional[str] = None
    message: str
    timestamp: str


# ====================================
# DEVICE ASSIGNMENT ENDPOINTS
# ====================================

@router.post("/assign", response_model=CommandResponse)
async def assign_device_to_patient(request: AssignDeviceRequest):
    """
    Assign device to patient

    Sends MQTT message to device on topic:
    `hospital/devices/{deviceId}/assign`

    The device will:
    1. Receive the patient ID
    2. Start monitoring vitals for that patient
    3. Send vitals with the patient ID in payload

    Example:
    ```json
    {
      "device_id": "DEV000001",
      "patient_id": "PAT000001"
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        success = publisher.assign_device_to_patient(
            request.device_id,
            request.patient_id
        )

        if success:
            return CommandResponse(
                success=True,
                message=f"Device {request.device_id} assigned to patient {request.patient_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unassign", response_model=CommandResponse)
async def unassign_device(request: UnassignDeviceRequest):
    """
    Unassign device from patient

    Sends MQTT message to device on topic:
    `hospital/devices/{deviceId}/assign` with empty patientId

    The device will:
    1. Stop monitoring the current patient
    2. Wait for new assignment

    Example:
    ```json
    {
      "device_id": "DEV000001"
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        success = publisher.unassign_device(request.device_id)

        if success:
            return CommandResponse(
                success=True,
                message=f"Device {request.device_id} unassigned from patient",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# DEVICE COMMAND ENDPOINTS
# ====================================

@router.post("/ping", response_model=CommandResponse)
async def ping_device(request: PingDeviceRequest):
    """
    Ping device to check if it's responsive

    Sends MQTT command to device on topic:
    `hospital/devices/{deviceId}/commands`

    The device will:
    1. Receive the ping command
    2. Send back acknowledgment (pong)
    3. Reset device unresponsive timer

    Example:
    ```json
    {
      "device_id": "DEV000001"
    }
    ```

    Response includes `command_id` for tracking acknowledgment
    """
    try:
        publisher = get_mqtt_publisher()
        command_id = publisher.send_ping_command(request.device_id)

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Ping command sent to {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calibrate", response_model=CommandResponse)
async def calibrate_device_waveform(request: CalibrateDeviceRequest):
    """
    Calibrate device waveform (ECG/EEG)

    Sends MQTT command to device on topic:
    `hospital/devices/{deviceId}/commands`

    The device will:
    1. Start 3-second calibration pulse
    2. Generate 100μV calibration waveform
    3. Send acknowledgment when complete

    Example:
    ```json
    {
      "device_id": "DEV000001"
    }
    ```

    Response includes `command_id` for tracking acknowledgment
    """
    try:
        publisher = get_mqtt_publisher()
        command_id = publisher.send_waveform_calibrate_command(request.device_id)

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Waveform calibration command sent to {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/command", response_model=CommandResponse)
async def send_custom_command(request: CustomCommandRequest):
    """
    Send custom command to device

    Sends MQTT command to device on topic:
    `hospital/devices/{deviceId}/commands`

    Example:
    ```json
    {
      "device_id": "DEV000001",
      "command_type": "setDisplayBrightness",
      "parameters": {
        "brightness": 75
      }
    }
    ```

    Response includes `command_id` for tracking acknowledgment
    """
    try:
        publisher = get_mqtt_publisher()
        command_id = publisher.send_custom_command(
            request.device_id,
            request.command_type,
            request.parameters
        )

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Command '{request.command_type}' sent to {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# DEVICE CONFIGURATION ENDPOINTS
# ====================================

@router.post("/display-brightness", response_model=CommandResponse)
async def set_display_brightness(request: DisplayBrightnessRequest):
    """
    Set display brightness (0-100%)

    Example:
    ```json
    {
      "device_id": "DEV000001",
      "brightness": 75
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        command_id = publisher.set_display_brightness(request.device_id, request.brightness)

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Display brightness set to {request.brightness}% on {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/waveform-streaming", response_model=CommandResponse)
async def set_waveform_streaming(request: WaveformStreamingRequest):
    """
    Enable or disable waveform streaming (ECG/EEG at 500Hz)

    Example:
    ```json
    {
      "device_id": "DEV000001",
      "enabled": true
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        if request.enabled:
            command_id = publisher.enable_waveform_streaming(request.device_id)
        else:
            command_id = publisher.disable_waveform_streaming(request.device_id)

        if command_id:
            action = "enabled" if request.enabled else "disabled"
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Waveform streaming {action} on {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sampling-rate", response_model=CommandResponse)
async def set_sampling_rate(request: SamplingRateRequest):
    """
    Set waveform sampling rate (100, 250, 500, 1000 Hz)

    Example:
    ```json
    {
      "device_id": "DEV000001",
      "sampling_rate_hz": 500
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        command_id = publisher.set_sampling_rate(request.device_id, request.sampling_rate_hz)

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Sampling rate set to {request.sampling_rate_hz} Hz on {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vitals-interval", response_model=CommandResponse)
async def set_vitals_interval(request: VitalsIntervalRequest):
    """
    Set vitals transmission interval (1-60 seconds)

    Example:
    ```json
    {
      "device_id": "DEV000001",
      "interval_seconds": 5
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        command_id = publisher.set_vitals_interval(request.device_id, request.interval_seconds)

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Vitals interval set to {request.interval_seconds} seconds on {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug-mode", response_model=CommandResponse)
async def set_debug_mode(request: DebugModeRequest):
    """
    Enable or disable debug logging on device

    Example:
    ```json
    {
      "device_id": "DEV000001",
      "enabled": true
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        if request.enabled:
            command_id = publisher.enable_debug_mode(request.device_id)
        else:
            command_id = publisher.disable_debug_mode(request.device_id)

        if command_id:
            action = "enabled" if request.enabled else "disabled"
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Debug mode {action} on {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alert-threshold", response_model=CommandResponse)
async def set_alert_threshold(request: AlertThresholdRequest):
    """
    Set alert thresholds for vital signs

    Example:
    ```json
    {
      "device_id": "DEV000001",
      "vital_type": "heartRate",
      "threshold_high": 120.0,
      "threshold_low": 50.0
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        command_id = publisher.set_alert_threshold(
            request.device_id,
            request.vital_type,
            request.threshold_high,
            request.threshold_low
        )

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Alert threshold set for {request.vital_type} on {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/led-alerts", response_model=CommandResponse)
async def set_led_alerts(request: LEDAlertsRequest):
    """
    Enable or disable LED alert flashing

    Example:
    ```json
    {
      "device_id": "DEV000001",
      "enabled": true
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        if request.enabled:
            command_id = publisher.enable_led_alerts(request.device_id)
        else:
            command_id = publisher.disable_led_alerts(request.device_id)

        if command_id:
            action = "enabled" if request.enabled else "disabled"
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"LED alerts {action} on {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ====================================
# DEVICE MANAGEMENT ENDPOINTS
# ====================================

@router.post("/reboot", response_model=CommandResponse)
async def reboot_device(request: RebootDeviceRequest):
    """
    Reboot device (ESP32 restart)

    Example:
    ```json
    {
      "device_id": "DEV000001"
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        command_id = publisher.reboot_device(request.device_id)

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Reboot command sent to {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/status", response_model=CommandResponse)
async def get_device_status(request: DeviceStatusRequest):
    """
    Request full device status (battery, memory, uptime, etc.)

    Example:
    ```json
    {
      "device_id": "DEV000001"
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        command_id = publisher.get_device_status(request.device_id)

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Status request sent to {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-offline-queue", response_model=CommandResponse)
async def clear_offline_queue(request: ClearOfflineQueueRequest):
    """
    Clear offline message queue (SPIFFS)

    Example:
    ```json
    {
      "device_id": "DEV000001"
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        command_id = publisher.clear_offline_queue(request.device_id)

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Clear offline queue command sent to {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-time", response_model=CommandResponse)
async def sync_time(request: SyncTimeRequest):
    """
    Force NTP time synchronization

    Example:
    ```json
    {
      "device_id": "DEV000001"
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        command_id = publisher.sync_time(request.device_id)

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Time sync command sent to {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/waveform-mode", response_model=CommandResponse)
async def set_waveform_mode(request: WaveformModeRequest):
    """
    Set device to ECG mode (12-lead) or EEG mode (8-channel)

    Example:
    ```json
    {
      "device_id": "DEV000001",
      "mode": "ECG"
    }
    ```
    """
    try:
        publisher = get_mqtt_publisher()
        if request.mode.upper() == "ECG":
            command_id = publisher.set_ecg_mode(request.device_id)
        elif request.mode.upper() == "EEG":
            command_id = publisher.set_eeg_mode(request.device_id)
        else:
            raise HTTPException(status_code=400, detail="Mode must be 'ECG' or 'EEG'")

        if command_id:
            return CommandResponse(
                success=True,
                command_id=command_id,
                message=f"Waveform mode set to {request.mode.upper()} on {request.device_id}",
                timestamp=datetime.now().isoformat()
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to publish MQTT message")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
