# MQTT Integration Guide

## Overview

This guide explains how to set up and test the MQTT integration for ESP32 watches and door scanners.

---

## Architecture

```
┌──────────────────┐
│  ESP32 Watch     │ --> MQTT Topic: hospital/devices/{deviceId}/vitals
│  (Arduino)       │ --> MQTT Topic: hospital/devices/{deviceId}/stream
└──────────────────┘
         |
         v
┌──────────────────┐
│  MQTT Broker     │
│  (Mosquitto)     │
│  Port: 1883      │
└──────────────────┘
         |
         v
┌──────────────────┐
│  MQTT Consumer   │ --> Calls ESP32WatchAdapter
│  (Python)        │ --> Posts to FHIR API
└──────────────────┘
         |
         v
┌──────────────────┐
│  FHIR API        │ --> Stores in TimescaleDB
│  (FastAPI)       │ --> Broadcasts via WebSocket
└──────────────────┘
```

---

## Prerequisites

### 1. Install Mosquitto MQTT Broker

**Windows:**
```powershell
# Download from https://mosquitto.org/download/
# Or use Docker:
docker run -d -p 1883:1883 -p 9001:9001 eclipse-mosquitto
```

**Linux:**
```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl start mosquitto
sudo systemctl enable mosquitto
```

**macOS:**
```bash
brew install mosquitto
brew services start mosquitto
```

### 2. Install Python Dependencies

```bash
cd hospital-backend
pip install -r requirements.txt
```

---

## Setup

### 1. Environment Configuration

Create or update [`.env`](hospital-backend/.env):

```env
# Database
DATABASE_URL=postgresql://hospital_user:dev_password_123@localhost:5432/hospital_iot

# JWT
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# MQTT Configuration
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=

# FHIR API
FHIR_API_BASE=http://localhost:8000
AUTH_TOKEN=

# Optional: Get AUTH_TOKEN by logging in first
```

### 2. Start Services

**Terminal 1: Start FHIR API Backend**
```bash
cd hospital-backend
uvicorn app.main:app --reload
```

**Terminal 2: Start MQTT Consumer**
```bash
cd hospital-backend
python run_mqtt_consumer.py
```

**Terminal 3: Start Mock HMS (optional)**
```bash
cd hospital-backend
python mock_hms_server.py
```

---

## Testing

### Test 1: Send Test Vitals via MQTT

**Using mosquitto_pub:**

```bash
mosquitto_pub -h localhost -t "hospital/devices/DEV000001/vitals" -m '{
  "deviceId": "DEV000001",
  "patientId": "PAT000001",
  "timestamp": "2025-11-21T10:00:00Z",
  "vitals": {
    "heartRate": 72,
    "spo2": 98,
    "temperature": 36.8,
    "systolicBP": 120,
    "diastolicBP": 80,
    "respiratoryRate": 16,
    "steps": 8500
  },
  "batteryLevel": 85,
  "signalStrength": -45
}'
```

**Expected Output (MQTT Consumer Terminal):**
```
💓 Processing vitals from device: DEV000001
✅ Created 7 FHIR Observations
✅ Posted Observation: OBS-heartRate-a1b2c3d4
✅ Posted Observation: OBS-spo2-e5f6g7h8
...
```

### Test 2: Send NFC Event via MQTT

**Using mosquitto_pub:**

```bash
mosquitto_pub -h localhost -t "hospital/devices/DEV000003/nfc" -m '{
  "deviceId": "DEV000003",
  "location": "ICU-Ward-Room-101",
  "nfcBadgeId": "NFC-DOC-001",
  "staffId": "STF000001",
  "staffRole": "doctor",
  "patientId": "PAT000001",
  "action": "entry",
  "timestamp": "2025-11-21T14:30:00Z"
}'
```

**Expected Output (MQTT Consumer Terminal):**
```
🚪 Processing NFC event: STF000001 → ICU-Ward-Room-101
✅ Created FHIR AuditEvent
✅ Posted AuditEvent: AUDIT-ACCESS-a1b2c3d4
```

### Test 3: Subscribe to MQTT Topics

**Monitor all device messages:**
```bash
mosquitto_sub -h localhost -t "hospital/devices/#" -v
```

**Monitor only vitals:**
```bash
mosquitto_sub -h localhost -t "hospital/devices/+/vitals" -v
```

**Monitor only NFC events:**
```bash
mosquitto_sub -h localhost -t "hospital/devices/+/nfc" -v
```

---

## ESP32 Watch Integration

### MQTT Topics Used by ESP32 Watch

| Topic | QoS | Purpose |
|-------|-----|---------|
| `hospital/devices/{deviceId}/vitals` | 1 | Vital signs (HR, SpO2, Temp, BP, RR, Steps) |
| `hospital/devices/{deviceId}/stream` | 0 | Waveform streaming (ECG/EEG 500Hz) |
| `hospital/devices/{deviceId}/heartbeat` | 0 | Device heartbeat (every 30s) |
| `hospital/devices/{deviceId}/alerts` | 1 | Device-level alerts |

### Vitals Message Format (from ESP32)

```json
{
  "deviceId": "DEV000001",
  "patientId": "PAT000001",
  "timestamp": "2025-11-21T10:00:00Z",
  "vitals": {
    "heartRate": 72,
    "spo2": 98,
    "temperature": 36.8,
    "systolicBP": 120,
    "diastolicBP": 80,
    "respiratoryRate": 16,
    "steps": 8500
  },
  "batteryLevel": 85,
  "signalStrength": -45,
  "vitalsSequenceCounter": 12345
}
```

### What the MQTT Consumer Does

1. **Validates** the MQTT payload structure
2. **Transforms** each vital sign into a separate FHIR Observation:
   - Heart Rate → LOINC 8867-4
   - SpO2 → LOINC 59408-5
   - Temperature → LOINC 8310-5
   - Systolic BP → LOINC 8480-6
   - Diastolic BP → LOINC 8462-4
   - Respiratory Rate → LOINC 9279-1
   - Steps → LOINC 41950-7
3. **Detects alerts** (normal, warning, critical)
4. **Posts observations** to `/fhir/Observation` endpoint
5. **Stores in TimescaleDB** (fhirObservations table)
6. **Broadcasts** via WebSocket to connected clients

---

## Device Commands (Backend → ESP32)

### Overview

The backend can send commands TO devices via MQTT. The ESP32 watches subscribe to their command topic and execute received commands.

### Command Topics

| Topic | Purpose |
|-------|---------|
| `hospital/devices/{deviceId}/assign` | Assign/unassign device to patient |
| `hospital/devices/{deviceId}/commands` | Send commands (ping, calibrate, etc.) |

### Available Commands

#### 1. **Assign Device to Patient**

**API Endpoint:** `POST /devices/assign`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/assign \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001",
    "patient_id": "PAT000001"
  }'
```

**MQTT Message Sent:**
- **Topic:** `hospital/devices/DEV000001/assign`
- **Payload:**
```json
{
  "patientId": "PAT000001",
  "timestamp": "2025-11-21T10:00:00Z"
}
```

**Device Action:**
- Stores `patientId` in SPIFFS
- Starts monitoring vitals for that patient
- All future vitals messages include this `patientId`

---

#### 2. **Ping Device (Health Check)**

**API Endpoint:** `POST /devices/ping`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/ping \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001"
  }'
```

**MQTT Message Sent:**
- **Topic:** `hospital/devices/DEV000001/commands`
- **Payload:**
```json
{
  "command": "ping",
  "commandId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-11-21T10:00:00Z"
}
```

**Device Action:**
- Receives ping command
- Sends acknowledgment (pong) back to backend
- Resets device unresponsive timer (prevents false alerts)

**Device Response:**
- **Topic:** `hospital/devices/DEV000001/ack`
- **Payload:**
```json
{
  "commandId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "success": true,
  "message": "Pong",
  "timestamp": "2025-11-21T10:00:01Z"
}
```

---

#### 3. **Calibrate Waveform (ECG/EEG)**

**API Endpoint:** `POST /devices/calibrate`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/calibrate \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001"
  }'
```

**MQTT Message Sent:**
- **Topic:** `hospital/devices/DEV000001/commands`
- **Payload:**
```json
{
  "command": "waveformCalibrate",
  "commandId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-11-21T10:00:00Z"
}
```

**Device Action:**
- Starts 3-second calibration pulse
- Generates 100μV calibration waveform
- Sends acknowledgment when complete

**Device Response:**
- **Topic:** `hospital/devices/DEV000001/ack`
- **Payload:**
```json
{
  "commandId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "success": true,
  "message": "Waveform calibration started (3000ms non-blocking)",
  "timestamp": "2025-11-21T10:00:01Z"
}
```

---

#### 4. **Unassign Device from Patient**

**API Endpoint:** `POST /devices/unassign`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/unassign \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001"
  }'
```

**MQTT Message Sent:**
- **Topic:** `hospital/devices/DEV000001/assign`
- **Payload:**
```json
{
  "patientId": "",
  "timestamp": "2025-11-21T10:00:00Z"
}
```

**Device Action:**
- Clears `patientId` from SPIFFS
- Stops monitoring current patient
- Waits for new assignment

---

#### 5. **Custom Commands** (Extensible)

**API Endpoint:** `POST /devices/command`

**Example: Set Display Brightness**
```bash
curl -X POST http://localhost:8000/devices/command \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001",
    "command_type": "setDisplayBrightness",
    "parameters": {
      "brightness": 75
    }
  }'
```

**MQTT Message Sent:**
- **Topic:** `hospital/devices/DEV000001/commands`
- **Payload:**
```json
{
  "command": "setDisplayBrightness",
  "commandId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-11-21T10:00:00Z",
  "brightness": 75
}
```

---

### Additional Device Commands

The system provides comprehensive device control commands organized into configuration and management categories.

#### Device Configuration Commands

##### 6. **Set Display Brightness**

**API Endpoint:** `POST /devices/display-brightness`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/display-brightness \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001",
    "brightness": 75
  }'
```

**Device Action:** Adjusts TFT display brightness (0-100%)

---

##### 7. **Enable/Disable Waveform Streaming**

**API Endpoint:** `POST /devices/waveform-streaming`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/waveform-streaming \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001",
    "enabled": true
  }'
```

**Device Action:** Enables/disables 500Hz ECG/EEG waveform streaming to MQTT

---

##### 8. **Set Sampling Rate**

**API Endpoint:** `POST /devices/sampling-rate`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/sampling-rate \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001",
    "sampling_rate_hz": 500
  }'
```

**Device Action:** Sets waveform sampling rate (100, 250, 500, 1000 Hz)

---

##### 9. **Set Vitals Transmission Interval**

**API Endpoint:** `POST /devices/vitals-interval`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/vitals-interval \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001",
    "interval_seconds": 5
  }'
```

**Device Action:** Sets how often vitals are transmitted (1-60 seconds)

---

##### 10. **Enable/Disable Debug Mode**

**API Endpoint:** `POST /devices/debug-mode`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/debug-mode \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001",
    "enabled": true
  }'
```

**Device Action:** Enables/disables verbose Serial debug logging

---

##### 11. **Set Alert Threshold**

**API Endpoint:** `POST /devices/alert-threshold`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/alert-threshold \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001",
    "vital_type": "heartRate",
    "threshold_high": 120.0,
    "threshold_low": 50.0
  }'
```

**Device Action:** Configures alert thresholds for vital signs monitoring

**Supported Vital Types:**
- `heartRate` - Beats per minute
- `spo2` - Blood oxygen saturation percentage
- `temperature` - Body temperature in Celsius
- `systolicBP` - Systolic blood pressure
- `diastolicBP` - Diastolic blood pressure
- `respiratoryRate` - Breaths per minute

---

##### 12. **Enable/Disable LED Alerts**

**API Endpoint:** `POST /devices/led-alerts`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/led-alerts \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001",
    "enabled": true
  }'
```

**Device Action:** Enables/disables LED alert flashing when thresholds are breached

---

#### Device Management Commands

##### 13. **Reboot Device**

**API Endpoint:** `POST /devices/reboot`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/reboot \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001"
  }'
```

**Device Action:** Performs ESP32.restart() to reboot the device

---

##### 14. **Get Device Status**

**API Endpoint:** `POST /devices/status`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/status \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001"
  }'
```

**Device Action:** Requests full device status including:
- Battery level and voltage
- Free heap memory
- SPIFFS storage usage
- Uptime
- WiFi RSSI
- Current configuration

**Device Response:**
- **Topic:** `hospital/devices/DEV000001/status`
- **Payload:**
```json
{
  "deviceId": "DEV000001",
  "batteryLevel": 85,
  "batteryVoltage": 3.7,
  "freeHeap": 156432,
  "spiffsUsed": 24576,
  "spiffsTotal": 1441792,
  "uptime": 3600000,
  "wifiRSSI": -45,
  "assignedPatientId": "PAT000001",
  "timestamp": "2025-11-21T10:00:00Z"
}
```

---

##### 15. **Clear Offline Queue**

**API Endpoint:** `POST /devices/clear-offline-queue`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/clear-offline-queue \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001"
  }'
```

**Device Action:** Deletes all queued messages from SPIFFS offline storage

---

##### 16. **Sync Time**

**API Endpoint:** `POST /devices/sync-time`

**Request:**
```bash
curl -X POST http://localhost:8000/devices/sync-time \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001"
  }'
```

**Device Action:** Forces immediate NTP time synchronization

---

##### 17. **Set Waveform Mode**

**API Endpoint:** `POST /devices/waveform-mode`

**Request (ECG Mode):**
```bash
curl -X POST http://localhost:8000/devices/waveform-mode \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001",
    "mode": "ECG"
  }'
```

**Request (EEG Mode):**
```bash
curl -X POST http://localhost:8000/devices/waveform-mode \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "DEV000001",
    "mode": "EEG"
  }'
```

**Device Action:** Switches between:
- **ECG Mode:** 12-lead electrocardiogram monitoring
- **EEG Mode:** 8-channel electroencephalogram monitoring

---

### Testing Device Commands

#### Test 1: Assign Device via MQTT (manual)

```bash
mosquitto_pub -h localhost -t "hospital/devices/DEV000001/assign" -m '{
  "patientId": "PAT000001",
  "timestamp": "2025-11-21T10:00:00Z"
}' -r
```

*Note: The `-r` flag retains the message so devices receive it on reconnect*

#### Test 2: Send Ping Command via MQTT (manual)

```bash
mosquitto_pub -h localhost -t "hospital/devices/DEV000001/commands" -m '{
  "command": "ping",
  "commandId": "test-ping-123",
  "timestamp": "2025-11-21T10:00:00Z"
}'
```

#### Test 3: Send Calibrate Command via MQTT (manual)

```bash
mosquitto_pub -h localhost -t "hospital/devices/DEV000001/commands" -m '{
  "command": "waveformCalibrate",
  "commandId": "test-cal-456",
  "timestamp": "2025-11-21T10:00:00Z"
}'
```

#### Test 4: Subscribe to Device Acknowledgments

```bash
mosquitto_sub -h localhost -t "hospital/devices/+/ack" -v
```

---

### Command Flow Diagram

```
┌──────────────────┐
│  Frontend/API    │
│  Dashboard       │
└────────┬─────────┘
         │ POST /devices/ping
         v
┌──────────────────┐
│  FastAPI         │
│  Backend         │
└────────┬─────────┘
         │ MQTT Publish
         v
┌──────────────────┐
│  MQTT Broker     │
│  (Mosquitto)     │
└────────┬─────────┘
         │ MQTT Subscribe
         v
┌──────────────────┐
│  ESP32 Watch     │ --┐
│  (Arduino)       │   │ MQTT Publish
└──────────────────┘   │
                       v
                ┌──────────────────┐
                │  MQTT Broker     │
                │  (Acknowledgment)│
                └──────────────────┘
```

---

## Door Scanner Integration

### MQTT Topics Used by Door Scanner

| Topic | QoS | Purpose |
|-------|-----|---------|
| `hospital/devices/{deviceId}/nfc` | 1 | NFC tap events (staff room access) |

### NFC Message Format (from Door Scanner)

```json
{
  "deviceId": "DEV000003",
  "location": "ICU-Ward-Room-101",
  "nfcBadgeId": "NFC-DOC-001",
  "staffId": "STF000001",
  "staffRole": "doctor",
  "patientId": "PAT000001",
  "action": "entry",
  "timestamp": "2025-11-21T14:30:00Z"
}
```

### What the MQTT Consumer Does

1. **Validates** the NFC payload structure
2. **Transforms** into FHIR AuditEvent (DPDP Act 2023 compliance)
3. **Posts audit event** to `/fhir/AuditEvent` endpoint
4. **Stores in PostgreSQL** (fhirAuditEvent table)
5. **Broadcasts** via WebSocket to connected clients

---

## Troubleshooting

### MQTT Consumer Not Receiving Messages

**Check 1: Is Mosquitto running?**
```bash
# Linux/macOS
sudo systemctl status mosquitto

# Windows (check Task Manager or Docker)
docker ps | grep mosquitto
```

**Check 2: Can you connect to Mosquitto?**
```bash
mosquitto_sub -h localhost -t "test" -v
```

**Check 3: Is the MQTT consumer connected?**
Look for this log message:
```
✅ Connected to MQTT broker at localhost:1883
📡 Subscribed to: hospital/devices/+/vitals (QoS 1)
```

### FHIR API Errors

**Check 1: Is the FHIR API running?**
```bash
curl http://localhost:8000/health
```

**Check 2: Do you have a valid auth token?**
```bash
# Login to get token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"staffId": "STF000001", "pin": "1234"}'

# Copy the accessToken and add to .env:
# AUTH_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Check 3: Does the device exist?**
```bash
# Create device if needed
curl -X POST http://localhost:8000/fhir/Device \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "Device",
    "id": "DEV000001",
    "type": [{"coding": [{"code": "706767009", "display": "Patient monitoring system"}]}],
    "status": "active"
  }'
```

### Observations Not Being Stored

**Check 1: Is TimescaleDB extension enabled?**
```sql
-- Connect to database
psql -U hospital_user hospital_iot

-- Check extension
SELECT * FROM pg_extension WHERE extname = 'timescaledb';

-- If not exists:
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

**Check 2: Does the hypertable exist?**
```sql
SELECT * FROM timescaledb_information.hypertables WHERE hypertable_name = 'fhirobservations';
```

**Check 3: Check observation_handler logs:**
Look for JSONB serialization errors or database connection errors.

---

## Production Deployment

### 1. Use TLS/SSL for MQTT

**Configure Mosquitto with TLS:**
Edit `/etc/mosquitto/mosquitto.conf`:

```conf
listener 8883
cafile /etc/mosquitto/ca_certificates/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
require_certificate true
```

**Update ESP32 Watch firmware:**
- Change MQTT port from 1883 → 8883
- Provision device certificates
- Enable mTLS authentication

**Update MQTT Consumer:**
```env
MQTT_PORT=8883
MQTT_USE_TLS=true
MQTT_CA_CERT=/path/to/ca.crt
MQTT_CLIENT_CERT=/path/to/client.crt
MQTT_CLIENT_KEY=/path/to/client.key
```

### 2. Use Authentication

**Configure Mosquitto with password:**
```bash
sudo mosquitto_passwd -c /etc/mosquitto/passwd hospital_backend
```

**Update MQTT Consumer:**
```env
MQTT_USERNAME=hospital_backend
MQTT_PASSWORD=your-secure-password
```

### 3. Run as System Service

**Create systemd service file:**
```bash
sudo nano /etc/systemd/system/mqtt-consumer.service
```

```ini
[Unit]
Description=Hospital MQTT Consumer Service
After=network.target mosquitto.service postgresql.service

[Service]
Type=simple
User=hospital
WorkingDirectory=/opt/hospital-backend
Environment="PATH=/opt/hospital-backend/venv/bin"
ExecStart=/opt/hospital-backend/venv/bin/python run_mqtt_consumer.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable mqtt-consumer
sudo systemctl start mqtt-consumer
sudo systemctl status mqtt-consumer
```

---

## Monitoring

### MQTT Consumer Statistics

The MQTT consumer logs statistics every time it shuts down:

```
📊 Statistics:
   Messages Received: 1234
   Vitals Processed: 567
   NFC Events Processed: 89
   Errors: 0
```

### Monitor MQTT Traffic

**Real-time monitoring:**
```bash
mosquitto_sub -h localhost -t '#' -v | tee mqtt_traffic.log
```

### Check Database

**Count observations:**
```sql
SELECT COUNT(*) FROM fhirObservations;
```

**Recent vitals:**
```sql
SELECT
    time,
    patientId,
    code,
    valueQuantity,
    valueUnit
FROM fhirObservations
WHERE time > NOW() - INTERVAL '1 hour'
ORDER BY time DESC
LIMIT 10;
```

---

## Integration Testing Script

Create `test_mqtt_integration.py`:

```python
import paho.mqtt.client as mqtt
import json
import time

def test_vitals_message():
    """Send test vitals message"""
    client = mqtt.Client()
    client.connect("localhost", 1883, 60)

    message = {
        "deviceId": "DEV000001",
        "patientId": "PAT000001",
        "timestamp": "2025-11-21T10:00:00Z",
        "vitals": {
            "heartRate": 72,
            "spo2": 98,
            "temperature": 36.8
        },
        "batteryLevel": 85
    }

    client.publish("hospital/devices/DEV000001/vitals", json.dumps(message))
    print("[OK] Sent test vitals message")

    client.disconnect()

def test_nfc_message():
    """Send test NFC message"""
    client = mqtt.Client()
    client.connect("localhost", 1883, 60)

    message = {
        "deviceId": "DEV000003",
        "location": "ICU-Ward-Room-101",
        "nfcBadgeId": "NFC-DOC-001",
        "staffId": "STF000001",
        "staffRole": "doctor",
        "patientId": "PAT000001",
        "action": "entry",
        "timestamp": "2025-11-21T14:30:00Z"
    }

    client.publish("hospital/devices/DEV000003/nfc", json.dumps(message))
    print("[OK] Sent test NFC message")

    client.disconnect()

if __name__ == "__main__":
    print("Testing MQTT Integration...")
    test_vitals_message()
    time.sleep(1)
    test_nfc_message()
    print("[OK] Integration test complete")
```

Run:
```bash
python test_mqtt_integration.py
```

---

## Next Steps

1. **Flash ESP32 Watch** with the firmware in `esp32_hospital_watch_complete/`
2. **Configure ESP32** with WiFi and MQTT broker IP
3. **Start MQTT Consumer** to listen for device messages
4. **Monitor WebSocket** for real-time vitals: `ws://localhost:8000/ws/vitals/PAT000001`
5. **View Dashboard** to see live data

---

## Support

For MQTT integration issues:
- Email: dev@hospital.org
- Slack: #hospital-iot-mqtt
- GitHub Issues: [hospital-management-system/issues](https://github.com/yourusername/hospital-management-system/issues)
