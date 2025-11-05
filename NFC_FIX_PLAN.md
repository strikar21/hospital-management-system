# NFC Implementation Fix - Based on Adafruit Examples

**Date:** 2025-10-27
**Issue:** Current NFCManager uses wrong API for IRQ mode
**Source:** Adafruit PN532 library examples (readMifareClassicIrq.ino)

---

## What's Wrong in Current NFCManager.cpp

### 1. Wrong API Usage
```cpp
// ❌ CURRENT (WRONG):
nfc->readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 200);
```

This is **polling mode**, not IRQ mode. It blocks for timeout period.

### 2. No startPassiveTargetIDDetection() Call
IRQ mode requires:
1. Call `startPassiveTargetIDDetection()` once to start listening
2. Wait for IRQ pin to go LOW
3. Call `readDetectedPassiveTargetID()` to get the data

### 3. No Debouncing
After reading a card, need to disable reader briefly to avoid repeated reads.

---

## Proper IRQ Implementation (from Adafruit Example)

### Key Functions:

#### Setup Phase:
```cpp
nfc.begin();
uint32_t versiondata = nfc.getFirmwareVersion();
// ... check version ...

startListeningToNFC();  // Start passive detection
```

#### startListeningToNFC():
```cpp
void startListeningToNFC() {
  irqPrev = irqCurr = HIGH;

  Serial.println("Starting passive read for an ISO14443A Card ...");
  if (!nfc.startPassiveTargetIDDetection(PN532_MIFARE_ISO14443A)) {
    Serial.println("No card found. Waiting...");
  } else {
    Serial.println("Card already present.");
    handleCardDetected();
  }
}
```

#### Loop Phase:
```cpp
void loop() {
  if (readerDisabled) {
    if (millis() - timeLastCardRead > DELAY_BETWEEN_CARDS) {
      readerDisabled = false;
      startListeningToNFC();  // Re-enable
    }
  } else {
    irqCurr = digitalRead(PN532_IRQ);

    // Detect LOW transition (card detected)
    if (irqCurr == LOW && irqPrev == HIGH) {
       Serial.println("Got NFC IRQ");
       handleCardDetected();
    }

    irqPrev = irqCurr;
  }
}
```

#### handleCardDetected():
```cpp
void handleCardDetected() {
    uint8_t success = false;
    uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };
    uint8_t uidLength;

    // ✅ CORRECT API for IRQ mode:
    success = nfc.readDetectedPassiveTargetID(uid, &uidLength);

    if (success) {
      // Process UID
      // ...
    }

    timeLastCardRead = millis();
    readerDisabled = true;  // Debounce
}
```

---

## Required Changes to NFCManager

### 1. Add State Variables to NFCManager.h
```cpp
class NFCManager {
private:
    // ... existing ...

    // IRQ state tracking
    int irqPrev;
    int irqCurr;
    bool readerDisabled;
    unsigned long timeLastCardRead;
    const int DELAY_BETWEEN_CARDS = 500;  // ms
};
```

### 2. Update NFCManager::begin()
```cpp
bool NFCManager::begin() {
    // ... existing initialization ...

    // Initialize IRQ state
    irqPrev = HIGH;
    irqCurr = HIGH;
    readerDisabled = false;
    timeLastCardRead = 0;

    // Start passive detection
    startListeningToNFC();

    initialized = true;
    return true;
}
```

### 3. Add startListeningToNFC()
```cpp
void NFCManager::startListeningToNFC() {
    if (!initialized) return;

    irqPrev = irqCurr = HIGH;

    Serial.println("[NFC] Starting passive target detection...");
    if (!nfc->startPassiveTargetIDDetection(PN532_MIFARE_ISO14443A)) {
        Serial.println("[NFC] No card found, waiting for IRQ...");
    } else {
        Serial.println("[NFC] Card already present");
        handleCardDetected();
    }
}
```

### 4. Add handleCardDetected()
```cpp
NFCReadResult NFCManager::handleCardDetected() {
    NFCReadResult result;
    result.success = false;
    result.timestamp = millis();

    uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };
    uint8_t uidLength;

    // ✅ Use IRQ mode API
    uint8_t success = nfc->readDetectedPassiveTargetID(uid, &uidLength);

    if (success) {
        result.uid = uidToString(uid, uidLength);
        result.success = true;
        result.tagType = detectTagType(result.uid, "");

        Serial.println("[NFC] Card detected:");
        Serial.println("  UID: " + result.uid);
        Serial.println("  Type: " + String(result.tagType));

        lastReadUID = result.uid;
    } else {
        Serial.println("[NFC] Failed to read card");
    }

    timeLastCardRead = millis();
    readerDisabled = true;

    return result;
}
```

### 5. Update loop() Integration in Main .ino
```cpp
// In main loop():
if (nfcAvailable) {
    nfc.updateIRQ();  // Check IRQ and handle cards
}
```

### 6. Add updateIRQ() Method
```cpp
void NFCManager::updateIRQ() {
    if (!initialized) return;

    if (readerDisabled) {
        if (millis() - timeLastCardRead > DELAY_BETWEEN_CARDS) {
            readerDisabled = false;
            startListeningToNFC();
        }
    } else {
        irqCurr = digitalRead(irqPin);

        // Detect HIGH→LOW transition
        if (irqCurr == LOW && irqPrev == HIGH) {
            Serial.println("[NFC] IRQ triggered!");
            handleCardDetected();
        }

        irqPrev = irqCurr;
    }
}
```

---

## Constructor for I2C Mode (from Example)

The Adafruit example uses:
```cpp
Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);
```

This is the **I2C constructor**:
- 1st parameter: IRQ pin
- 2nd parameter: RESET pin (-1 if not connected)

Our current code already does this correctly:
```cpp
nfc = new Adafruit_PN532(irqPin, -1);  // ✅ Correct
```

---

## Summary of Changes

| File | Change | Reason |
|------|--------|--------|
| NFCManager.h | Add irqPrev, irqCurr, readerDisabled, timeLastCardRead | Track IRQ state |
| NFCManager.h | Add startListeningToNFC(), updateIRQ(), handleCardDetected() | IRQ mode API |
| NFCManager.cpp | Implement startListeningToNFC() | Start passive detection |
| NFCManager.cpp | Implement handleCardDetected() | Use readDetectedPassiveTargetID() |
| NFCManager.cpp | Implement updateIRQ() | Check IRQ pin in loop |
| NFCManager.cpp | Update begin() | Initialize IRQ state, start listening |
| esp32_hospital_watch_complete.ino | Add nfc.updateIRQ() to loop() | Poll for IRQ events |

---

## Testing Steps

1. **Compile** - Verify no compilation errors
2. **Upload** - Flash to ESP32
3. **Check serial output**:
   - Look for "Starting passive target detection..."
   - If no PN532: "PN532 not found"
   - If PN532 connected: "waiting for IRQ..."
4. **Scan NFC card**:
   - Should see "IRQ triggered!"
   - Should see UID printed
   - Card type detected
5. **Verify debouncing**:
   - After 500ms, should see "Starting passive target detection..." again
   - Ready for next card

---

## Why This Fixes the Issue

**Old code:**
- Used blocking `readPassiveTargetID()` with timeout
- Never actually used IRQ pin
- Would timeout waiting, wasting CPU

**New code:**
- Uses non-blocking `startPassiveTargetIDDetection()`
- Actually monitors IRQ pin for LOW signal
- Calls `readDetectedPassiveTargetID()` only when card present
- Efficient, event-driven, proper IRQ usage

---

## Next: Apply These Changes

Ready to implement these fixes to NFCManager.h and NFCManager.cpp?
