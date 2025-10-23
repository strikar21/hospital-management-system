# ESP32 Security Fix - Registration Authentication

**Date:** October 14, 2025
**Priority:** 🔴 CRITICAL SECURITY VULNERABILITY
**Issue:** Registration endpoint allows device spoofing

---

## Security Vulnerability Analysis

### Current Flow (INSECURE ❌)

1. **Provisioning:** ✅ Secure
   - Staff authenticates with credentials
   - Device gets assigned ID + serial number
   - **No device key issued**

2. **Registration:** ❌ **UNSECURED**
   - NO authentication
   - Anyone can call with any device ID
   - Can create or update devices
   - **SPOOFING POSSIBLE**

3. **Heartbeat:** ❌ **UNSECURED**
   - NO authentication
   - Updates battery, status, lastSeen
   - **SPOOFING POSSIBLE**

4. **Vitals:** ✅ Partially Secured
   - Requires `X-Device-Key` header
   - Validates device assignment
   - **BUT: Where does device get the key?**

---

## Root Cause

**Problem:** Device key (deviceKey) is stored in database but:
1. ❌ Never issued during provisioning
2. ❌ Not returned in provisioning response
3. ❌ Not validated in registration/heartbeat

**Result:** Device authentication is incomplete

---

## Proposed Security Model

### Option 1: Device Key Based (RECOMMENDED ✅)

**Flow:**
1. **Provisioning** (Staff authenticated)
   - Staff provides MAC address + credentials
   - Backend generates: `deviceId`, `serialNumber`, **`deviceKey`** (UUID)
   - Returns: `deviceId`, `serialNumber`, **`deviceKey`**
   - Staff must **securely configure** ESP32 with device key

2. **Registration** (Device authenticated)
   - ESP32 sends: `deviceId`, `macAddress`, `deviceKey` (in header or body)
   - Backend validates: MAC + device key match
   - Only updates if authentication succeeds

3. **Heartbeat** (Device authenticated)
   - ESP32 sends: `deviceId`, `deviceKey` (in header)
   - Backend validates before updating

4. **Vitals** (Device authenticated)
   - Already implemented ✅

**Pros:**
- ✅ Prevents spoofing (requires secret key)
- ✅ No password hashing needed
- ✅ Key can be rotated if compromised
- ✅ Simple to implement

**Cons:**
- ⚠️ Staff must securely enter key into ESP32
- ⚠️ Key stored in ESP32 firmware (could be extracted)

---

### Option 2: MAC Address + Shared Secret (LESS SECURE)

**Flow:**
1. Provisioning: Store MAC address
2. Registration: Validate MAC address matches
3. Problem: ❌ MAC addresses can be spoofed

**Verdict:** ❌ NOT RECOMMENDED

---

### Option 3: Certificate-Based (MOST SECURE, COMPLEX)

**Flow:**
1. Provisioning: Issue X.509 certificate
2. Registration: Validate certificate
3. Problem: ⚠️ Very complex for ESP32, certificate management

**Verdict:** ⚠️ OVERKILL for this use case

---

## Implementation Plan

### Phase 1: Update Provisioning ✅

**File:** `hospital-backend/app/api/v1/esp32.py`

**Changes to `/provision` endpoint (line 32-120):**

```python
@router.post("/provision")
async def provisionEsp32Device(provisionData: Dict[str, Any]):
    # ... existing validation ...

    # Generate device key (NEW)
    deviceKey = str(uuid.uuid4())  # Unique secret for this device

    # Create new device record (UPDATED)
    await conn.execute("""
        INSERT INTO devices (id, deviceType, serialNumber, macAddress,
                           firmwareVersion, batteryLevel, status, location,
                           deviceKey, lastSeen, createdAt, updatedAt)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW(), NOW())
    """, deviceId, deviceType, serialNumber, macAddress,
         firmwareVersion, 100, 'available', 'Device Pool', deviceKey)

    # Return device key to provisioner (NEW)
    return JSONResponse({
        "success": True,
        "deviceId": deviceId,
        "serialNumber": serialNumber,
        "deviceKey": deviceKey,  # ← CRITICAL: Staff must configure ESP32 with this
        "provisionedby": provisioner['name'],
        "status": "new"
    })
```

**Database Check:**
- Verify `devices.deviceKey` column exists (line 18 in devices table: `deviceKey TEXT`)
- ✅ Column already exists in schema

---

### Phase 2: Secure Registration Endpoint 🔒

**File:** `hospital-backend/app/api/v1/esp32.py`

**Changes to `/register` endpoint (line 158-198):**

```python
@router.post("/register")
async def registerEsp32Device(
    deviceData: Dict[str, Any],
    device_key: str = Header(None, alias="X-Device-Key")  # ← NEW: Require authentication
):
    """
    Register ESP32 device in the system
    Called by ESP32 on startup

    Security: Requires X-Device-Key header for authentication
    """
    try:
        # Transform ESP32 lowercase fields to backend camelCase
        deviceData = ESP32FieldMapper.transform_request(deviceData)

        deviceId = deviceData.get('deviceId')
        macAddress = deviceData.get('macAddress')

        if not deviceId or not macAddress:
            raise HTTPException(status_code=400, detail="Device ID and MAC address required")

        # ====================================
        # NEW: AUTHENTICATE DEVICE
        # ====================================
        if not device_key:
            logger.warning(f"⚠️ Registration attempt without device key: {deviceId}")
            raise HTTPException(status_code=401, detail="Device key required (X-Device-Key header)")

        async with getDbConnection() as conn:
            # Validate device exists and key matches
            device = await conn.fetchrow(
                'SELECT id, "macAddress", "deviceKey" FROM devices WHERE id = $1',
                deviceId
            )

            if not device:
                logger.warning(f"❌ Registration failed: Device {deviceId} not found (must provision first)")
                raise HTTPException(status_code=404, detail="Device not provisioned")

            if device['deviceKey'] != device_key:
                logger.warning(f"❌ Registration failed: Invalid device key for {deviceId}")
                raise HTTPException(status_code=403, detail="Invalid device key")

            # Optionally verify MAC address matches (extra security)
            if device['macAddress'] != macAddress:
                logger.warning(f"⚠️ MAC address mismatch for {deviceId}: expected {device['macAddress']}, got {macAddress}")
                # Could choose to reject or just log warning

            # ====================================
            # AUTHENTICATED: Update device
            # ====================================
            await conn.execute("""
                UPDATE devices
                SET "batteryLevel" = $2, "firmwareVersion" = $3,
                    "lastSeen" = NOW(), "updatedAt" = NOW(), status = 'available'
                WHERE id = $1
            """, deviceId, deviceData.get('batteryLevel', 100), deviceData.get('firmwareVersion', '3.0.0'))

            logger.info(f"✅ ESP32 device registered: {deviceId} (authenticated)")

        return JSONResponse({
            "success": True,
            "deviceId": deviceId,
            "message": "Device registered successfully",
            "servertime": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ESP32 registration error: {e}")
        raise HTTPException(status_code=500, detail="Device registration failed")
```

**Key Changes:**
1. ✅ Require `X-Device-Key` header
2. ✅ Validate device exists in database (must be provisioned first)
3. ✅ Validate device key matches
4. ✅ Log authentication failures
5. ❌ **REMOVE ability to create new devices** (must provision first)

---

### Phase 3: Secure Heartbeat Endpoint 🔒

**File:** `hospital-backend/app/api/v1/esp32.py`

**Changes to `/{deviceId}/heartbeat` endpoint (line 100-141):**

```python
@router.post("/{deviceId}/heartbeat")
async def deviceHeartbeat(
    deviceId: str,
    heartbeatData: Dict[str, Any],
    device_key: str = Header(None, alias="X-Device-Key")  # ← NEW: Require authentication
):
    """
    Receive heartbeat from ESP32 device
    Updates device status and battery level

    Security: Requires X-Device-Key header for authentication
    """
    try:
        # Transform ESP32 lowercase fields to backend camelCase
        heartbeatData = ESP32FieldMapper.transform_request(heartbeatData)

        # ====================================
        # NEW: AUTHENTICATE DEVICE
        # ====================================
        if not device_key:
            raise HTTPException(status_code=401, detail="Device key required")

        async with getDbConnection() as conn:
            # Validate device and key
            device = await conn.fetchrow(
                'SELECT id, "deviceKey" FROM devices WHERE id = $1',
                deviceId
            )

            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            if device['deviceKey'] != device_key:
                logger.warning(f"❌ Invalid device key for heartbeat: {deviceId}")
                raise HTTPException(status_code=403, detail="Invalid device key")

            # ====================================
            # AUTHENTICATED: Update device
            # ====================================
            batteryLevel = heartbeatData.get('batteryLevel', 100)
            signalStrength = heartbeatData.get('signalStrength', -50)

            await conn.execute("""
                UPDATE devices
                SET "batteryLevel" = $2, "lastSeen" = NOW(), "updatedAt" = NOW()
                WHERE id = $1
            """, deviceId, batteryLevel)

        logger.info(f"💓 Heartbeat from {deviceId}: Battery {batteryLevel}%, Signal {signalStrength}dBm")

        return JSONResponse({
            "success": True,
            "message": "Heartbeat received",
            "servertime": datetime.now().isoformat(),
            "batteryLevel": batteryLevel
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ESP32 heartbeat error: {e}")
        raise HTTPException(status_code=500, detail="Heartbeat processing failed")
```

---

### Phase 4: Emergency Alert Endpoint (Optional) 🔒

**File:** `hospital-backend/app/api/v1/esp32.py`

**Changes to `/{deviceId}/alert` endpoint (line 303-341):**

**Decision:** Should emergency alerts require authentication?

**Option A:** ✅ **Yes, require authentication** (RECOMMENDED)
- Pro: Prevents false alarms
- Pro: Audit trail (know which device sent alert)
- Con: Adds ~10ms latency

**Option B:** ❌ No authentication
- Pro: Faster (no validation)
- Con: Anyone can send false emergency alerts
- Verdict: ❌ **TOO RISKY**

**Implementation:**
```python
@router.post("/{deviceId}/alert")
async def receiveEmergencyAlert(
    deviceId: str,
    alertData: Dict[str, Any],
    device_key: str = Header(None, alias="X-Device-Key")  # ← NEW
):
    # Validate device key before broadcasting alert
    # ... similar to heartbeat validation ...
```

---

## ESP32 Firmware Changes Required

### Configuration
ESP32 must store **3 secrets**:
1. `DEVICE_ID` - Assigned during provisioning (e.g., "ESP32_WATCH_001")
2. `MAC_ADDRESS` - Hardware MAC
3. **`DEVICE_KEY`** - Secret UUID from provisioning (e.g., "a1b2c3d4-...")

### HTTP Headers
All authenticated endpoints require:
```cpp
HTTPClient http;
http.begin(url);
http.addHeader("Content-Type", "application/json");
http.addHeader("X-Device-Key", DEVICE_KEY);  // ← NEW
int httpCode = http.POST(payload);
```

### Updated Endpoint List
| Endpoint | Authentication | Header Required |
|----------|---------------|-----------------|
| `/provision` | ✅ Staff credentials | None (staff authenticated) |
| `/register` | ✅ **Device key** | **X-Device-Key** |
| `/heartbeat` | ✅ **Device key** | **X-Device-Key** |
| `/vitals` | ✅ Device key | X-Device-Key (already) |
| `/alert` | ✅ **Device key** | **X-Device-Key** |

---

## Testing Plan

### Test 1: Provisioning Returns Device Key ✅
```bash
curl -X POST http://localhost:8001/api/v1/esp32/provision \
  -H "Content-Type: application/json" \
  -d '{
    "macaddress": "AA:BB:CC:DD:EE:FF",
    "devicetype": "esp32Watch",
    "firmwareversion": "3.0.0",
    "provisionerid": "TEC0001",
    "provisionerpassword": "tech123"
  }'

# Expected response includes deviceKey:
{
  "deviceId": "ESP32_WATCH_002",
  "serialNumber": "SN_W002",
  "deviceKey": "uuid-here",  # ← NEW
  "status": "new"
}
```

### Test 2: Registration Requires Device Key 🔒
```bash
# WITHOUT key - should FAIL
curl -X POST http://localhost:8001/api/v1/esp32/register \
  -H "Content-Type: application/json" \
  -d '{
    "deviceid": "ESP32_WATCH_002",
    "macaddress": "AA:BB:CC:DD:EE:FF",
    "batterylevel": 100
  }'
# Expected: 401 Unauthorized

# WITH valid key - should SUCCEED
curl -X POST http://localhost:8001/api/v1/esp32/register \
  -H "Content-Type: application/json" \
  -H "X-Device-Key: <uuid-from-provisioning>" \
  -d '{
    "deviceid": "ESP32_WATCH_002",
    "macaddress": "AA:BB:CC:DD:EE:FF",
    "batterylevel": 100
  }'
# Expected: 200 OK

# WITH wrong key - should FAIL
curl -X POST http://localhost:8001/api/v1/esp32/register \
  -H "Content-Type: application/json" \
  -H "X-Device-Key: wrong-key" \
  -d '{
    "deviceid": "ESP32_WATCH_002",
    "macaddress": "AA:BB:CC:DD:EE:FF",
    "batterylevel": 100
  }'
# Expected: 403 Forbidden
```

### Test 3: Spoofing Attempt BLOCKED 🛡️
```bash
# Attacker tries to spoof existing device
curl -X POST http://localhost:8001/api/v1/esp32/register \
  -H "Content-Type: application/json" \
  -d '{
    "deviceid": "ESP32_WATCH_001",  # Someone else's device
    "macaddress": "FAKE:MAC:ADDR",
    "batterylevel": 50
  }'
# Expected: 401 Unauthorized (no key provided)

# Even with a key, wrong device ID
curl -X POST http://localhost:8001/api/v1/esp32/register \
  -H "Content-Type: application/json" \
  -H "X-Device-Key: attacker-key" \
  -d '{
    "deviceid": "ESP32_WATCH_001",
    "macaddress": "FAKE:MAC:ADDR"
  }'
# Expected: 403 Forbidden (key doesn't match)
```

---

## Migration Strategy

### Step 1: Database Check ✅
Check if `deviceKey` column exists:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'devices' AND column_name = 'deviceKey';
```

If missing, add column:
```sql
ALTER TABLE devices ADD COLUMN "deviceKey" TEXT;
```

### Step 2: Generate Keys for Existing Devices
```python
# Run this migration script
async def migrate_device_keys():
    async with getDbConnection() as conn:
        devices = await conn.fetch('SELECT id FROM devices WHERE "deviceKey" IS NULL')

        for device in devices:
            device_key = str(uuid.uuid4())
            await conn.execute(
                'UPDATE devices SET "deviceKey" = $1 WHERE id = $2',
                device_key, device['id']
            )
            print(f"Generated key for {device['id']}: {device_key}")
```

### Step 3: Update Backend Code
Apply all changes above to `esp32.py`

### Step 4: Test with curl
Run all 3 test scenarios above

### Step 5: Update ESP32 Firmware
Add device key storage and header transmission

---

## Security Improvements Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Provisioning** | ✅ Secure | ✅ Secure + returns key |
| **Registration** | ❌ No auth | ✅ **Device key required** |
| **Heartbeat** | ❌ No auth | ✅ **Device key required** |
| **Vitals** | ✅ Key required | ✅ Key required (unchanged) |
| **Alert** | ❌ No auth | ✅ **Device key required** |
| **Spoofing Risk** | 🔴 **HIGH** | ✅ **MITIGATED** |

---

## Alternative: Rate Limiting Only (NOT RECOMMENDED)

**Could we just rate-limit instead of authenticating?**

❌ **NO - Rate limiting is NOT authentication**

- Rate limiting stops **volume attacks** (DoS)
- Does NOT stop **targeted spoofing** (single attacker pretending to be device)
- Example attack: Attacker sends 1 heartbeat per minute as "ESP32_WATCH_001" → looks legitimate to rate limiter

**Verdict:** Rate limiting is **defense in depth**, not a replacement for authentication

---

## Rollout Plan

### Phase 1: Add Device Keys ✅
1. Verify `deviceKey` column exists
2. Generate keys for existing devices
3. Update provisioning endpoint
4. Test provisioning returns key

### Phase 2: Secure Registration 🔒
1. Update `/register` endpoint
2. Test authentication enforcement
3. Test spoofing prevention

### Phase 3: Secure Heartbeat 🔒
1. Update `/heartbeat` endpoint
2. Test authentication

### Phase 4: Secure Alerts 🔒
1. Update `/alert` endpoint
2. Test emergency workflow

### Phase 5: ESP32 Firmware Update 📱
1. Update firmware to store device key
2. Update firmware to send X-Device-Key header
3. Flash test device
4. Run end-to-end tests

---

## Approval Required

**Before implementing, confirm:**
1. ✅ You agree device key authentication is correct approach?
2. ✅ You want registration/heartbeat/alert endpoints secured?
3. ✅ You have a test ESP32 to update firmware?
4. ✅ You can flash ESP32 with device key after provisioning?

**Once approved, I will:**
1. Check database schema
2. Update `esp32.py` with authentication
3. Create migration script for existing devices
4. Create test scripts
5. Update documentation

---

**Status:** ⏳ AWAITING USER APPROVAL
**Priority:** 🔴 CRITICAL (security vulnerability)
**Estimated Time:** 1-2 hours to implement + test
