# MQTT Shared Credentials Security Audit

**Date:** 2025-10-17
**Severity:** 🔴 **CRITICAL SECURITY VULNERABILITY**
**Status:** Currently in production

---

## Executive Summary

You are **100% correct**. Storing hardcoded plaintext credentials is a serious security vulnerability. The current implementation has **multiple critical security flaws** that expose the entire MQTT infrastructure to attack.

---

## Current Vulnerability Analysis

### 1. Hardcoded Plaintext Credentials in Firmware

**Location:** [esp32_hospital_watch_complete.ino:79-80](esp32_hospital_watch_complete.ino#L79-L80)

```cpp
String mqttUsername = "hospitalEsp32";
String mqttPassword = "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=";
```

**🔴 CRITICAL ISSUES:**

#### Issue 1: Firmware Reverse Engineering
- **Anyone with physical access** to an ESP32 watch can extract the firmware
- ESP32 flash memory is **NOT encrypted** by default (no Secure Boot in current setup)
- Tools like `esptool.py` can dump flash contents in **under 30 seconds**
- Shared credentials are exposed in **plaintext** in firmware binary

**Attack Scenario:**
```bash
# Attacker with physical access to ANY watch:
esptool.py --chip esp32 --port COM3 read_flash 0x00000 0x400000 firmware_dump.bin
strings firmware_dump.bin | grep "hospitalEsp32"
# Output: hospitalEsp32
# Output: ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=
```

**Impact:** Attacker now has credentials to connect to MQTT broker from ANY device.

#### Issue 2: All Unprovisioned Devices Share Same Credentials
- **10,000+ devices** will use the same `hospitalEsp32/password` to connect
- If ONE device is compromised, **ALL devices** are compromised
- Cannot revoke access for a single compromised device without affecting all unprovisioned devices
- **No way to track which physical device** is connecting (before provisioning)

#### Issue 3: Credentials in Source Code (Version Control Risk)
- Credentials visible in **GitHub/Git** repository
- Every developer, intern, contractor who clones repo gets credentials
- Git history preserves credentials **forever** (even if deleted later)
- Public repository exposure risk if repo accidentally made public

#### Issue 4: Credentials in Docker Compose Healthcheck
**Location:** [docker-compose.yml:52](docker-compose.yml#L52)

```yaml
test: ["CMD-SHELL", "mosquitto_sub -h localhost -p 8883 -u hospitalEsp32 -P ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF+Q= ..."]
```

**🔴 RISK:** Credentials exposed in Docker healthcheck command visible to anyone with access to:
- Docker container inspection (`docker inspect`)
- Docker logs
- Kubernetes/Orchestration dashboards

---

### 2. Mosquitto Broker Authentication Analysis

**Location:** [mosquitto/config/passwords.txt](mosquitto/config/passwords.txt)

```
hospitalEsp32:$7$101$uhTE7y9QviF2GgeG$7rHzvsVRjRY+jrqbS4D97iVH2rsI5vxVzKdgAz3AtPWJIdgTI9w66LMrN+b+00FCNFkPkMu1POuo9rqjPuWQVA==
```

**✅ GOOD:** Password is hashed using Argon2 (strong algorithm)
**🔴 BAD:** Only **ONE** shared credential for all unprovisioned devices

**Current Validation Flow:**
1. ESP32 connects with `hospitalEsp32/password`
2. Mosquitto broker validates against hashed password file ✅
3. **ALL unprovisioned devices** authenticate with same credentials ❌
4. Backend **cannot distinguish** which physical device is connecting ❌

---

### 3. Backend MQTT Credential Management

**Location:** [mqtt_service.py:43-44](hospital-backend/app/services/mqtt_service.py#L43-L44)

```python
'username': 'hospitalEsp32',
'password': 'ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF+Q=',
```

**Location:** [mqtt_service.py:809-826](hospital-backend/app/services/mqtt_service.py#L809-L826)

```python
def _generateDevicePassword(self, deviceId: str) -> str:
    """Generate unique MQTT password for device"""
    secret = settings.esp32FactorySecret
    password_bytes = f"{deviceId}:{secret}".encode('utf-8')
    hashed = hashlib.sha256(password_bytes).digest()
    password = base64.urlsafe_b64encode(hashed[:24]).decode('utf-8')
    return password
```

**Analysis:**
- ✅ **Per-device credentials** are generated **AFTER** provisioning (secure)
- ❌ **Shared credentials** required **BEFORE** provisioning (insecure)
- ❌ Generated device passwords **not dynamically added** to Mosquitto broker
- ❌ No mechanism to **revoke** compromised credentials

---

## Attack Vectors

### Attack Vector 1: Device Theft + Firmware Dump
**Difficulty:** Easy (30 minutes, $5 tools)

```
1. Steal ANY ESP32 watch from hospital
2. Connect to USB (30 seconds)
3. Dump firmware: esptool.py read_flash (30 seconds)
4. Extract credentials: strings firmware.bin | grep mqtt (5 seconds)
5. Connect rogue device: mosquitto_pub -u hospitalEsp32 -P ... (instant)
```

**Impact:**
- ✅ Attacker can now publish **fake vitals data** to ANY patient
- ✅ Attacker can **spoof device heartbeats** to hide malicious activity
- ✅ Attacker can **subscribe to all vitals** from all patients (privacy breach)
- ✅ Attacker can **DoS attack** by flooding MQTT broker with messages

### Attack Vector 2: Insider Threat
**Difficulty:** Trivial (0 effort)

```
1. Any developer/intern with repo access sees credentials
2. Copy hospitalEsp32/password from code
3. Connect from personal laptop: mosquitto_pub -u hospitalEsp32 -P ...
```

**Impact:**
- ✅ Ex-employee with old repo access retains MQTT access **forever**
- ✅ No audit trail of who accessed MQTT (all appear as "hospitalEsp32")
- ✅ Cannot revoke access without reprovisioning **ALL devices**

### Attack Vector 3: Supply Chain Attack
**Difficulty:** Medium (requires firmware modification during manufacturing)

```
1. Malicious manufacturer modifies ESP32 firmware
2. Adds backdoor that exfiltrates credentials
3. All devices ship with compromised firmware
```

**Impact:**
- ✅ Manufacturer has permanent access to MQTT infrastructure
- ✅ Can monitor all patient data
- ✅ Can inject false data

---

## What You Asked: "Do We Know If ID/Pass Are Being Validated?"

### Answer: YES, but only by Mosquitto

**Validation Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│ ESP32 Watch (Unprovisioned)                                 │
│ Credentials: hospitalEsp32 / ahTb1xbhkUeLaTTvvnb9IXI5Spox...│
└──────────────┬──────────────────────────────────────────────┘
               │
               │ 1. MQTT CONNECT with username/password
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│ Mosquitto Broker                                             │
│ ✅ Validates against /mosquitto/config/passwords.txt        │
│ ✅ Checks Argon2 hash                                        │
│ ✅ Grants connection if valid                                │
│ ❌ NO per-device tracking (all show as "hospitalEsp32")     │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ 2. Connection established (but who is it?)
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend MQTT Service                                         │
│ ✅ Receives MQTT messages                                    │
│ ❌ CANNOT distinguish which physical device sent message    │
│    (before provisioning)                                     │
│ ✅ AFTER provisioning: unique credentials per device         │
└─────────────────────────────────────────────────────────────┘
```

**KEY PROBLEM:**
- Mosquitto validates credentials ✅
- But Mosquitto **doesn't know which physical ESP32** is connecting ❌
- Backend **cannot track** who used shared credentials ❌

---

## What You Asked: "Do We Have to Track 10,000s of ID/Pass?"

### Answer: NO! You Should NOT Track 10,000s of Passwords

**Current Backend Approach (CORRECT):**
- **ONE shared credential** for unprovisioned devices (insecure)
- **Per-device unique credentials** AFTER provisioning (secure)
- Generated on-the-fly using HMAC-SHA256
- Stored in backend database (implicit - device can authenticate)

**Problem:** The shared credential stage is the vulnerability.

---

## Root Cause Analysis

### Why Does This Design Exist?

**The Chicken-and-Egg Problem:**

```
Question: How does an unprovisioned ESP32 connect to MQTT to REQUEST provisioning?

Current Answer: Use shared credentials (insecure)

Better Answer: Don't use MQTT for initial provisioning (see solutions below)
```

**Design Flaw:**
- Provisioning requires MQTT connection
- MQTT connection requires credentials
- Credentials are assigned during provisioning
- **Circular dependency!**

**Current "Solution":** Give all devices shared credentials (breaks security)

---

## Recommended Solutions

### Solution 1: **Certificate-Based Provisioning (BEST - Production Grade)**

**Overview:** Use X.509 client certificates for initial authentication instead of shared passwords.

#### How It Works:

```
┌──────────────────────────────────────────────────────────┐
│ FACTORY PROVISIONING                                      │
├──────────────────────────────────────────────────────────┤
│ 1. Generate unique client certificate per device         │
│    Serial Number: MAC address (hardware ID)              │
│    Common Name: ESP32-{MAC}                              │
│    Signed by Hospital CA                                 │
│                                                           │
│ 2. Flash certificate to ESP32 SPIFFS                     │
│    /certs/client.crt                                     │
│    /certs/client.key                                     │
│                                                           │
│ 3. Configure Mosquitto:                                  │
│    require_certificate true                              │
│    use_identity_as_username true                         │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ DEVICE CONNECTS                                           │
├──────────────────────────────────────────────────────────┤
│ ESP32 → Mosquitto (TLS with client cert)                │
│ Mosquitto validates certificate against CA               │
│ Mosquitto extracts username from certificate CN          │
│ Backend knows EXACTLY which device (by MAC)              │
└──────────────────────────────────────────────────────────┘
```

**✅ BENEFITS:**
- **No shared credentials**
- **No hardcoded passwords** in firmware
- **Unique identity** per device from day one
- **Certificate revocation** via CRL/OCSP
- **Physically secure** (private key stored in ESP32 flash, can use secure element)
- **Industry standard** for IoT device authentication

**❌ CHALLENGES:**
- Requires factory programming step
- Certificate management infrastructure
- More complex setup

**Implementation:**
1. Generate CA certificate for hospital
2. Create provisioning script that generates client cert per device
3. Flash certs to ESP32 during manufacturing/deployment
4. Configure Mosquitto to require client certificates
5. Backend maps certificate CN (MAC address) to device ID

---

### Solution 2: **One-Time Provisioning Codes (GOOD - Easier to Implement)**

**Overview:** Use short-lived, single-use provisioning codes instead of shared credentials.

#### How It Works:

```
┌──────────────────────────────────────────────────────────┐
│ PROVISIONING WORKFLOW                                     │
├──────────────────────────────────────────────────────────┤
│ 1. Technician requests provisioning code from backend    │
│    Backend generates: PROV-12AB-CD34 (valid 10 minutes)  │
│                                                           │
│ 2. Technician enters code in ESP32 captive portal        │
│    Code + MAC address sent to backend (HTTP)             │
│                                                           │
│ 3. Backend validates:                                    │
│    - Code exists and not expired                         │
│    - Code not already used                               │
│    - Technician credentials valid                        │
│                                                           │
│ 4. Backend generates per-device MQTT credentials         │
│    ESP32 saves credentials and connects to MQTT          │
└──────────────────────────────────────────────────────────┘
```

**✅ BENEFITS:**
- **No shared credentials**
- **No hardcoded passwords**
- **Time-limited** exposure (10 minutes)
- **Single-use** codes (cannot reuse)
- **Audit trail** of who provisioned which device

**❌ CHALLENGES:**
- Requires backend API endpoint for code generation
- Initial provisioning must be over HTTP (not MQTT)
- Requires secure HTTPS connection for code exchange

**Implementation:**
1. Remove MQTT provisioning flow
2. Add HTTP provisioning endpoint: `POST /api/v1/provisioning/request`
3. Generate one-time codes with expiration
4. Store codes in database with `used` flag
5. Validate code + MAC during provisioning

---

### Solution 3: **QR Code Provisioning (BEST UX)**

**Overview:** Combine one-time codes with QR code scanning for seamless UX.

#### How It Works:

```
┌──────────────────────────────────────────────────────────┐
│ PROVISIONING WORKFLOW                                     │
├──────────────────────────────────────────────────────────┤
│ 1. Backend generates QR code containing:                 │
│    - One-time provisioning token (JWT)                   │
│    - Server IP                                           │
│    - Expiration timestamp                                │
│                                                           │
│ 2. Display QR code on provisioning dashboard             │
│                                                           │
│ 3. ESP32 captive portal shows "Scan QR Code" button      │
│    User scans QR with phone camera                       │
│    Phone opens ESP32 captive portal with token auto-fill │
│                                                           │
│ 4. ESP32 sends token + MAC to backend (HTTP)             │
│    Backend validates JWT and provisions device           │
└──────────────────────────────────────────────────────────┘
```

**✅ BENEFITS:**
- **Best user experience** (one scan)
- All security benefits of one-time codes
- **No typing** errors (QR contains all data)
- **Short-lived tokens** (JWT with 10-min expiration)

---

## Recommended Implementation Plan

### Phase 1: Remove Shared Credentials (IMMEDIATE - 2 days)

**Step 1:** Implement One-Time Provisioning Codes

**Changes Required:**

1. **Backend:** Add HTTP provisioning endpoint
```python
@router.post("/provisioning/request-code")
async def generateProvisioningCode(
    request: ProvisioningCodeRequest,
    technician: Staff = Depends(verifyStaffRole(['Technician', 'Provisioner']))
):
    # Generate one-time code
    code = generateShortCode()  # e.g., "PROV-AB12-CD34"

    # Store in database with expiration
    await conn.execute("""
        INSERT INTO provisioning_codes (code, technician_id, expires_at, used)
        VALUES ($1, $2, NOW() + INTERVAL '10 minutes', false)
    """, code, technician.id)

    return {"code": code, "expiresIn": "10 minutes"}

@router.post("/provisioning/provision-with-code")
async def provisionWithCode(request: ProvisionWithCodeRequest):
    # Validate code
    codeRecord = await conn.fetchrow("""
        SELECT * FROM provisioning_codes
        WHERE code = $1 AND used = false AND expires_at > NOW()
    """, request.code)

    if not codeRecord:
        raise HTTPException(400, "Invalid or expired provisioning code")

    # Generate device credentials (existing logic)
    deviceId = generateDeviceId()
    mqttCredentials = generateMQTTCredentials(deviceId)

    # Mark code as used
    await conn.execute("UPDATE provisioning_codes SET used = true WHERE code = $1", request.code)

    return {
        "deviceId": deviceId,
        "mqttUsername": mqttCredentials.username,
        "mqttPassword": mqttCredentials.password
    }
```

2. **ESP32 Firmware:** Remove hardcoded credentials
```cpp
// OLD (REMOVE):
String mqttUsername = "hospitalEsp32";
String mqttPassword = "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=";

// NEW:
String provisioningCode = "";  // Entered by technician in captive portal

void attemptProvisioning() {
    // Make HTTP request to backend
    HTTPClient http;
    http.begin("https://" + serverIP + ":8001/api/v1/provisioning/provision-with-code");

    JsonDocument doc;
    doc["code"] = provisioningCode;
    doc["macAddress"] = macAddress;

    String payload;
    serializeJson(doc, payload);

    int httpCode = http.POST(payload);
    if (httpCode == 200) {
        String response = http.getString();
        JsonDocument responseDoc;
        deserializeJson(responseDoc, response);

        deviceId = responseDoc["deviceId"].as<String>();
        mqttUsername = responseDoc["mqttUsername"].as<String>();
        mqttPassword = responseDoc["mqttPassword"].as<String>();

        saveConfiguration();
        setupMQTT();
    }
}
```

3. **Captive Portal:** Add provisioning code field
```cpp
html += "<label>Provisioning Code:</label>";
html += "<input type='text' name='prov_code' placeholder='PROV-XXXX-XXXX' required>";
```

4. **Mosquitto:** Remove shared credential from passwords.txt
```bash
# DELETE LINE:
# hospitalEsp32:$7$101$uhTE7y9QviF2GgeG$...
```

**Step 2:** Update Mosquitto to Support Dynamic Credentials

**Problem:** Generated device passwords need to be added to Mosquitto `passwords.txt`

**Solution:** Use Mosquitto dynamic authentication plugin

```bash
# Install auth plugin
apt-get install mosquitto-auth-plugin

# Configure mosquitto.conf
auth_plugin /usr/lib/mosquitto_dynamic_security.so
auth_opt_backends postgres
auth_opt_host 127.0.0.1
auth_opt_port 5432
auth_opt_dbname hospitaldb
auth_opt_user hospital_user
auth_opt_pass hospital123
auth_opt_userquery SELECT password FROM mqtt_credentials WHERE username = $1 AND active = true
```

**Backend Migration:** Create `mqtt_credentials` table
```sql
CREATE TABLE mqtt_credentials (
    username VARCHAR(100) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,  -- Argon2 hashed
    device_id VARCHAR(50) REFERENCES devices(id),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- When provisioning device:
INSERT INTO mqtt_credentials (username, password, device_id, active)
VALUES ('ESP32_WATCH_001_mqtt', '{argon2_hash}', 'ESP32_WATCH_001', true);
```

**Benefits:**
- ✅ No manual password file updates
- ✅ Can revoke credentials by setting `active = false`
- ✅ Can expire credentials after N days
- ✅ Full audit trail of credential lifecycle

---

### Phase 2: Certificate-Based Auth (FUTURE - 1 week)

**Step 1:** Set up Hospital CA

```bash
# Generate CA certificate
openssl genrsa -out hospital_ca.key 4096
openssl req -x509 -new -nodes -key hospital_ca.key -sha256 -days 3650 \
    -out hospital_ca.crt -subj "/CN=Hospital CA"
```

**Step 2:** Generate client certificates per device

```bash
# Script: generate_device_cert.sh
DEVICE_MAC=$1

openssl genrsa -out ${DEVICE_MAC}.key 2048
openssl req -new -key ${DEVICE_MAC}.key -out ${DEVICE_MAC}.csr \
    -subj "/CN=ESP32-${DEVICE_MAC}"
openssl x509 -req -in ${DEVICE_MAC}.csr -CA hospital_ca.crt \
    -CAkey hospital_ca.key -CAcreateserial -out ${DEVICE_MAC}.crt \
    -days 365 -sha256
```

**Step 3:** Update Mosquitto config

```conf
require_certificate true
use_identity_as_username true
cafile /mosquitto/certs/hospital_ca.crt
```

**Step 4:** Flash certificates to ESP32 during manufacturing

---

## Security Checklist

### Immediate Actions (Do TODAY):

- [ ] **REMOVE** hardcoded credentials from ESP32 firmware
- [ ] **REMOVE** credentials from docker-compose.yml healthcheck
- [ ] **REMOVE** `hospitalEsp32` from Mosquitto passwords.txt
- [ ] **ROTATE** all shared credentials (even though removing)
- [ ] **AUDIT** Git history for credential exposure
- [ ] **IMPLEMENT** one-time provisioning codes (Phase 1)

### Short-Term (This Week):

- [ ] Deploy HTTP-based provisioning endpoint
- [ ] Update ESP32 firmware to use one-time codes
- [ ] Set up dynamic authentication with Mosquitto
- [ ] Create `mqtt_credentials` table in database
- [ ] Add credential revocation capability

### Long-Term (This Month):

- [ ] Implement certificate-based authentication
- [ ] Set up PKI infrastructure (CA + cert generation)
- [ ] Deploy certificate provisioning workflow
- [ ] Enable Secure Boot on ESP32 (prevent firmware dumps)
- [ ] Implement credential rotation policy (90 days)

---

## Compliance Impact

### HIPAA Violation Risk: 🔴 HIGH

**164.312(a)(1) - Access Control:**
> "Implement technical policies and procedures ... that allow access only to those persons or software programs that have been granted access rights"

**Current Violation:** Shared credentials mean **all devices** have same access rights. Cannot restrict access per device.

**164.312(d) - Person or Entity Authentication:**
> "Implement procedures to verify that a person or entity seeking access ... is the one claimed"

**Current Violation:** Cannot verify **which physical device** is connecting (all show as "hospitalEsp32").

### Indian DPDP Act 2023 Violation Risk: 🔴 HIGH

**Section 8 - Security Safeguards:**
> "Data Fiduciary shall take reasonable security safeguards to prevent personal data breach"

**Current Violation:** Hardcoded credentials in firmware are **NOT reasonable security safeguards**.

---

## Cost-Benefit Analysis

### Cost of Current Vulnerability:

- **Data Breach:** $150-400 per patient record (avg HIPAA breach cost)
- **10,000 patients** × $200 = **$2 million liability**
- **Regulatory fines:** Up to $50,000 per violation
- **Reputation damage:** Incalculable

### Cost to Fix:

- **Phase 1 (One-time codes):** 2 developer days = **$1,000**
- **Phase 2 (Certificates):** 5 developer days = **$2,500**
- **Total:** **$3,500**

**ROI:** Prevent $2M+ breach for $3.5K investment = **57,000% ROI**

---

## Conclusion

**You are absolutely right to question this design.**

The hardcoded shared credentials are:
1. ❌ **Security vulnerability** (easy to extract and exploit)
2. ❌ **Compliance violation** (HIPAA + DPDP)
3. ❌ **Not scalable** (cannot track/revoke per device)
4. ❌ **Not production-ready**

**Recommended Action:**
1. **IMMEDIATELY** implement Phase 1 (one-time provisioning codes)
2. **Remove** all shared credentials from firmware and config
3. **Plan** Phase 2 (certificate-based auth) for next month

This is a **critical security fix** that should be prioritized above all other features.

---

## Questions for Next Steps

1. **Do you want me to implement Phase 1 (one-time provisioning codes) now?**
2. **Should I create the database migration for `mqtt_credentials` table?**
3. **Do you want to use QR codes for provisioning (better UX)?**
4. **What's your timeline for deploying this fix?**

Let me know which approach you prefer, and I'll implement it.
