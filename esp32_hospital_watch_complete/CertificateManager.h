/**
 * CertificateManager.h
 *
 * SPIFFS certificate storage helpers for the ESP32 Hospital Watch.
 * Handles CA cert, device cert, and private key load/save for mTLS.
 *
 * Files on SPIFFS:
 *   /ca.crt      — CA certificate (written during provisioning)
 *   /device.crt  — Device certificate (written during provisioning)
 *   /device.key  — Device private key  (written during provisioning)
 *
 * Dependencies (defined in the main .ino sketch):
 *   extern String caCertificate        — global for TLS lifetime
 *   extern String deviceCertificate    — global for TLS lifetime
 *   extern String devicePrivateKey     — global for TLS lifetime
 */

#ifndef CERTIFICATE_MANAGER_H
#define CERTIFICATE_MANAGER_H

#include <Arduino.h>
#include <SPIFFS.h>
#include "SPIFFSManager.h"

// ── Cert globals defined in the main .ino (kept global to avoid dangling .c_str()) ──
extern String caCertificate;
extern String deviceCertificate;
extern String devicePrivateKey;

// ── CA cert path ─────────────────────────────────────────────────────────────
static const char* CERT_CA_PATH      = "/ca.crt";
static const char* CERT_DEVICE_PATH  = "/device.crt";
static const char* CERT_KEY_PATH     = "/device.key";

// ─────────────────────────────────────────────────────────────────────────────

/**
 * Return true if both /device.crt and /device.key exist on SPIFFS.
 */
inline bool hasCertificates() {
    if (!SPIFFSManager::isMounted()) {
        Serial.println("SPIFFS not mounted");
        return false;
    }
    if (SPIFFS.exists(CERT_DEVICE_PATH) && SPIFFS.exists(CERT_KEY_PATH)) {
        Serial.println("Device certificates found in SPIFFS");
        return true;
    }
    Serial.println("Device certificates NOT found — provisioning required");
    return false;
}

/**
 * Load /device.crt and /device.key into the provided String references.
 * Returns false if either file is missing or empty.
 */
inline bool loadDeviceCertificate(String& cert, String& key) {
    if (!SPIFFSManager::isMounted()) {
        Serial.println("SPIFFS not mounted");
        return false;
    }

    File certFile = SPIFFS.open(CERT_DEVICE_PATH, "r");
    if (!certFile) { Serial.println("Device certificate file not found"); return false; }
    cert = certFile.readString();
    certFile.close();

    File keyFile = SPIFFS.open(CERT_KEY_PATH, "r");
    if (!keyFile) { Serial.println("Device private key file not found"); return false; }
    key = keyFile.readString();
    keyFile.close();

    if (cert.length() == 0 || key.length() == 0) {
        Serial.println("Device certificate or key is empty");
        return false;
    }

    Serial.printf("Device certificate loaded (%u bytes)\n", (unsigned)cert.length());
    Serial.printf("Device private key loaded (%u bytes)\n", (unsigned)key.length());
    return true;
}

/**
 * Write device cert and private key to SPIFFS.
 */
inline bool saveCertificates(String cert, String key) {
    if (!SPIFFSManager::isMounted()) {
        Serial.println("SPIFFS not mounted");
        return false;
    }

    File certFile = SPIFFS.open(CERT_DEVICE_PATH, "w");
    if (!certFile) { Serial.println("Failed to open device.crt for writing"); return false; }
    certFile.print(cert);
    certFile.close();

    File keyFile = SPIFFS.open(CERT_KEY_PATH, "w");
    if (!keyFile) { Serial.println("Failed to open device.key for writing"); return false; }
    keyFile.print(key);
    keyFile.close();

    Serial.println("Device certificates saved to SPIFFS");
    return true;
}

/**
 * Load /ca.crt into the global caCertificate string.
 */
inline bool loadCACertificate() {
    if (!SPIFFSManager::isMounted()) {
        Serial.println("SPIFFS not mounted");
        return false;
    }

    File file = SPIFFS.open(CERT_CA_PATH, "r");
    if (!file) {
        Serial.printf("CA certificate file not found: %s — upload ca.crt to SPIFFS\n", CERT_CA_PATH);
        return false;
    }

    caCertificate = file.readString();
    file.close();

    if (caCertificate.length() == 0) {
        Serial.println("CA certificate file is empty");
        return false;
    }

    Serial.printf("CA certificate loaded from SPIFFS (%u bytes)\n", (unsigned)caCertificate.length());
    return true;
}

#endif // CERTIFICATE_MANAGER_H
