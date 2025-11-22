/*
 * NFC Manager for ESP32 Hospital Watch
 * PN532 NFC Module over I2C Bus 1 (Separate from Display Touch)
 *
 * Features:
 * - Staff badge authentication
 * - Patient wristband identification
 * - Room location tracking via NFC tags
 * - Medication verification
 * - MIFARE Classic/Ultralight/DESFire support
 * - Interrupt-driven tag detection (scan on demand)
 *
 * Hardware: PN532 NFC Module connected via I2C Bus 1 (TwoWire)
 * Wiring (v5.3.0 - Updated for dual I2C bus):
 *   PN532 SDA   → GPIO 16 (I2C Bus 1 SDA)
 *   PN532 SCL   → GPIO 17 (I2C Bus 1 SCL)
 *   PN532 IRQ   → GPIO 25 (ESP32 interrupt pin)
 *   PN532 VCC   → 3.3V
 *   PN532 GND   → GND
 *
 * Note:
 * - Set PN532 DIP switches to I2C mode (usually OFF, ON)
 * - Display/Touch uses I2C Bus 0 (GPIO 21/22)
 * - NFC uses I2C Bus 1 (GPIO 16/17) to avoid driver conflict
 *
 * Author: Claude/Anthropic
 * Date: 2025-10-27, Updated: 2025-11-21
 */

#ifndef NFC_MANAGER_H
#define NFC_MANAGER_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_PN532.h>

// NFC Tag Types (Hospital Use Cases)
enum NFCTagType {
    NFC_UNKNOWN = 0,
    NFC_STAFF_BADGE = 1,      // Staff authentication
    NFC_PATIENT_WRISTBAND = 2, // Patient identification
    NFC_ROOM_TAG = 3,          // Room/bed location
    NFC_MEDICATION = 4,        // Medication package
    NFC_EQUIPMENT = 5          // Equipment tracking
};

// NFC Read Result
struct NFCReadResult {
    bool success;
    NFCTagType tagType;
    String uid;              // Unique ID of the tag
    String data;             // Payload data (JSON format)
    unsigned long timestamp; // millis() when tag was read
};

class NFCManager {
public:
    // Constructor with custom I2C pins (separate bus from display)
    // Default: SDA=16, SCL=17 (I2C Bus 1), IRQ=25
    NFCManager(uint8_t sda_pin = 16, uint8_t scl_pin = 17, uint8_t irq_pin = 25);

    // Initialize NFC module
    bool begin();

    // Read NFC tag (called when interrupt triggers)
    NFCReadResult readTag();

    // Check if tag is present (quick check without reading data)
    bool isTagPresent();

    // Get tag UID only (faster than full read)
    String getTagUID();

    // Write data to tag (for programming new tags)
    bool writeTag(NFCTagType tagType, String jsonData);

    // Hospital-specific helper functions
    bool authenticateStaff(String& staffId, String& staffName, String& role);
    bool identifyPatient(String& patientId, String& patientName);
    bool readRoomTag(String& roomNumber, String& bedNumber);
    bool verifyMedication(String& medicationId, String& medicationName, String& dosage);

    // Detect tag type from UID prefix or NDEF record
    NFCTagType detectTagType(String uid, String data);

    // Get last error message
    String getLastError();

    // Get NFC module status
    bool isReady();

    // Check if IRQ pin is low (tag detected)
    bool isIRQTriggered();

    // Enable/disable interrupt mode
    void enableInterrupt();
    void disableInterrupt();

    // ✅ IRQ mode functions (based on Adafruit example)
    void updateIRQ();  // Call this in main loop() to check for cards
    void startListeningToNFC();
    NFCReadResult handleCardDetected();

    // Parse functions (public for use in main .ino file)
    bool parseStaffBadge(String data, String& staffId, String& staffName, String& role);
    bool parsePatientWristband(String data, String& patientId, String& patientName);
    bool parseRoomTag(String data, String& roomNumber, String& bedNumber);
    bool parseMedicationTag(String data, String& medId, String& medName, String& dosage);

private:
    Adafruit_PN532* nfc;
    TwoWire* i2cBus;  // Separate I2C bus for NFC

    uint8_t irqPin;
    uint8_t sdaPin;
    uint8_t sclPin;
    bool initialized;
    bool interruptEnabled;
    String lastError;
    unsigned long lastReadTime;
    String lastReadUID;

    // ✅ IRQ state tracking (from Adafruit example)
    int irqPrev;
    int irqCurr;
    bool readerDisabled;
    unsigned long timeLastCardRead;
    static const int DELAY_BETWEEN_CARDS = 500;  // ms debounce delay

    // Internal helpers
    bool readNDEFMessage(String& payload);
    bool writeNDEFMessage(String payload);
    String uidToString(uint8_t* uid, uint8_t uidLength);
};

#endif // NFC_MANAGER_H
