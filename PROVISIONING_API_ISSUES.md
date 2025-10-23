# Provisioning API Issues Found

## File: `hospital-backend/app/api/v1/provisioning.py`

---

## Issue #1: Timezone Naive Datetime (Line 139)
**Problem:**
```python
expires_at = datetime.utcnow() + timedelta(minutes=request.validityMinutes)
```
- Uses `datetime.utcnow()` which creates **naive datetime** (no timezone info)
- PostgreSQL `NOW()` returns **timezone-aware datetime**
- Comparison fails when validating codes

**Fix:**
```python
from datetime import datetime, timedelta, timezone
expires_at = datetime.now(timezone.utc) + timedelta(minutes=request.validityMinutes)
```

---

## Issue #2: Timezone Comparison (Line 228)
**Problem:**
```python
if datetime.utcnow() > code_row["expires_at"].replace(tzinfo=None):
```
- Removes timezone from database timestamp
- Compares naive to naive (hacky workaround)
- Should use timezone-aware comparison

**Fix:**
```python
if datetime.now(timezone.utc) > code_row["expires_at"]:
```

---

## Issue #3: Device Must Exist (Lines 236-246)
**CRITICAL ASSUMPTION:**
```python
device_row = await conn.fetchrow(
    'SELECT id, name, "deviceType", status FROM devices WHERE id = $1',
    request.deviceId
)

if not device_row:
    logger.warning(f"❌ Provisioning attempted for non-existent device: {request.deviceId}")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Device {request.deviceId} not found in database. Create device first."
    )
```

**Problem:**
- ESP32 sends `deviceId` like "ESP32-WATCH-AA:BB:CC:DD:EE:FF"
- This device ID is **NOT in the devices table yet**
- Devices table needs to be created manually or by admin first
- ESP32 cannot provision itself if device doesn't exist

**Real-World Scenario:**
1. Fresh ESP32 watch arrives from manufacturer
2. IT staff generates provisioning code
3. ESP32 tries to provision → **FAILS** because device not in table
4. Admin must manually add device to devices table first
5. Then ESP32 can provision

**Options:**
1. **Auto-create device** during provisioning
2. **Require pre-registration** (current behavior - too strict)
3. **Separate device pool** for unprovisioned devices

---

## Issue #4: Certificate Expiry Uses Naive Datetime (Line 271)
**Problem:**
```python
cert_expires_at = datetime.utcnow() + timedelta(days=365)
```
Same timezone issue

**Fix:**
```python
cert_expires_at = datetime.now(timezone.utc) + timedelta(days=365)
```

---

## Issue #5: Path Assumptions (Lines 310-315)
**Problem:**
```python
ca_cert_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "mosquitto", "certs", "hospital_ca.crt"
)
```
- Assumes directory structure
- Fragile path navigation with `..`
- May fail if file structure changes

**Better Approach:**
```python
# In main.py startup, store CA cert content in app.state
app.state.ca_certificate_pem = load_ca_certificate()

# In provisioning.py
ca_certificate_pem = fastapi_request.app.state.ca_certificate_pem
```

---

## Issue #6: No Device Auto-Creation

**Current Flow:**
```
1. Admin manually creates device in devices table
2. IT staff generates provisioning code
3. ESP32 provisions
```

**Expected Flow (for new devices):**
```
1. IT staff generates provisioning code
2. ESP32 provisions → AUTO-CREATES device in devices table
3. Device ready to use
```

**Recommendation:**
Add option to auto-create device during provisioning:

```python
if not device_row:
    # Auto-create device for new ESP32
    await conn.execute(
        '''INSERT INTO devices (id, name, "deviceType", status)
           VALUES ($1, $2, $3, $4)''',
        request.deviceId,
        f"Watch {request.macAddress}",
        "watch",
        "active"
    )
    logger.info(f"✅ Auto-created device: {request.deviceId}")
```

---

## Summary of Fixes Needed

### High Priority (Breaks Functionality):
1. ✅ **Issue #1**: Fix timezone in code generation
2. ✅ **Issue #2**: Fix timezone in code validation
3. ❌ **Issue #3**: Device must exist (too strict - blocks new devices)
4. ✅ **Issue #4**: Fix timezone in certificate expiry

### Medium Priority (Improves Code):
5. **Issue #5**: Better CA cert path handling
6. **Issue #3 Solution**: Auto-create devices during provisioning

### Testing Notes:
- Issues #1, #2, #4 were already discovered during testing
- Issue #3 was NOT discovered because test removed foreign key constraints
- Issue #3 will FAIL in production when provisioning new ESP32 devices

---

## Recommended Fix

```python
# Line 139: Fix timezone
from datetime import datetime, timedelta, timezone
expires_at = datetime.now(timezone.utc) + timedelta(minutes=request.validityMinutes)

# Line 228: Fix timezone comparison
if datetime.now(timezone.utc) > code_row["expires_at"]:

# Lines 236-260: Auto-create device if it doesn't exist
device_row = await conn.fetchrow(
    'SELECT id FROM devices WHERE id = $1',
    request.deviceId
)

if not device_row:
    # Auto-create device for new ESP32
    logger.info(f"📝 Auto-creating device: {request.deviceId}")
    await conn.execute(
        '''INSERT INTO devices (id, name, "deviceType", status, "createdAt", "updatedAt")
           VALUES ($1, $2, $3, $4, NOW(), NOW())''',
        request.deviceId,
        f"ESP32 Watch {request.macAddress[-8:]}",  # Name: "ESP32 Watch EE:FF"
        "watch",
        "active"
    )

# Line 271: Fix timezone
cert_expires_at = datetime.now(timezone.utc) + timedelta(days=365)
```

---

## Testing Needed

1. Test with device that doesn't exist in devices table
2. Test with timezone-aware datetime comparison
3. Test certificate expiry timestamp
4. Test foreign key constraints are satisfied

