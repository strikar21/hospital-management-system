# STS40 Temperature Sensor Simulator - Detailed Design
**Date**: 2025-10-30
**Sensor**: Sensirion STS40 High-Precision Temperature Sensor
**Datasheet**: [Sensirion STS4x June 2024](https://sensirion.com/media/documents/D2D0B4A9/667AC1F4/HT_DS_Datasheet_STS4x.pdf)
**Complexity**: LOW (Easiest sensor - implement first)

---

## Overview

**Purpose**: Simulate Sensirion STS40 I2C temperature sensor for ESP32 hospital watch

**Why Implement**: Medical-grade skin temperature monitoring (fever detection, hypothermia)

**Key Features**:
- I2C address 0x44 (fixed - no conflicts with MAX86178 0x57 or BMI323 0x68)
- High-precision mode: ±0.1°C accuracy (9ms conversion time)
- 16-bit digital output
- CRC-8 checksum for data integrity
- Temperature range: -40°C to +125°C

---

## Hardware Specifications (From Datasheet)

### I2C Communication
- **Address**: 0x44 (7-bit), 0x45, or 0x46 (selectable at order - we use 0x44)
- **Clock Speed**: Up to 1 MHz (Fast Mode Plus)
- **Communication Protocol**: NXP I2C-bus specification UM10204 Rev.6

### Precision Modes

| Mode | Accuracy | Conversion Time | Command |
|------|----------|-----------------|---------|
| **Low Precision** | ±0.3°C | 2ms | 0xE0 |
| **Medium Precision** | ±0.2°C | 5ms | 0xF6 |
| **High Precision** | ±0.1°C | 9ms | **0xFD** (we use this) |

**Our Choice**: High-precision mode (0xFD) for medical-grade accuracy

### I2C Command Sequence

```
1. Master sends START condition
2. Master sends address 0x44 + WRITE bit
3. Slave ACKs
4. Master sends command 0xFD (high-precision measurement)
5. Slave ACKs
6. Master sends STOP condition
7. [WAIT 9ms for conversion]
8. Master sends START condition
9. Master sends address 0x44 + READ bit
10. Slave ACKs
11. Slave sends Temperature MSB
12. Master ACKs
13. Slave sends Temperature LSB
14. Master ACKs
15. Slave sends CRC-8 checksum
16. Master NACKs
17. Master sends STOP condition
```

### Data Format

**Temperature Conversion Formula** (from datasheet):
```cpp
uint16_t rawTemp = (MSB << 8) | LSB;  // 16-bit unsigned
float tempC = -45.0 + 175.0 * (rawTemp / 65535.0);
float tempF = tempC * 9.0 / 5.0 + 32.0;
```

**Example**:
- Raw value: 0x7FFF (32767) → 42.5°C → 108.5°F
- Raw value: 0x0000 (0) → -45°C → -49°F
- Raw value: 0xFFFF (65535) → 130°C → 266°F

### CRC-8 Checksum

**Algorithm**: CRC-8 with polynomial 0x31 (x^8 + x^5 + x^4 + 1)
**Initial Value**: 0xFF
**Input**: 2 bytes (Temperature MSB + LSB)

**Implementation**:
```cpp
uint8_t calculateCRC(uint16_t value) {
    uint8_t crc = 0xFF;  // Initial value
    uint8_t data[2] = {(uint8_t)(value >> 8), (uint8_t)(value & 0xFF)};

    for (int i = 0; i < 2; i++) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; bit++) {
            if (crc & 0x80) {
                crc = (crc << 1) ^ 0x31;  // Polynomial 0x31
            } else {
                crc = crc << 1;
            }
        }
    }
    return crc;
}
```

### Other Commands (Not Implemented in Phase 1)

| Command | Hex | Function | Notes |
|---------|-----|----------|-------|
| **Soft Reset** | 0x94 | Reset sensor | Use after power-on |
| **Read Serial Number** | 0x89 | Get 48-bit unique ID | For calibration tracking |
| **Heater Enable** | Various | Enable internal heater | For humidity sensors only (SHT40, not STS40) |

---

## Class Interface Design

### STS40Simulator.h

```cpp
#ifndef STS40_SIMULATOR_H
#define STS40_SIMULATOR_H

#include <Arduino.h>
#include "PhysiologicalSimulator.h"  // Get shared physiological state

class STS40Simulator {
public:
    // Constructor
    STS40Simulator(PhysiologicalSimulator* physioSim);

    // Initialize sensor
    void begin();

    // Start temperature measurement (high-precision mode)
    void startMeasurement();

    // Check if measurement is ready (9ms elapsed)
    bool isReady();

    // Read temperature result (returns °C)
    float readTemperature();

    // Advanced: Get raw 16-bit value + CRC
    void readRaw(uint16_t& rawValue, uint8_t& crc);

    // Soft reset (optional - for completeness)
    void softReset();

    // Read serial number (optional - for tracking)
    uint64_t getSerialNumber();

private:
    // Reference to shared physiological state
    PhysiologicalSimulator* physio;

    // Measurement state
    unsigned long measurementStartTime;
    bool measurementInProgress;
    uint16_t lastRawValue;
    uint8_t lastCRC;

    // Sensor serial number (simulated - fixed per instance)
    uint64_t serialNumber;

    // Helper methods
    uint8_t calculateCRC(uint16_t value);
    uint16_t temperatureToCounts(float tempC);
    float countsToTemperature(uint16_t counts);
};

#endif
```

### Key Methods Explained

#### `STS40Simulator(PhysiologicalSimulator* physioSim)`
**Purpose**: Constructor - stores reference to shared physiological state
**Parameters**: Pointer to PhysiologicalSimulator
**Example**:
```cpp
PhysiologicalSimulator simulator;
STS40Simulator sts40(&simulator);
```

#### `void begin()`
**Purpose**: Initialize sensor (simulates power-on sequence)
**Actions**:
- Generate random serial number
- Reset measurement state
- Print debug info

#### `void startMeasurement()`
**Purpose**: Start high-precision temperature measurement (command 0xFD)
**Actions**:
- Record start time
- Set `measurementInProgress = true`
- Simulate I2C command 0xFD sent

**Timing**: Measurement takes 9ms (high-precision mode)

#### `bool isReady()`
**Purpose**: Check if 9ms conversion time has elapsed
**Returns**: `true` if `millis() - measurementStartTime >= 9`

#### `float readTemperature()`
**Purpose**: Read temperature in Celsius
**Actions**:
1. Get current temperature from `physio->getTemperature()` (returns Fahrenheit)
2. Convert Fahrenheit → Celsius
3. Convert Celsius → 16-bit raw counts
4. Calculate CRC-8 checksum
5. Store raw value and CRC (for `readRaw()`)
6. Convert back to Celsius (simulates sensor ADC round-trip)
7. Add ±0.1°C random noise (simulate ±0.1°C accuracy spec)
8. Set `measurementInProgress = false`
9. Return temperature in Celsius

**Returns**: Temperature in °C (float)

**Example**:
```cpp
sts40.startMeasurement();
delay(10);  // Wait > 9ms
if (sts40.isReady()) {
    float tempC = sts40.readTemperature();
    Serial.println("Temp: " + String(tempC) + "°C");
}
```

#### `void readRaw(uint16_t& rawValue, uint8_t& crc)`
**Purpose**: Get raw 16-bit value + CRC (for advanced users)
**Parameters**:
- `rawValue` (output): 16-bit unsigned raw ADC counts
- `crc` (output): CRC-8 checksum

**Use Case**: Verify CRC calculation, low-level debugging

#### `void softReset()`
**Purpose**: Simulate soft reset (command 0x94)
**Actions**: Reset measurement state, clear buffers

#### `uint64_t getSerialNumber()`
**Purpose**: Get 48-bit unique serial number
**Returns**: Simulated serial number (fixed per instance)
**Use Case**: Track individual sensor calibration drift over time

---

## Integration with PhysiologicalSimulator

### Data Flow

```
PhysiologicalSimulator
    ↓ currentTemp (Fahrenheit, e.g., 98.6°F)
STS40Simulator
    ↓ Convert F → C (37.0°C)
    ↓ Convert C → raw counts (0x9C5D)
    ↓ Calculate CRC-8 (0x2F)
    ↓ Convert raw counts → C (37.0°C)
    ↓ Add ±0.1°C noise (37.08°C)
    ↓ Return to firmware
MQTT Vitals Payload
    "skinTemperature": 37.08
```

### Activity State Impact

PhysiologicalSimulator changes temperature based on activity:

| Activity State | Temperature Range | STS40 Reading |
|----------------|------------------|---------------|
| **RESTING** | 97.0-98.0°F (36.1-36.7°C) | 36.1-36.7°C |
| **LIGHT_ACTIVITY** | 97.9-98.5°F (36.6-36.9°C) | 36.6-36.9°C |
| **EXERCISE** | 99.0-100.0°F (37.2-37.8°C) | 37.2-37.8°C |
| **SLEEP** | 96.3-97.3°F (35.7-36.3°C) | 35.7-36.3°C |

### Error Simulation (Future Enhancement)

Currently NOT implemented (Phase 1 focuses on happy path):
- I2C NACK (device not found)
- CRC mismatch (data corruption)
- Out-of-range temperature (sensor malfunction)

Can add in Phase 2 for robustness testing.

---

## Implementation Code

### STS40Simulator.cpp (Skeleton)

```cpp
#include "STS40Simulator.h"

// Constructor
STS40Simulator::STS40Simulator(PhysiologicalSimulator* physioSim) {
    physio = physioSim;
    measurementInProgress = false;
    measurementStartTime = 0;
    lastRawValue = 0;
    lastCRC = 0;
    serialNumber = 0;  // Will be generated in begin()
}

// Initialize sensor
void STS40Simulator::begin() {
    // Generate random 48-bit serial number
    serialNumber = ((uint64_t)random(0, 0xFFFF) << 32) |
                   ((uint64_t)random(0, 0xFFFF) << 16) |
                   ((uint64_t)random(0, 0xFFFF));

    Serial.println("✅ STS40 Simulator initialized");
    Serial.println("   I2C Address: 0x44");
    Serial.println("   Mode: High-precision (±0.1°C, 9ms)");
    Serial.println("   Serial: 0x" + String((unsigned long)(serialNumber >> 16), HEX));
}

// Start measurement
void STS40Simulator::startMeasurement() {
    measurementStartTime = millis();
    measurementInProgress = true;
}

// Check if ready
bool STS40Simulator::isReady() {
    if (!measurementInProgress) return false;
    return (millis() - measurementStartTime) >= 9;  // 9ms for high-precision
}

// Read temperature (main method)
float STS40Simulator::readTemperature() {
    if (!isReady()) {
        Serial.println("⚠️  STS40: Measurement not ready (wait 9ms)");
        return 0.0;
    }

    // Get current temperature from physiological simulator (Fahrenheit)
    float tempF = physio->getTemperature();

    // Convert to Celsius
    float tempC = (tempF - 32.0) * 5.0 / 9.0;

    // Convert to 16-bit raw counts (simulate ADC)
    uint16_t rawCounts = temperatureToCounts(tempC);

    // Calculate CRC
    uint8_t crc = calculateCRC(rawCounts);

    // Store for readRaw()
    lastRawValue = rawCounts;
    lastCRC = crc;

    // Convert back to Celsius (simulate sensor round-trip with quantization)
    float measuredTempC = countsToTemperature(rawCounts);

    // Add ±0.1°C random noise (simulate sensor accuracy spec)
    float noise = (random(-100, 101) / 1000.0);  // ±0.1°C
    measuredTempC += noise;

    // Reset measurement state
    measurementInProgress = false;

    return measuredTempC;
}

// Get raw value + CRC
void STS40Simulator::readRaw(uint16_t& rawValue, uint8_t& crc) {
    rawValue = lastRawValue;
    crc = lastCRC;
}

// Soft reset
void STS40Simulator::softReset() {
    measurementInProgress = false;
    measurementStartTime = 0;
    lastRawValue = 0;
    lastCRC = 0;
    Serial.println("🔄 STS40: Soft reset");
}

// Get serial number
uint64_t STS40Simulator::getSerialNumber() {
    return serialNumber;
}

// === PRIVATE HELPER METHODS ===

// Calculate CRC-8 checksum
uint8_t STS40Simulator::calculateCRC(uint16_t value) {
    uint8_t crc = 0xFF;  // Initial value
    uint8_t data[2] = {(uint8_t)(value >> 8), (uint8_t)(value & 0xFF)};

    for (int i = 0; i < 2; i++) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; bit++) {
            if (crc & 0x80) {
                crc = (crc << 1) ^ 0x31;  // Polynomial 0x31
            } else {
                crc = crc << 1;
            }
        }
    }
    return crc;
}

// Convert temperature (°C) to 16-bit raw counts
uint16_t STS40Simulator::temperatureToCounts(float tempC) {
    // Formula from datasheet: rawTemp = ((tempC + 45.0) / 175.0) * 65535.0
    if (tempC < -45.0) tempC = -45.0;
    if (tempC > 130.0) tempC = 130.0;

    float normalized = (tempC + 45.0) / 175.0;  // 0.0 to 1.0
    uint16_t counts = (uint16_t)(normalized * 65535.0);
    return counts;
}

// Convert 16-bit raw counts to temperature (°C)
float STS40Simulator::countsToTemperature(uint16_t counts) {
    // Formula from datasheet: tempC = -45.0 + 175.0 * (counts / 65535.0)
    float normalized = counts / 65535.0;  // 0.0 to 1.0
    float tempC = -45.0 + 175.0 * normalized;
    return tempC;
}
```

---

## Usage in Main Firmware

### Setup (esp32_hospital_watch_complete.ino)

```cpp
// Global instances
PhysiologicalSimulator simulator;
STS40Simulator sts40(&simulator);

void setup() {
    // ... existing setup code ...

    // Initialize physiological simulator
    simulator.begin();

    // Initialize STS40 temperature sensor
    sts40.begin();

    Serial.println("✅ All simulators initialized");
}
```

### Loop (Read Temperature Every 1 Second)

```cpp
void loop() {
    // Update shared physiological state
    simulator.update();

    // Read temperature from STS40 (every 1 second)
    if (millis() - lastVitals > 1000) {
        // Start temperature measurement
        sts40.startMeasurement();

        // Wait for conversion (9ms)
        delay(10);

        // Read temperature in Celsius
        if (sts40.isReady()) {
            float tempC = sts40.readTemperature();

            // Store for MQTT vitals
            temperature = tempC;  // Backend expects Celsius

            Serial.println("🌡️ Temperature: " + String(tempC, 2) + "°C");
        }

        lastVitals = millis();
    }

    // ... rest of loop ...
}
```

### MQTT Vitals Payload

```cpp
void sendVitals() {
    // ... existing code ...

    doc["skinTemperature"] = temperature;  // Already in Celsius

    // ... send MQTT ...
}
```

---

## Testing Plan

### Unit Tests

1. **CRC-8 Validation**
   - Input: 0x0000 → Expected CRC: 0x81
   - Input: 0x7FFF → Expected CRC: ?
   - Input: 0xFFFF → Expected CRC: ?

2. **Temperature Conversion**
   - 0°C → 0x5999 → 0.0°C
   - 37.0°C → 0x9C5D → 37.0°C
   - 100.0°C → 0xD3F2 → 100.0°C

3. **Timing**
   - `startMeasurement()` → `isReady()` should return `false` for 8ms
   - `startMeasurement()` → wait 10ms → `isReady()` should return `true`

### Integration Tests

1. **Activity State Changes**
   - RESTING → temperature should be 36.1-36.7°C
   - EXERCISE → temperature should be 37.2-37.8°C
   - SLEEP → temperature should be 35.7-36.3°C

2. **MQTT Payload**
   - Verify `skinTemperature` field present
   - Verify value matches STS40 reading

### Clinical Validation

1. **Fever Detection**
   - Normal: 36.5-37.5°C
   - Low fever: 37.5-38.0°C
   - High fever: >38.0°C
   - Verify ±0.1°C accuracy sufficient for fever threshold

2. **Hypothermia Detection**
   - Mild: <35.0°C
   - Moderate: <32.0°C
   - Severe: <28.0°C

---

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Update Rate** | 1 Hz | Read temperature every 1 second |
| **Latency** | 9ms | High-precision mode conversion time |
| **Accuracy** | ±0.1°C | Simulated noise added |
| **Memory** | ~100 bytes | Small class, minimal state |
| **CPU** | <1% | Simple calculations |

---

## Future Enhancements (Phase 2)

### Enhancement 1: CRC Validation
Add option to intentionally corrupt data for testing:
```cpp
void injectError() {
    lastCRC = ~lastCRC;  // Flip all bits
}
```

### Enhancement 2: Serial Number Tracking
Store calibration offset per serial number:
```cpp
float calibrationOffset;  // ±0.05°C adjustment
```

### Enhancement 3: I2C Error Simulation
```cpp
bool simulateNACK = false;  // Simulate device not responding
```

---

## Summary

**STS40 Simulator**:
- ✅ Simplest sensor (LOW complexity)
- ✅ Validates architecture pattern (gets state from PhysiologicalSimulator)
- ✅ Medical-grade accuracy (±0.1°C)
- ✅ CRC-8 data integrity
- ✅ Realistic timing (9ms conversion)
- ✅ Ready for implementation (all details documented)

**Estimated Implementation Time**: 2 hours
**Files**: `STS40Simulator.h`, `STS40Simulator.cpp`
**Lines of Code**: ~200 lines total

**Next**: Implement MAX86178 (PPG + BioZ + Green LED) - MEDIUM complexity
