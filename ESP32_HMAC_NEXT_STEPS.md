# ESP32 HMAC Authentication - Remaining Implementation Steps

**Date:** 2025-10-14
**Current Status:** Configuration & Middleware Complete, Endpoint Updates Needed

---

## ✅ What's Been Completed

1. **Backend Configuration** ([config.py](hospital-backend/app/core/config.py))
   - Added `esp32FactorySecret` and `esp32TimestampWindow` config

2. **HMAC Middleware** ([esp32_hmac_auth.py](hospital-backend/app/middleware/esp32_hmac_auth.py))
   - Complete HMAC-SHA256 authentication system
   - Timestamp validation, MAC format validation
   - Cryptographically secure signature verification

3. **Provisioning Endpoint** ([esp32.py:33-127](hospital-backend/app/api/v1/esp32.py#L33-L127))
   - Staff authentication working (Provisioner ID + Password)
   - Removed deviceKey generation
   - Device provisions with MAC address only

4. **Imports Added** ([esp32.py:20-21](hospital-backend/app/api/v1/esp32.py#L20-L21))
   - `ESP32HMACAuth` and `settings` imported

---

## 📋 Remaining Tasks

### Task 1: Initialize HMAC Authenticator Instance

**Location:** After imports, before router definition

**Add this code:**
```python
# Initialize HMAC authenticator
hmac_auth = ESP32HMACAuth(
    factory_secret=settings.esp32FactorySecret,
    timestamp_window=settings.esp32TimestampWindow
)
logger.info("✅ ESP32 HMAC authenticator initialized")
```

---

### Task 2: Update `/register` Endpoint

**Current Location:** Lines 158-233
**Current Auth:** `X-Device-Key` header
**New Auth:** `X-Device-MAC`, `X-Device-Signature`, `X-Timestamp` headers

**Changes Needed:**

```python
@router.post("/register")
async def registerEsp32Device(
    request: Request,
    deviceData: Dict[str, Any],
    device_mac: str = Header(None, alias="X-Device-MAC"),
    device_signature: str = Header(None, alias="X-Device-Signature"),
    device_timestamp: str = Header(None, alias="X-Timestamp")
):
    """
    Register ESP32 device in the system
    Called by ESP32 after provisioning

    Security: Requires HMAC-SHA256 authentication
    - X-Device-MAC: Device MAC address
    - X-Device-Signature: HMAC signature
    - X-Timestamp: ISO 8601 timestamp
    """
    try:
        # Transform ESP32 lowercase fields to backend camelCase
        deviceData = ESP32FieldMapper.transform_request(deviceData)

        macAddress = deviceData.get('macAddress')
        firmwareVersion = deviceData.get('firmwareVersion', '3.0.0')
        batteryLevel = deviceData.get('batteryLevel', 100)

        if not macAddress:
            raise HTTPException(status_code=400, detail="MAC address required")

        # ====================================
        # AUTHENTICATE DEVICE VIA HMAC
        # ====================================
        endpoint = "/api/v1/esp32/register"
        is_valid, validated_mac, error_msg = hmac_auth.authenticate_device(
            device_mac,
            device_signature,
            device_timestamp,
            endpoint
        )

        if not is_valid:
            logger.warning(f"❌ Registration failed: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        # Verify MAC in payload matches authenticated MAC
        if macAddress != validated_mac:
            logger.warning(f"⚠️ MAC mismatch: payload={macAddress}, header={validated_mac}")
            raise HTTPException(status_code=403, detail="MAC address mismatch")

        async with getDbConnection() as conn:
            # Find device by MAC address
            device = await conn.fetchrow(
                'SELECT id, "serialNumber", status FROM devices WHERE "macAddress" = $1',
                validated_mac
            )

            if not device:
                logger.warning(f"❌ Registration failed: Device {validated_mac} not provisioned")
                raise HTTPException(status_code=404, detail="Device not provisioned. Ask staff to provision device first.")

            deviceId = device['id']

            # ====================================
            # AUTHENTICATED: Update device
            # ====================================
            await conn.execute("""
                UPDATE devices
                SET "batteryLevel" = $2, "firmwareVersion" = $3,
                    "lastSeen" = NOW(), "updatedAt" = NOW(), status = 'available'
                WHERE id = $1
            """, deviceId, batteryLevel, firmwareVersion)

            logger.info(f"✅ ESP32 device registered: {deviceId} (MAC: {validated_mac}, HMAC authenticated)")

        return JSONResponse({
            "success": True,
            "deviceId": deviceId,
            "serialNumber": device['serialNumber'],
            "message": "Device registered successfully",
            "servertime": datetime.now().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ESP32 registration error: {e}")
        raise HTTPException(status_code=500, detail="Device registration failed")
```

---

### Task 3: Update `/{deviceId}/heartbeat` Endpoint

**Current Location:** Lines 235-296
**Current Auth:** `X-Device-Key` header
**New Auth:** `X-Device-MAC`, `X-Device-Signature`, `X-Timestamp` headers

**Changes Needed:**

```python
@router.post("/{deviceId}/heartbeat")
async def deviceHeartbeat(
    request: Request,
    deviceId: str,
    heartbeatData: Dict[str, Any],
    device_mac: str = Header(None, alias="X-Device-MAC"),
    device_signature: str = Header(None, alias="X-Device-Signature"),
    device_timestamp: str = Header(None, alias="X-Timestamp")
):
    """
    Receive heartbeat from ESP32 device
    Updates device status and battery level

    Security: Requires HMAC-SHA256 authentication
    """
    try:
        # Transform ESP32 lowercase fields to backend camelCase
        heartbeatData = ESP32FieldMapper.transform_request(heartbeatData)

        batteryLevel = heartbeatData.get('batteryLevel', 100)
        signalStrength = heartbeatData.get('signalStrength', -50)

        # ====================================
        # AUTHENTICATE DEVICE VIA HMAC
        # ====================================
        endpoint = f"/api/v1/esp32/{deviceId}/heartbeat"
        is_valid, validated_mac, error_msg = hmac_auth.authenticate_device(
            device_mac,
            device_signature,
            device_timestamp,
            endpoint
        )

        if not is_valid:
            logger.warning(f"❌ Heartbeat failed: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        async with getDbConnection() as conn:
            # Verify device exists and MAC matches
            device = await conn.fetchrow(
                'SELECT id, "macAddress" FROM devices WHERE id = $1',
                deviceId
            )

            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            if device['macAddress'] != validated_mac:
                logger.warning(f"⚠️ MAC mismatch for {deviceId}: expected {device['macAddress']}, got {validated_mac}")
                raise HTTPException(status_code=403, detail="Device ID / MAC mismatch")

            # ====================================
            # AUTHENTICATED: Update device
            # ====================================
            await conn.execute("""
                UPDATE devices
                SET "batteryLevel" = $2, "lastSeen" = NOW(), "updatedAt" = NOW(),
                    status = CASE WHEN status = 'offline' THEN 'available' ELSE status END
                WHERE id = $1
            """, deviceId, batteryLevel)

        logger.info(f"💓 Heartbeat from {deviceId}: Battery {batteryLevel}%, Signal {signalStrength}dBm (HMAC authenticated)")

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

### Task 4: Update `/{deviceId}/vitals/{patientId}` Endpoint

**Current Location:** Lines 298-420
**Current Auth:** `verify_device_key()` function
**New Auth:** `X-Device-MAC`, `X-Device-Signature`, `X-Timestamp` headers

**Changes Needed:**

```python
@router.post("/{deviceId}/vitals/{patientId}")
@limiter.limit("100/minute")  # Allow 100 vitals updates per minute per device
async def receiveVitalsData(
    request: Request,
    deviceId: str,
    patientId: str,
    vitalsData: Dict[str, Any],
    device_mac: str = Header(None, alias="X-Device-MAC"),
    device_signature: str = Header(None, alias="X-Device-Signature"),
    device_timestamp: str = Header(None, alias="X-Timestamp")
):
    """
    Receive vitals data from ESP32 device
    Stores in TimescaleDB and broadcasts to WebSocket subscribers

    Security:
    - Requires HMAC-SHA256 authentication
    - Rate limited to 100 requests per minute per device
    - Validates device is assigned to patient
    """
    try:
        # Transform ESP32 lowercase fields to backend camelCase
        vitalsData = ESP32FieldMapper.transform_request(vitalsData)
        logger.debug(f"🔄 Transformed ESP32 vitals data to camelCase for device {deviceId}")

        # ====================================
        # AUTHENTICATE DEVICE VIA HMAC
        # ====================================
        endpoint = f"/api/v1/esp32/{deviceId}/vitals/{patientId}"
        is_valid, validated_mac, error_msg = hmac_auth.authenticate_device(
            device_mac,
            device_signature,
            device_timestamp,
            endpoint
        )

        if not is_valid:
            logger.warning(f"❌ Vitals upload failed: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        # Validate that device is assigned to this patient
        async with getDbConnection() as conn:
            # Verify device exists and MAC matches
            device = await conn.fetchrow(
                'SELECT id, "macAddress" FROM devices WHERE id = $1',
                deviceId
            )

            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            if device['macAddress'] != validated_mac:
                logger.warning(f"⚠️ Device {deviceId} MAC mismatch")
                raise HTTPException(status_code=403, detail="Device ID / MAC mismatch")

            # Check patient exists
            patient = await conn.fetchrow('SELECT id FROM patients WHERE id = $1', patientId)
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")

            # Check device assignment via deviceassignments table
            assignment = await conn.fetchrow(
                'SELECT "deviceId" FROM deviceassignments WHERE "patientId" = $1 AND status = \'active\'',
                patientId
            )
            if not assignment or assignment['deviceId'] != deviceId:
                logger.warning(f"⚠️ Device {deviceId} sent vitals for patient {patientId} but not assigned")
                raise HTTPException(status_code=403, detail="Device not assigned to this patient")

        # ... (rest of vitals processing logic remains the same) ...
```

---

### Task 5: Update `/{deviceId}/alert` Endpoint

**Current Location:** Lines 422-489
**Current Auth:** `X-Device-Key` header
**New Auth:** `X-Device-MAC`, `X-Device-Signature`, `X-Timestamp` headers

**Changes Needed:**

```python
@router.post("/{deviceId}/alert")
async def receiveEmergencyAlert(
    request: Request,
    deviceId: str,
    alertData: Dict[str, Any],
    device_mac: str = Header(None, alias="X-Device-MAC"),
    device_signature: str = Header(None, alias="X-Device-Signature"),
    device_timestamp: str = Header(None, alias="X-Timestamp")
):
    """
    Receive emergency alert from ESP32 device

    Security: Requires HMAC-SHA256 authentication
    Prevents false emergency alerts from unauthorized devices
    """
    try:
        # ====================================
        # AUTHENTICATE DEVICE VIA HMAC
        # ====================================
        endpoint = f"/api/v1/esp32/{deviceId}/alert"
        is_valid, validated_mac, error_msg = hmac_auth.authenticate_device(
            device_mac,
            device_signature,
            device_timestamp,
            endpoint
        )

        if not is_valid:
            logger.warning(f"❌ Alert rejected: {error_msg}")
            raise HTTPException(status_code=401, detail=error_msg)

        async with getDbConnection() as conn:
            # Verify device exists and MAC matches
            device = await conn.fetchrow(
                'SELECT id, "macAddress" FROM devices WHERE id = $1',
                deviceId
            )

            if not device:
                raise HTTPException(status_code=404, detail="Device not found")

            if device['macAddress'] != validated_mac:
                logger.warning(f"⚠️ Device {deviceId} MAC mismatch in alert")
                raise HTTPException(status_code=403, detail="Device ID / MAC mismatch")

        # ====================================
        # AUTHENTICATED: Process alert
        # ====================================
        # Transform ESP32 lowercase fields to backend camelCase
        alertData = ESP32FieldMapper.transform_request(alertData)

        patientId = alertData.get('patientId')
        alertType = alertData.get('alertType', 'emergency')
        message = alertData.get('message', 'Emergency button pressed')
        vitals = alertData.get('vitals', {})

        # Broadcast emergency alert
        alertPayload = {
            'severity': alertType,
            'message': message,
            'source': f'Device {deviceId}',
            'vitals': vitals,
            'deviceId': deviceId
        }

        await connectionManager.sendAlert(patientId, alertPayload)

        logger.warning(f"🚨 Emergency alert from {deviceId} for patient {patientId}: {message} (HMAC authenticated)")

        return JSONResponse({
            "success": True,
            "message": "Emergency alert broadcasted",
            "alertid": str(uuid.uuid4())
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ ESP32 alert error: {e}")
        raise HTTPException(status_code=500, detail="Alert processing failed")
```

---

### Task 6: Create Database Migration

**File:** `hospital-backend/migrations/009_remove_device_key.sql` (NEW)

```sql
-- Migration 009: Remove deviceKey column (replaced by HMAC authentication)
-- Date: 2025-10-14
-- Purpose: Switch from per-device keys to HMAC-based authentication

BEGIN;

-- Step 1: Drop unique constraint on deviceKey (if exists)
ALTER TABLE devices DROP CONSTRAINT IF EXISTS devices_deviceKey_key;

-- Step 2: Remove deviceKey column (no longer needed)
ALTER TABLE devices DROP COLUMN IF EXISTS "deviceKey";

-- Step 3: Add index on macAddress for fast lookups (if not exists)
CREATE INDEX IF NOT EXISTS idx_devices_mac ON devices("macAddress");

-- Step 4: Add comment documenting authentication change
COMMENT ON TABLE devices IS 'ESP32 devices authenticated via HMAC-SHA256 using factory secret + MAC address (deviceKey removed in migration 009)';

COMMIT;
```

**Rollback File:** `hospital-backend/migrations/009_rollback.sql` (NEW)

```sql
-- Rollback 009: Re-add deviceKey column

BEGIN;

-- Add deviceKey column back
ALTER TABLE devices ADD COLUMN IF NOT EXISTS "deviceKey" TEXT;

-- Add unique constraint
ALTER TABLE devices ADD CONSTRAINT devices_deviceKey_key UNIQUE ("deviceKey");

-- Remove comment
COMMENT ON TABLE devices IS 'ESP32 devices';

COMMIT;
```

**Apply Migration Script:** `hospital-backend/apply_migration_009.py` (NEW)

```python
"""Apply migration 009: Remove deviceKey column"""
import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def apply_migration():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    try:
        logger.info("🔄 Applying migration 009: Remove deviceKey column...")

        # Read migration SQL
        with open('migrations/009_remove_device_key.sql', 'r') as f:
            migration_sql = f.read()

        # Execute migration
        await conn.execute(migration_sql)

        logger.info("✅ Migration 009 applied successfully")

        # Verify column removed
        columns = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'devices' AND column_name = 'deviceKey'
        """)

        if not columns:
            logger.info("✅ Verified: deviceKey column removed")
        else:
            logger.warning("⚠️ deviceKey column still exists!")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())
```

---

### Task 7: Create Test Suite

**File:** `hospital-backend/test_esp32_hmac_auth.py` (NEW)

See full test suite in [ESP32_SCALABLE_AUTHENTICATION_DESIGN.md](ESP32_SCALABLE_AUTHENTICATION_DESIGN.md) under "Phase 3: Testing & Validation"

**Key Tests:**
1. Device provisioning with valid staff credentials
2. Device registration with valid HMAC signature
3. Registration blocked without signature (401)
4. Registration blocked with invalid signature (403)
5. Registration blocked with expired timestamp (401)
6. Heartbeat with valid HMAC
7. Vitals upload with valid HMAC
8. Emergency alert with valid HMAC
9. Spoofing attack prevention
10. MAC address mismatch detection

---

### Task 8: Update Documentation

**Files to Update:**
1. `ESP32_SCALABLE_AUTHENTICATION_DESIGN.md` - Add authenticated provisioning workflow
2. `ESP32_HMAC_IMPLEMENTATION_STATUS.md` - Mark tasks complete
3. `README.md` - Document new authentication system

---

## Implementation Order

**Recommended sequence:**

1. ✅ Add HMAC authenticator instance initialization
2. ✅ Update `/register` endpoint
3. ✅ Update `/{deviceId}/heartbeat` endpoint
4. ✅ Update `/{deviceId}/vitals/{patientId}` endpoint
5. ✅ Update `/{deviceId}/alert` endpoint
6. ✅ Create and apply database migration
7. ✅ Restart backend
8. ✅ Create and run test suite
9. ✅ Update documentation

---

## Testing Workflow

After implementing all endpoints:

```bash
# 1. Kill existing backend processes
powershell "Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force"

# 2. Apply database migration
cd hospital-backend
python apply_migration_009.py

# 3. Start backend
python main.py &

# 4. Wait for startup
sleep 15

# 5. Run HMAC test suite
python test_esp32_hmac_auth.py

# 6. Verify all tests pass
```

---

## Estimated Time

| Task | Duration | Complexity |
|------|----------|------------|
| Init HMAC authenticator | 5 min | Low |
| Update `/register` | 15 min | Medium |
| Update `/heartbeat` | 10 min | Low |
| Update `/vitals` | 20 min | Medium |
| Update `/alert` | 10 min | Low |
| Database migration | 15 min | Low |
| Test suite creation | 30 min | Medium |
| Testing & debugging | 45 min | Medium |
| Documentation | 30 min | Low |
| **TOTAL** | **3 hours** | **Medium** |

---

## Success Criteria

✅ All endpoints updated to use HMAC authentication
✅ `deviceKey` column removed from database
✅ All 10 security tests pass
✅ Provisioning still requires staff authentication
✅ Backend starts without errors
✅ Documentation updated
✅ ESP32 firmware requirements documented

---

**Last Updated:** 2025-10-14 12:30 UTC
**Status:** Ready for endpoint updates
**Next Action:** Update ESP32 endpoints with HMAC auth
