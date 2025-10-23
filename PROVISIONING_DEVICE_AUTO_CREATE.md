# Device Auto-Creation During Provisioning

## Devices Table Schema (Required Fields)

```sql
id                  text NOT NULL
deviceType          text NOT NULL
name                text NOT NULL
serialNumber        text NOT NULL
```

## Correct INSERT Statement

```python
if not device_row:
    # Auto-create device for new ESP32
    await conn.execute(
        '''INSERT INTO devices
           (id, name, "deviceType", "serialNumber", status, "createdAt", "updatedAt")
           VALUES ($1, $2, $3, $4, $5, NOW(), NOW())''',
        request.deviceId,                          # id: "ESP32-WATCH-AA:BB:CC:DD:EE:FF"
        f"ESP32 Watch {request.macAddress[-8:]}",  # name: "ESP32 Watch DD:EE:FF"
        "watch",                                    # deviceType: "watch"
        request.serialNumber or f"SN-{request.macAddress}",  # serialNumber
        "active"                                    # status: "active"
    )
```

## Logic Flow

### Case 1: New Device (First Time Provisioning)
```
1. ESP32 connects to captive portal
2. User enters provisioning code
3. ESP32 sends: deviceId, macAddress, serialNumber
4. Backend checks: device exists? NO
5. Backend creates device in devices table
6. Backend generates certificate
7. ESP32 receives certificate and connects to MQTT
```

### Case 2: Existing Device (Re-Provisioning)
```
1. ESP32 lost certificate or re-flashed
2. User enters new provisioning code
3. ESP32 sends: deviceId, macAddress, serialNumber
4. Backend checks: device exists? YES
5. Backend checks: has active cert? YES or NO
6. Backend generates NEW certificate (replaces old via ON CONFLICT)
7. ESP32 receives certificate and connects to MQTT
```

### Case 3: Revoked Device (Re-Provisioning After Revocation)
```
1. Device was revoked due to security issue
2. Issue resolved, device needs re-provisioning
3. User enters new provisioning code
4. ESP32 sends: deviceId, macAddress, serialNumber
5. Backend checks: device exists? YES
6. Backend checks: has active cert? NO (revoked)
7. Backend generates NEW certificate (un-revokes via ON CONFLICT)
8. ESP32 receives certificate and connects to MQTT
```

## Fixed Code

Replace lines 235-259 in `hospital-backend/app/api/v1/provisioning.py`:

```python
# Step 2: Check if device exists, if not create it
device_row = await conn.fetchrow(
    'SELECT id FROM devices WHERE id = $1',
    request.deviceId
)

if not device_row:
    # Auto-create device for new ESP32
    logger.info(f"Creating new device: {request.deviceId}")
    await conn.execute(
        '''INSERT INTO devices
           (id, name, "deviceType", "serialNumber", status, "createdAt", "updatedAt")
           VALUES ($1, $2, $3, $4, $5, NOW(), NOW())''',
        request.deviceId,
        f"ESP32 Watch {request.macAddress[-8:]}",
        "watch",
        request.serialNumber or f"SN-{request.macAddress}",
        "active"
    )
    logger.info(f"Device {request.deviceId} created")

# Step 3: Check certificate status (for logging)
existing_cert = await conn.fetchrow(
    'SELECT id, revoked FROM device_certificates WHERE device_id = $1',
    request.deviceId
)

if existing_cert and not existing_cert["revoked"]:
    logger.info(f"Re-provisioning device {request.deviceId}")
elif existing_cert and existing_cert["revoked"]:
    logger.info(f"Re-provisioning revoked device {request.deviceId}")
else:
    logger.info(f"First-time provisioning for {request.deviceId}")
```

## Result

- ✅ New ESP32 devices can self-provision without manual database entry
- ✅ Existing devices can re-provision (lost certs, re-flashing)
- ✅ Revoked devices can be re-provisioned after issue resolution
- ✅ ON CONFLICT in certificate INSERT handles all cases
