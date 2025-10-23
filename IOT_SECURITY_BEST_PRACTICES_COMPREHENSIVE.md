# IoT Security Best Practices for Hospital Watches & Door Scanners

**Date:** 2025-10-17
**Context:** ESP32-based medical devices (patient watches + door scanners)
**Environment:** Hospital deployment (India - DPDP 2023 + HIPAA reference)

---

## Table of Contents

1. [Authentication & Authorization](#1-authentication--authorization)
2. [Provisioning & Onboarding](#2-provisioning--onboarding)
3. [Communication Security](#3-communication-security)
4. [Data Protection](#4-data-protection)
5. [Device Identity & Management](#5-device-identity--management)
6. [Firmware Security](#6-firmware-security)
7. [Physical Security](#7-physical-security)
8. [Monitoring & Alerting](#8-monitoring--alerting)
9. [Compliance & Audit](#9-compliance--audit)
10. [Incident Response](#10-incident-response)

---

## 1. Authentication & Authorization

### 1.1 Certificate-Based Authentication (PKI) ⭐ **BEST FOR PRODUCTION**

**What It Is:**
Use X.509 certificates for device authentication instead of passwords.

**How It Works:**
```
Factory Setup:
1. Generate unique client certificate per device (signed by Hospital CA)
2. Flash certificate + private key to ESP32 secure storage
3. Configure TLS mutual authentication (mTLS)

Device Connection:
1. Device presents certificate to backend/broker
2. Backend validates certificate against trusted CA
3. Device identity verified cryptographically
```

**Standards:**
- **X.509 v3** certificates
- **RSA 2048-bit** or **ECDSA P-256** keys
- **TLS 1.2+** with mutual authentication (mTLS)
- **OCSP** or **CRL** for certificate revocation

**Pros:**
- ✅ No passwords to store or steal
- ✅ Unique cryptographic identity per device
- ✅ Certificate revocation (CRL/OCSP)
- ✅ Industry standard (used by AWS IoT, Azure IoT)
- ✅ Scales to millions of devices
- ✅ HIPAA/DPDP compliant

**Cons:**
- ❌ Requires PKI infrastructure (CA, certificate management)
- ❌ More complex initial setup
- ❌ Requires secure storage on device (ESP32 flash encryption or secure element)

**Implementation:**

```cpp
// ESP32 Firmware
#include <WiFiClientSecure.h>

WiFiClientSecure espClient;

void setupMQTTWithCertificates() {
    // Load client certificate from SPIFFS
    espClient.setCACert(ca_cert);          // CA certificate (validates server)
    espClient.setCertificate(client_cert); // Device certificate (proves identity)
    espClient.setPrivateKey(client_key);   // Device private key

    mqttClient.setClient(espClient);
    mqttClient.connect(deviceId);          // No username/password needed!
}
```

**Backend (Mosquitto):**
```conf
# mosquitto.conf
listener 8883
protocol mqtt

# Enable TLS with client certificate verification
cafile /mosquitto/certs/hospital_ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
require_certificate true
use_identity_as_username true  # Extract username from certificate CN
```

**Tools:**
- **OpenSSL** for certificate generation
- **CFSSL** for CA management
- **HashiCorp Vault** for PKI automation
- **Let's Encrypt** (for internal CA alternative)

---

### 1.2 Token-Based Authentication (JWT/OAuth2) ⭐ **GOOD FOR TESTING**

**What It Is:**
Devices authenticate with short-lived JWT tokens issued by backend.

**How It Works:**
```
Provisioning:
1. Device connects with one-time provisioning code
2. Backend validates code and issues JWT token
3. Device uses JWT for all subsequent requests

Token Refresh:
1. JWT expires after N hours/days
2. Device automatically requests new token before expiration
3. Backend issues new token if device still authorized
```

**Standards:**
- **JWT (RFC 7519)** for token format
- **HS256** or **RS256** for signing
- **Short expiration** (1-24 hours)
- **Refresh tokens** for automatic renewal

**Pros:**
- ✅ Stateless authentication
- ✅ Tokens can be revoked
- ✅ Fine-grained permissions (scopes in token)
- ✅ Easier to implement than PKI
- ✅ Standard web authentication flow

**Cons:**
- ❌ Requires clock synchronization (NTP)
- ❌ Token theft risk if not encrypted in transit
- ❌ More network requests (token refresh)

**Implementation:**

```cpp
// ESP32 Firmware
String jwtToken = "";
unsigned long tokenExpiry = 0;

void authenticateWithJWT() {
    HTTPClient http;
    http.begin(backendUrl + "/api/v1/auth/device-login");
    http.addHeader("Content-Type", "application/json");

    String payload = "{\"deviceId\":\"" + deviceId + "\",\"provisioningCode\":\"" + code + "\"}";

    int httpCode = http.POST(payload);
    if (httpCode == 200) {
        DynamicJsonDocument doc(1024);
        deserializeJson(doc, http.getString());

        jwtToken = doc["token"].as<String>();
        tokenExpiry = doc["expiresAt"].as<unsigned long>();
    }

    http.end();
}

void makeAuthenticatedRequest() {
    HTTPClient http;
    http.begin(backendUrl + "/api/v1/vitals");
    http.addHeader("Authorization", "Bearer " + jwtToken);
    http.POST(vitalsData);
    http.end();
}
```

**Backend:**
```python
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key"

def generate_device_token(device_id: str) -> str:
    payload = {
        "sub": device_id,
        "deviceType": "watch",
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
        "scopes": ["vitals:write", "alerts:read"]
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def verify_device_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.JWTError:
        raise HTTPException(401, "Invalid token")
```

---

### 1.3 HMAC-Based Authentication ⭐ **CURRENT IMPLEMENTATION**

**What It Is:**
Use HMAC-SHA256 to sign requests with shared secret.

**How It Works:**
```
Device side:
1. Concatenate request data: deviceId + timestamp + payload
2. Sign with HMAC-SHA256 using device secret
3. Send: data + signature

Backend side:
1. Lookup device secret from database
2. Re-compute HMAC with same inputs
3. Compare signatures (constant-time comparison)
4. Verify timestamp (prevent replay attacks)
```

**Standards:**
- **HMAC-SHA256** (RFC 2104)
- **Timestamp validation** (max 5 minutes old)
- **Nonce** (prevent replay attacks)

**Pros:**
- ✅ Simple to implement
- ✅ No certificate management
- ✅ Fast (symmetric crypto)
- ✅ Works offline (no token refresh)

**Cons:**
- ❌ Shared secrets must be pre-distributed
- ❌ Secret rotation is difficult
- ❌ Vulnerable to secret theft if device compromised
- ❌ Backend must store secrets for all devices

**Current Implementation Review:**
- ✅ Uses HMAC-SHA256
- ✅ Per-device secrets generated
- ❌ Missing timestamp validation (replay attack risk)
- ❌ Missing nonce (replay attack risk)
- ❌ Secrets stored in plaintext in database (should be hashed)

**Improved Implementation:**

```cpp
// ESP32 Firmware
String generateHMAC(String data, String secret) {
    uint8_t hmac_result[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;

    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
    mbedtls_md_hmac_starts(&ctx, (const uint8_t*)secret.c_str(), secret.length());
    mbedtls_md_hmac_update(&ctx, (const uint8_t*)data.c_str(), data.length());
    mbedtls_md_hmac_finish(&ctx, hmac_result);
    mbedtls_md_free(&ctx);

    // Convert to hex string
    String hmac = "";
    for (int i = 0; i < 32; i++) {
        char hex[3];
        sprintf(hex, "%02x", hmac_result[i]);
        hmac += hex;
    }
    return hmac;
}

void sendAuthenticatedRequest() {
    String timestamp = String(millis());
    String nonce = String(random(100000, 999999));
    String data = deviceId + ":" + timestamp + ":" + nonce + ":" + payload;
    String signature = generateHMAC(data, deviceSecret);

    HTTPClient http;
    http.begin(backendUrl);
    http.addHeader("X-Device-ID", deviceId);
    http.addHeader("X-Timestamp", timestamp);
    http.addHeader("X-Nonce", nonce);
    http.addHeader("X-Signature", signature);
    http.POST(payload);
}
```

**Backend:**
```python
import hmac
import hashlib
from datetime import datetime, timedelta

def verify_hmac_request(request):
    device_id = request.headers.get("X-Device-ID")
    timestamp = request.headers.get("X-Timestamp")
    nonce = request.headers.get("X-Nonce")
    signature = request.headers.get("X-Signature")
    payload = request.body

    # 1. Check timestamp (prevent replay - max 5 minutes old)
    request_time = datetime.fromtimestamp(int(timestamp) / 1000)
    if datetime.utcnow() - request_time > timedelta(minutes=5):
        raise HTTPException(401, "Request timestamp too old")

    # 2. Check nonce (prevent replay - store recent nonces in Redis)
    if redis_client.exists(f"nonce:{device_id}:{nonce}"):
        raise HTTPException(401, "Nonce already used (replay attack)")
    redis_client.setex(f"nonce:{device_id}:{nonce}", 300, "1")  # 5 min TTL

    # 3. Lookup device secret
    device = await db.fetchrow("SELECT hmac_secret FROM devices WHERE id = $1", device_id)
    if not device:
        raise HTTPException(404, "Device not found")

    # 4. Compute expected signature
    data = f"{device_id}:{timestamp}:{nonce}:{payload}"
    expected_signature = hmac.new(
        device["hmac_secret"].encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()

    # 5. Constant-time comparison (prevent timing attacks)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(401, "Invalid signature")

    return device_id
```

---

### 1.4 Comparison Table

| Method | Security | Complexity | Scalability | Revocation | Cost |
|--------|----------|------------|-------------|------------|------|
| **PKI (Certificates)** | 🟢 Excellent | 🟡 Medium | 🟢 Excellent | 🟢 Easy (CRL/OCSP) | 🟡 Medium |
| **JWT Tokens** | 🟢 Good | 🟢 Low | 🟢 Excellent | 🟢 Easy (blacklist) | 🟢 Low |
| **HMAC Signatures** | 🟡 Good | 🟢 Low | 🟡 Medium | 🔴 Hard | 🟢 Low |
| **Shared Credentials** | 🔴 Poor | 🟢 Low | 🔴 Poor | 🔴 Impossible | 🟢 Low |

**Recommendation:**
- **Production:** PKI (Certificates) - best security and scalability
- **Testing/POC:** JWT Tokens - good security, easier to implement
- **Acceptable:** HMAC (with timestamp + nonce) - if PKI/JWT too complex
- **NEVER:** Shared credentials hardcoded in firmware

---

## 2. Provisioning & Onboarding

### 2.1 QR Code Provisioning ⭐ **BEST UX**

**How It Works:**
```
1. Technician logs into backend dashboard
2. Backend generates unique QR code containing:
   - One-time provisioning token (JWT)
   - Backend server URL
   - Expiration timestamp (10 minutes)
3. Technician scans QR with phone camera
4. Phone opens ESP32 captive portal with token auto-filled
5. ESP32 sends token + MAC to backend
6. Backend validates token and provisions device
```

**Implementation:**

**Backend:**
```python
import qrcode
import jwt
from io import BytesIO

@router.post("/provisioning/generate-qr")
async def generate_provisioning_qr(
    technician: Staff = Depends(verify_technician)
):
    # Generate one-time provisioning token
    token_payload = {
        "type": "provisioning",
        "technician_id": technician.id,
        "exp": datetime.utcnow() + timedelta(minutes=10),
        "jti": str(uuid.uuid4())  # Unique token ID
    }
    token = jwt.encode(token_payload, settings.secret_key, algorithm="HS256")

    # Create QR code data
    qr_data = {
        "action": "provision_device",
        "token": token,
        "backend_url": settings.backend_url,
        "backend_port": settings.backend_port
    }
    qr_json = json.dumps(qr_data)

    # Generate QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_json)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64 for web display
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        "success": True,
        "token": token,
        "qr_code": f"data:image/png;base64,{img_base64}",
        "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat()
    }
```

**ESP32 Firmware:**
```cpp
// Captive portal HTML with QR scanner
String html = R"(
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/html5-qrcode/minified/html5-qrcode.min.js"></script>
</head>
<body>
    <h1>Hospital Device Provisioning</h1>
    <div id="qr-reader" style="width:300px"></div>
    <script>
        const html5QrCode = new Html5Qrcode("qr-reader");

        html5QrCode.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: 250 },
            (decodedText) => {
                const provisioningData = JSON.parse(decodedText);

                // Auto-fill form
                document.getElementById('token').value = provisioningData.token;
                document.getElementById('backend_url').value = provisioningData.backend_url;

                // Auto-submit
                document.getElementById('provision-form').submit();
            }
        );
    </script>

    <form id="provision-form" action="/provision" method="POST">
        <input type="hidden" id="token" name="token">
        <input type="hidden" id="backend_url" name="backend_url">
        <input type="text" name="mac_address" value=")" + WiFi.macAddress() + R"(" readonly>
        <button type="submit">Provision Device</button>
    </form>
</body>
</html>
)";
```

**Pros:**
- ✅ Best user experience (one scan)
- ✅ No typing errors
- ✅ Time-limited tokens (10 min)
- ✅ Single-use tokens
- ✅ Audit trail (who provisioned when)

**Cons:**
- ❌ Requires camera/QR scanner
- ❌ Slightly more complex implementation

---

### 2.2 NFC Provisioning ⭐ **BEST FOR WEARABLES**

**How It Works:**
```
1. Technician has NFC-enabled badge with credentials
2. Tap badge on ESP32 watch (ESP32 reads NFC)
3. ESP32 extracts technician ID + auth token from badge
4. ESP32 provisions itself with backend
```

**Hardware:**
- **ESP32** with NFC reader (PN532 or MFRC522)
- **NFC badges** (NTAG216 or Mifare DESFire)

**Implementation:**

```cpp
#include <PN532.h>
#include <PN532_I2C.h>

PN532_I2C pn532i2c(Wire);
PN532 nfc(pn532i2c);

void setupNFC() {
    nfc.begin();
    nfc.SAMConfig();
}

void waitForNFCProvisioning() {
    uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };
    uint8_t uidLength;

    if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 1000)) {
        Serial.println("NFC Tag Detected!");

        // Read provisioning data from NFC tag (NDEF record)
        uint8_t data[128];
        nfc.mifareclassic_ReadDataBlock(4, data);

        String provisioningToken = String((char*)data);

        // Provision device with token
        provisionDevice(provisioningToken);
    }
}
```

**Pros:**
- ✅ Extremely fast (tap and go)
- ✅ Works without network (offline provisioning)
- ✅ No captive portal needed
- ✅ Secure (encrypted NFC tags possible)

**Cons:**
- ❌ Requires NFC hardware ($5-10 per device)
- ❌ NFC badges must be secured (physical access control)

---

### 2.3 BLE Provisioning (ESP RainMaker Style) ⭐ **GOOD FOR ESP32**

**How It Works:**
```
1. ESP32 advertises BLE service "HospitalProvision"
2. Technician uses mobile app (iOS/Android)
3. App discovers ESP32 via BLE
4. App sends WiFi credentials + backend URL via BLE
5. ESP32 connects to WiFi and provisions with backend
```

**Standards:**
- **ESP BLE Provisioning** (Espressif's official library)
- **Google Nearby** (Android)
- **Apple EasyConfig** (iOS)

**Implementation:**

```cpp
#include <WiFiProv.h>
#include <wifi_provisioning/manager.h>

void setup() {
    // Start BLE provisioning
    WiFiProv.beginProvision(
        WIFI_PROV_SCHEME_BLE,
        WIFI_PROV_SCHEME_HANDLER_FREE_BTDM,
        WIFI_PROV_SECURITY_1,
        "proof-of-possession",  // PoP (printed on device)
        "HospitalWatch"         // Service name
    );

    // Custom data endpoint for backend config
    WiFiProv.onProvisioningComplete([]() {
        Serial.println("WiFi provisioning complete");

        // Get backend config from custom endpoint
        String backendUrl = WiFiProv.getCustomData("backend_url");
        String provisioningToken = WiFiProv.getCustomData("provisioning_token");

        // Provision with backend
        provisionWithBackend(backendUrl, provisioningToken);
    });
}
```

**Mobile App (Flutter):**
```dart
import 'package:esp_provisioning/esp_provisioning.dart';

void provisionDevice() async {
    final provisioner = ESPProvisioning();

    // Scan for devices
    final devices = await provisioner.scanDevices();

    // Connect to device
    await provisioner.connectDevice(devices.first);

    // Send WiFi credentials
    await provisioner.provisionWiFi(
        ssid: "HospitalWiFi",
        password: "password123"
    );

    // Send custom data (backend config)
    await provisioner.sendCustomData({
        "backend_url": "https://backend.hospital.com",
        "provisioning_token": "eyJhbGciOiJIUzI1NiIs..."
    });
}
```

**Pros:**
- ✅ Official Espressif support
- ✅ Mobile app available (iOS/Android)
- ✅ Encrypted provisioning (SRP6a protocol)
- ✅ PoP (Proof-of-Possession) security

**Cons:**
- ❌ Requires mobile app
- ❌ BLE range limited (10m)

---

### 2.4 Comparison Table

| Method | UX | Security | Hardware | Complexity |
|--------|----|---------| ---------|------------|
| **QR Code** | 🟢 Excellent | 🟢 Good | 🟢 None | 🟡 Medium |
| **NFC** | 🟢 Excellent | 🟢 Excellent | 🔴 Requires NFC | 🟡 Medium |
| **BLE (RainMaker)** | 🟢 Good | 🟢 Good | 🟢 Built-in | 🟡 Medium |
| **Captive Portal** | 🟡 Fair | 🟡 Fair | 🟢 None | 🟢 Easy |
| **Hardcoded** | 🔴 Poor | 🔴 Poor | 🟢 None | 🟢 Easy |

**Recommendation:**
- **Watches:** QR Code or NFC (best UX for medical staff)
- **Door Scanners:** Captive Portal (current implementation is good)
- **Mobile App:** BLE Provisioning (if building custom app)

---

## 3. Communication Security

### 3.1 TLS 1.3 for HTTPS ⭐ **BEST**

**Current:** TLS 1.2
**Upgrade to:** TLS 1.3 (2023 standard)

**Benefits of TLS 1.3:**
- ✅ Faster handshake (1-RTT vs 2-RTT)
- ✅ Better cipher suites (removes weak ciphers)
- ✅ Forward secrecy by default
- ✅ Encrypted Server Hello (protects metadata)

**ESP32 Support:**
```cpp
#include <WiFiClientSecure.h>

WiFiClientSecure client;

void setupHTTPS() {
    client.setCACert(ca_cert);
    client.setInsecure(false);  // Require certificate validation

    // Force TLS 1.3 (mbedTLS 3.0+)
    // Note: ESP-IDF v5.0+ supports TLS 1.3
    client.setMinimumTLSVersion(MBEDTLS_SSL_MINOR_VERSION_4); // TLS 1.3
}
```

**Backend:**
```python
# main.py
import uvicorn
import ssl

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('server.crt', 'server.key')
ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3  # Force TLS 1.3
ssl_context.set_ciphers('TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256')

uvicorn.run(
    app,
    host="0.0.0.0",
    port=8001,
    ssl_version=ssl.PROTOCOL_TLS_SERVER,
    ssl_cert_reqs=ssl.CERT_REQUIRED,  # Require client certs (mTLS)
    ssl_context=ssl_context
)
```

---

### 3.2 MQTT over TLS (MQTTS) ⭐ **CURRENT - GOOD**

**Current Implementation:** ✅ Already using TLS 1.2 on port 8883

**Improvements:**
1. **Enable client certificate verification** (mTLS)
2. **Implement connection rate limiting**
3. **Add topic-level ACLs** (restrict what each device can publish/subscribe)

**Mosquitto Config:**
```conf
# mosquitto.conf

# TLS Listener with mutual auth
listener 8883
protocol mqtt

# TLS Configuration
cafile /mosquitto/certs/hospital_ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
require_certificate true           # ✅ NEW: Require client certificates
use_identity_as_username true      # ✅ NEW: Use cert CN as username
tls_version tlsv1.3                # ✅ UPGRADE: TLS 1.3

# ACL (Topic-level permissions)
acl_file /mosquitto/config/acl.conf

# Rate Limiting
max_connections 100
max_inflight_messages 20
max_queued_messages 1000
message_size_limit 10240
```

**ACL Configuration:**
```conf
# /mosquitto/config/acl.conf

# Pattern-based ACLs
pattern read hospital/%u/#          # Device can read its own topics
pattern write hospital/%u/#         # Device can write its own topics

# Specific device rules
user ESP32_WATCH_001
topic write hospital/vitals/ESP32_WATCH_001
topic read hospital/commands/ESP32_WATCH_001

user ESP32_WATCH_002
topic write hospital/vitals/ESP32_WATCH_002
topic read hospital/commands/ESP32_WATCH_002

# Backend has full access
user hospitalBackend
topic readwrite #
```

---

### 3.3 Certificate Pinning ⭐ **ADVANCED**

**What It Is:**
Hardcode expected server certificate fingerprint in firmware to prevent MITM attacks.

**Implementation:**

```cpp
// ESP32 Firmware
const char* server_cert_fingerprint = "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD";

WiFiClientSecure client;

void setupCertificatePinning() {
    client.setCACert(ca_cert);

    // Verify server certificate fingerprint
    if (!client.connect(serverIP, 8001)) {
        Serial.println("Connection failed");
        return;
    }

    String fingerprint = client.getCertFingerprint();
    if (fingerprint != server_cert_fingerprint) {
        Serial.println("❌ Certificate fingerprint mismatch! Possible MITM attack!");
        client.stop();
        return;
    }

    Serial.println("✅ Certificate pinning verified");
}
```

**Pros:**
- ✅ Prevents MITM even if CA is compromised
- ✅ Additional layer of defense

**Cons:**
- ❌ Firmware update needed when certificate rotates
- ❌ Inflexible (hard to change)

**Alternative: Certificate Public Key Pinning (HPKP):**
```cpp
// Pin public key hash instead of full cert (survives cert rotation)
const char* server_pubkey_hash = "sha256//kPyhz8xg+WPGRRHvyUWRZKqXTvIhFXJHBNHZz5NaZQE=";
```

---

## 4. Data Protection

### 4.1 End-to-End Encryption (E2EE) ⭐ **BEST FOR PHI**

**What It Is:**
Encrypt vitals data on device, decrypt only on trusted backend (not even MQTT broker can read).

**How It Works:**
```
ESP32 Watch:
1. Read vitals (HR, SpO2, temp)
2. Encrypt with AES-256-GCM using patient's public key
3. Publish encrypted payload to MQTT

MQTT Broker:
- Forwards encrypted payload (cannot decrypt)

Backend:
1. Receive encrypted payload
2. Decrypt with patient's private key
3. Process and store decrypted data
```

**Implementation:**

```cpp
// ESP32 Firmware
#include <mbedtls/gcm.h>

String encryptVitals(String plaintext, String patientPublicKey) {
    // 1. Generate random AES key
    uint8_t aes_key[32];
    esp_fill_random(aes_key, 32);

    // 2. Encrypt vitals with AES-GCM
    mbedtls_gcm_context aes;
    mbedtls_gcm_init(&aes);
    mbedtls_gcm_setkey(&aes, MBEDTLS_CIPHER_ID_AES, aes_key, 256);

    uint8_t iv[12];
    esp_fill_random(iv, 12);

    uint8_t ciphertext[256];
    uint8_t tag[16];

    mbedtls_gcm_crypt_and_tag(
        &aes, MBEDTLS_GCM_ENCRYPT,
        plaintext.length(), iv, 12,
        NULL, 0,  // No additional authenticated data
        (uint8_t*)plaintext.c_str(), ciphertext,
        16, tag
    );

    // 3. Encrypt AES key with patient's RSA public key
    // (RSA-OAEP)
    uint8_t encrypted_key[256];
    mbedtls_rsa_context rsa;
    // ... load patient public key ...
    mbedtls_rsa_rsaes_oaep_encrypt(&rsa, ...);

    // 4. Package: encrypted_key + iv + ciphertext + tag
    String encrypted_payload =
        base64_encode(encrypted_key) + ":" +
        base64_encode(iv) + ":" +
        base64_encode(ciphertext) + ":" +
        base64_encode(tag);

    return encrypted_payload;
}
```

**Backend:**
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

async def decrypt_vitals(encrypted_payload: str, patient_id: str):
    # 1. Parse payload
    parts = encrypted_payload.split(":")
    encrypted_key = base64.b64decode(parts[0])
    iv = base64.b64decode(parts[1])
    ciphertext = base64.b64decode(parts[2])
    tag = base64.b64decode(parts[3])

    # 2. Load patient's private key from HSM/KMS
    private_key = await get_patient_private_key(patient_id)

    # 3. Decrypt AES key with RSA private key
    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # 4. Decrypt vitals with AES key
    aesgcm = AESGCM(aes_key)
    plaintext = aesgcm.decrypt(iv, ciphertext + tag, None)

    return plaintext.decode('utf-8')
```

**Pros:**
- ✅ Maximum privacy (broker cannot read data)
- ✅ HIPAA/DPDP compliant
- ✅ Protects against broker compromise

**Cons:**
- ❌ Complex key management
- ❌ Higher CPU usage on ESP32
- ❌ Requires HSM/KMS for key storage

**Alternative: Field-Level Encryption (Simpler):**
```python
# Encrypt only sensitive fields, not entire payload
{
    "deviceId": "ESP32_WATCH_001",  # Plaintext (for routing)
    "timestamp": "2025-10-17T10:30:00Z",  # Plaintext
    "vitals": {
        "heartRate": "encrypted:eyJhbGciOi...",  # Encrypted
        "spo2": "encrypted:eyJhbGciOi...",       # Encrypted
        "temperature": "encrypted:eyJhbGciOi..." # Encrypted
    }
}
```

---

### 4.2 Data Minimization ⭐ **COMPLIANCE REQUIREMENT**

**Principle:** Only collect, transmit, and store data that is absolutely necessary.

**Current Issues:**
- ❓ Door scanner sends MAC addresses (PII)
- ❓ Watches send full waveform data (large payloads)

**Best Practices:**

**1. Anonymize Non-Essential Data:**
```cpp
// Door Scanner - BEFORE (Bad)
{
    "deviceId": "DOOR_SCANNER_001",
    "detectedDevices": [
        {
            "name": "ESP32_WATCH_001",
            "address": "30:AE:A4:12:34:56",  // ❌ PII (MAC address)
            "rssi": -45
        }
    ]
}

// Door Scanner - AFTER (Good)
{
    "deviceId": "DOOR_SCANNER_001",
    "detectedDevices": [
        {
            "deviceId": "ESP32_WATCH_001",  // ✅ Use device ID, not MAC
            "proximityLevel": "near",        // ✅ Abstracted (not raw RSSI)
            "timestamp": 1234567890
        }
    ]
}
```

**2. Aggregate Data on Device:**
```cpp
// Watch - BEFORE (Bad)
// Send 100 ECG samples/second = 8,640,000 samples/day
for (int i = 0; i < 100; i++) {
    sendECGSample(ecg_samples[i]);
}

// Watch - AFTER (Good)
// Send 1 summary/minute = 1,440 summaries/day
ECGSummary summary = {
    "avgHeartRate": 75,
    "hrVariability": 45,
    "arrhythmiaDetected": false
};
sendECGSummary(summary);

// Only send full waveform if arrhythmia detected
if (arrhythmiaDetected) {
    sendFullECGWaveform(ecg_samples);
}
```

**3. Retention Limits:**
```sql
-- Automatically delete old data
CREATE TABLE vitals_realtime (
    patient_id VARCHAR(50),
    timestamp TIMESTAMPTZ NOT NULL,
    vitals JSONB,
    PRIMARY KEY (patient_id, timestamp)
);

-- TimescaleDB: Auto-delete data older than 30 days
SELECT add_retention_policy('vitals_realtime', INTERVAL '30 days');
```

---

## 5. Device Identity & Management

### 5.1 Unique Device Identity ⭐ **MANDATORY**

**Current:** Device ID = "ESP32_WATCH_" + truncated MAC address ✅ Good

**Best Practice: Use Multiple Identifiers:**
```cpp
struct DeviceIdentity {
    String hardwareId;      // MAC address (immutable)
    String deviceId;        // Backend-assigned ID (mutable)
    String serialNumber;    // Manufacturer serial (immutable)
    String firmwareVersion; // Current firmware version
    String certificateCN;   // Certificate common name (for mTLS)
};

DeviceIdentity identity = {
    .hardwareId = WiFi.macAddress(),
    .deviceId = "ESP32_WATCH_001",       // From provisioning
    .serialNumber = "SN-2025-001234",    // From factory
    .firmwareVersion = "v4.2.0",
    .certificateCN = "ESP32-30:AE:A4:12:34:56"
};
```

**Why Multiple IDs?**
- **Hardware ID (MAC):** Immutable, survives firmware reset
- **Device ID:** Backend can reassign if device replaced
- **Serial Number:** Physical asset tracking
- **Certificate CN:** For mTLS authentication

---

### 5.2 Device Enrollment (Zero-Touch Provisioning) ⭐ **ENTERPRISE**

**What It Is:**
Devices self-register with backend on first boot without manual configuration.

**How It Works:**
```
1. Device boots with factory certificate (signed by manufacturer CA)
2. Device connects to backend using factory cert
3. Backend validates factory cert and checks device serial in database
4. Backend issues permanent device certificate (signed by hospital CA)
5. Device stores permanent cert and reboots
```

**Implementation:**

**Factory Setup:**
```bash
# Manufacturer generates factory certificate per device
openssl genrsa -out factory_device_001.key 2048
openssl req -new -key factory_device_001.key -out factory_device_001.csr \
    -subj "/CN=FACTORY-SN-2025-001234/O=HospitalDevices"
openssl x509 -req -in factory_device_001.csr \
    -CA manufacturer_ca.crt -CAkey manufacturer_ca.key \
    -CAcreateserial -out factory_device_001.crt -days 365

# Flash to device SPIFFS
esptool.py write_flash 0x310000 spiffs.bin  # Contains factory cert
```

**ESP32 First Boot:**
```cpp
void enrollDevice() {
    // Load factory certificate
    String factoryCert = loadFromSPIFFS("/certs/factory.crt");
    String factoryKey = loadFromSPIFFS("/certs/factory.key");

    // Connect to backend with factory cert
    WiFiClientSecure client;
    client.setCertificate(factoryCert.c_str());
    client.setPrivateKey(factoryKey.c_str());

    HTTPClient http;
    http.begin(&client, "https://backend.hospital.com/api/v1/enrollment");
    http.addHeader("Content-Type", "application/json");

    String payload = "{\"serialNumber\":\"" + serialNumber + "\",\"macAddress\":\"" + WiFi.macAddress() + "\"}";

    int httpCode = http.POST(payload);
    if (httpCode == 200) {
        String response = http.getString();
        JsonDocument doc;
        deserializeJson(doc, response);

        // Save permanent certificate issued by backend
        String deviceCert = doc["certificate"];
        String deviceKey = doc["privateKey"];
        saveToSPIFFS("/certs/device.crt", deviceCert);
        saveToSPIFFS("/certs/device.key", deviceKey);

        // Delete factory certificate (security)
        SPIFFS.remove("/certs/factory.crt");
        SPIFFS.remove("/certs/factory.key");

        Serial.println("✅ Device enrolled! Rebooting...");
        ESP.restart();
    }
}
```

**Backend:**
```python
@router.post("/api/v1/enrollment")
async def enroll_device(request: Request):
    # 1. Validate factory certificate (signed by manufacturer CA)
    client_cert = request.client.cert
    if not validate_cert_chain(client_cert, manufacturer_ca):
        raise HTTPException(401, "Invalid factory certificate")

    # 2. Extract serial number from certificate CN
    serial_number = extract_cn(client_cert)

    # 3. Check if device is authorized (in database)
    device = await db.fetchrow(
        "SELECT * FROM device_inventory WHERE serial_number = $1",
        serial_number
    )
    if not device:
        raise HTTPException(404, "Device not found in inventory")

    # 4. Generate permanent device certificate
    device_id = f"ESP32_WATCH_{device['id']}"
    device_cert, device_key = generate_device_certificate(
        common_name=device_id,
        serial_number=serial_number,
        ca=hospital_ca
    )

    # 5. Store in database
    await db.execute(
        "UPDATE devices SET certificate = $1, enrolled_at = NOW() WHERE serial_number = $2",
        device_cert, serial_number
    )

    return {
        "success": True,
        "deviceId": device_id,
        "certificate": device_cert,
        "privateKey": device_key
    }
```

**Pros:**
- ✅ Zero manual configuration
- ✅ Scales to thousands of devices
- ✅ Factory-to-deployment automation
- ✅ Secure (factory cert only used once)

**Cons:**
- ❌ Requires manufacturer cooperation
- ❌ Complex PKI infrastructure

---

### 5.3 Device Lifecycle Management ⭐ **OPERATIONS**

**States:**
```
1. Manufactured → 2. Enrolled → 3. Provisioned → 4. Active →
5. Maintenance → 6. Decommissioned → 7. Retired
```

**Database Schema:**
```sql
CREATE TABLE device_lifecycle (
    device_id VARCHAR(50) PRIMARY KEY,
    state VARCHAR(20) NOT NULL,
    state_changed_at TIMESTAMPTZ NOT NULL,
    state_changed_by VARCHAR(50),
    reason TEXT,
    previous_state VARCHAR(20),
    CHECK (state IN ('manufactured', 'enrolled', 'provisioned', 'active', 'maintenance', 'decommissioned', 'retired'))
);

CREATE TABLE device_lifecycle_history (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) REFERENCES devices(id),
    from_state VARCHAR(20),
    to_state VARCHAR(20),
    changed_at TIMESTAMPTZ NOT NULL,
    changed_by VARCHAR(50),
    reason TEXT
);
```

**State Transitions:**
```python
async def transition_device_state(
    device_id: str,
    new_state: str,
    changed_by: str,
    reason: str
):
    async with db.transaction():
        # Get current state
        current = await db.fetchrow(
            "SELECT state FROM device_lifecycle WHERE device_id = $1",
            device_id
        )

        # Validate transition
        valid_transitions = {
            "manufactured": ["enrolled"],
            "enrolled": ["provisioned"],
            "provisioned": ["active"],
            "active": ["maintenance", "decommissioned"],
            "maintenance": ["active", "retired"],
            "decommissioned": ["retired"]
        }

        if new_state not in valid_transitions.get(current["state"], []):
            raise ValueError(f"Invalid transition: {current['state']} → {new_state}")

        # Update state
        await db.execute(
            "UPDATE device_lifecycle SET state = $1, state_changed_at = NOW(), state_changed_by = $2, reason = $3, previous_state = $4 WHERE device_id = $5",
            new_state, changed_by, reason, current["state"], device_id
        )

        # Log history
        await db.execute(
            "INSERT INTO device_lifecycle_history (device_id, from_state, to_state, changed_at, changed_by, reason) VALUES ($1, $2, $3, NOW(), $4, $5)",
            device_id, current["state"], new_state, changed_by, reason
        )

        # Trigger actions based on new state
        if new_state == "decommissioned":
            await revoke_device_certificate(device_id)
            await disconnect_device(device_id)
        elif new_state == "retired":
            await delete_device_credentials(device_id)
            await archive_device_data(device_id)
```

---

## 6. Firmware Security

### 6.1 Secure Boot ⭐ **CRITICAL**

**What It Is:**
ESP32 verifies firmware signature before execution (prevents malware).

**How It Works:**
```
1. Bootloader verifies app firmware signature with public key
2. If signature invalid → refuse to boot
3. If signature valid → execute firmware
```

**Implementation:**

**Enable Secure Boot (ESP-IDF):**
```bash
# Generate signing key
espsecure.py generate_signing_key --version 2 secure_boot_signing_key.pem

# Enable in menuconfig
idf.py menuconfig
# Security features → Enable Secure Boot V2
# Select signing key

# Build with secure boot
idf.py build

# Flash bootloader (one-time, burns eFuses)
esptool.py --port COM3 burn_key secure_boot_v2 secure_boot_signing_key.pem

# Flash app (signed automatically)
esptool.py --port COM3 write_flash 0x10000 build/app.bin
```

**Pros:**
- ✅ Prevents firmware tampering
- ✅ Prevents malware injection
- ✅ One-time setup (eFuses cannot be undone)

**Cons:**
- ❌ Cannot be disabled once enabled (permanent)
- ❌ Requires careful key management (lose key = bricked device)
- ❌ Slightly slower boot time

---

### 6.2 Flash Encryption ⭐ **CRITICAL**

**What It Is:**
Encrypt entire flash contents (firmware + data) at rest.

**How It Works:**
```
1. ESP32 generates random encryption key on first boot
2. Key stored in eFuse (cannot be read)
3. All flash reads/writes transparently encrypted/decrypted
4. Physical flash dump is useless (encrypted)
```

**Implementation:**

```bash
# Enable in menuconfig
idf.py menuconfig
# Security features → Enable Flash Encryption
# Select "Development mode" (allows reflashing) or "Release mode" (one-time)

# Build and flash
idf.py build flash
# On first boot, ESP32 will encrypt flash automatically
```

**Pros:**
- ✅ Protects against physical flash dumps
- ✅ Protects secrets (WiFi passwords, certificates, API keys)
- ✅ Transparent (no code changes)

**Cons:**
- ❌ Cannot read flash externally (debugging difficult)
- ❌ Permanent in "Release mode"

---

### 6.3 Over-The-Air (OTA) Updates ⭐ **MANDATORY**

**Best Practices:**

**1. Signed Firmware:**
```cpp
#include <Update.h>
#include <mbedtls/sha256.h>
#include <mbedtls/rsa.h>

bool verifyFirmwareSignature(uint8_t* firmware, size_t size, String signature) {
    // 1. Compute firmware hash
    uint8_t hash[32];
    mbedtls_sha256(firmware, size, hash, 0);

    // 2. Load public key
    mbedtls_rsa_context rsa;
    mbedtls_rsa_init(&rsa, MBEDTLS_RSA_PKCS_V21, MBEDTLS_MD_SHA256);
    // ... load public key from SPIFFS ...

    // 3. Verify signature
    int ret = mbedtls_rsa_rsassa_pss_verify(
        &rsa, NULL, NULL, MBEDTLS_RSA_PUBLIC,
        MBEDTLS_MD_SHA256, 32, hash,
        (uint8_t*)signature.c_str()
    );

    return (ret == 0);
}

void performOTA(String firmwareUrl) {
    HTTPClient http;
    http.begin(firmwareUrl);

    int httpCode = http.GET();
    if (httpCode == 200) {
        WiFiClient* stream = http.getStreamPtr();

        // Download firmware to buffer
        uint8_t* firmware = (uint8_t*)malloc(http.getSize());
        stream->readBytes(firmware, http.getSize());

        // Download signature
        http.begin(firmwareUrl + ".sig");
        String signature = http.getString();

        // Verify signature
        if (!verifyFirmwareSignature(firmware, http.getSize(), signature)) {
            Serial.println("❌ Firmware signature verification failed!");
            free(firmware);
            return;
        }

        // Flash firmware
        Update.begin(http.getSize());
        Update.write(firmware, http.getSize());
        Update.end();

        Serial.println("✅ OTA update successful! Rebooting...");
        ESP.restart();
    }
}
```

**2. Rollback Protection:**
```cpp
#include <esp_ota_ops.h>

void setupRollbackProtection() {
    const esp_partition_t* running = esp_ota_get_running_partition();
    esp_ota_img_states_t ota_state;
    esp_ota_get_state_partition(running, &ota_state);

    if (ota_state == ESP_OTA_IMG_PENDING_VERIFY) {
        // New firmware booted successfully
        // Run self-tests
        if (runSelfTests()) {
            Serial.println("✅ Self-tests passed - marking firmware as valid");
            esp_ota_mark_app_valid_cancel_rollback();
        } else {
            Serial.println("❌ Self-tests failed - rolling back to previous firmware");
            esp_ota_mark_app_invalid_rollback_and_reboot();
        }
    }
}
```

**3. Incremental Updates (Delta Updates):**
```python
# Backend generates delta patch
import bsdiff4

old_firmware = open("v4.1.0.bin", "rb").read()
new_firmware = open("v4.2.0.bin", "rb").read()

# Generate binary diff (only changed bytes)
delta = bsdiff4.diff(old_firmware, new_firmware)

# Delta is typically 10-30% of full firmware size
print(f"Full firmware: {len(new_firmware)} bytes")
print(f"Delta patch: {len(delta)} bytes ({len(delta)/len(new_firmware)*100:.1f}%)")
```

```cpp
// ESP32 applies delta patch
#include <BSpatch.h>

void applyDeltaUpdate(uint8_t* delta, size_t delta_size) {
    // Read old firmware from partition
    const esp_partition_t* running = esp_ota_get_running_partition();
    uint8_t* old_firmware = (uint8_t*)malloc(running->size);
    esp_partition_read(running, 0, old_firmware, running->size);

    // Apply patch
    uint8_t* new_firmware = (uint8_t*)malloc(running->size);
    bspatch(old_firmware, running->size, delta, delta_size, new_firmware);

    // Write to OTA partition
    const esp_partition_t* update_partition = esp_ota_get_next_update_partition(NULL);
    esp_ota_begin(update_partition, OTA_SIZE_UNKNOWN, &update_handle);
    esp_ota_write(update_handle, new_firmware, running->size);
    esp_ota_end(update_handle);
    esp_ota_set_boot_partition(update_partition);

    ESP.restart();
}
```

---

## 7. Physical Security

### 7.1 Tamper Detection ⭐ **MEDICAL DEVICE REQUIREMENT**

**What It Is:**
Detect if device case is opened or device is physically compromised.

**Methods:**

**1. Hall Effect Sensor (Magnetic Tamper Detection):**
```cpp
#include <driver/hall_sensor.h>

bool detectTamper() {
    int hall_value = hall_sensor_read();

    // Threshold depends on magnet placement
    // Normal: -100 to +100
    // Tampered (case opened, magnet moved): > 200 or < -200

    if (hall_value > 200 || hall_value < -200) {
        Serial.println("⚠️ TAMPER DETECTED! Case opened!");

        // Alert backend
        sendTamperAlert();

        // Wipe sensitive data
        wipeSensitiveData();

        return true;
    }

    return false;
}

void setup() {
    // Check tamper on boot
    if (detectTamper()) {
        // Refuse to boot
        while(1) {
            Serial.println("❌ Device tampered - halting");
            delay(1000);
        }
    }
}
```

**2. Secure Element (Hardware Security Module):**
```cpp
// Use ATECC608A secure element for key storage
#include <ArduinoECCX08.h>

void setupSecureElement() {
    if (!ECCX08.begin()) {
        Serial.println("❌ Secure element not found!");
        return;
    }

    // Store private key in secure slot (cannot be read out)
    ECCX08.writePrivateKey(0, privateKey);

    // Lock configuration (one-time, irreversible)
    ECCX08.lock();
}

String signDataWithSecureElement(String data) {
    // Sign data using key in secure element
    // Private key never leaves chip
    byte signature[64];
    ECCX08.ecSign(0, (byte*)data.c_str(), signature);
    return base64_encode(signature);
}
```

**3. Potting/Encapsulation:**
- Fill device case with epoxy resin
- Makes physical access extremely difficult
- Destroys device if tampered

---

### 7.2 Debug Port Protection

**Disable JTAG/Serial in Production:**
```cpp
// Disable JTAG debugging in production
#ifdef PRODUCTION
    gpio_set_direction(GPIO_NUM_12, GPIO_MODE_INPUT);  // TMS
    gpio_set_direction(GPIO_NUM_13, GPIO_MODE_INPUT);  // TCK
    gpio_set_direction(GPIO_NUM_14, GPIO_MODE_INPUT);  // TDI
    gpio_set_direction(GPIO_NUM_15, GPIO_MODE_INPUT);  // TDO

    // Disable ROM bootloader (UART download mode)
    esp_efuse_write_field_bit(ESP_EFUSE_UART_DOWNLOAD_DIS);
#endif
```

---

## 8. Monitoring & Alerting

### 8.1 Device Health Monitoring ⭐ **OPERATIONS**

**Metrics to Track:**

```python
# Backend service
class DeviceHealthMonitor:
    async def monitor_device_health(self, device_id: str):
        device = await db.fetchrow("SELECT * FROM devices WHERE id = $1", device_id)

        alerts = []

        # 1. Connection health
        last_seen = device["lastSeen"]
        if datetime.utcnow() - last_seen > timedelta(minutes=5):
            alerts.append({
                "type": "device_offline",
                "severity": "high",
                "message": f"Device {device_id} offline for {(datetime.utcnow() - last_seen).seconds // 60} minutes"
            })

        # 2. Battery health
        battery = device["batteryLevel"]
        if battery < 10:
            alerts.append({
                "type": "battery_critical",
                "severity": "critical",
                "message": f"Device {device_id} battery critically low ({battery}%)"
            })

        # 3. Memory health
        free_memory = device.get("freeMemory", 0)
        if free_memory < 10000:  # < 10KB
            alerts.append({
                "type": "memory_low",
                "severity": "medium",
                "message": f"Device {device_id} low memory ({free_memory} bytes free)"
            })

        # 4. Signal strength
        rssi = device.get("signalStrength", 0)
        if rssi < -80:
            alerts.append({
                "type": "weak_signal",
                "severity": "low",
                "message": f"Device {device_id} weak signal ({rssi} dBm)"
            })

        # 5. Firmware version
        firmware = device.get("firmwareVersion", "")
        latest_firmware = await get_latest_firmware_version()
        if firmware != latest_firmware:
            alerts.append({
                "type": "firmware_outdated",
                "severity": "low",
                "message": f"Device {device_id} firmware outdated ({firmware} vs {latest_firmware})"
            })

        # 6. Crash detection
        crash_count = await db.fetchval(
            "SELECT COUNT(*) FROM device_crashes WHERE device_id = $1 AND created_at > NOW() - INTERVAL '1 hour'",
            device_id
        )
        if crash_count > 3:
            alerts.append({
                "type": "frequent_crashes",
                "severity": "high",
                "message": f"Device {device_id} crashed {crash_count} times in past hour"
            })

        return alerts
```

---

### 8.2 Security Event Logging (SIEM Integration) ⭐ **COMPLIANCE**

**Events to Log:**

```python
security_events = [
    "authentication_failed",
    "authorization_denied",
    "firmware_update_attempted",
    "firmware_signature_invalid",
    "tamper_detected",
    "connection_from_unknown_ip",
    "rate_limit_exceeded",
    "mqtt_acl_violation",
    "tls_handshake_failed",
    "certificate_expired",
    "device_decommissioned"
]

async def log_security_event(
    event_type: str,
    device_id: str,
    severity: str,
    details: dict
):
    # 1. Log to database
    await db.execute("""
        INSERT INTO security_events (event_type, device_id, severity, details, timestamp)
        VALUES ($1, $2, $3, $4, NOW())
    """, event_type, device_id, severity, json.dumps(details))

    # 2. Send to SIEM (Splunk, ELK, etc.)
    await send_to_siem({
        "event_type": event_type,
        "device_id": device_id,
        "severity": severity,
        "details": details,
        "timestamp": datetime.utcnow().isoformat(),
        "source": "hospital_iot_backend"
    })

    # 3. Alert security team if critical
    if severity == "critical":
        await alert_security_team(event_type, device_id, details)
```

---

## 9. Compliance & Audit

### 9.1 HIPAA Technical Safeguards Checklist

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| **164.312(a)(1) Access Control** | JWT/PKI authentication | ✅ |
| **164.312(a)(2)(i) Unique User ID** | Device certificates with CN | ✅ |
| **164.312(a)(2)(ii) Emergency Access** | Emergency access procedure | ❌ TODO |
| **164.312(a)(2)(iii) Automatic Logoff** | Session timeout (24h JWT expiry) | ✅ |
| **164.312(a)(2)(iv) Encryption** | TLS 1.3 + optional E2EE | ✅ |
| **164.312(b) Audit Controls** | Security event logging | ✅ |
| **164.312(c)(1) Integrity** | HMAC signatures | ✅ |
| **164.312(c)(2) Mechanism to Authenticate** | Digital signatures | ✅ |
| **164.312(d) Person/Entity Authentication** | mTLS certificates | ⚠️ Partial |
| **164.312(e)(1) Transmission Security** | TLS 1.3 for all comms | ✅ |
| **164.312(e)(2)(i) Integrity Controls** | TLS AEAD ciphers | ✅ |
| **164.312(e)(2)(ii) Encryption** | TLS 1.3 mandatory | ✅ |

---

### 9.2 DPDP Act 2023 (India) Compliance

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| **Section 8: Security Safeguards** | TLS, encryption, access control | ✅ |
| **Section 9: Data Breach Notification** | Security event alerting | ✅ |
| **Section 10: Data Retention Limits** | TimescaleDB retention policy | ✅ |
| **Section 11: Right to Erasure** | Device decommissioning procedure | ✅ |
| **Section 12: Data Portability** | Export API | ❌ TODO |
| **Section 16: Consent Management** | Patient consent tracking | ❌ TODO |

---

## 10. Incident Response

### 10.1 Incident Response Plan

**Scenario 1: Device Compromised (Stolen/Tampered)**

```
1. Detection:
   - Tamper alert received from device
   - Device offline unexpectedly
   - Unusual activity detected

2. Response:
   a) Immediately revoke device certificate
      → CRL update → blocks MQTT/HTTPS access
   b) Blacklist device ID in firewall
   c) Rotate all credentials that device had access to
   d) Alert security team
   e) Review logs for data exfiltration

3. Recovery:
   a) Replace device with new one
   b) Re-provision with new credentials
   c) Document incident for audit

4. Post-Incident:
   a) Analyze how device was compromised
   b) Update security controls
   c) Retrain staff if necessary
```

**Scenario 2: MQTT Broker Compromise**

```
1. Detection:
   - Unusual MQTT traffic patterns
   - Unauthorized topic access
   - Memory/CPU spike on broker

2. Response:
   a) Isolate broker (firewall rules)
   b) Switch to backup broker
   c) Dump broker memory for forensics
   d) Rotate all MQTT credentials
   e) Review ACL violations

3. Recovery:
   a) Rebuild broker from clean image
   b) Restore configurations
   c) Re-establish device connections

4. Post-Incident:
   a) Patch vulnerabilities
   b) Enable additional monitoring
   c) Update incident playbook
```

**Scenario 3: TLS Certificate Expiry**

```
1. Prevention:
   - Automated cert renewal (Let's Encrypt/ACME)
   - Certificate expiry monitoring (30 days before)
   - Backup certificates ready

2. Detection:
   - Certificate expiry alerts
   - Devices failing TLS handshake

3. Response:
   a) Deploy new certificate immediately
   b) Restart services
   c) Verify all devices reconnect

4. Post-Incident:
   a) Review certificate lifecycle management
   b) Automate renewal process
```

---

## Summary: Recommended Stack for Hospital IoT

### For **ESP32 Watches** (Medical Devices):

| Component | Recommendation | Priority |
|-----------|---------------|----------|
| **Authentication** | PKI (X.509 certificates) | 🔴 Critical |
| **Provisioning** | QR Code → One-time JWT → Device cert | 🔴 Critical |
| **Communication** | TLS 1.3 (HTTPS + MQTTS with mTLS) | 🔴 Critical |
| **Data Protection** | Field-level encryption (sensitive vitals) | 🟡 High |
| **Firmware Security** | Secure Boot + Flash Encryption | 🔴 Critical |
| **Physical Security** | Tamper detection (Hall sensor) | 🟡 High |
| **OTA Updates** | Signed firmware + rollback protection | 🔴 Critical |
| **Monitoring** | Device health + security events | 🟢 Medium |

### For **Door Scanners** (Non-Medical):

| Component | Recommendation | Priority |
|-----------|---------------|----------|
| **Authentication** | HMAC signatures (simpler) | 🟡 High |
| **Provisioning** | Captive Portal (current is good) | 🟢 Medium |
| **Communication** | TLS 1.2 (current is acceptable) | 🟡 High |
| **Data Protection** | Anonymize MAC addresses | 🟡 High |
| **Firmware Security** | Signed OTA (not secure boot) | 🟢 Medium |
| **Physical Security** | Physical mounting security | 🟢 Low |

---

## Next Steps

1. **Immediate (Week 1):**
   - [ ] Remove hardcoded MQTT credentials
   - [ ] Implement one-time provisioning codes
   - [ ] Add timestamp + nonce to HMAC authentication

2. **Short-Term (Month 1):**
   - [ ] Deploy PKI infrastructure (CA setup)
   - [ ] Enable mTLS for MQTT
   - [ ] Implement device health monitoring

3. **Long-Term (Quarter 1):**
   - [ ] Enable Secure Boot on all devices
   - [ ] Implement E2EE for vitals data
   - [ ] Set up SIEM integration

4. **Continuous:**
   - [ ] Monthly security audits
   - [ ] Quarterly penetration testing
   - [ ] Annual compliance review

---

## References & Standards

1. **NIST SP 800-183** - Networks of 'Things' Security
2. **IEC 62443** - Industrial Communication Networks Security
3. **FDA Cybersecurity Guidelines** (Reference for medical devices)
4. **OWASP IoT Top 10** (2018)
5. **ISO 27001/27002** - Information Security Management
6. **HIPAA Security Rule** - 45 CFR Part 164 Subpart C
7. **Digital Personal Data Protection Act 2023 (India)**
8. **Clinical Establishments Act 2010 (India)**

---

**Document Version:** 1.0
**Last Updated:** 2025-10-17
**Next Review:** 2025-11-17
