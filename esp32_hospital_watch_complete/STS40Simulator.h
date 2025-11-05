/**
 * STS40Simulator.h
 *
 * Simulates Sensirion STS40 High-Accuracy Temperature Sensor
 *
 * Hardware Specifications:
 * - Accuracy: ±0.1°C (0-65°C)
 * - Resolution: 0.01°C
 * - I2C Address: 0x44
 * - Conversion Time: 9ms (high precision)
 * - CRC-8 Checksum: Polynomial 0x31
 *
 * Integration:
 * - Reads temperature from PhysiologicalSimulator
 * - Adds realistic hardware behavior (timing, CRC, I2C format)
 * - Simulates sensor registers and conversion delays
 */

#ifndef STS40_SIMULATOR_H
#define STS40_SIMULATOR_H

#include <Arduino.h>
#include "PhysiologicalSimulator.h"

class STS40Simulator {
public:
    // ===== Constructor =====
    /**
     * @param physioSim Pointer to PhysiologicalSimulator (shared state)
     */
    STS40Simulator(PhysiologicalSimulator* physioSim);

    // ===== Initialization =====
    /**
     * Initialize STS40 simulator
     * - Set I2C address to 0x44
     * - Prepare for measurements
     */
    void begin();

    // ===== Measurement Control =====
    /**
     * Start temperature conversion (high precision mode)
     * Simulates I2C command: 0xFD (measure high precision)
     * Conversion takes 9ms
     */
    void startMeasurement();

    /**
     * Check if measurement is ready
     * @return true if 9ms have elapsed since startMeasurement()
     */
    bool isReady();

    /**
     * Read temperature in Celsius
     * @return Temperature in °C (with ±0.1°C accuracy)
     */
    float readTemperature();

    /**
     * Read raw temperature data with CRC (simulates I2C read)
     * @param rawValue 16-bit raw temperature value (0-65535)
     * @param crc CRC-8 checksum (polynomial 0x31)
     */
    void readRaw(uint16_t& rawValue, uint8_t& crc);

    // ===== Diagnostic Methods =====
    /**
     * Get I2C address
     * @return 0x44 (STS40 address)
     */
    uint8_t getI2CAddress();

    /**
     * Get conversion time
     * @return Conversion time in milliseconds (9ms)
     */
    uint8_t getConversionTime();

    /**
     * Verify CRC checksum
     * @param rawValue 16-bit data
     * @param receivedCRC CRC byte to verify
     * @return true if CRC matches
     */
    bool verifyCRC(uint16_t rawValue, uint8_t receivedCRC);

private:
    // ===== References =====
    PhysiologicalSimulator* physio;  // Shared physiological state

    // ===== State =====
    unsigned long measurementStartTime;  // Time when startMeasurement() called
    bool measurementInProgress;          // Conversion in progress
    float currentTemperature;            // Latest temperature reading (°C)

    // ===== Constants =====
    static const uint8_t I2C_ADDRESS = 0x44;
    static const uint8_t CONVERSION_TIME_MS = 9;  // High precision mode
    static const uint8_t CRC_POLYNOMIAL = 0x31;

    // ===== Private Methods =====

    /**
     * Calculate CRC-8 checksum (polynomial 0x31)
     * @param data 16-bit value to checksum
     * @return CRC-8 byte
     */
    uint8_t calculateCRC(uint16_t value);

    /**
     * Convert temperature (°C) to raw 16-bit counts
     * Formula from STS40 datasheet:
     * rawValue = (tempC + 45) * 65535 / 175
     *
     * @param tempC Temperature in Celsius
     * @return 16-bit raw value (0-65535)
     */
    uint16_t temperatureToCounts(float tempC);

    /**
     * Convert raw 16-bit counts to temperature (°C)
     * Formula from STS40 datasheet:
     * tempC = -45 + 175 * (rawValue / 65535)
     *
     * @param counts 16-bit raw value (0-65535)
     * @return Temperature in Celsius
     */
    float countsToTemperature(uint16_t counts);

    /**
     * Add simulated sensor noise (±0.05°C)
     * Simulates real-world sensor variation
     *
     * @param temp Input temperature
     * @return Temperature with added noise
     */
    float addSensorNoise(float temp);
};

#endif // STS40_SIMULATOR_H
