/**
 * BatteryManager.cpp
 * Hospital Watch Battery Monitoring Implementation
 */

#include "BatteryManager.h"

BatteryManager::BatteryManager()
    : adcPin(4),
      voltageDividerRatio(2.0),
      initialized(false) {
}

void BatteryManager::init(uint8_t pin, float ratio) {
    adcPin = pin;
    voltageDividerRatio = ratio;

    // Configure ADC pin
    pinMode(adcPin, INPUT);

    // ESP32-S3 ADC configuration
    analogReadResolution(12);  // 12-bit resolution (0-4095)
    analogSetAttenuation(ADC_11db);  // 0-3.3V range

    initialized = true;
    Serial.printf("✅ BatteryManager initialized (ADC pin: %d, ratio: %.2f)\n", adcPin, ratio);
}

uint16_t BatteryManager::readVoltage() {
    if (!initialized) {
        Serial.println("⚠️  BatteryManager not initialized");
        return 0;
    }

    // Read ADC value (0-4095 for 12-bit)
    uint16_t adcValue = analogRead(adcPin);

    // Convert to voltage (ESP32-S3 ADC: 0-3.3V)
    // ADC reading → voltage (mV) = (adcValue / 4095) * 3300
    float adcVoltage = (adcValue / 4095.0) * 3300.0;

    // Apply voltage divider ratio to get actual battery voltage
    uint16_t batteryVoltage = (uint16_t)(adcVoltage * voltageDividerRatio);

    return batteryVoltage;
}

uint8_t BatteryManager::getBatteryPercentage() {
    uint16_t voltage = readVoltage();
    return voltageToPercentage(voltage);
}

bool BatteryManager::isCharging() {
    // TODO: Implement charging detection via GPIO pin monitoring
    // For now, assume not charging if we can read voltage
    // Real implementation would check USB VBUS detection pin
    return false;
}

bool BatteryManager::isLow() {
    uint16_t voltage = readVoltage();
    return voltage < VOLTAGE_LOW;
}

bool BatteryManager::isCritical() {
    uint16_t voltage = readVoltage();
    return voltage < VOLTAGE_CRITICAL;
}

uint8_t BatteryManager::voltageToPercentage(uint16_t voltage) {
    // LiPo discharge curve is non-linear
    // Use piecewise linear approximation:
    // 4.2V - 3.7V: 100% - 50% (top half, slow discharge)
    // 3.7V - 3.0V: 50% - 0% (bottom half, fast discharge)

    if (voltage >= VOLTAGE_FULL) {
        return 100;
    } else if (voltage <= VOLTAGE_EMPTY) {
        return 0;
    } else if (voltage >= VOLTAGE_NOMINAL) {
        // Top half: 3.7V-4.2V = 50%-100%
        // Map 3700-4200 → 50-100
        return 50 + ((voltage - VOLTAGE_NOMINAL) * 50) / (VOLTAGE_FULL - VOLTAGE_NOMINAL);
    } else {
        // Bottom half: 3.0V-3.7V = 0%-50%
        // Map 3000-3700 → 0-50
        return ((voltage - VOLTAGE_EMPTY) * 50) / (VOLTAGE_NOMINAL - VOLTAGE_EMPTY);
    }
}
