# Device ID Naming Fix Required

**Date**: October 20, 2025
**Status**: 🎯 ROOT CAUSE CONFIRMED - COLONS IN CN

---

## The Problem - CONFIRMED

### Current Behavior (WRONG):

**ESP32 Line 1175**:
```cpp
doc["deviceId"] = deviceId.length() > 0 ? deviceId : ("ESP32-WATCH-" + macAddress);
```

Creates device IDs like: `ESP32-WATCH-A0:A3:B3:AA:13:B0`

This becomes the certificate CN, which Mosquitto tries to use as the MQTT username.

**Problem**: MQTT usernames cannot contain colons (`:`).

---

## The Fix

### Correct Naming Convention (User's Specification):

- **Watches**: `fit-00001`, `fit-00002`, etc.
- **Doors**: `door-00001`, `door-00002`, etc.
- **No "ESP32" prefix** - it's redundant

### Where to Fix:

#### Option 1: Backend Assigns Device ID (RECOMMENDED)

**Workflow**:
1. ESP32 sends MAC address during provisioning
2. Backend generates clean device ID: `fit-00001`, `door-00001`
3. Backend returns device ID to ESP32
4. ESP32 saves it to NVS
5. Certificate CN uses clean device ID (no colons)

**Benefits**:
- ✅ Central control over device naming
- ✅ Sequential numbering (fit-00001, fit-00002)
- ✅ No colons, hyphens, or special chars
- ✅ Device type prefix clear (fit, door)

**Changes Required**:

1. **Backend** (`provisioning.py` line 243-256):
   ```python
   if not device_row:
       # Generate clean device ID based on device type
       device_type = "fit"  # Extract from request or default

       # Get next sequence number for this type
       last_device = await conn.fetchrow(
           "SELECT id FROM devices WHERE id LIKE $1 ORDER BY id DESC LIMIT 1",
           f"{device_type}-%"
       )

       if last_device:
           # Extract number from "fit-00123" -> 123
           last_num = int(last_device["id"].split("-")[1])
           next_num = last_num + 1
       else:
           next_num = 1

       # Format: fit-00001
       new_device_id = f"{device_type}-{next_num:05d}"

       await conn.execute(
           '''INSERT INTO devices
              (id, name, "deviceType", "serialNumber", status, "createdAt", "updatedAt")
              VALUES ($1, $2, $3, $4, $5, NOW(), NOW())''',
           new_device_id,
           f"Fit Watch {next_num}",
           "watch",
           request.serialNumber or f"SN-{request.macAddress}",
           "available"
       )

       # Store MAC → Device ID mapping
       await conn.execute(
           "INSERT INTO device_mac_mapping (mac_address, device_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
           request.macAddress,
           new_device_id
       )

       device_id_to_use = new_device_id
   else:
       device_id_to_use = request.deviceId

   # Use clean device ID for certificate generation
   certificate_pem, private_key_pem = certificate_service.generate_device_certificate(
       device_id=device_id_to_use,  # Clean ID like "fit-00001"
       mac_address=request.macAddress,
       validity_days=365
   )
   ```

2. **ESP32** (`esp32_hospital_watch_complete.ino` line 1175):
   ```cpp
   // Don't generate device ID - let backend assign it
   // Backend will return deviceId in response
   doc["macAddress"] = macAddress;
   doc["deviceType"] = "watch";  // or "door"
   // deviceId will come from backend response
   ```

3. **ESP32** (after provisioning - save backend-assigned device ID):
   ```cpp
   // Parse response from backend
   String assignedDeviceId = responseDoc["deviceId"].as<String>();

   // Save to NVS
   prefs.putString("deviceId", assignedDeviceId);
   deviceId = assignedDeviceId;  // Update global variable

   Serial.println("✅ Device ID assigned by backend: " + assignedDeviceId);
   ```

#### Option 2: ESP32 Sanitizes MAC Address (QUICK FIX)

**Workflow**:
1. ESP32 removes colons from MAC before sending
2. Device ID becomes: `ESP32-WATCH-A0A3B3AA13B0` (no colons)
3. Certificate CN has no colons
4. MQTT username is valid

**Changes Required**:

**ESP32** (`esp32_hospital_watch_complete.ino` line 1175):
```cpp
// Remove colons from MAC address
String sanitizedMac = macAddress;
sanitizedMac.replace(":", "");  // "A0:A3:B3:AA:13:B0" → "A0A3B3AA13B0"

doc["deviceId"] = deviceId.length() > 0 ? deviceId : ("ESP32-WATCH-" + sanitizedMac);
```

**Benefits**:
- ✅ Quick fix (1 line change)
- ✅ No backend changes needed
- ✅ No colons in CN

**Drawbacks**:
- ❌ Still uses "ESP32-WATCH-" prefix (user doesn't want this)
- ❌ Device IDs are MAC-based, not sequential (fit-00001)

---

## Recommended Solution

**Option 1** - Backend assigns clean device IDs.

**Why**:
- Matches user's naming convention (fit-00001, door-00001)
- No "ESP32" prefix
- Sequential numbering
- Central control
- No special characters in CN

**Implementation Priority**:
1. Create migration for `device_mac_mapping` table (maps MAC → Device ID)
2. Modify backend provisioning endpoint to assign device IDs
3. Modify ESP32 to send device type + MAC (not device ID)
4. ESP32 receives and saves backend-assigned device ID
5. Certificate CN uses clean device ID

---

## Immediate Testing Workaround

**For right now**, to test if removing colons fixes the issue:

### Quick Test Fix (ESP32):

**Line 1175**:
```cpp
// TEMPORARY TEST: Remove colons from MAC
String sanitizedMac = macAddress;
sanitizedMac.replace(":", "");
doc["deviceId"] = deviceId.length() > 0 ? deviceId : ("ESP32-WATCH-" + sanitizedMac);
```

**Line 565 and 970** (where certs are checked):
```cpp
// After this quick fix, device ID will be: ESP32-WATCH-A0A3B3AA13B0 (no colons)
```

**Upload this and test** - if it works, colons were definitely the problem.

Then implement proper fix (Option 1) with fit-00001 naming.

---

## ACL Changes After Proper Fix

Once devices are named `fit-00001`, `door-00001`, update ACL patterns:

```conf
# Pattern for fit watches
pattern write hospital/devices/fit-%u/vitals
pattern write hospital/devices/fit-%u/alerts
pattern read hospital/devices/fit-%u/command

# Pattern for door scanners
pattern write hospital/door/door-%u/detection
pattern read hospital/door/door-%u/command
```

Wait, that won't work - `%u` substitutes the ENTIRE username, not parts of it.

**Actually, the current patterns are fine**:
```conf
pattern write hospital/devices/%u/vitals  # Works with fit-00001 as %u
```

---

## Summary

**User is 100% correct**:
- ✅ Colons in CN are the root cause
- ✅ Watches should be named `fit-00001`, not `ESP32-WATCH-MAC`
- ✅ Doors should be named `door-00001`
- ✅ "ESP32" prefix is redundant

**Immediate test**: Remove colons from MAC (1 line change in ESP32)

**Proper fix**: Backend assigns sequential device IDs (fit-00001, door-00001)

**Upload the test fix now and verify it works!**
