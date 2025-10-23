# MQTT Authentication Flow - Simple Explanation

**Date:** October 17, 2025

---

## YOUR QUESTION

> "so mqtt auth password,. we fill prov0001 and password in the form. backend validates then gives auth to watch?"

---

## SHORT ANSWER

**YES! But there are TWO different sets of credentials:**

1. **Provisioner credentials** (TEC0001/tech123) - Used ONCE to prove you're authorized to provision the device
2. **MQTT credentials** (generated per-device) - Used FOREVER by the watch to communicate with backend

---

## DETAILED FLOW

### Step 1: User Fills Captive Portal Form

**What You See:**
```
┌──────────────────────────────────────┐
│   🏥 Hospital Watch Setup           │
├──────────────────────────────────────┤
│   WiFi: HospitalNetwork              │
│   Password: ********                 │
│                                      │
│   Server IP: 192.168.0.113          │
│   MQTT Port: 8883                    │
│                                      │
│   Provisioner ID: TEC0001   ← YOU FILL THIS (your staff ID)
│   Password: tech123         ← YOU FILL THIS (your password)
│                                      │
│   [🚀 Configure & Connect]           │
└──────────────────────────────────────┘
```

**What Happens:**
- ESP32 saves provisioner credentials to flash (Lines 781-782)
- ESP32 connects to WiFi
- ESP32 connects to MQTT using **SHARED** credentials

---

### Step 2: ESP32 Connects to MQTT (First Time)

**ESP32 Firmware (Lines 1096-1100):**
```cpp
String mqttUsername = "hospitalEsp32";  // ← SHARED username (ALL unprovisioned devices use this)
String mqttPassword = "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=";  // ← SHARED password

// Connect with SHARED credentials
mqttClient.connect("HospitalWatch_UNPROVISIONED_30:AE:A4:12:34:56",
                   mqttUsername.c_str(),
                   mqttPassword.c_str());
```

**Purpose:** The shared credentials allow ANY unprovisioned device to connect to MQTT **ONLY** to request provisioning. They cannot send vitals or do anything else.

---

### Step 3: ESP32 Publishes Provisioning Request

**ESP32 Firmware (Lines 1108-1120):**
```cpp
// Publish to: hospital/provisioning/request
{
  "macAddress": "30:AE:A4:12:34:56",
  "deviceType": "watch",
  "firmwareVersion": "4.2.0",
  "provisionerId": "TEC0001",           // ← YOUR credentials from form
  "provisionerPassword": "tech123",     // ← YOUR credentials from form
  "timestamp": "2025-10-17T10:30:45.123Z"
}
```

---

### Step 4: Backend Validates YOUR Provisioner Credentials

**Backend MQTT Service (Lines 658-685):**
```python
# 1. Look up provisioner in staff table
provisioner = await conn.fetchrow(
    "SELECT id, firstName, lastName, role, password FROM staff WHERE id = $1 AND role IN ('Provisioner', 'Technician')",
    provisionerId  # "TEC0001"
)

if not provisioner:
    # ❌ FAIL: Invalid staff ID or wrong role
    return error

# 2. Verify provisioner password using bcrypt
passwordValid = bcrypt.checkpw(
    provisionerPassword.encode('utf-8'),  # "tech123"
    provisioner['password'].encode('utf-8')  # hashed password from DB
)

if not passwordValid:
    # ❌ FAIL: Wrong password
    return error

# ✅ SUCCESS: Provisioner credentials are valid!
# Now we can trust this provisioning request
```

**What This Proves:**
- You are a real staff member (ID exists in database)
- You have the correct role (Technician or Provisioner)
- You know the correct password
- You are authorized to provision devices

---

### Step 5: Backend Generates Device-Specific MQTT Credentials

**Backend MQTT Service (Lines 744-750):**
```python
deviceId = "ESP32_WATCH_001"  # Auto-generated
serialNumber = "SN_W001"      # Auto-generated

# Generate PER-DEVICE MQTT credentials
mqttUsername = f"{deviceId}_mqtt"  # "ESP32_WATCH_001_mqtt"
mqttPassword = self._generateDevicePassword(deviceId)  # Generated unique password
```

**Password Generation (Lines 809-826):**
```python
def _generateDevicePassword(self, deviceId: str) -> str:
    """Generate unique MQTT password for device"""
    # HMAC(deviceId, secret) → base64
    password_bytes = f"{deviceId}:{secret}".encode('utf-8')
    hashed = hashlib.sha256(password_bytes).digest()
    password = base64.urlsafe_b64encode(hashed[:24]).decode('utf-8')
    return password
```

**Result:**
- Device ID: `ESP32_WATCH_001`
- MQTT Username: `ESP32_WATCH_001_mqtt`
- MQTT Password: `xY7zK9mN2pQ4rT6vB8wE1aC3dF5gH7jL` (example, unique per device)

---

### Step 6: Backend Publishes Response to ESP32

**Backend MQTT Service (Lines 772-781):**
```python
# Publish to: hospital/provisioning/response/30:AE:A4:12:34:56
await self._publishProvisioningResponse(macAddress, {
    "success": True,
    "message": "Device provisioned successfully",
    "deviceId": "ESP32_WATCH_001",
    "serialNumber": "SN_W001",
    "mqttUsername": "ESP32_WATCH_001_mqtt",        # ← NEW credentials
    "mqttPassword": "xY7zK9mN2pQ4rT6vB8wE1aC3dF5gH7jL",  # ← NEW credentials
    "provisionedBy": "John Technician",
    "status": "new"
})
```

---

### Step 7: ESP32 Receives NEW Credentials and Saves

**ESP32 Firmware (Lines 987-1005):**
```cpp
// Receive response on: hospital/provisioning/response/30:AE:A4:12:34:56
if (doc["success"]) {
  deviceId = "ESP32_WATCH_001";
  serialNumber = "SN_W001";

  // ✅ SAVE NEW PER-DEVICE CREDENTIALS
  mqttUsername = "ESP32_WATCH_001_mqtt";
  mqttPassword = "xY7zK9mN2pQ4rT6vB8wE1aC3dF5gH7jL";

  isProvisioned = true;
  saveConfiguration();  // Save to flash forever

  Serial.println("🎉 DEVICE PROVISIONED via MQTT!");
}
```

---

### Step 8: ESP32 Reconnects with NEW Credentials

**ESP32 Firmware (Lines 1007-1010):**
```cpp
// Disconnect SHARED credentials
mqttClient.disconnect();
delay(1000);

// Reconnect with NEW per-device credentials
setupMQTT();
```

**ESP32 Firmware (Lines 956-962):**
```cpp
// Now using PER-DEVICE credentials forever
String clientId = "HospitalWatch_ESP32_WATCH_001";
mqttClient.connect(clientId.c_str(),
                   "ESP32_WATCH_001_mqtt",  // ← NEW username
                   "xY7zK9mN2pQ4rT6vB8wE1aC3dF5gH7jL");  // ← NEW password

// ✅ MQTT TLS Connected with device credentials!
```

---

## SUMMARY: TWO TYPES OF CREDENTIALS

### Type 1: Provisioner Credentials (Used ONCE)

| Field | Value | Purpose |
|-------|-------|---------|
| **Where?** | Captive portal form | Human fills this |
| **Who?** | Staff member (YOU) | TEC0001 (Technician John) |
| **Password** | tech123 | Your staff password |
| **Stored where?** | Staff table in database | Hashed with bcrypt |
| **Used for?** | Proving you're authorized to provision | One-time authentication |
| **Validated by?** | Backend checks staff table + bcrypt | Lines 658-685 |

### Type 2: Device MQTT Credentials (Used FOREVER)

| Field | Value | Purpose |
|-------|-------|---------|
| **Where?** | Generated by backend | Automatic |
| **Who?** | Device (ESP32_WATCH_001) | Per-device unique |
| **Username** | ESP32_WATCH_001_mqtt | Generated from device ID |
| **Password** | xY7zK9mN2pQ4rT6vB8wE1aC3dF5gH7jL | HMAC generated |
| **Stored where?** | ESP32 flash + Mosquitto broker | Plaintext (Issue #4) |
| **Used for?** | All MQTT communication forever | Sending vitals, alerts, heartbeat |
| **Validated by?** | Mosquitto broker checks credentials | Every MQTT connection |

---

## ANALOGY

Think of it like getting a passport:

**Provisioner Credentials (TEC0001/tech123):**
- Like showing your government ID to the passport office
- Proves you're a real citizen authorized to get a passport
- Used ONCE during application
- Cannot be used to travel (you need the passport)

**Device MQTT Credentials (ESP32_WATCH_001_mqtt/password):**
- Like the passport itself
- Issued to the device by the backend (passport office)
- Used FOREVER for all future communication (travel)
- Unique to this specific device

---

## SECURITY MODEL

```
User (TEC0001/tech123)
      ↓
  [Validates human authority]
      ↓
Backend generates
      ↓
Device Credentials (ESP32_WATCH_001_mqtt/unique_password)
      ↓
  [Device uses forever]
```

**Why Two Credentials?**

1. **Security:** If device credentials are compromised, you can revoke just that device without changing staff passwords
2. **Accountability:** Every provisioning is logged with WHO provisioned it (TEC0001 = John Technician)
3. **Scalability:** 1000 devices can be provisioned by 1 technician without sharing device passwords
4. **Revocation:** Backend can disable device credentials without affecting staff access

---

## WHAT GETS STORED WHERE?

### ESP32 Flash (NVS)
```cpp
prefs.putString("prov_id", "TEC0001");          // ✅ Saved (for re-provisioning)
prefs.putString("prov_pass", "tech123");        // ✅ Saved (for re-provisioning)
prefs.putString("deviceId", "ESP32_WATCH_001"); // ✅ Saved
prefs.putString("mqttuser", "ESP32_WATCH_001_mqtt");  // ✅ Saved
prefs.putString("mqttpwd", "xY7zK9mN2pQ4rT6vB8wE1aC3dF5gH7jL");  // ✅ Saved
```

### Backend Database (PostgreSQL)
```sql
-- Staff table
TEC0001 | John | Technician | $2b$12$hash... (bcrypt)

-- Devices table
ESP32_WATCH_001 | watch | SN_W001 | 30:AE:A4:12:34:56 | ...

-- Audit logs
provisionDevice | TEC0001 | John Technician | Provisioned ESP32_WATCH_001
```

### Mosquitto MQTT Broker (Password File)
```
# SHARED credentials (for unprovisioned devices)
hospitalEsp32:ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=

# PER-DEVICE credentials (after provisioning)
ESP32_WATCH_001_mqtt:xY7zK9mN2pQ4rT6vB8wE1aC3dF5gH7jL
ESP32_WATCH_002_mqtt:aB2cD3eF4gH5iJ6kL7mN8oP9qR0sT1u
ESP32_WATCH_003_mqtt:zX9yW8vU7tS6rQ5pO4nM3lK2jI1hG0f
```

---

## FAQ

**Q: Can I provision multiple devices with same TEC0001/tech123?**
**A:** YES! You use YOUR credentials (TEC0001/tech123) to provision as many devices as needed. Each device gets DIFFERENT MQTT credentials automatically.

**Q: What if I forget my provisioner password?**
**A:** Admin can reset it in the staff table. Device MQTT credentials are unaffected.

**Q: What if device MQTT password is compromised?**
**A:** Admin can regenerate credentials by re-provisioning the device (same MAC address).

**Q: Why store provisioner credentials on ESP32?**
**A:** For re-provisioning! If device flash is erased or firmware upgraded, it can auto-provision again using same provisioner credentials.

**Q: Is it safe to store tech123 in plaintext on ESP32?**
**A:** For testing: OK (low risk). For production: Enable flash encryption (Issue #4) to encrypt all stored data.

---

## TESTING THE FLOW

### Test 1: Provision New Device

```bash
# 1. Connect to "HospitalWatch" hotspot
# 2. Fill form:
#    - WiFi: HospitalNetwork / password
#    - Server: 192.168.0.113:8883
#    - Provisioner ID: TEC0001
#    - Provisioner Password: tech123
# 3. Click "Configure & Connect"

# ESP32 Serial Output:
# 🔄 Connecting to MQTT as: HospitalWatch_UNPROVISIONED_30AEA4123456
# 🔐 Using credentials: hospitalEsp32
# ✅ MQTT connected (unprovisioned)
# 📤 Provisioning request sent via MQTT
# ⏳ Waiting for response...
# 🎉 DEVICE PROVISIONED via MQTT!
#    📱 Device ID: ESP32_WATCH_001
#    📋 Serial: SN_W001
#    🔐 MQTT User: ESP32_WATCH_001_mqtt
# ✅ MQTT TLS Connected with device credentials!
```

### Test 2: Verify Backend Validation

```bash
# Try WRONG provisioner password
# Provisioner ID: TEC0001
# Password: WRONG_PASSWORD

# Backend Logs:
# ❌ Invalid provisioner password for ID: TEC0001
# 📤 Provisioning response sent: {"success": false, "message": "Invalid provisioner credentials"}

# ESP32 Serial Output:
# ❌ Provisioning failed: Invalid provisioner credentials
# (LED flashes rapidly 6 times)
```

### Test 3: Device Continues Working After Reboot

```bash
# 1. Reboot ESP32 (power cycle)

# ESP32 Serial Output:
# 📖 Loaded: ESP32_WATCH_001 (SN_W001)
# 🔐 MQTT User: ESP32_WATCH_001_mqtt
# 🔄 Connecting to MQTT TLS broker as: HospitalWatch_ESP32_WATCH_001
# ✅ MQTT TLS Connected with device credentials!
# (No re-provisioning needed - credentials saved in flash)
```

---

## CONCLUSION

**YES, you're correct!**

1. You fill **TEC0001/tech123** (YOUR provisioner credentials) in the form
2. Backend validates **your identity** (staff table lookup + bcrypt check)
3. Backend generates **NEW device-specific MQTT credentials** for the watch
4. Watch uses **device credentials** forever for all communication

**Your provisioner credentials** = Prove you're authorized to provision
**Device MQTT credentials** = Allow device to communicate with backend

Both are needed, but serve different purposes in the authentication chain.

---

**END OF EXPLANATION**
