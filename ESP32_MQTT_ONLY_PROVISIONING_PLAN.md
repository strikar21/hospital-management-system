# ESP32 MQTT-Only Provisioning Architecture Plan

## Current State Analysis

### What Uses HTTP Now:
1. **Provisioning Endpoint** (`/api/v1/esp32/provision`):
   - POST with MAC, device type, firmware version
   - Staff credentials (provisionerId + password)
   - Returns: deviceId, serialNumber
   - Backend validates staff, creates device in pool

2. **Online Status** (`/api/v1/esp32/online`):
   - POST to mark device as available
   - Used after provisioning completes

3. **Captive Portal** (Local WebServer):
   - Runs on ESP32 itself (192.168.4.1)
   - NOT HTTP to backend - this stays as-is

### What Uses MQTT Now:
1. **Vitals transmission** - `hospital/devices/{deviceId}/vitals`
2. **Heartbeat** - `hospital/devices/{deviceId}/heartbeat`
3. **Alerts** - `hospital/devices/{deviceId}/alerts`
4. **Patient assignment** - `hospital/devices/{deviceId}/assign` (subscribe)
5. **Commands** - `hospital/devices/{deviceId}/command` (subscribe)

## Problem Statement

User wants to **eliminate ALL HTTP calls from ESP32 to backend** after captive portal setup. Only MQTT should be used.

**Challenge**: How do we provision a device via MQTT when the device doesn't have a deviceId yet?

## Proposed Solution: MQTT Provisioning Flow

### Step 1: Captive Portal (STAYS UNCHANGED)
- User connects to "HospitalWatch" AP
- Enters WiFi credentials
- Enters hospital server IP
- Enters staff provisioner ID and password
- **NO BACKEND CALL** - just saves config locally

### Step 2: ESP32 Connects to WiFi
- Connects to hospital WiFi
- Syncs NTP time
- Gets server IP from captive portal form

### Step 3: MQTT Connection with MAC Address as Client ID
**NEW APPROACH**:
- ESP32 connects to MQTT using **MAC address as client ID** (before provisioning)
- Client ID format: `HospitalWatch_UNPROVISIONED_{MAC_ADDRESS}`
- Example: `HospitalWatch_UNPROVISIONED_AA:BB:CC:DD:EE:FF`

### Step 4: Publish to Provisioning Topic
**NEW MQTT TOPIC**: `hospital/provisioning/request`

ESP32 publishes:
```json
{
  "macAddress": "AA:BB:CC:DD:EE:FF",
  "deviceType": "watch",
  "firmwareVersion": "4.2.0",
  "provisionerId": "TEC0001",
  "provisionerPassword": "tech123",
  "timestamp": "2025-10-17T10:30:45.123Z"
}
```

### Step 5: Backend MQTT Listener Handles Provisioning
**NEW BACKEND SERVICE**: `mqtt_provisioning_handler.py`

Listens to `hospital/provisioning/request` topic:
1. Validates staff credentials (same as HTTP endpoint)
2. Checks if device exists by MAC
3. Generates deviceId and serialNumber
4. Creates device record in database
5. **Publishes response to device-specific topic**

### Step 6: Backend Publishes Provisioning Response
**RESPONSE TOPIC**: `hospital/provisioning/response/{MAC_ADDRESS}`

ESP32 subscribes to: `hospital/provisioning/response/AA:BB:CC:DD:EE:FF`

Backend publishes:
```json
{
  "success": true,
  "deviceId": "ESP32_WATCH_001",
  "serialNumber": "SN_W001",
  "mqttUsername": "hospitalEsp32",
  "mqttPassword": "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF+Q=",
  "message": "Device provisioned successfully"
}
```

### Step 7: ESP32 Receives Provisioning Response
- Saves deviceId, serialNumber, MQTT credentials to Preferences
- Disconnects from MQTT
- Reconnects with new deviceId as client ID: `HospitalWatch_ESP32_WATCH_001`
- Uses MQTT credentials for authentication
- Subscribes to device-specific topics

### Step 8: Normal Operation (ALL MQTT)
- Heartbeat via MQTT
- Vitals via MQTT
- Alerts via MQTT
- Patient assignment via MQTT
- Commands via MQTT

## MQTT Credentials Storage

**Where to store MQTT username/password?**

**OPTION A: SPIFFS Config File** (Simple, same for all devices)
- Create `data/mqtt.config` file with:
  ```
  hospitalEsp32
  ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF+Q=
  ```
- Upload via ESP32FS plugin (like certificate)
- Read at boot, use for MQTT auth

**OPTION B: Backend Returns in Provisioning** (Device-specific possible)
- Backend includes credentials in provisioning response
- ESP32 saves to Preferences
- Can have per-device credentials if needed
- More flexible, centrally managed

**RECOMMENDATION: OPTION B** (Backend returns credentials during provisioning)
- More secure (not stored in firmware/SPIFFS)
- Centrally managed
- Can be per-device if needed
- No manual upload step

## Implementation Checklist

### Backend Changes:
- [ ] Create `mqtt_provisioning_handler.py` service
- [ ] Subscribe to `hospital/provisioning/request`
- [ ] Validate staff credentials
- [ ] Create device records
- [ ] Publish to `hospital/provisioning/response/{MAC}`
- [ ] Include MQTT credentials in response
- [ ] Remove or deprecate HTTP `/api/v1/esp32/provision` endpoint

### ESP32 Changes:
- [ ] Connect to MQTT with MAC-based client ID before provisioning
- [ ] Subscribe to `hospital/provisioning/response/{MAC}`
- [ ] Publish provisioning request to `hospital/provisioning/request`
- [ ] Handle provisioning response
- [ ] Save MQTT credentials to Preferences
- [ ] Reconnect with deviceId and MQTT auth
- [ ] Remove HTTP provisioning code
- [ ] Update firmware version to 4.2.0

### Security Considerations:
- [ ] MQTT TLS 1.2 ensures provisioner password is encrypted in transit
- [ ] Staff credentials validated before device creation
- [ ] MAC address used as temporary identifier (immutable hardware ID)
- [ ] MQTT credentials returned only after successful staff auth
- [ ] Credentials stored in ESP32 Preferences (encrypted storage)

## Benefits of MQTT-Only Approach

1. **Single Protocol**: Only MQTT after WiFi connection (simpler)
2. **Consistent Security**: All backend communication uses TLS 1.2
3. **No HTTP Dependencies**: Remove HTTPClient library from ESP32
4. **Smaller Firmware**: Less code, less memory usage
5. **Unified Message Flow**: Everything goes through MQTT broker
6. **Better for Production**: MQTT more reliable for IoT than HTTP

## Migration Path

1. **Phase 1**: Implement MQTT provisioning alongside existing HTTP (both work)
2. **Phase 2**: Test with new devices using MQTT provisioning
3. **Phase 3**: Update existing devices to use MQTT provisioning
4. **Phase 4**: Remove HTTP provisioning code entirely

## Questions to Resolve

1. **Do we need per-device MQTT credentials?**
   - Option A: All devices use shared `hospitalEsp32` credentials
   - Option B: Generate unique credentials per device (more secure, more complex)

2. **What if provisioning fails?**
   - ESP32 should retry with exponential backoff
   - After N failures, revert to captive portal for reconfiguration

3. **How long should ESP32 wait for provisioning response?**
   - Recommend: 30 seconds timeout
   - If no response, disconnect and retry

## Next Steps

**Question for User**:
- Do you want **shared MQTT credentials** (all devices use `hospitalEsp32`) or **per-device credentials** (each device gets unique MQTT username/password)?

**After decision, I will**:
1. Implement backend MQTT provisioning handler
2. Update ESP32 firmware to use MQTT provisioning
3. Remove HTTP provisioning code
4. Test end-to-end flow
5. Update firmware version to 4.2.0
