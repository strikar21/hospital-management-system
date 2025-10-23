# ESP32 Hospital Watch - HMAC Authentication Version

## What's New in v3.2.0

This version adds **HMAC-SHA256 authentication** for secure communication with the hospital backend.

### Key Changes from v3.1.0:

1. **HMAC-SHA256 Authentication**
   - All runtime requests (register, heartbeat) now use HMAC signatures
   - Factory secret embedded in firmware (same for all devices)
   - MAC address + timestamp + endpoint used for signature

2. **NTP Time Synchronization**
   - Syncs with NTP server on WiFi connection
   - Prevents replay attacks (5-minute window)
   - Auto-resyncs every hour

3. **New Authentication Headers**
   ```
   X-Device-MAC: AA:BB:CC:DD:EE:FF
   X-Device-Signature: <hmac-sha256-hex>
   X-Timestamp: <unix-timestamp>
   ```

4. **Staff-Authenticated Provisioning** (unchanged from v3.1.0)
   - Still requires Provisioner ID + Password
   - This part didn't change

---

## Setup Instructions

### 1. Arduino IDE Configuration

**Required Libraries:**
```
WiFi (built-in)
WebServer (built-in)
DNSServer (built-in)
HTTPClient (built-in)
ArduinoJson (install via Library Manager - v7.x)
Preferences (built-in)
PubSubClient (install via Library Manager)
mbedtls (built-in ESP32 crypto library)
```

### 2. Factory Secret Configuration

**IMPORTANT:** Before uploading to production devices, change this line:

```cpp
const char* FACTORY_SECRET = "CHANGE_THIS_IN_PRODUCTION_ESP32_HMAC_SECRET_KEY_MIN_64_CHARS_REQUIRED";
```

This **must match** the backend's `ESP32_FACTORY_SECRET` environment variable.

### 3. NTP Configuration

Default is IST (UTC+5:30):
```cpp
const long GMT_OFFSET_SEC = 19800;  // IST
```

For other timezones, change accordingly:
- UTC: `0`
- EST: `-18000` (UTC-5)
- PST: `-28800` (UTC-8)

---

## How It Works

### Phase 1: WiFi Setup (Captive Portal)
1. Device creates "HospitalWatch" WiFi network
2. User connects and enters:
   - WiFi credentials
   - Hospital server IP
   - Provisioner credentials (TEC0001/tech123)

### Phase 2: Time Sync
1. Device connects to WiFi
2. Syncs time with NTP server (pool.ntp.org)
3. Time sync required for HMAC authentication

### Phase 3: Provisioning (Staff Auth)
1. Device sends provision request with staff credentials:
   ```json
   {
     "macaddress": "AA:BB:CC:DD:EE:FF",
     "devicetype": "watch",
     "firmwareversion": "3.2.0",
     "provisionerid": "TEC0001",
     "provisionerpassword": "tech123"
   }
   ```
2. Backend validates staff credentials
3. Device receives ID and serial number

### Phase 4: Registration (HMAC Auth)
1. Device computes HMAC signature:
   ```
   Message = MAC + Timestamp + Endpoint
   Signature = HMAC-SHA256(FactorySecret, Message)
   ```
2. Sends register request with HMAC headers
3. Backend validates signature

### Phase 5: Runtime (HMAC Auth)
- Heartbeat every 30 seconds (HMAC authenticated)
- Vitals via MQTT when assigned to patient
- All HTTP requests include HMAC headers

---

## HMAC Signature Computation

```cpp
// Example for /api/v1/esp32/register endpoint
String macAddress = "AA:BB:CC:DD:EE:FF";
String timestamp = "1729175000";
String endpoint = "/api/v1/esp32/register";

String message = macAddress + timestamp + endpoint;
// Message = "AA:BB:CC:DD:EE:FF1729175000/api/v1/esp32/register"

String signature = computeHMAC(message);
// Uses mbedtls HMAC-SHA256 with FACTORY_SECRET
```

---

## Missing Web Handlers

**NOTE:** The file is incomplete - you need to copy 4 web handler functions from your original `esp32_hospital_watch_complete.ino`:

1. `handleRoot()` - Lines 240-323
2. `handleScan()` - Lines 325-330
3. `handleConfigure()` - Lines 332-394
4. `handleStatus()` - Lines 396-425

These handle the captive portal web interface and haven't changed.

---

## Testing with Your ESP32

### Test 1: Provisioning
1. Upload firmware to ESP32
2. Connect to "HospitalWatch" WiFi
3. Go to any website (redirects to captive portal)
4. Fill in:
   - WiFi: Your network
   - Server IP: `192.168.0.113` (or your server)
   - Provisioner: `TEC0001` / `tech123`
5. Watch Serial Monitor for:
   ```
   ✅ WiFi Connected!
   ✅ NTP synced: ...
   🔄 Attempting device provisioning...
   🎉 DEVICE PROVISIONED!
   ```

### Test 2: HMAC Registration
After provisioning, watch for:
```
🔄 Registering device with HMAC authentication...
🔐 HMAC Headers:
   MAC: AA:BB:CC:DD:EE:FF
   Timestamp: 1729175000
   Signature: a1b2c3d4...
✅ Device registered successfully
```

### Test 3: Heartbeat
Every 30 seconds:
```
💓 Heartbeat sent (HMAC authenticated)
```

---

## Troubleshooting

### "Time not synced!" errors
**Problem:** NTP sync failed
**Solution:**
- Check WiFi connection
- Verify NTP server reachable (`pool.ntp.org`)
- Check firewall allows NTP (UDP port 123)

### "Registration failed: 401" errors
**Problem:** HMAC signature validation failed
**Solution:**
- Verify `FACTORY_SECRET` matches backend
- Check time is synced (timestamp must be recent)
- Verify MAC address format (AA:BB:CC:DD:EE:FF)

### "Provisioning failed: 403" errors
**Problem:** Staff authentication failed
**Solution:**
- Check provisioner credentials (TEC0001/tech123)
- Verify staff member exists in backend database
- Confirm role is Technician or Provisioner

---

## Security Notes

1. **Factory Secret:** In production, use a strong 64+ character random string
2. **HTTPS:** For production, use HTTPS instead of HTTP
3. **Time Sync:** Critical for replay attack prevention
4. **Timestamp Window:** Backend allows 5-minute clock drift
5. **Constant-Time Comparison:** Backend uses timing-attack-resistant validation

---

## Deployment Checklist

- [ ] Change FACTORY_SECRET in firmware
- [ ] Update FACTORY_SECRET in backend `.env`
- [ ] Configure correct timezone (GMT_OFFSET_SEC)
- [ ] Test NTP connectivity
- [ ] Test provisioning with staff credentials
- [ ] Test HMAC authentication with backend
- [ ] Verify heartbeat working
- [ ] Document provisioner credentials for hospital staff

---

## Backend Configuration

Ensure backend has matching configuration in `.env`:

```env
ESP32_FACTORY_SECRET=CHANGE_THIS_IN_PRODUCTION_ESP32_HMAC_SECRET_KEY_MIN_64_CHARS_REQUIRED
ESP32_TIMESTAMP_WINDOW=300
```

---

## Files in This Directory

- `esp32_hospital_watch_hmac.ino` - Main firmware (incomplete - needs web handlers)
- `README.md` - This file

---

## Next Steps

1. Copy the 4 web handler functions from original firmware
2. Verify FACTORY_SECRET matches backend
3. Upload to ESP32 and test provisioning
4. Monitor Serial output for HMAC authentication
5. Verify backend receives requests successfully

---

**Version:** 3.2.0
**Date:** October 14, 2025
**Backend Compatibility:** Requires backend with HMAC authentication (completed)
**Status:** Ready for testing (after adding web handlers)
