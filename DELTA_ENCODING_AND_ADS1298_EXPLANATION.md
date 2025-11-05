# Delta Encoding & ADS1298 Output - Explained
**Date:** 2025-11-02
**User's Question:** "The delta encoding what's that about? Does ADS1298 send out such data?"

---

## WHAT IS DELTA ENCODING?

### Simple Explanation

**Normal Data (Raw Values):**
```
[8388608, 8388610, 8388613, 8388615, 8388617, ...]
```
Each value is a complete 24-bit number (~3 bytes each)

**Delta Encoded (Differences):**
```
{
  "baseline": 8388608,
  "deltas": [2, 3, 2, 2, ...]
}
```
Store first value + differences between consecutive values

### Why Use Delta Encoding?

**ECG/EEG samples are HIGHLY CORRELATED:**
- Sample 1: 8388608
- Sample 2: 8388610 (difference: +2)
- Sample 3: 8388613 (difference: +3)
- Sample 4: 8388615 (difference: +2)

**Storage Savings:**
- Raw: 50 samples × 3 bytes = 150 bytes
- Delta: 1 baseline (3 bytes) + 49 deltas (~1 byte each) = ~52 bytes
- **Compression: 65% reduction!**

### Code Example (From Backend)

```python
class ChannelData(BaseModel):
    """Delta-encoded channel data for bandwidth efficiency"""
    baseline: int  # First sample value
    deltas: List[int]  # Differences from previous sample

    def decompress(self) -> List[int]:
        """Reconstruct original samples"""
        values = [self.baseline]  # Start with baseline
        for delta in self.deltas:
            values.append(values[-1] + delta)  # Add delta to previous value
        return values

# Example
encoded = ChannelData(baseline=8388608, deltas=[2, 3, 2, 2])
decoded = encoded.decompress()
# Result: [8388608, 8388610, 8388613, 8388615, 8388617]
```

---

## DOES ADS1298 SEND DELTA-ENCODED DATA?

### Short Answer: **NO!**

**ADS1298 sends RAW 24-bit ADC values**

---

## HOW ADS1298 ACTUALLY WORKS

### Physical Reality

**ADS1298** = 8-channel, 24-bit analog-to-digital converter (Texas Instruments)

**Output Format:**
```
CH1: 0x7FFFFF (24-bit binary)
CH2: 0x800010
CH3: 0x7FFFF2
... (8 channels total)
```

Each sample is a **raw 24-bit signed integer** representing voltage.

### ADS1298 Data Sheet Facts

**From TI ADS1298 Datasheet:**
- Resolution: 24-bit
- Sampling rate: Up to 8000 samples/second
- Output: SPI interface, binary data
- Range: ±2.4V (configurable with PGA gain)
- **Output format: Two's complement binary** (NOT delta-encoded)

### ESP32 Reads ADS1298 Like This:

**Hypothetical ADS1298 Integration (if we had real hardware):**
```cpp
// Read 8 channels from ADS1298 via SPI
void readADS1298Channels(int32_t samples[8]) {
    digitalWrite(CS_PIN, LOW);  // Select ADS1298

    for (int ch = 0; ch < 8; ch++) {
        // Read 3 bytes (24 bits) per channel
        uint8_t byte1 = SPI.transfer(0x00);  // MSB
        uint8_t byte2 = SPI.transfer(0x00);
        uint8_t byte3 = SPI.transfer(0x00);  // LSB

        // Combine into 24-bit signed integer
        int32_t value = (byte1 << 16) | (byte2 << 8) | byte3;

        // Sign-extend from 24-bit to 32-bit
        if (value & 0x800000) {
            value |= 0xFF000000;  // Negative number
        }

        samples[ch] = value;  // RAW ADC value (NOT delta-encoded!)
    }

    digitalWrite(CS_PIN, HIGH);
}
```

**Output Example:**
```cpp
samples[0] = 8388608;  // RAW value
samples[1] = 8388610;  // RAW value
samples[2] = 8388613;  // RAW value
// ... all RAW values
```

---

## OUR CURRENT SYSTEM (Simulator)

### What We Actually Use

**File:** `PhysiologicalSimulator.cpp` (lines 273-329)

**We DON'T have real ADS1298!** We simulate it:

```cpp
void PhysiologicalSimulator::generateECGSample(int lead, int32_t& sample) {
    // Generate realistic ECG waveform mathematically
    float amplitude = generatePQRST(phase, lead);

    // Convert to 24-bit ADC units (simulating ADS1298 output)
    sample = 8388608 + (int32_t)(amplitude * 100000);

    // Add realistic noise
    sample += random(-50, 51);
}
```

**Output:** RAW 24-bit integers (same format as real ADS1298 would produce)

---

## WHERE DELTA ENCODING HAPPENS

### Current System Flow

```
ESP32 PhysiologicalSimulator
  ↓ Generates RAW samples [8388608, 8388610, 8388613, ...]

ESP32 Firmware (esp32_hospital_watch_complete.ino)
  ↓ Sends RAW arrays to backend via MQTT

{
  "ecgWaveform": {
    "limb": {
      "lead1": [8388608, 8388610, 8388613, ...],  // ✅ RAW arrays
      "lead2": [...]
    }
  }
}

Backend (mqtt_service.py)
  ↓ Receives RAW arrays
  ↓ Stores RAW arrays as JSONB in database

Database (waveform_snapshots table)
  ✅ STORES RAW ARRAYS (NO delta encoding currently!)
```

### Backend Schema SUPPORTS Delta Encoding (But We're Not Using It)

**Backend Pydantic Model** (lines 109-122):
```python
class ChannelData(BaseModel):
    """Delta-encoded channel data for bandwidth efficiency"""
    baseline: int
    deltas: List[int]
```

**BUT!** This is **OPTIONAL**. The schema ALSO accepts raw arrays.

---

## WHY BACKEND HAS DELTA ENCODING SUPPORT

### Design Intent (Not Currently Implemented)

**Original Plan:**
1. ESP32 sends RAW arrays
2. Backend converts to delta encoding before database storage
3. Saves database space

**Current Reality:**
1. ESP32 sends RAW arrays ✅
2. Backend stores RAW arrays AS-IS ✅
3. No delta encoding conversion yet ❌

### Does It Matter?

**For 100ms packets (50 samples):**
- Raw: 50 samples × 4 bytes (JSON integer) = ~200 bytes
- Delta: 1 baseline + 49 deltas = ~150 bytes
- **Savings: 25%** (not critical)

**For 10-second snapshots (5000 samples):**
- Raw: 5000 samples × 4 bytes = ~20,000 bytes = 20KB
- Delta: 1 baseline + 4999 deltas = ~15KB
- **Savings: 25%** (more significant)

### PostgreSQL JSON Compression

**TimescaleDB automatically compresses JSONB data!**

PostgreSQL's TOAST (The Oversized-Attribute Storage Technique) automatically compresses large JSONB fields.

**Compression methods:**
- LZ compression (similar to gzip)
- Already gets ~50-70% compression on raw arrays
- Adding delta encoding on top = maybe 10% more savings

**Conclusion:** Delta encoding is a "nice-to-have" optimization, not critical.

---

## SHOULD WE IMPLEMENT DELTA ENCODING?

### Option 1: Store RAW Arrays (Current Plan) ✅ RECOMMENDED

**Advantages:**
- ✅ Simple (no conversion needed)
- ✅ Fast (direct storage)
- ✅ PostgreSQL TOAST compression handles it
- ✅ Easy to query and analyze

**Disadvantages:**
- ❌ Slightly larger storage (~25% more)

### Option 2: Add Delta Encoding Conversion

**Advantages:**
- ✅ ~25% storage savings
- ✅ Matches backend schema design intent

**Disadvantages:**
- ❌ More complex code
- ❌ Conversion overhead on every write
- ❌ Need decompression for queries
- ❌ PostgreSQL TOAST already compresses well

---

## ANSWER TO USER'S QUESTIONS

### 1. "What's delta encoding about?"

**Answer:**
Compression technique where you store:
- First value (baseline)
- Differences between consecutive samples (deltas)

Instead of: `[100, 102, 105, 107]`
Store: `{baseline: 100, deltas: [2, 3, 2]}`

Saves ~25% space because ECG/EEG samples change slowly.

### 2. "Does ADS1298 send delta-encoded data?"

**Answer:**
**NO!** ADS1298 sends RAW 24-bit ADC values over SPI.

Delta encoding would happen in SOFTWARE (ESP32 or backend), not in the ADC chip itself.

### 3. "Should we use delta encoding?"

**Answer:**
**Not necessary right now.**

Reasons:
1. We're using simulator (not real ADS1298), already generates efficient data
2. PostgreSQL JSONB compression handles raw arrays well
3. Adds complexity for ~10% additional savings after PostgreSQL compression
4. Can add later if storage becomes an issue

**Recommendation: Store RAW arrays for now (simpler)**

---

## REAL ADS1298 INTEGRATION (Future)

### When We Add Real Hardware

**File to create:** `ADS1298Driver.cpp`

```cpp
#include <SPI.h>

class ADS1298Driver {
public:
    void begin() {
        SPI.begin();
        pinMode(CS_PIN, OUTPUT);
        pinMode(DRDY_PIN, INPUT);

        // Configure ADS1298 registers
        writeRegister(CONFIG1, 0x96);  // 500 SPS
        writeRegister(CONFIG2, 0xE0);  // Internal reference
        // ... more configuration

        // Start continuous conversion
        sendCommand(START);
    }

    void readChannels(int32_t samples[8]) {
        // Wait for DRDY (data ready) pin
        while (digitalRead(DRDY_PIN) == HIGH);

        digitalWrite(CS_PIN, LOW);

        // Read status bytes (3 bytes)
        SPI.transfer(0x00);
        SPI.transfer(0x00);
        SPI.transfer(0x00);

        // Read 8 channels × 3 bytes each = 24 bytes
        for (int ch = 0; ch < 8; ch++) {
            uint8_t byte1 = SPI.transfer(0x00);  // MSB
            uint8_t byte2 = SPI.transfer(0x00);
            uint8_t byte3 = SPI.transfer(0x00);  // LSB

            // Combine into 32-bit signed integer
            int32_t value = ((int32_t)byte1 << 16) |
                          ((int32_t)byte2 << 8) |
                          byte3;

            // Sign-extend from 24-bit to 32-bit
            if (value & 0x800000) {
                value |= 0xFF000000;
            }

            samples[ch] = value;  // ✅ RAW ADC value
        }

        digitalWrite(CS_PIN, HIGH);
    }
};
```

**Output will still be RAW values!** ADS1298 doesn't do delta encoding.

---

## SUMMARY

| Question | Answer |
|----------|--------|
| **What is delta encoding?** | Compression: Store first value + differences between samples |
| **Does ADS1298 use it?** | NO - ADS1298 outputs RAW 24-bit ADC values over SPI |
| **Do we use it now?** | NO - Backend supports it but we store RAW arrays |
| **Should we add it?** | NOT NECESSARY - PostgreSQL TOAST compression is sufficient |
| **Where would it happen?** | In SOFTWARE (ESP32 or backend), not in ADS1298 hardware |
| **Storage savings?** | ~25% raw, but PostgreSQL compresses anyway → ~10% net benefit |

---

## RECOMMENDATION FOR OUR PROJECT

**Store RAW arrays (current approach)**

**Reasons:**
1. ✅ Simpler implementation
2. ✅ Faster writes (no conversion)
3. ✅ PostgreSQL handles compression automatically
4. ✅ Easier to query and analyze
5. ✅ Can add delta encoding later if needed
6. ✅ 10% storage savings not worth complexity right now

**If we implement delta encoding later:**
- Add conversion function in backend `_storeWaveformSnapshot()`
- Convert raw arrays to `{baseline, deltas}` format before storage
- Update query functions to decompress on retrieval
