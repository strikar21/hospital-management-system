/**
 * BMI323Simulator.h
 *
 * Simulates Bosch BMI323 6-Axis IMU with Advanced Features
 *
 * Hardware Specifications:
 * - 3-axis 16-bit accelerometer (±2g/±4g/±8g/±16g)
 * - 3-axis 16-bit gyroscope (±125/±250/±500/±1000/±2000 dps)
 * - Sample rate: Up to 1600 Hz
 * - I2C Address: 0x68
 *
 * Built-in Features (Bosch algorithms):
 * - Step counter (pedometer)
 * - Tap/double-tap detection
 * - No-motion detection
 *
 * ESP32-Side Processing (We Implement):
 * - Tremor detection (FFT analysis, 4-12 Hz)
 * - Fall detection (state machine)
 * - Fall risk scoring (0-10 scale)
 *
 * Integration:
 * - Reads activity state from PhysiologicalSimulator
 * - Generates realistic motion patterns (walking, running, tremor)
 * - Simulates hardware interrupts and features
 */

#ifndef BMI323_SIMULATOR_H
#define BMI323_SIMULATOR_H

#include <Arduino.h>
#include "PhysiologicalSimulator.h"

class BMI323Simulator {
public:
    // ===== Activity State =====
    enum ActivityState {
        STILL,        // Stationary
        WALKING,      // Walking (100 steps/min)
        RUNNING,      // Running (>100 steps/min)
        FALL_DETECTED // Fall in progress (renamed from FALLING to avoid Arduino.h macro conflict)
    };

    // ===== Fall Detection States =====
    enum FallState {
        NORMAL,       // Normal activity
        FREEFALL,     // Detected freefall (< 0.5g)
        IMPACT,       // Detected impact (> 3g)
        LYING         // Lying still after fall (CRITICAL)
    };

    // ===== Constructor =====
    /**
     * @param physioSim Pointer to PhysiologicalSimulator (shared state)
     */
    BMI323Simulator(PhysiologicalSimulator* physioSim);

    // ===== Initialization =====
    /**
     * Initialize BMI323 simulator
     * - Set I2C address to 0x68
     * - Configure ±8g accelerometer range
     * - Configure ±2000 dps gyroscope range
     * - Enable step counter, tap detection
     * - Start 1600 Hz sampling
     */
    void begin();

    // ===== Update =====
    /**
     * Call this every ~0.6ms (1600 Hz) to update IMU samples
     * Generates accelerometer and gyroscope data
     */
    void update();

    // ===== Raw IMU Data =====
    /**
     * Read 3-axis accelerometer data (16-bit)
     * @param x X-axis acceleration (±8g range, 4096 LSB/g)
     * @param y Y-axis acceleration
     * @param z Z-axis acceleration (1g = gravity at rest)
     */
    void readAccel(int16_t& x, int16_t& y, int16_t& z);

    /**
     * Read 3-axis gyroscope data (16-bit)
     * @param x X-axis rotation rate (±2000 dps range, 16.4 LSB/dps)
     * @param y Y-axis rotation rate
     * @param z Z-axis rotation rate
     */
    void readGyro(int16_t& x, int16_t& y, int16_t& z);

    // ===== Built-in Features (Bosch Algorithms) =====
    /**
     * Get total step count since begin()
     * Uses Bosch built-in pedometer algorithm
     * @return Step count (0 to 2^32-1)
     */
    uint32_t getStepCount();

    /**
     * Check if double-tap was detected
     * Clears flag after read
     * @return true if double-tap interrupt occurred
     */
    bool detectDoubleTap();

    /**
     * Get time of last detected movement
     * Used for no-motion alerts (bedsore prevention)
     * @return Milliseconds since last movement
     */
    unsigned long getLastMovementTime();

    // ===== ESP32-Side Processing =====
    /**
     * Get tremor intensity (FFT-based, 4-12 Hz band)
     * @return Tremor intensity (0-10 scale)
     *         0 = no tremor
     *         1-3 = mild tremor
     *         4-6 = moderate tremor
     *         7-10 = severe tremor
     */
    float getTremorIntensity();

    /**
     * Get fall risk score
     * @return Fall risk (0-10 scale)
     *         0-3 = low risk
     *         4-6 = medium risk
     *         7-8 = high risk
     *         9-10 = CRITICAL (fall detected)
     */
    float getFallRisk();

    /**
     * Get fall risk category
     * @return "low", "medium", "high", or "critical"
     */
    String getFallRiskCategory();

    /**
     * Get current fall detection state
     * @return NORMAL, FREEFALL, IMPACT, or LYING
     */
    FallState getFallState();

    // ===== Activity Recognition =====
    /**
     * Set current activity state
     * @param state STILL, WALKING, RUNNING, or FALLING
     */
    void setActivity(ActivityState state);

    /**
     * Get current activity state
     * @return Current ActivityState
     */
    ActivityState getActivity();

    // ===== Diagnostic Methods =====
    /**
     * Get I2C address
     * @return 0x68 (BMI323 address)
     */
    uint8_t getI2CAddress();

    /**
     * Get sample rate
     * @return Sample rate in Hz (1600)
     */
    int getSampleRate();

private:
    // ===== References =====
    PhysiologicalSimulator* physio;  // Shared physiological state

    // ===== State =====
    ActivityState currentActivity;   // Current activity
    FallState fallState;             // Fall detection state
    unsigned long lastUpdateTime;    // For 1600 Hz timing
    unsigned long lastMovementTime;  // For no-motion detection

    // ===== Latest IMU Samples =====
    int16_t accelX, accelY, accelZ;  // Latest accelerometer (±8g, 4096 LSB/g)
    int16_t gyroX, gyroY, gyroZ;     // Latest gyroscope (±2000 dps, 16.4 LSB/dps)

    // ===== Motion Pattern State =====
    float motionPhase;               // Phase accumulator for periodic motion
    uint32_t stepCount;              // Pedometer count
    bool doubleTapFlag;              // Double-tap interrupt flag

    // ===== Tremor Analysis =====
    static const int FFT_SIZE = 128;
    float accelMagHistory[FFT_SIZE]; // Acceleration magnitude history for FFT
    int fftIndex;                    // Circular buffer index
    float currentTremorIntensity;    // Latest tremor intensity (0-10)

    // ===== Fall Detection =====
    unsigned long freefallStartTime; // When freefall detected
    unsigned long impactTime;        // When impact detected
    float currentFallRisk;           // Latest fall risk (0-10)

    // ===== Constants =====
    static const uint8_t I2C_ADDRESS = 0x68;
    static const int SAMPLE_RATE_HZ = 1600;
    static const int UPDATE_PERIOD_US = 625;  // 1/1600 Hz ≈ 625 µs

    // Accelerometer range: ±8g
    static const int ACCEL_RANGE_G = 8;
    static const int ACCEL_LSB_PER_G = 4096;  // 16-bit / 8g

    // Gyroscope range: ±2000 dps
    static const int GYRO_RANGE_DPS = 2000;
    static constexpr float GYRO_LSB_PER_DPS = 16.4;

    // ===== Private Methods =====

    /**
     * Generate accelerometer/gyro data for STILL state
     * Only gravity on Z-axis, minimal noise
     */
    void generateStillMotion();

    /**
     * Generate accelerometer/gyro data for WALKING state
     * Periodic vertical motion (heel strikes)
     * Frequency: ~1.67 Hz (100 steps/min)
     */
    void generateWalkingMotion();

    /**
     * Generate accelerometer/gyro data for RUNNING state
     * Similar to walking but higher amplitude and frequency
     */
    void generateRunningMotion();

    /**
     * Generate accelerometer/gyro data with tremor
     * Overlays 4-12 Hz oscillation on normal motion
     */
    void generateTremorMotion();

    /**
     * Update tremor analysis using FFT
     * Analyzes accelMagHistory[] for 4-12 Hz content
     */
    void updateTremorAnalysis();

    /**
     * Update fall detection state machine
     * NORMAL → FREEFALL → IMPACT → LYING
     */
    void updateFallDetection();

    /**
     * Detect lying orientation
     * Check if body is horizontal (fallen)
     * @return true if lying position detected
     */
    bool detectLyingOrientation();

    /**
     * Update step counter (Bosch algorithm simulation)
     * Detects heel strikes from accelerometer peaks
     */
    void updateStepCounter();

    /**
     * Detect tap/double-tap (Bosch algorithm simulation)
     * Looks for sharp acceleration transients
     */
    void updateTapDetection();

    /**
     * Add realistic IMU noise
     * White noise + temperature drift
     * @param sample Input sample
     * @return Sample with added noise
     */
    int16_t addIMUNoise(int16_t sample);

    /**
     * Simple FFT for tremor detection
     * Analyzes accelMagHistory[] and returns power in 4-12 Hz band
     * @return Tremor band power (arbitrary units)
     */
    float analyzeTremorFFT();
};

#endif // BMI323_SIMULATOR_H
