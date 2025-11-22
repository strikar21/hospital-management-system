/**
 * MAX86178Simulator.h
 *
 * Simulates Maxim MAX86178 3-LED PPG + BioZ AFE
 *
 * Hardware Specifications:
 * - 3 LEDs: Red (660nm), Green (537nm), IR (880nm)
 * - 20-bit ADC resolution
 * - Sample rate: 100 Hz (10ms period)
 * - I2C Address: 0x57
 * - Green LED: Critical for equitable healthcare (works on all skin tones)
 *
 * Capabilities:
 * - Heart Rate (from green LED PPG)
 * - SpO2 (from red + IR LEDs)
 * - Perfusion Index (AC/DC ratio for sepsis detection)
 * - Bioimpedance (respiratory rate)
 * - Proximity Detection (watch worn status)
 *
 * Integration:
 * - Reads HR, SpO2 from PhysiologicalSimulator
 * - Generates realistic PPG waveforms
 * - Simulates hardware features (FIFO, interrupts)
 */

#ifndef MAX86178_SIMULATOR_H
#define MAX86178_SIMULATOR_H

#include <Arduino.h>
#include "PhysiologicalSimulator.h"

class MAX86178Simulator {
public:
    // ===== LED Mode Configuration =====
    enum LEDMode {
        MODE_RED_IR,      // 2-LED SpO2 (traditional)
        MODE_GREEN,       // Green LED HR only (best for dark skin)
        MODE_MULTI        // All 3 LEDs (multi-wavelength SpO2)
    };

    // ===== Constructor =====
    /**
     * @param physioSim Pointer to PhysiologicalSimulator (shared state)
     */
    MAX86178Simulator(PhysiologicalSimulator* physioSim);

    // ===== Initialization =====
    /**
     * Initialize MAX86178 simulator
     * - Set I2C address to 0x57
     * - Configure default LED mode (MODE_MULTI)
     * - Enable all LEDs
     * - Start 100 Hz sampling
     */
    void begin();

    // ===== Configuration =====
    /**
     * Set LED operation mode
     * @param mode MODE_RED_IR, MODE_GREEN, or MODE_MULTI
     */
    void setLEDMode(LEDMode mode);

    /**
     * Get current LED mode
     * @return Current LEDMode
     */
    LEDMode getLEDMode();

    // ===== Update =====
    /**
     * Call this every 10ms (100 Hz) to update PPG samples
     * Generates new PPG waveform points
     */
    void update();

    // ===== Raw PPG Samples =====
    /**
     * Get latest green LED PPG sample (20-bit)
     * Best for heart rate on all skin tones
     * @return 20-bit ADC value (0 to 1048575)
     */
    int32_t getGreenSample();

    /**
     * Get latest red LED PPG sample (20-bit)
     * Used for SpO2 calculation
     * @return 20-bit ADC value (0 to 1048575)
     */
    int32_t getRedSample();

    /**
     * Get latest IR LED PPG sample (20-bit)
     * Used for SpO2 calculation
     * @return 20-bit ADC value (0 to 1048575)
     */
    int32_t getIRSample();

    // ===== Derived Vitals =====
    /**
     * Get heart rate from green LED PPG
     * Uses peak detection on buffered samples
     * @return Heart rate in BPM (40-200)
     */
    int getHeartRate();

    /**
     * Get SpO2 from red + IR ratio
     * @return SpO2 percentage (70-100%)
     */
    int getSpO2();

    /**
     * Get respiratory rate from bioimpedance
     * @return Respiratory rate in breaths/min (8-30)
     */
    int getRespiratoryRate();

    // ===== Advanced Features =====
    /**
     * Get perfusion index (AC/DC ratio)
     * Critical for sepsis/shock detection
     * @return Perfusion index (0.0-20.0%)
     *         < 0.5% = shock/sepsis (CRITICAL)
     *         0.5-1.5% = poor perfusion
     *         > 1.5% = normal
     */
    float getPerfusionIndex();

    /**
     * Check if watch is worn (proximity detection)
     * @return true if watch detects skin contact
     */
    bool isWatchWorn();

    /**
     * Get bioimpedance measurement
     * Used for respiratory rate calculation
     * @return Impedance in Ohms (20-50Ω typical)
     */
    float getBioimpedance();

    // ===== Diagnostic Methods =====
    /**
     * Get I2C address
     * @return 0x57 (MAX86178 address)
     */
    uint8_t getI2CAddress();

    /**
     * Get sample rate
     * @return Sample rate in Hz (100)
     */
    int getSampleRate();

private:
    // ===== References =====
    PhysiologicalSimulator* physio;  // Shared physiological state

    // ===== State =====
    LEDMode currentMode;             // Current LED mode
    unsigned long lastUpdateTime;    // For 100 Hz timing
    float ppgPhase;                  // Phase accumulator for PPG waveform

    // ===== Latest Samples =====
    int32_t greenSample;             // Latest green LED sample (20-bit)
    int32_t redSample;               // Latest red LED sample (20-bit)
    int32_t irSample;                // Latest IR LED sample (20-bit)

    // ===== Sample Buffers (for HR detection) =====
    static const int BUFFER_SIZE = 32;  // 320ms window @ 100 Hz
    int32_t greenBuffer[BUFFER_SIZE];
    int32_t redBuffer[BUFFER_SIZE];
    int32_t irBuffer[BUFFER_SIZE];
    int bufferIndex;

    // ===== Cached Vitals =====
    int cachedHeartRate;             // Latest HR from peak detection
    int cachedSpO2;                  // Latest SpO2 from ratio
    int cachedRespiratoryRate;       // Latest RR from BioZ
    float cachedPerfusionIndex;      // Latest PI
    bool cachedWatchWorn;            // Latest proximity status

    // ===== Constants =====
    static const uint8_t I2C_ADDRESS = 0x57;
    static const int SAMPLE_RATE_HZ = 100;
    static const int UPDATE_PERIOD_MS = 10;

    // PPG baseline values (20-bit ADC)
    static const int32_t PPG_BASELINE = 500000;      // DC component
    static const int32_t PPG_MAX = 1048575;          // 20-bit max

    // ===== Private Methods =====

    /**
     * Generate green LED PPG sample
     * Best for HR on all skin tones (2.5× better on dark skin)
     * @return 20-bit ADC sample
     */
    int32_t generateGreenPPG();

    /**
     * Generate red LED PPG sample
     * Used for SpO2 (660nm absorption)
     * @return 20-bit ADC sample
     */
    int32_t generateRedPPG();

    /**
     * Generate IR LED PPG sample
     * Used for SpO2 (880nm absorption)
     * @return 20-bit ADC sample
     */
    int32_t generateIRPPG();

    /**
     * Detect heart rate from PPG buffer using peak detection
     * @param buffer Sample buffer (32 samples)
     * @return Heart rate in BPM
     */
    int detectHeartRatePPG(int32_t* buffer);

    /**
     * Calculate SpO2 from red/IR ratio
     * Formula: SpO2 = 110 - 25 * R
     * where R = (AC_red / DC_red) / (AC_ir / DC_ir)
     *
     * @param redAC Red LED AC component
     * @param redDC Red LED DC component
     * @param irAC IR LED AC component
     * @param irDC IR LED DC component
     * @return SpO2 percentage (70-100)
     */
    int calculateSpO2(float redAC, float redDC, float irAC, float irDC);

    /**
     * Calculate perfusion index from PPG buffer
     * PI = (AC / DC) * 100%
     *
     * @param buffer Sample buffer
     * @return Perfusion index (0-20%)
     */
    float calculatePerfusionIndex(int32_t* buffer);

    /**
     * Generate bioimpedance measurement
     * Simulates thoracic impedance for respiratory monitoring
     * @return Impedance in Ohms (varies with breathing)
     */
    float generateBioimpedance();

    /**
     * Simulate proximity detection
     * Detects if watch is worn (skin contact)
     * @return true if watch is on wrist
     */
    bool detectProximity();

    /**
     * Add realistic PPG noise
     * Motion artifact, ambient light, etc.
     * @param sample Input sample
     * @return Sample with added noise
     */
    int32_t addPPGNoise(int32_t sample);
};

#endif // MAX86178_SIMULATOR_H
