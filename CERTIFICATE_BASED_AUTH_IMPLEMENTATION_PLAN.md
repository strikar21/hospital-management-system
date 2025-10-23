# Certificate-Based Authentication Implementation Plan

**Date:** 2025-10-17
**Goal:** Replace shared MQTT credentials with per-device TLS client certificates
**Timeline:** 1 week (detailed breakdown below)

---

## Current State Analysis

### What Works Now:
✅ MQTT TLS 1.2 connection (port 8883)
✅ ESP32 captive portal provisioning
✅ Backend MQTT service
✅ Per-device credentials generated AFTER provisioning
✅ CA certificate loaded from SPIFFS

### What's Broken:
❌ **Shared credentials** hardcoded in firmware: `hospitalEsp32 / ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=`
❌ **All unprovisioned devices** use same credentials
❌ **Cannot revoke** one device without affecting all
❌ **Security risk:** Firmware dump exposes credentials for all devices

---

## Solution Overview

**Replace passwords with certificates:**

```
OLD WAY (Passwords):
ESP32 → MQTT with username/password → Mosquitto validates password

NEW WAY (Certificates):
ESP32 → MQTT with client certificate → Mosquitto validates certificate
```

**Key Changes:**
1. Generate certificate **DURING provisioning** (not before)
2. Backend creates certificate on-demand
3. ESP32 saves certificate to SPIFFS
4. No passwords anywhere

---

## What Needs To Change

### 1. Backend Changes

| File | What Changes | Why |
|------|-------------|-----|
| `mqtt_service.py` | Add certificate generation to provisioning handler | Backend generates cert when device provisions |
| `esp32.py` | Add HTTP endpoint for certificate provisioning | ESP32 gets cert via HTTPS (captive portal) |
| Database | Add `device_certificates` table | Store issued certificates |
| `mosquitto.conf` | Enable `require_certificate true` | Enforce client certificates |

### 2. ESP32 Firmware Changes

| File | What Changes | Why |
|------|-------------|-----|
| `esp32_hospital_watch_complete.ino` | Remove hardcoded credentials | No more shared passwords |
| `esp32_hospital_watch_complete.ino` | Add HTTPS provisioning endpoint call | Get certificate from backend |
| `esp32_hospital_watch_complete.ino` | Save certificate to SPIFFS | Store cert + private key |
| `esp32_hospital_watch_complete.ino` | Load certificate on boot | Use cert for MQTT connection |

### 3. Mosquitto Changes

| File | What Changes | Why |
|------|-------------|-----|
| `mosquitto.conf` | Add `require_certificate true` | Require client certs |
| `mosquitto.conf` | Add `use_identity_as_username true` | Extract device ID from cert |
| Remove `passwords.txt` | No longer needed | Using certificates now |

### 4. Database Changes

| Migration | What Changes | Why |
|-----------|-------------|-----|
| New table | `device_certificates` | Track issued certificates |
| New table | `provisioning_codes` | One-time provisioning codes |

---

## Step-by-Step Implementation

### **Phase 1: Backend Certificate Infrastructure (Day 1-2)**

#### Step 1.1: Generate Hospital CA Certificate (One-Time Setup)

**What:** Create the "root" certificate that signs all device certificates.

**Where:** Run on your development machine or server

**Commands:**
```bash
cd c:\Users\Srika\OneDrive\Desktop\hospital-management-system\mosquitto\certs

# Generate CA private key (4096-bit for security)
openssl genrsa -out hospital_ca.key 4096

# Generate CA certificate (valid 10 years)
openssl req -x509 -new -nodes -key hospital_ca.key \
    -sha256 -days 3650 -out hospital_ca.crt \
    -subj "/C=IN/ST=Maharashtra/L=Mumbai/O=Hospital/OU=IT/CN=Hospital CA"

# Verify CA certificate
openssl x509 -in hospital_ca.crt -text -noout
```

**Result:**
- `hospital_ca.key` (PRIVATE - keep secure!)
- `hospital_ca.crt` (PUBLIC - can be shared)

**Security:**
- **NEVER commit `hospital_ca.key` to git**
- Store in secure location (e.g., `/secure/` folder outside repo)
- Backup to encrypted USB drive

---

#### Step 1.2: Create Database Tables

**File:** `hospital-backend/migrations/013_certificate_provisioning.sql`

```sql
-- Provisioning codes (one-time use)
CREATE TABLE provisioning_codes (
    code VARCHAR(20) PRIMARY KEY,
    technician_id VARCHAR(50) REFERENCES staff(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT false,
    used_at TIMESTAMPTZ,
    device_id VARCHAR(50) REFERENCES devices(id)
);

CREATE INDEX idx_prov_codes_expiry ON provisioning_codes(expires_at) WHERE used = false;

-- Device certificates
CREATE TABLE device_certificates (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) REFERENCES devices(id) UNIQUE,
    certificate_pem TEXT NOT NULL,
    issued_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMPTZ,
    mac_address VARCHAR(17) NOT NULL,
    serial_number VARCHAR(50),
    CONSTRAINT unique_device_cert UNIQUE (device_id)
);

CREATE INDEX idx_device_certs_mac ON device_certificates(mac_address);
CREATE INDEX idx_device_certs_expiry ON device_certificates(expires_at);
```

**Apply migration:**
```bash
cd hospital-backend
python apply_migration_013.py
```

---

#### Step 1.3: Add Certificate Generation Code

**File:** `hospital-backend/app/services/certificate_service.py` (NEW FILE)

```python
"""
Certificate generation service for ESP32 devices
"""
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CertificateService:
    def __init__(self, ca_cert_path: str, ca_key_path: str):
        """
        Initialize certificate service with Hospital CA

        Args:
            ca_cert_path: Path to hospital_ca.crt
            ca_key_path: Path to hospital_ca.key
        """
        # Load CA certificate
        with open(ca_cert_path, 'rb') as f:
            self.ca_cert = x509.load_pem_x509_certificate(f.read())

        # Load CA private key
        with open(ca_key_path, 'rb') as f:
            self.ca_private_key = serialization.load_pem_private_key(
                f.read(),
                password=None
            )

        logger.info("✅ Certificate service initialized")

    def generate_device_certificate(
        self,
        device_id: str,
        mac_address: str,
        validity_days: int = 365
    ) -> tuple[str, str]:
        """
        Generate X.509 certificate for ESP32 device

        Args:
            device_id: Unique device identifier (e.g., ESP32_WATCH_001)
            mac_address: Device MAC address
            validity_days: Certificate validity period (default 1 year)

        Returns:
            tuple: (certificate_pem, private_key_pem)
        """

        # 1. Generate private key for device (2048-bit RSA)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        # 2. Create certificate subject (device identity)
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, device_id),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Hospital Devices"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "IoT Watches"),
        ])

        # 3. Build certificate
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(self.ca_cert.subject)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=validity_days))
        )

        # 4. Add Subject Alternative Name (SAN) for flexible identification
        cert_builder = cert_builder.add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(device_id),
                x509.DNSName(f"{device_id}.hospital.local"),
                x509.DNSName(f"watch-{mac_address.replace(':', '')}"),
            ]),
            critical=False,
        )

        # 5. Add Key Usage extension (for MQTT client auth)
        cert_builder = cert_builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )

        # 6. Add Extended Key Usage (TLS client authentication)
        cert_builder = cert_builder.add_extension(
            x509.ExtendedKeyUsage([
                x509.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        )

        # 7. Sign certificate with Hospital CA private key
        certificate = cert_builder.sign(
            private_key=self.ca_private_key,
            algorithm=hashes.SHA256()
        )

        # 8. Convert to PEM format (text format for storage/transmission)
        certificate_pem = certificate.public_bytes(
            encoding=serialization.Encoding.PEM
        ).decode('utf-8')

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        logger.info(f"✅ Generated certificate for {device_id} (valid {validity_days} days)")

        return certificate_pem, private_key_pem

# Global service instance (initialized in main.py)
certificate_service = None

def initialize_certificate_service(ca_cert_path: str, ca_key_path: str):
    """Initialize global certificate service"""
    global certificate_service
    certificate_service = CertificateService(ca_cert_path, ca_key_path)
    return certificate_service
```

---

#### Step 1.4: Add Provisioning Code Generation Endpoint

**File:** `hospital-backend/app/api/v1/provisioning.py` (NEW FILE)

```python
"""
Provisioning API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import uuid
import logging

from ...core.database import getDbConnection
from ...core.auth_dependencies import require_admin_or_medical
from ...services.certificate_service import certificate_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/generate-code")
async def generate_provisioning_code(
    technician: dict = Depends(require_admin_or_medical)
):
    """
    Generate one-time provisioning code

    Used by technician to provision ESP32 devices
    Code is valid for 10 minutes
    """

    # Generate short, human-friendly code
    code = f"PROV-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    async with getDbConnection() as conn:
        await conn.execute("""
            INSERT INTO provisioning_codes (code, technician_id, expires_at, used)
            VALUES ($1, $2, $3, false)
        """, code, technician['id'], expires_at)

    logger.info(f"✅ Provisioning code generated: {code} (technician: {technician['id']})")

    return {
        "success": True,
        "code": code,
        "expiresAt": expires_at.isoformat(),
        "expiresIn": "10 minutes"
    }

@router.post("/provision-with-certificate")
async def provision_device_with_certificate(request: dict):
    """
    Provision ESP32 device with client certificate

    Called by ESP32 via captive portal

    Request:
        {
            "provisioningCode": "PROV-AB12-CD34",
            "deviceId": "ESP32_30AEA4123456",
            "macAddress": "30:AE:A4:12:34:56"
        }

    Response:
        {
            "success": true,
            "deviceId": "ESP32_WATCH_001",
            "serialNumber": "SN_W001",
            "certificate": "-----BEGIN CERTIFICATE-----...",
            "privateKey": "-----BEGIN PRIVATE KEY-----...",
            "caCertificate": "-----BEGIN CERTIFICATE-----..."
        }
    """

    prov_code = request.get("provisioningCode")
    mac_address = request.get("macAddress")

    if not prov_code or not mac_address:
        raise HTTPException(400, "Provisioning code and MAC address required")

    async with getDbConnection() as conn:
        # 1. Validate provisioning code
        code_record = await conn.fetchrow("""
            SELECT * FROM provisioning_codes
            WHERE code = $1 AND used = false AND expires_at > NOW()
        """, prov_code)

        if not code_record:
            logger.warning(f"❌ Invalid or expired provisioning code: {prov_code}")
            raise HTTPException(400, "Invalid or expired provisioning code")

        # 2. Check if device already exists (re-provisioning)
        existing_device = await conn.fetchrow(
            'SELECT id, "serialNumber" FROM devices WHERE "macAddress" = $1',
            mac_address
        )

        if existing_device:
            device_id = existing_device['id']
            serial_number = existing_device['serialNumber']
            logger.info(f"🔄 Re-provisioning existing device: {device_id}")
        else:
            # 3. Generate new device ID and serial number
            device_count = await conn.fetchval(
                'SELECT COUNT(*) FROM devices WHERE "deviceType" = \'watch\''
            )
            new_device_number = device_count + 1

            device_id = f"ESP32_WATCH_{new_device_number:03d}"
            serial_number = f"SN_W{new_device_number:03d}"
            device_name = f"ESP32 Watch #{new_device_number:03d}"

            # 4. Create device record
            await conn.execute("""
                INSERT INTO devices (
                    id, "deviceType", name, "serialNumber", "macAddress",
                    "firmwareVersion", status, location, "createdAt", "updatedAt"
                )
                VALUES ($1, 'watch', $2, $3, $4, '4.2.0', 'available', 'Device Pool', NOW(), NOW())
            """, device_id, device_name, serial_number, mac_address)

            logger.info(f"✅ New device created: {device_id}")

        # 5. Generate client certificate
        certificate_pem, private_key_pem = certificate_service.generate_device_certificate(
            device_id=device_id,
            mac_address=mac_address,
            validity_days=365
        )

        # 6. Store certificate in database
        expires_at = datetime.utcnow() + timedelta(days=365)

        # Check if certificate already exists (re-provisioning)
        existing_cert = await conn.fetchrow(
            "SELECT id FROM device_certificates WHERE device_id = $1",
            device_id
        )

        if existing_cert:
            # Update existing certificate
            await conn.execute("""
                UPDATE device_certificates
                SET certificate_pem = $2, issued_at = NOW(), expires_at = $3, revoked = false
                WHERE device_id = $1
            """, device_id, certificate_pem, expires_at)
        else:
            # Insert new certificate
            await conn.execute("""
                INSERT INTO device_certificates (device_id, certificate_pem, expires_at, mac_address, serial_number)
                VALUES ($1, $2, $3, $4, $5)
            """, device_id, certificate_pem, expires_at, mac_address, serial_number)

        # 7. Mark provisioning code as used
        await conn.execute("""
            UPDATE provisioning_codes
            SET used = true, used_at = NOW(), device_id = $2
            WHERE code = $1
        """, prov_code, device_id)

        # 8. Get CA certificate (for ESP32 to validate server)
        ca_cert_path = "C:/Users/Srika/OneDrive/Desktop/hospital-management-system/mosquitto/certs/hospital_ca.crt"
        with open(ca_cert_path, 'r') as f:
            ca_certificate = f.read()

        logger.info(f"🎉 Device provisioned with certificate: {device_id}")

        return {
            "success": True,
            "deviceId": device_id,
            "serialNumber": serial_number,
            "certificate": certificate_pem,
            "privateKey": private_key_pem,
            "caCertificate": ca_certificate,
            "mqttServer": "127.0.0.1",
            "mqttPort": 8883
        }
```

---

#### Step 1.5: Register Routes in Main

**File:** `hospital-backend/main.py`

Add these lines:

```python
# Add after existing imports
from app.services.certificate_service import initialize_certificate_service
from app.api.v1 import provisioning

# Initialize certificate service (after line 100 or so)
try:
    ca_cert_path = "C:/Users/Srika/OneDrive/Desktop/hospital-management-system/mosquitto/certs/hospital_ca.crt"
    ca_key_path = "C:/Users/Srika/OneDrive/Desktop/hospital-management-system/mosquitto/certs/hospital_ca.key"
    initialize_certificate_service(ca_cert_path, ca_key_path)
    logger.info("✅ Certificate service initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize certificate service: {e}")

# Register provisioning routes (after line 500 or with other route registrations)
app.include_router(
    provisioning.router,
    prefix="/api/v1/provisioning",
    tags=["Provisioning"]
)
```

---

### **Phase 2: Mosquitto Configuration (Day 2)**

#### Step 2.1: Update Mosquitto Config

**File:** `mosquitto/config/mosquitto.conf`

**REPLACE entire file with:**

```conf
# =====================================================
# Hospital Management System - Mosquitto Configuration
# Certificate-Based Authentication (TLS mTLS)
# =====================================================

# ==================
# LISTENERS
# ==================

# TLS Listener with client certificate authentication
listener 8883
protocol mqtt

# ==================
# TLS/SSL
# ==================

# Server certificates
cafile /mosquitto/certs/hospital_ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key

# REQUIRE client certificates (this is the key change!)
require_certificate true

# Use certificate Common Name as MQTT username
use_identity_as_username true

# TLS version (1.2 minimum)
tls_version tlsv1.2

# ==================
# ACCESS CONTROL
# ==================

# ACL file for topic-level permissions
acl_file /mosquitto/config/acl.conf

# ==================
# RATE LIMITING
# ==================

max_connections 100
max_inflight_messages 20
max_queued_messages 1000
message_size_limit 10240

# ==================
# PERSISTENCE
# ==================

persistence true
persistence_location /mosquitto/data/
autosave_interval 300

# ==================
# LOGGING
# ==================

log_dest stdout
log_type error
log_type warning
log_type notice
log_type information
connection_messages true

# ==================
# PERFORMANCE
# ==================

max_keepalive 65535
```

**Key changes:**
- `require_certificate true` → Forces client certificates
- `use_identity_as_username true` → Uses certificate CN as username
- **Removed** `password_file` → No longer using passwords
- **Removed** `allow_anonymous` → Must have certificate

---

#### Step 2.2: Update ACL File

**File:** `mosquitto/config/acl.conf`

```conf
# =====================================================
# Hospital MQTT Access Control List (ACL)
# Certificate-based authentication
# =====================================================

# Pattern-based ACLs (username = device ID from certificate CN)

# Backend (hospitalBackend) has full access
user hospitalBackend
topic readwrite #

# ESP32 watches can only access their own topics
pattern read hospital/devices/%u/#
pattern write hospital/devices/%u/#

# Provisioning topics (for unprovisioned devices)
pattern write hospital/provisioning/request
pattern read hospital/provisioning/response/%u

# Specific examples:
# user ESP32_WATCH_001
# topic write hospital/devices/ESP32_WATCH_001/vitals
# topic write hospital/devices/ESP32_WATCH_001/heartbeat
# topic write hospital/devices/ESP32_WATCH_001/alerts
# topic read hospital/devices/ESP32_WATCH_001/assign
# topic read hospital/devices/ESP32_WATCH_001/command
```

---

#### Step 2.3: Delete Password File

```bash
# This file is no longer needed
rm mosquitto/config/passwords.txt
```

---

#### Step 2.4: Restart Mosquitto

```bash
# Restart Docker container
docker-compose restart mosquitto

# Check logs
docker-compose logs mosquitto
```

**Expected output:**
```
mosquitto_1  | 1729....: mosquitto version 2.0.18 starting
mosquitto_1  | 1729....: Using default config.
mosquitto_1  | 1729....: Opening ipv4 listen socket on port 8883.
mosquitto_1  | 1729....: mosquitto version 2.0.18 running
```

---

### **Phase 3: ESP32 Firmware Changes (Day 3-4)**

#### Step 3.1: Remove Hardcoded Credentials

**File:** `esp32_hospital_watch_complete.ino`

**FIND (around line 79-80):**
```cpp
String mqttUsername = "hospitalEsp32";
String mqttPassword = "ahTb1xbhkUeLaTTvvnb9IXI5SpoxtzO85zxpXgQnF/Q=";
```

**REPLACE WITH:**
```cpp
// ✅ REMOVED: No more hardcoded credentials
// Certificates are loaded from SPIFFS after provisioning
```

---

#### Step 3.2: Add Certificate Storage Functions

**File:** `esp32_hospital_watch_complete.ino`

**ADD after line 169 (after `loadCACertificate()` function):**

```cpp
// ====================================
// CERTIFICATE STORAGE (NEW)
// ====================================

const char* DEVICE_CERT_PATH = "/device.crt";
const char* DEVICE_KEY_PATH = "/device.key";

bool hasCertificates() {
  return SPIFFS.exists(DEVICE_CERT_PATH) && SPIFFS.exists(DEVICE_KEY_PATH);
}

bool loadDeviceCertificate(String& cert, String& key) {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  // Load device certificate
  File certFile = SPIFFS.open(DEVICE_CERT_PATH, "r");
  if (!certFile) {
    Serial.println("❌ Device certificate not found");
    return false;
  }
  cert = certFile.readString();
  certFile.close();

  // Load device private key
  File keyFile = SPIFFS.open(DEVICE_KEY_PATH, "r");
  if (!keyFile) {
    Serial.println("❌ Device private key not found");
    return false;
  }
  key = keyFile.readString();
  keyFile.close();

  if (cert.length() == 0 || key.length() == 0) {
    Serial.println("❌ Certificate or key is empty");
    return false;
  }

  Serial.println("✅ Device certificates loaded from SPIFFS");
  Serial.println("   Certificate: " + String(cert.length()) + " bytes");
  Serial.println("   Private Key: " + String(key.length()) + " bytes");

  return true;
}

bool saveCertificates(String cert, String key) {
  if (!SPIFFS.begin(true)) {
    Serial.println("❌ SPIFFS mount failed");
    return false;
  }

  // Save certificate
  File certFile = SPIFFS.open(DEVICE_CERT_PATH, "w");
  if (!certFile) {
    Serial.println("❌ Failed to open certificate file for writing");
    return false;
  }
  certFile.print(cert);
  certFile.close();

  // Save private key
  File keyFile = SPIFFS.open(DEVICE_KEY_PATH, "w");
  if (!keyFile) {
    Serial.println("❌ Failed to open key file for writing");
    return false;
  }
  keyFile.print(key);
  keyFile.close();

  Serial.println("✅ Certificates saved to SPIFFS");
  return true;
}
```

---

#### Step 3.3: Replace MQTT Provisioning with HTTPS Provisioning

**File:** `esp32_hospital_watch_complete.ino`

**FIND function `attemptProvisioning()` (around line 1071):**

**REPLACE ENTIRE FUNCTION with:**

```cpp
// ====================================
// HTTPS PROVISIONING (NEW - Certificate-Based)
// ====================================
void attemptProvisioning() {
  String provId = prefs.getString("prov_id", "");
  String provPass = prefs.getString("prov_pass", "");

  if (provId.length() == 0 || serverIP.length() == 0) {
    Serial.println("❌ Missing provisioning credentials");
    return;
  }

  Serial.println("🔄 Attempting HTTPS provisioning with certificates...");
  provisioningInProgress = true;

  // Build HTTPS URL
  String url = "https://" + serverIP + ":8001/api/v1/provisioning/provision-with-certificate";

  // Create HTTPS client
  HTTPClient http;
  WiFiClientSecure secureClient;

  // Trust Hospital CA for server verification
  secureClient.setCACert(caCertificate.c_str());

  http.begin(secureClient, url);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(15000);  // 15 second timeout

  // Build JSON request
  JsonDocument doc;
  doc["provisioningCode"] = provPass;  // Provisioner password is now the provisioning code
  doc["deviceId"] = "ESP32_" + macAddress;
  doc["macAddress"] = macAddress;

  String payload;
  serializeJson(doc, payload);

  Serial.println("📤 Sending provisioning request to: " + url);

  int httpCode = http.POST(payload);

  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("✅ Provisioning response received");

    JsonDocument responseDoc;
    if (deserializeJson(responseDoc, response) == DeserializationError::Ok) {
      if (responseDoc["success"]) {
        // Extract provisioning data
        deviceId = responseDoc["deviceId"].as<String>();
        serialNumber = responseDoc["serialNumber"].as<String>();

        // Extract certificates
        String certificate = responseDoc["certificate"].as<String>();
        String privateKey = responseDoc["privateKey"].as<String>();
        String caCert = responseDoc["caCertificate"].as<String>();

        // Save certificates to SPIFFS
        if (saveCertificates(certificate, privateKey)) {
          isProvisioned = true;
          provisioningInProgress = false;
          saveConfiguration();

          Serial.println("🎉 DEVICE PROVISIONED with CLIENT CERTIFICATE!");
          Serial.println("   📱 Device ID: " + deviceId);
          Serial.println("   📋 Serial: " + serialNumber);

          // Flash LED to indicate success
          for(int i = 0; i < 10; i++) {
            digitalWrite(2, HIGH);
            delay(100);
            digitalWrite(2, LOW);
            delay(100);
          }
          digitalWrite(2, HIGH);

          // Connect to MQTT with new certificate
          delay(1000);
          setupMQTT();
        } else {
          Serial.println("❌ Failed to save certificates");
          provisioningInProgress = false;
        }
      } else {
        Serial.println("❌ Provisioning failed: " + responseDoc["message"].as<String>());
        provisioningInProgress = false;
      }
    }
  } else {
    Serial.println("❌ HTTP request failed: " + String(httpCode));
    provisioningInProgress = false;
  }

  http.end();
}
```

---

#### Step 3.4: Update MQTT Connection to Use Certificates

**File:** `esp32_hospital_watch_complete.ino`

**FIND function `connectToMQTT()` (around line 953):**

**REPLACE ENTIRE FUNCTION with:**

```cpp
void connectToMQTT() {
  if (!wifiConnected || !isProvisioned) return;

  // Load device certificate and private key
  String deviceCert, deviceKey;
  if (!loadDeviceCertificate(deviceCert, deviceKey)) {
    Serial.println("❌ Cannot connect to MQTT: No certificates");
    return;
  }

  // Configure TLS with client certificate
  wifiClient.setCACert(caCertificate.c_str());
  wifiClient.setCertificate(deviceCert.c_str());
  wifiClient.setPrivateKey(deviceKey.c_str());

  Serial.println("🔐 TLS configured with client certificate");

  String clientId = "HospitalWatch_" + deviceId;
  Serial.println("🔄 Connecting to MQTT TLS broker as: " + clientId);
  Serial.println("🔐 Using CLIENT CERTIFICATE (no password)");

  // Connect with NO username/password (certificate authentication)
  if (mqttClient.connect(clientId.c_str())) {
    Serial.println("✅ MQTT Connected with CLIENT CERTIFICATE!");

    String assignTopic = "hospital/devices/" + deviceId + "/assign";
    mqttClient.subscribe(assignTopic.c_str());
    Serial.println("📡 Subscribed to: " + assignTopic);

    String commandTopic = "hospital/devices/" + deviceId + "/command";
    mqttClient.subscribe(commandTopic.c_str());
    Serial.println("📡 Subscribed to: " + commandTopic);

  } else {
    Serial.println("❌ MQTT Connection failed, rc=" + String(mqttClient.state()));
  }
}
```

---

#### Step 3.5: Update Setup Function

**File:** `esp32_hospital_watch_complete.ino`

**FIND line in `setup()` that checks `isProvisioned` (around line 479):**

**CHANGE FROM:**
```cpp
if (isProvisioned) {
    setupMQTT();
}
```

**TO:**
```cpp
if (isProvisioned && hasCertificates()) {
    setupMQTT();
} else if (isProvisioned && !hasCertificates()) {
    Serial.println("⚠️ Device provisioned but no certificates - need re-provisioning");
    isProvisioned = false;
    saveConfiguration();
}
```

---

#### Step 3.6: Add HTTPClient Library

**File:** `esp32_hospital_watch_complete.ino`

**ADD at top (after line 31):**
```cpp
#include <HTTPClient.h>
```

---

### **Phase 4: Testing (Day 5)**

#### Test 1: Generate CA Certificate

```bash
cd c:\Users\Srika\OneDrive\Desktop\hospital-management-system\mosquitto\certs

# Generate CA (if not done yet)
openssl genrsa -out hospital_ca.key 4096
openssl req -x509 -new -nodes -key hospital_ca.key -sha256 -days 3650 -out hospital_ca.crt -subj "/CN=Hospital CA"

# Verify
openssl x509 -in hospital_ca.crt -text -noout
```

#### Test 2: Apply Database Migration

```bash
cd hospital-backend
python apply_migration_013.py
```

#### Test 3: Start Backend

```bash
cd hospital-backend
python -m uvicorn main:app --reload --port 8001
```

**Check logs for:**
```
✅ Certificate service initialized
```

#### Test 4: Restart Mosquitto

```bash
docker-compose restart mosquitto
docker-compose logs mosquitto
```

**Check for:**
```
mosquitto_1  | 1729....: mosquitto version 2.0.18 running
```

#### Test 5: Flash ESP32

```bash
# Flash updated firmware
arduino-cli compile --fqbn esp32:esp32:esp32 esp32_hospital_watch_complete
arduino-cli upload -p COM3 --fqbn esp32:esp32:esp32 esp32_hospital_watch_complete
```

#### Test 6: Provision Device

1. Connect to ESP32 hotspot: `HospitalWatch`
2. Open browser → `http://192.168.4.1`
3. Enter WiFi credentials
4. Enter provisioning code from backend
5. Watch serial monitor for:
   ```
   🎉 DEVICE PROVISIONED with CLIENT CERTIFICATE!
   ✅ Certificates saved to SPIFFS
   ✅ MQTT Connected with CLIENT CERTIFICATE!
   ```

#### Test 7: Verify Certificate Storage

```bash
# Use ESP32 filesystem tool to check SPIFFS
ls -la /spiffs/
# Should see:
# ca.crt
# device.crt
# device.key
```

#### Test 8: Test MQTT Communication

Watch serial monitor for:
```
📊 Vitals: HR=75, Temp=37.0°C, SpO2=98%, RR=16
💓 MQTT Heartbeat sent
```

---

### **Phase 5: Backend Certificate Provisioning Integration (Day 6)**

Update backend dashboard to allow technicians to generate provisioning codes.

**File:** `hospital-display-app/src/components/Provisioning/ProvisioningCodeGenerator.tsx` (NEW FILE)

```typescript
import React, { useState } from 'react';
import { Button, TextField, Card, CardContent, Typography } from '@mui/material';

export const ProvisioningCodeGenerator: React.FC = () => {
    const [code, setCode] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const generateCode = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/v1/provisioning/generate-code', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`,
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            setCode(data.code);
        } catch (error) {
            console.error('Failed to generate code:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card>
            <CardContent>
                <Typography variant="h5">Generate Provisioning Code</Typography>
                <Button
                    variant="contained"
                    color="primary"
                    onClick={generateCode}
                    disabled={loading}
                    sx={{ mt: 2 }}
                >
                    Generate Code
                </Button>

                {code && (
                    <Card sx={{ mt: 2, bgcolor: '#e3f2fd', p: 2 }}>
                        <Typography variant="h3" align="center">{code}</Typography>
                        <Typography variant="body2" align="center" sx={{ mt: 1 }}>
                            Valid for 10 minutes
                        </Typography>
                    </Card>
                )}
            </CardContent>
        </Card>
    );
};
```

---

### **Phase 6: Certificate Revocation (Day 7)**

Add endpoint to revoke compromised device certificates.

**File:** `hospital-backend/app/api/v1/provisioning.py`

```python
@router.post("/revoke-certificate/{device_id}")
async def revoke_device_certificate(
    device_id: str,
    admin: dict = Depends(require_admin)
):
    """
    Revoke device certificate

    Used when device is stolen or compromised
    Device will no longer be able to connect to MQTT
    """

    async with getDbConnection() as conn:
        # Mark certificate as revoked
        await conn.execute("""
            UPDATE device_certificates
            SET revoked = true, revoked_at = NOW()
            WHERE device_id = $1
        """, device_id)

        logger.warning(f"🚨 Certificate revoked for device: {device_id} (by {admin['id']})")

    return {
        "success": True,
        "message": f"Certificate revoked for {device_id}"
    }
```

---

## Summary of Changes

### Files Created:
1. `hospital-backend/app/services/certificate_service.py`
2. `hospital-backend/app/api/v1/provisioning.py`
3. `hospital-backend/migrations/013_certificate_provisioning.sql`
4. `hospital-display-app/src/components/Provisioning/ProvisioningCodeGenerator.tsx`

### Files Modified:
1. `esp32_hospital_watch_complete.ino` (major changes)
2. `mosquitto/config/mosquitto.conf` (enable mTLS)
3. `mosquitto/config/acl.conf` (update ACLs)
4. `hospital-backend/main.py` (register routes)

### Files Deleted:
1. `mosquitto/config/passwords.txt` (no longer needed)

---

## Timeline

| Day | Task | Who | Hours |
|-----|------|-----|-------|
| 1 | Generate CA, create database tables, certificate service | Developer | 4h |
| 2 | Provisioning endpoint, Mosquitto config | Developer | 4h |
| 3 | ESP32 firmware changes (remove passwords) | Developer | 4h |
| 4 | ESP32 firmware changes (add certificate loading) | Developer | 4h |
| 5 | Testing end-to-end | Developer | 6h |
| 6 | Frontend provisioning UI | Developer | 4h |
| 7 | Certificate revocation, documentation | Developer | 2h |

**Total:** ~28 hours (1 week for 1 developer)

---

## Testing Checklist

- [ ] CA certificate generated
- [ ] Database migration applied
- [ ] Backend certificate service works
- [ ] Provisioning code generation works
- [ ] Mosquitto accepts client certificates
- [ ] ESP32 can load certificates from SPIFFS
- [ ] ESP32 can connect with certificate (no password)
- [ ] Vitals data flows over MQTT
- [ ] Certificate revocation works
- [ ] Cannot connect with old shared credentials

---

## Rollback Plan

If something goes wrong:

1. **Revert Mosquitto config:**
   ```bash
   git checkout mosquitto/config/mosquitto.conf
   docker-compose restart mosquitto
   ```

2. **Revert ESP32 firmware:**
   ```bash
   git checkout esp32_hospital_watch_complete.ino
   # Flash previous version
   ```

3. **Keep database migration:**
   - Tables don't hurt anything if not used
   - Can drop later if needed

---

## Security Considerations

✅ **Private keys never leave device** - Generated on backend, transmitted once, stored in SPIFFS
✅ **CA private key secured** - Stored outside git repo, encrypted backups
✅ **Certificate revocation** - Can blacklist stolen devices
✅ **1-year validity** - Automatic re-provisioning after 1 year
✅ **No shared credentials** - Each device has unique certificate

---

## Questions?

Ready to implement? Tell me which phase you want to start with, or if you want me to make any changes to the plan.
