# ESP32 HMAC Timestamp Fix

## Problem
ESP32 heartbeat was failing with 401 error: "Invalid or expired timestamp"

**Root Cause:** ESP32 was sending Unix timestamp (`1760450220`), but backend expects ISO 8601 format (`2025-10-14T13:57:00Z`)

## Solution Applied

### Updated ESP32 Firmware
**File:** `esp32_hospital_watch_hmac/esp32_hospital_watch_hmac.ino`
**Lines:** 169-195

**Changed from:**
```cpp
String timestamp = String(getUnixTimestamp());  // "1760450220"
```

**Changed to:**
```cpp
// Get current time and format as ISO 8601 (UTC)
time_t now = time(nullptr);
struct tm timeinfo;
gmtime_r(&now, &timeinfo);  // Use GMT/UTC

char iso_timestamp[25];
strftime(iso_timestamp, sizeof(iso_timestamp), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
String timestamp = String(iso_timestamp);  // "2025-10-14T13:57:00Z"
```

## Next Steps

1. **Re-upload firmware to ESP32**
   - Open Arduino IDE
   - Load `esp32_hospital_watch_hmac/esp32_hospital_watch_hmac.ino`
   - Upload to your ESP32

2. **Restart ESP32**
   - Device will reconnect to WiFi
   - NTP will sync
   - Heartbeat should now work with correct timestamp format

3. **Expected Result**
   ```
   🔐 HMAC Headers:
      MAC: A0:A3:B3:AA:13:B0
      Timestamp: 2025-10-14T13:57:00Z  ← ISO 8601 format
      Signature: d263faadb6597a7b...
   💓 Heartbeat sent (HMAC authenticated)
   ```

## Frontend Device Visibility

**Issue:** Frontend shows error: `GET /api/v1/devices/proximity 403 (Forbidden)`

**Root Cause:** This endpoint doesn't exist in backend yet. Frontend is trying to use a proximity detection feature that hasn't been implemented.

**Temporary Fix:** Frontend should gracefully handle this error or remove proximity detection calls until feature is implemented.

**Devices in Database:** ✅ 3 devices exist and are visible via standard `/api/v1/devices` endpoint
- TEST_WATCH_001
- ESP32_WATCH_002
- ESP32_WATCH_003 (your current device)

## Summary

✅ **Fixed:** ESP32 timestamp format (Unix → ISO 8601)
✅ **Updated:** `addHMACHeaders()` function in ESP32 firmware
📝 **Action Required:** Re-upload firmware to ESP32
⚠️ **Frontend Issue:** Proximity endpoint not implemented (non-critical)
