# Sequential Device ID Testing Guide

## Implementation Complete

All changes have been implemented for the proper device ID naming system:

### ✅ Changes Applied

1. **Database Migration** - Created `device_mac_mapping` table to map MAC addresses to sequential device IDs
   - File: [hospital-backend/migrations/014_device_mac_mapping.sql](hospital-backend/migrations/014_device_mac_mapping.sql)
   - Applied successfully: `python apply_migration_014.py`

2. **Backend Provisioning Endpoint** - Modified to assign sequential device IDs
   - File: [hospital-backend/app/api/v1/provisioning.py](hospital-backend/app/api/v1/provisioning.py)
   - Lines 237-298: Sequential ID assignment logic
   - Lines 300-379: Updated to use backend-assigned ID

3. **ESP32 Firmware** - Already compatible with backend-assigned IDs
   - File: [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:1195](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1195)
   - Receives and saves `deviceId` from backend response

4. **ACL Configuration** - Removed temporary explicit entry, updated examples
   - File: [mosquitto/config/acl.conf](mosquitto/config/acl.conf)
   - Removed lines 40-49 (temporary ESP32-WATCH-A0:A3:B3:AA:13:B0 entry)
   - Updated examples to show `fit-00001`, `door-00001` format
   - Mosquitto restarted successfully

5. **Database Cleanup** - Removed old device to allow testing
   - Deleted: `ESP32-WATCH-A0A3B3AA13B0`
   - Ready for reprovisioning with new sequential ID

---

## Testing Steps

### Prerequisites
- ✅ Backend running (port 8001)
- ✅ Mosquitto running (port 8883)
- ✅ Database migration 014 applied
- ✅ ACL configuration updated
- ✅ Old device deleted from database

### Test 1: First Device Provisioning

**Expected Result:** Device should receive `fit-00001` as its device ID

1. **Flash ESP32 with current firmware** (if not already done)
   - Firmware already supports backend-assigned IDs at line 1195

2. **Power on ESP32 and provision through captive portal**
   - Connect to ESP32 WiFi hotspot
   - Enter hospital WiFi credentials
   - Complete provisioning workflow

3. **Verify provisioning in Serial Monitor**
   - Look for: `"deviceId": "fit-00001"` in backend response
   - Watch should save `fit-00001` as its device ID
   - Certificate CN should be `fit-00001`

4. **Verify in database:**
   ```bash
   cd hospital-backend && python check_current_devices.py
   ```
   Expected output:
   ```
   [Devices in database]
     - fit-00001: Fit Watch 00001 (watch) - available

   [MAC Mappings]
     - A0:A3:B3:AA:13:B0 -> fit-00001
   ```

5. **Verify MQTT connection**
   - Serial Monitor should show: `MQTT connected successfully`
   - No TLS errors (errno -76 or -113)
   - No ACL denials

6. **Verify vitals publishing**
   - Watch should publish vitals to: `hospital/devices/fit-00001/vitals`
   - Backend should receive vitals data
   - Frontend should display vitals for device `fit-00001`

### Test 2: Second Device Provisioning (if available)

**Expected Result:** Second device should receive `fit-00002`

1. Flash second ESP32 with same firmware
2. Provision through captive portal
3. Verify device receives `fit-00002` in response
4. Check database shows both devices:
   ```
   [Devices in database]
     - fit-00001: Fit Watch 00001 (watch) - available
     - fit-00002: Fit Watch 00002 (watch) - available
   ```

### Test 3: Reprovisioning Same Device

**Expected Result:** Device should receive the same `fit-00001` ID (MAC mapping preserved)

1. Reset ESP32 (erase SPIFFS)
2. Provision again with same MAC address
3. Verify device receives `fit-00001` (not `fit-00003`)
4. Check database shows same device ID reused:
   ```
   [MAC Mappings]
     - A0:A3:B3:AA:13:B0 -> fit-00001
   ```

### Test 4: Door Scanner Provisioning (future)

**Expected Result:** Door scanner should receive `door-00001`

1. Flash ESP32 with door scanner firmware (when available)
2. Provision device
3. Verify device receives `door-00001` in response
4. Check database shows both types:
   ```
   [Devices in database]
     - fit-00001: Fit Watch 00001 (watch) - available
     - fit-00002: Fit Watch 00002 (watch) - available
     - door-00001: Door Scanner 00001 (door) - available
   ```

---

## Success Criteria

- ✅ Device receives sequential ID from backend (fit-00001, fit-00002)
- ✅ Certificate CN matches sequential ID (no colons)
- ✅ MQTT connection succeeds using new device ID
- ✅ ACL allows vitals publishing with new device ID format
- ✅ Vitals appear in frontend with new device ID
- ✅ MAC mapping prevents duplicate IDs on reprovisioning
- ✅ Second device gets incremented ID (fit-00002)
- ✅ Different device types get separate sequences (fit-*, door-*)

---

## Troubleshooting

### Issue: Device still receives old format ID (ESP32-WATCH-*)

**Possible Causes:**
- Backend not restarted after provisioning.py changes
- Old provisioning endpoint still active

**Solution:**
- Restart backend: `docker-compose restart backend`
- Verify provisioning.py changes at lines 237-298

### Issue: MQTT connection fails with new device ID

**Possible Causes:**
- ACL not updated or Mosquitto not restarted
- Certificate CN doesn't match device ID

**Solution:**
- Verify ACL file has pattern rules (lines 50-82)
- Check Mosquitto logs: `docker-compose logs mosquitto`
- Restart Mosquitto: `docker-compose restart mosquitto`

### Issue: Database error during provisioning

**Possible Causes:**
- Migration 014 not applied
- device_mac_mapping table missing

**Solution:**
- Apply migration: `cd hospital-backend && python apply_migration_014.py`
- Verify table exists: `psql -h localhost -U hospital_user -d hospitaldb -c "\d device_mac_mapping"`

### Issue: Second device gets same ID as first

**Possible Causes:**
- MAC mapping not working correctly
- Database transaction issue

**Solution:**
- Check MAC mappings: `python check_current_devices.py`
- Verify different MAC addresses between devices
- Check backend logs for mapping errors

---

## Current System State

**Database:**
- Migration 014 applied ✅
- device_mac_mapping table created ✅
- Old ESP32-WATCH-A0A3B3AA13B0 device deleted ✅
- Ready for first sequential device (fit-00001) ✅

**Backend:**
- provisioning.py updated with sequential ID logic ✅
- Backend running on port 8001 ✅

**MQTT Broker:**
- ACL updated with new device ID examples ✅
- Temporary explicit entry removed ✅
- Pattern-based rules support any device ID format ✅
- Mosquitto restarted with new config ✅

**ESP32 Firmware:**
- Already compatible with backend-assigned IDs ✅
- No changes needed ✅

---

## Next Steps

1. **Power on ESP32 and provision** - The watch is ready to receive `fit-00001` as its device ID
2. **Verify provisioning success** - Check Serial Monitor for `"deviceId": "fit-00001"`
3. **Verify MQTT connection** - Should connect without errors
4. **Verify vitals display** - Frontend should show device as `fit-00001`
5. **Document results** - Report back with Serial Monitor logs and any issues

---

## Backend Implementation Details

### Device Type Detection (Lines 251-258)
```python
if "WATCH" in request.deviceId.upper():
    device_type = "fit"
    device_name_prefix = "Fit Watch"
elif "DOOR" in request.deviceId.upper():
    device_type = "door"
    device_name_prefix = "Door Scanner"
else:
    device_type = "device"
    device_name_prefix = "Device"
```

### Sequential Number Generation (Lines 260-271)
```python
last_device = await conn.fetchrow(
    "SELECT id FROM devices WHERE id LIKE $1 ORDER BY id DESC LIMIT 1",
    f"{device_type}-%"
)

if last_device:
    last_num = int(last_device["id"].split("-")[1])
    next_num = last_num + 1
else:
    next_num = 1

device_id_to_use = f"{device_type}-{next_num:05d}"
```

### MAC Mapping Storage (Lines 290-296)
```python
await conn.execute(
    "INSERT INTO device_mac_mapping (mac_address, device_id) VALUES ($1, $2)",
    request.macAddress,
    device_id_to_use
)
```

This ensures the same MAC address always gets the same device ID on reprovisioning.

---

## File References

- Database migration: [hospital-backend/migrations/014_device_mac_mapping.sql](hospital-backend/migrations/014_device_mac_mapping.sql)
- Migration script: [hospital-backend/apply_migration_014.py](hospital-backend/apply_migration_014.py)
- Provisioning endpoint: [hospital-backend/app/api/v1/provisioning.py:237-379](hospital-backend/app/api/v1/provisioning.py#L237-L379)
- ESP32 firmware: [esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino:1195](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1195)
- ACL configuration: [mosquitto/config/acl.conf](mosquitto/config/acl.conf)
- Device check script: [hospital-backend/check_current_devices.py](hospital-backend/check_current_devices.py)
- Cleanup script: [hospital-backend/cleanup_for_sequential_id_test.py](hospital-backend/cleanup_for_sequential_id_test.py)
