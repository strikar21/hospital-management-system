# NFC Tap Demo - ESP32 Hospital Watch

## What Happens When You Tap an NFC Card?

### Visual Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Card Approaches Watch                                  │
│  ────────────────────────────────────                           │
│                                                                  │
│   [NFC Card]  ➜  [ESP32 Watch]                                  │
│                                                                  │
│   IRQ Pin: HIGH (no card)                                       │
│   Display: Idle screen showing vitals                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Card Detection (IRQ Triggered)                         │
│  ──────────────────────────────────────                         │
│                                                                  │
│   [NFC Card] ✅ [ESP32 Watch]                                   │
│                                                                  │
│   IRQ Pin: HIGH → LOW (card detected!)                          │
│   PN532 Module: Activates RF field, reads UID                   │
│   Response Time: <100ms                                          │
│                                                                  │
│   Serial Console:                                                │
│   [NFC] 🔔 IRQ triggered!                                       │
│   [NFC] ✅ Card detected:                                       │
│   UID: 04A1B2C3                                                  │
│   UID Length: 4 bytes                                            │
│   Type: NFC_STAFF_BADGE                                          │
│   Mifare Classic card #77459139                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Visual Feedback on Display                             │
│  ───────────────────────────────────                            │
│                                                                  │
│   ┌──────────────────────────────────────────────┐              │
│   │  ╔══════════════════════════════════════╗   │              │
│   │  ║                                       ║   │              │
│   │  ║    📇 STAFF BADGE                    ║   │              │
│   │  ║                                       ║   │              │
│   │  ║    UID: 04A1B2C3                     ║   │              │
│   │  ║                                       ║   │              │
│   │  ╚══════════════════════════════════════╝   │              │
│   │                                              │              │
│   │  [Alert popup displayed for 3 seconds]      │              │
│   └──────────────────────────────────────────────┘              │
│                                                                  │
│   LED Status: 🔵 Blue flash (3 blinks)                          │
│   Duration: Alert auto-closes after 3 seconds                   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Debounce Period                                        │
│  ──────────────────────                                         │
│                                                                  │
│   Reader Disabled: 500ms cooldown                               │
│   Prevents duplicate reads if card stays in range               │
│                                                                  │
│   Serial Console:                                                │
│   [NFC] Reader disabled for 500ms (debounce)                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: Return to Listening Mode                               │
│  ─────────────────────────────────                              │
│                                                                  │
│   After 500ms:                                                   │
│   - Reader re-enabled                                            │
│   - PN532 resumes passive target detection                      │
│   - IRQ pin ready for next card                                 │
│   - Display returns to idle screen                              │
│                                                                  │
│   Serial Console:                                                │
│   [NFC] Starting passive target detection for Mifare cards...   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Card Type Detection

The watch automatically identifies different card types based on UID prefix:

| UID Prefix | Card Type | Display Text | Use Case |
|------------|-----------|--------------|----------|
| `04xxxxxx` | NFC_STAFF_BADGE | **📇 STAFF BADGE** | Healthcare worker authentication |
| `05xxxxxx` | NFC_PATIENT_WRISTBAND | **🏥 PATIENT ID** | Patient identification |
| `06xxxxxx` | NFC_ROOM_TAG | **🚪 ROOM TAG** | Room/bed location tracking |
| `07xxxxxx` | NFC_MEDICATION | **💊 MEDICATION** | Medication verification |
| `08xxxxxx` | NFC_EQUIPMENT | **🔧 EQUIPMENT** | Medical equipment tracking |
| Other | NFC_UNKNOWN | **🔖 NFC CARD** | Generic NFC tag |

---

## Code Flow

### 1. Main Loop (Every 100ms)
```cpp
// esp32_hospital_watch_complete.ino:1827
if (nfcAvailable) {
  NFCReadResult nfcResult = nfc.updateIRQ();  // Check IRQ pin

  if (nfcResult.success) {  // Card detected?
    // Determine card type
    String cardType = "NFC CARD";
    if (nfcResult.tagType == NFC_STAFF_BADGE) cardType = "STAFF BADGE";
    // ... other card types ...

    // Show visual alert
    ui.showAlert(cardType, "UID: " + nfcResult.uid);

    // Flash LED
    flashAlertPattern("info");
  }
}
```

### 2. NFCManager (IRQ Detection)
```cpp
// NFCManager.cpp:526
NFCReadResult NFCManager::updateIRQ() {
  // Read IRQ pin state
  irqCurr = digitalRead(irqPin);

  // Detect HIGH → LOW transition (card detected)
  if (irqCurr == LOW && irqPrev == HIGH) {
    Serial.println("[NFC] 🔔 IRQ triggered!");
    NFCReadResult result = handleCardDetected();  // Read UID
    return result;  // Return to main loop
  }

  // No card detected
  return emptyResult;
}
```

### 3. Card Reading
```cpp
// NFCManager.cpp:470
NFCReadResult NFCManager::handleCardDetected() {
  uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };
  uint8_t uidLength;

  // Read UID from card
  uint8_t success = nfc->readDetectedPassiveTargetID(uid, &uidLength);

  if (success) {
    result.uid = uidToString(uid, uidLength);  // Convert to hex string
    result.success = true;
    result.tagType = detectTagType(result.uid, "");  // Identify card type
    result.timestamp = millis();

    Serial.println("[NFC] ✅ Card detected:");
    Serial.println("  UID: " + result.uid);
    Serial.println("  Type: " + String(result.tagType));
  }

  // Disable reader for 500ms (debounce)
  readerDisabled = true;
  timeLastCardRead = millis();

  return result;
}
```

---

## Hardware Setup

### PN532 NFC Module Wiring

```
┌──────────────────────────────────────────────────────────┐
│  PN532 Module              ESP32-S3                      │
│  ─────────────              ───────                      │
│                                                           │
│  VCC (3.3V)   ────────────► 3V3                          │
│  GND          ────────────► GND                          │
│  SDA          ────────────► GPIO 16 (I2C Bus 1)          │
│  SCL          ────────────► GPIO 17 (I2C Bus 1)          │
│  IRQ          ────────────► GPIO 25 (Interrupt)          │
│                                                           │
└──────────────────────────────────────────────────────────┘

Note: Set PN532 DIP switches to I2C mode (OFF, ON)
      Display/Touch uses I2C Bus 0 (GPIO 47/48)
      NFC uses I2C Bus 1 (GPIO 16/17) - separate bus!
```

---

## Testing Checklist

### Hardware Tests
- [ ] Tap Mifare Classic card (4-byte UID)
  - Expected: "NFC CARD - UID: XXXXXXXX" (if UID doesn't match pattern)
  - Expected: "STAFF BADGE - UID: 04XXXXXX" (if UID starts with 04)
- [ ] Tap Mifare Ultralight card (7-byte UID)
  - Expected: "NFC CARD - UID: XXXXXXXXXXXXXX"
- [ ] Check Serial console shows detailed card info
  - UID in hex
  - UID length in bytes
  - Card ID as decimal number (for 4-byte UIDs)
- [ ] Verify LED flashes blue when card detected
- [ ] Verify alert popup auto-closes after 3 seconds
- [ ] Verify 500ms debounce prevents duplicate reads
- [ ] Test rapid tap/remove (should only register once per 500ms)

### Software Tests
- [ ] Compile firmware without errors
- [ ] Upload to ESP32-S3 hardware
- [ ] Monitor Serial output (115200 baud)
- [ ] Verify IRQ pin transitions (GPIO 25 should be HIGH normally, LOW when card present)
- [ ] Test with multiple card types (if programmed with different UID prefixes)

---

## Example Serial Console Output

```
[NFC] Starting passive target detection for Mifare cards...
[NFC] No card found, waiting for IRQ...

... user taps card ...

[NFC] 🔔 IRQ triggered!
[NFC] ✅ Card detected:
  UID: 04A1B2C3
  UID Length: 4 bytes
  Type: 1
  Mifare Classic card #77459139
[NFC] Reader disabled for 500ms (debounce)

... 500ms passes ...

[NFC] Starting passive target detection for Mifare cards...
[NFC] No card found, waiting for IRQ...
```

---

## Example Screen Display

### Scenario 1: Staff Badge Detected
```
┌─────────────────────────────┐
│  ╔══════════════════════╗   │
│  ║                       ║   │
│  ║  📇 STAFF BADGE      ║   │
│  ║                       ║   │
│  ║  UID: 04A1B2C3       ║   │
│  ║                       ║   │
│  ╚══════════════════════╝   │
│                              │
│  Heart Rate: 78 bpm          │
│  SpO₂: 98%                   │
│  Temp: 36.8°C                │
└─────────────────────────────┘
```

### Scenario 2: Patient Wristband Detected
```
┌─────────────────────────────┐
│  ╔══════════════════════╗   │
│  ║                       ║   │
│  ║  🏥 PATIENT ID       ║   │
│  ║                       ║   │
│  ║  UID: 05C4D5E6       ║   │
│  ║                       ║   │
│  ╚══════════════════════╝   │
│                              │
│  Heart Rate: 78 bpm          │
│  SpO₂: 98%                   │
│  Temp: 36.8°C                │
└─────────────────────────────┘
```

### Scenario 3: Unknown Card
```
┌─────────────────────────────┐
│  ╔══════════════════════╗   │
│  ║                       ║   │
│  ║  🔖 NFC CARD         ║   │
│  ║                       ║   │
│  ║  UID: 12AB34CD       ║   │
│  ║                       ║   │
│  ╚══════════════════════╝   │
│                              │
│  Heart Rate: 78 bpm          │
│  SpO₂: 98%                   │
│  Temp: 36.8°C                │
└─────────────────────────────┘
```

---

## LED Flash Patterns

| Pattern | Color | Duration | Use Case |
|---------|-------|----------|----------|
| `info` | 🔵 Blue | 3 blinks × 200ms | NFC card detected |
| `warning` | 🟡 Yellow | 5 blinks × 150ms | Abnormal vitals |
| `critical` | 🔴 Red | Rapid flash (10 blinks × 100ms) | Fall detected |

---

## Troubleshooting

### No IRQ Trigger
- Check GPIO 25 wiring
- Verify PN532 DIP switches (should be OFF, ON for I2C mode)
- Check Serial console for "PN532 not found" error
- Verify 3.3V power supply to PN532

### Card Not Detected
- Bring card closer (within 5cm of PN532 antenna)
- Check Serial console shows "Starting passive target detection..."
- Verify IRQ pin is HIGH when no card present

### Duplicate Reads
- Normal - 500ms debounce period
- If reading same card multiple times, increase `DELAY_BETWEEN_CARDS` in NFCManager.h

### Display Not Showing Alert
- Check LVGL initialization in Serial console
- Verify `ui.showAlert()` is called (add Serial.println before it)
- Check if display is stuck in another screen mode

---

**Last Updated**: 2025-11-22
**Firmware Version**: v5.4.1
**Status**: ✅ Ready for hardware testing
