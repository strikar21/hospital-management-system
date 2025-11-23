/**
 * BatteryManager.h
 * Hospital Watch Battery Monitoring
 *
 * Monitors 3.7V lithium battery voltage via ADC
 * Calculates battery percentage using voltage curve
 *
 * Hardware: ESP32-S3-Touch-AMOLED-1.64
 * Battery: 3.7V Li-Po (MX1.25 connector)
 * ADC: GPIO pin for voltage divider reading
 */

#ifndef BATTERY_MANAGER_H
#define BATTERY_MANAGER_H

#include <Arduino.h>

class BatteryManager {
public:
    /**
     * Constructor
     */
    BatteryManager();

    /**
     * Initialize battery monitoring
     * @param adcPin GPIO pin connected to battery voltage divider
     * @param voltageDividerRatio Voltage divider ratio (e.g., 2.0 for 1:1 divider)
     */
    void init(uint8_t adcPin = 4, float voltageDividerRatio = 2.0);

    /**
     * Read current battery voltage
     * @return Voltage in millivolts (mV)
     */
    uint16_t readVoltage();

    /**
     * Get battery percentage (0-100%)
     * Uses LiPo discharge curve: 4.2V=100%, 3.7V=50%, 3.0V=0%
     * @return Battery percentage (0-100)
     */
    uint8_t getBatteryPercentage();

    /**
     * Check if battery is charging
     * @return true if USB connected and charging
     */
    bool isCharging();

    /**
     * Check if battery is low (< 20%)
     * @return true if battery below 20%
     */
    bool isLow();

    /**
     * Check if battery is critical (< 5%)
     * @return true if battery below 5%
     */
    bool isCritical();

private:
    uint8_t adcPin;
    float voltageDividerRatio;
    bool initialized;

    // LiPo voltage thresholds (in mV)
    static const uint16_t VOLTAGE_FULL = 4200;    // 4.2V = 100%
    static const uint16_t VOLTAGE_NOMINAL = 3700; // 3.7V = 50%
    static const uint16_t VOLTAGE_EMPTY = 3000;   // 3.0V = 0%
    static const uint16_t VOLTAGE_CRITICAL = 3200; // 3.2V = 5%
    static const uint16_t VOLTAGE_LOW = 3400;     // 3.4V = 20%

    /**
     * Convert voltage to percentage using LiPo discharge curve
     * @param voltage Voltage in millivolts
     * @return Percentage (0-100)
     */
    uint8_t voltageToPercentage(uint16_t voltage);
};

#endif // BATTERY_MANAGER_H
