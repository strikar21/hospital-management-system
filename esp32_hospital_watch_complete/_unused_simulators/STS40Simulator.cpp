/**
 * STS40Simulator.cpp
 *
 * Implementation of STS40 temperature sensor simulator
 */

#include "STS40Simulator.h"

// ===== Constructor =====
STS40Simulator::STS40Simulator(PhysiologicalSimulator* physioSim) {
    physio = physioSim;
    measurementStartTime = 0;
    measurementInProgress = false;
    currentTemperature = 37.0;  // Default body temperature
}

// ===== Initialization =====
void STS40Simulator::begin() {
    Serial.println("[STS40] Temperature sensor initialized");
    Serial.print("[STS40] I2C Address: 0x");
    Serial.println(I2C_ADDRESS, HEX);
    Serial.print("[STS40] Conversion Time: ");
    Serial.print(CONVERSION_TIME_MS);
    Serial.println(" ms");
}

// ===== Measurement Control =====
void STS40Simulator::startMeasurement() {
    measurementStartTime = millis();
    measurementInProgress = true;

    // Get temperature from PhysiologicalSimulator
    currentTemperature = physio->getTemperature();

    // Add sensor noise (±0.05°C for realism)
    currentTemperature = addSensorNoise(currentTemperature);
}

bool STS40Simulator::isReady() {
    if (!measurementInProgress) {
        return false;
    }

    unsigned long elapsed = millis() - measurementStartTime;
    return (elapsed >= CONVERSION_TIME_MS);
}

float STS40Simulator::readTemperature() {
    if (!isReady()) {
        // Measurement not ready, return cached value
        return currentTemperature;
    }

    // Mark measurement complete
    measurementInProgress = false;

    return currentTemperature;
}

void STS40Simulator::readRaw(uint16_t& rawValue, uint8_t& crc) {
    // Convert current temperature to raw counts
    rawValue = temperatureToCounts(currentTemperature);

    // Calculate CRC-8 checksum
    crc = calculateCRC(rawValue);
}

// ===== Diagnostic Methods =====
uint8_t STS40Simulator::getI2CAddress() {
    return I2C_ADDRESS;
}

uint8_t STS40Simulator::getConversionTime() {
    return CONVERSION_TIME_MS;
}

bool STS40Simulator::verifyCRC(uint16_t rawValue, uint8_t receivedCRC) {
    uint8_t calculatedCRC = calculateCRC(rawValue);
    return (calculatedCRC == receivedCRC);
}

// ===== Private Methods =====

uint8_t STS40Simulator::calculateCRC(uint16_t value) {
    // CRC-8 calculation per STS40 datasheet
    // Polynomial: 0x31 (x^8 + x^5 + x^4 + 1)
    // Initialization: 0xFF
    // Final XOR: 0x00

    uint8_t data[2];
    data[0] = (value >> 8) & 0xFF;  // MSB
    data[1] = value & 0xFF;         // LSB

    uint8_t crc = 0xFF;  // Initial value

    for (int i = 0; i < 2; i++) {
        crc ^= data[i];

        for (int bit = 0; bit < 8; bit++) {
            if (crc & 0x80) {
                crc = (crc << 1) ^ CRC_POLYNOMIAL;
            } else {
                crc = crc << 1;
            }
        }
    }

    return crc;
}

uint16_t STS40Simulator::temperatureToCounts(float tempC) {
    // Formula from STS40 datasheet:
    // rawValue = (T + 45) * 65535 / 175
    //
    // Temperature range: -40°C to +125°C
    // Raw value range: 0 to 65535

    // Clamp to sensor range
    tempC = constrain(tempC, -40.0, 125.0);

    // Convert to counts
    float rawFloat = (tempC + 45.0) * 65535.0 / 175.0;
    uint16_t rawValue = (uint16_t)rawFloat;

    return rawValue;
}

float STS40Simulator::countsToTemperature(uint16_t counts) {
    // Formula from STS40 datasheet:
    // T = -45 + 175 * (rawValue / 65535)

    float tempC = -45.0 + 175.0 * ((float)counts / 65535.0);

    return tempC;
}

float STS40Simulator::addSensorNoise(float temp) {
    // STS40 accuracy: ±0.1°C (0-65°C range)
    // Add realistic noise: ±0.05°C (half of max error)

    float noise = (random(-50, 51) / 1000.0);  // -0.05 to +0.05°C
    return temp + noise;
}
