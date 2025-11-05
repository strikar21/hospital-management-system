/*
 * NFC Manager for ESP32 Hospital Watch - Implementation
 * PN532 NFC Module over I2C Interface with IRQ Interrupt Support
 *
 * Features:
 * - Staff badge authentication
 * - Patient wristband identification
 * - Room location tracking via NFC tags
 * - Medication verification
 * - MIFARE Classic/Ultralight/DESFire support
 * - Interrupt-driven tag detection (scan on demand)
 *
 * Hardware: PN532 NFC Module connected via I2C
 * Wiring:
 *   PN532 SDA   → GPIO 21 (ESP32 default I2C SDA)
 *   PN532 SCL   → GPIO 22 (ESP32 default I2C SCL)
 *   PN532 IRQ   → GPIO 25 (ESP32 interrupt pin - configurable)
 *   PN532 VCC   → 3.3V
 *   PN532 GND   → GND
 *
 * Note: Set PN532 DIP switches to I2C mode (usually OFF, ON)
 *
 * Author: Claude/Anthropic
 * Date: 2025-10-27
 */

#include "NFCManager.h"
#include <ArduinoJson.h>

// Constructor
NFCManager::NFCManager(uint8_t irq_pin) {
    irqPin = irq_pin;
    sdaPin = 21;
    sclPin = 22;
    initialized = false;
    interruptEnabled = false;
    lastReadTime = 0;
    lastReadUID = "";
    lastError = "";
    nfc = nullptr;

    // ✅ Initialize IRQ state
    irqPrev = HIGH;
    irqCurr = HIGH;
    readerDisabled = false;
    timeLastCardRead = 0;
}

// Initialize NFC module
bool NFCManager::begin() {
    Serial.println("[NFC] Initializing PN532 NFC module over I2C...");

    // Configure IRQ pin as input with pullup
    pinMode(irqPin, INPUT_PULLUP);

    // Initialize I2C on default ESP32 pins (SDA=GPIO21, SCL=GPIO22)
    Wire.begin(sdaPin, sclPin);

    // Create Adafruit PN532 with I2C interface
    nfc = new Adafruit_PN532(irqPin, -1);  // IRQ pin, no reset pin

    // Initialize PN532
    nfc->begin();

    // Get firmware version to verify connection
    uint32_t versiondata = nfc->getFirmwareVersion();
    if (!versiondata) {
        lastError = "PN532 not found - check I2C wiring and DIP switches";
        Serial.println("[NFC] ERROR: " + lastError);
        return false;
    }

    Serial.print("[NFC] Found PN532 chip - Firmware version: ");
    Serial.print((versiondata >> 24) & 0xFF, DEC);
    Serial.print(".");
    Serial.println((versiondata >> 16) & 0xFF, DEC);

    // Configure for reading RFID tags
    nfc->SAMConfig();

    initialized = true;

    // ✅ Start passive target detection (IRQ mode)
    startListeningToNFC();

    Serial.println("[NFC] PN532 initialization complete (I2C mode with IRQ on GPIO " + String(irqPin) + ")");
    return true;
}

// Enable interrupt mode
void NFCManager::enableInterrupt() {
    if (!initialized) return;

    // Configure PN532 for IRQ on tag detection
    // IRQ pin goes LOW when tag is detected
    interruptEnabled = true;
    Serial.println("[NFC] Interrupt mode enabled - IRQ will trigger on tag detection");
}

// Disable interrupt mode
void NFCManager::disableInterrupt() {
    interruptEnabled = false;
    Serial.println("[NFC] Interrupt mode disabled");
}

// Check if IRQ pin is low (tag detected)
bool NFCManager::isIRQTriggered() {
    if (!initialized || !interruptEnabled) {
        return false;
    }

    // IRQ pin goes LOW when tag is present
    return (digitalRead(irqPin) == LOW);
}

// Check if NFC module is ready
bool NFCManager::isReady() {
    return initialized;
}

// Get last error message
String NFCManager::getLastError() {
    return lastError;
}

// Check if tag is present (quick check without reading data)
bool NFCManager::isTagPresent() {
    if (!initialized) {
        lastError = "NFC module not initialized";
        return false;
    }

    // Check IRQ pin first (much faster than I2C communication)
    if (interruptEnabled && !isIRQTriggered()) {
        return false;  // No tag detected via interrupt
    }

    uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };
    uint8_t uidLength;

    // Quick passive scan (timeout 100ms)
    bool success = nfc->readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 100);
    return success;
}

// Get tag UID only (faster than full read)
String NFCManager::getTagUID() {
    if (!initialized) {
        lastError = "NFC module not initialized";
        return "";
    }

    uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };
    uint8_t uidLength;

    // Read tag UID
    bool success = nfc->readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 200);
    if (!success) {
        lastError = "No tag detected";
        return "";
    }

    String uidStr = uidToString(uid, uidLength);
    lastReadUID = uidStr;
    lastReadTime = millis();

    return uidStr;
}

// Read NFC tag (full read with data payload)
NFCReadResult NFCManager::readTag() {
    NFCReadResult result;
    result.success = false;
    result.tagType = NFC_UNKNOWN;
    result.uid = "";
    result.data = "";
    result.timestamp = millis();

    if (!initialized) {
        lastError = "NFC module not initialized";
        return result;
    }

    // First get UID
    String uid = getTagUID();
    if (uid.length() == 0) {
        return result;
    }

    result.uid = uid;

    // Try to read NDEF message
    String payload = "";
    if (readNDEFMessage(payload)) {
        result.data = payload;
        result.tagType = detectTagType(uid, payload);
        result.success = true;

        Serial.println("[NFC] Tag read successful:");
        Serial.println("  UID: " + uid);
        Serial.println("  Type: " + String(result.tagType));
        Serial.println("  Data: " + payload);
    } else {
        // No NDEF data, but UID is valid
        result.success = true;
        result.tagType = detectTagType(uid, "");

        Serial.println("[NFC] Tag detected (no NDEF data):");
        Serial.println("  UID: " + uid);
    }

    lastReadTime = millis();
    lastReadUID = uid;

    return result;
}

// Write data to tag (for programming new tags)
bool NFCManager::writeTag(NFCTagType tagType, String jsonData) {
    if (!initialized) {
        lastError = "NFC module not initialized";
        return false;
    }

    if (!isTagPresent()) {
        lastError = "No tag present to write";
        return false;
    }

    // Create JSON payload with tag type identifier
    JsonDocument doc;  // ✅ ArduinoJson v7 compatible
    doc["type"] = tagType;
    doc["data"] = jsonData;

    String payload;
    serializeJson(doc, payload);

    // Write NDEF message
    bool success = writeNDEFMessage(payload);
    if (success) {
        Serial.println("[NFC] Tag written successfully:");
        Serial.println("  Type: " + String(tagType));
        Serial.println("  Data: " + jsonData);
    } else {
        Serial.println("[NFC] ERROR: Failed to write tag");
    }

    return success;
}

// Hospital-specific helper: Authenticate staff badge
bool NFCManager::authenticateStaff(String& staffId, String& staffName, String& role) {
    NFCReadResult result = readTag();
    if (!result.success || result.tagType != NFC_STAFF_BADGE) {
        lastError = "Not a valid staff badge";
        return false;
    }

    return parseStaffBadge(result.data, staffId, staffName, role);
}

// Hospital-specific helper: Identify patient wristband
bool NFCManager::identifyPatient(String& patientId, String& patientName) {
    NFCReadResult result = readTag();
    if (!result.success || result.tagType != NFC_PATIENT_WRISTBAND) {
        lastError = "Not a valid patient wristband";
        return false;
    }

    return parsePatientWristband(result.data, patientId, patientName);
}

// Hospital-specific helper: Read room location tag
bool NFCManager::readRoomTag(String& roomNumber, String& bedNumber) {
    NFCReadResult result = readTag();
    if (!result.success || result.tagType != NFC_ROOM_TAG) {
        lastError = "Not a valid room tag";
        return false;
    }

    return parseRoomTag(result.data, roomNumber, bedNumber);
}

// Hospital-specific helper: Verify medication tag
bool NFCManager::verifyMedication(String& medicationId, String& medicationName, String& dosage) {
    NFCReadResult result = readTag();
    if (!result.success || result.tagType != NFC_MEDICATION) {
        lastError = "Not a valid medication tag";
        return false;
    }

    return parseMedicationTag(result.data, medicationId, medicationName, dosage);
}

// Detect tag type from UID prefix or NDEF record
NFCTagType NFCManager::detectTagType(String uid, String data) {
    // If data contains type field, use it
    if (data.length() > 0) {
        JsonDocument doc;  // ✅ ArduinoJson v7 compatible
        DeserializationError error = deserializeJson(doc, data);
        if (!error && doc.containsKey("type")) {
            return (NFCTagType)doc["type"].as<int>();
        }
    }

    // Otherwise, try to detect from UID prefix
    // Hospital can configure UID ranges for different tag types
    // Example: Staff badges start with "04", Patient wristbands with "05", etc.
    if (uid.startsWith("04")) {
        return NFC_STAFF_BADGE;
    } else if (uid.startsWith("05")) {
        return NFC_PATIENT_WRISTBAND;
    } else if (uid.startsWith("06")) {
        return NFC_ROOM_TAG;
    } else if (uid.startsWith("07")) {
        return NFC_MEDICATION;
    } else if (uid.startsWith("08")) {
        return NFC_EQUIPMENT;
    }

    return NFC_UNKNOWN;
}

// Internal: Read NDEF message from tag
// Note: Simplified version - NDEF reading requires additional libraries
// For now, this returns false and users should use UID-based detection
bool NFCManager::readNDEFMessage(String& payload) {
    lastError = "NDEF reading not implemented - use UID-based tag detection";
    return false;
}

// Internal: Write NDEF message to tag
// Note: Simplified version - NDEF writing requires additional libraries
// For production use, install NDEF library or use external tag programming tool
bool NFCManager::writeNDEFMessage(String payload) {
    lastError = "NDEF writing not implemented - program tags externally";
    return false;
}

// Internal: Convert UID byte array to hex string
String NFCManager::uidToString(uint8_t* uid, uint8_t uidLength) {
    String uidStr = "";
    for (uint8_t i = 0; i < uidLength; i++) {
        if (uid[i] < 0x10) {
            uidStr += "0";
        }
        uidStr += String(uid[i], HEX);
    }
    uidStr.toUpperCase();
    return uidStr;
}

// Internal: Parse staff badge JSON
bool NFCManager::parseStaffBadge(String data, String& staffId, String& staffName, String& role) {
    JsonDocument doc;  // ✅ ArduinoJson v7 compatible
    DeserializationError error = deserializeJson(doc, data);

    if (error) {
        lastError = "Invalid JSON in staff badge";
        return false;
    }

    JsonObject dataObj = doc["data"];
    if (!dataObj.containsKey("staffId") || !dataObj.containsKey("staffName") || !dataObj.containsKey("role")) {
        lastError = "Missing required fields in staff badge";
        return false;
    }

    staffId = dataObj["staffId"].as<String>();
    staffName = dataObj["staffName"].as<String>();
    role = dataObj["role"].as<String>();

    return true;
}

// Internal: Parse patient wristband JSON
bool NFCManager::parsePatientWristband(String data, String& patientId, String& patientName) {
    JsonDocument doc;  // ✅ ArduinoJson v7 compatible
    DeserializationError error = deserializeJson(doc, data);

    if (error) {
        lastError = "Invalid JSON in patient wristband";
        return false;
    }

    JsonObject dataObj = doc["data"];
    if (!dataObj.containsKey("patientId") || !dataObj.containsKey("patientName")) {
        lastError = "Missing required fields in patient wristband";
        return false;
    }

    patientId = dataObj["patientId"].as<String>();
    patientName = dataObj["patientName"].as<String>();

    return true;
}

// Internal: Parse room tag JSON
bool NFCManager::parseRoomTag(String data, String& roomNumber, String& bedNumber) {
    JsonDocument doc;  // ✅ ArduinoJson v7 compatible
    DeserializationError error = deserializeJson(doc, data);

    if (error) {
        lastError = "Invalid JSON in room tag";
        return false;
    }

    JsonObject dataObj = doc["data"];
    if (!dataObj.containsKey("roomNumber") || !dataObj.containsKey("bedNumber")) {
        lastError = "Missing required fields in room tag";
        return false;
    }

    roomNumber = dataObj["roomNumber"].as<String>();
    bedNumber = dataObj["bedNumber"].as<String>();

    return true;
}

// Internal: Parse medication tag JSON
bool NFCManager::parseMedicationTag(String data, String& medId, String& medName, String& dosage) {
    JsonDocument doc;  // ✅ ArduinoJson v7 compatible
    DeserializationError error = deserializeJson(doc, data);

    if (error) {
        lastError = "Invalid JSON in medication tag";
        return false;
    }

    JsonObject dataObj = doc["data"];
    if (!dataObj.containsKey("medicationId") || !dataObj.containsKey("medicationName") || !dataObj.containsKey("dosage")) {
        lastError = "Missing required fields in medication tag";
        return false;
    }

    medId = dataObj["medicationId"].as<String>();
    medName = dataObj["medicationName"].as<String>();
    dosage = dataObj["dosage"].as<String>();

    return true;
}

// ====================================
// IRQ MODE FUNCTIONS (Adafruit Example-Based)
// ====================================

// Start listening for NFC tags (passive target detection)
void NFCManager::startListeningToNFC() {
    if (!initialized) return;

    // Reset IRQ state
    irqPrev = irqCurr = HIGH;

    Serial.println("[NFC] Starting passive target detection for Mifare cards...");

    // ✅ Use IRQ mode API: startPassiveTargetIDDetection()
    if (!nfc->startPassiveTargetIDDetection(PN532_MIFARE_ISO14443A)) {
        Serial.println("[NFC] No card found, waiting for IRQ...");
    } else {
        Serial.println("[NFC] Card already present, reading...");
        handleCardDetected();
    }

    interruptEnabled = true;
}

// Handle card detected via IRQ
NFCReadResult NFCManager::handleCardDetected() {
    NFCReadResult result;
    result.success = false;
    result.timestamp = millis();
    result.tagType = NFC_UNKNOWN;
    result.uid = "";
    result.data = "";

    if (!initialized) {
        lastError = "NFC module not initialized";
        return result;
    }

    uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };
    uint8_t uidLength;

    // ✅ Use IRQ mode API: readDetectedPassiveTargetID()
    uint8_t success = nfc->readDetectedPassiveTargetID(uid, &uidLength);

    if (success) {
        result.uid = uidToString(uid, uidLength);
        result.success = true;
        result.tagType = detectTagType(result.uid, "");

        Serial.println("[NFC] ✅ Card detected:");
        Serial.println("  UID: " + result.uid);
        Serial.print("  UID Length: "); Serial.print(uidLength); Serial.println(" bytes");
        Serial.println("  Type: " + String(result.tagType));

        if (uidLength == 4) {
            // Mifare Classic card - show card ID as number
            uint32_t cardid = uid[0];
            cardid <<= 8;
            cardid |= uid[1];
            cardid <<= 8;
            cardid |= uid[2];
            cardid <<= 8;
            cardid |= uid[3];
            Serial.println("  Mifare Classic card #" + String(cardid));
        }

        lastReadUID = result.uid;
        lastReadTime = millis();
    } else {
        Serial.println("[NFC] ❌ Failed to read card");
        lastError = "Failed to read detected card";
    }

    // Disable reader temporarily (debounce)
    timeLastCardRead = millis();
    readerDisabled = true;

    return result;
}

// Update function - call this in main loop() to check IRQ pin
void NFCManager::updateIRQ() {
    if (!initialized) return;

    // If reader is disabled (debouncing), check if enough time has passed
    if (readerDisabled) {
        if (millis() - timeLastCardRead > DELAY_BETWEEN_CARDS) {
            readerDisabled = false;
            startListeningToNFC();  // Re-enable listening
        }
        return;
    }

    // Read current IRQ pin state
    irqCurr = digitalRead(irqPin);

    // Detect HIGH → LOW transition (card detected)
    if (irqCurr == LOW && irqPrev == HIGH) {
        Serial.println("[NFC] 🔔 IRQ triggered!");
        handleCardDetected();
    }

    // Save current state for next iteration
    irqPrev = irqCurr;
}
