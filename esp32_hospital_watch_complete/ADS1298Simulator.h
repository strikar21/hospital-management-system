/**
 * ADS1298Simulator.h
 *
 * Simulates TI ADS1298 8-Channel 24-Bit ECG/EEG ADC
 *
 * Hardware Specifications:
 * - 8 differential input channels (simultaneous sampling)
 * - 24-bit resolution (±8.4 million counts)
 * - Sample rate: 250 to 32,000 SPS (we use 500 Hz for ECG/EEG)
 * - Input range: ±2.4V / gain
 * - SPI interface (Mode 1)
 * - Lead-off detection per channel
 * - Pacemaker pulse rejection
 *
 * Integration:
 * - Wraps PhysiologicalSimulator's ECG/EEG waveform generation
 * - Adds realistic ADC behavior (24-bit format, noise, lead-off)
 * - Simulates ADS1298 registers and SPI protocol
 * - This is the ONLY sensor responsible for ECG/EEG waveforms
 *
 * Architecture:
 * - COMPOSITION, not replacement
 * - PhysiologicalSimulator generates waveforms
 * - ADS1298Simulator adds hardware abstraction layer
 */

#ifndef ADS1298_SIMULATOR_H
#define ADS1298_SIMULATOR_H

#include <Arduino.h>
#include "PhysiologicalSimulator.h"

class ADS1298Simulator {
public:
    // ===== Constructor =====
    /**
     * @param physioSim Pointer to PhysiologicalSimulator (shared state)
     */
    ADS1298Simulator(PhysiologicalSimulator* physioSim);

    // ===== Initialization =====
    /**
     * Initialize ADS1298 simulator
     * - Set default register values (500 Hz, gain=6, all channels enabled)
     * - Configure lead-off detection
     * - Start internal sample timer
     */
    void begin();

    // ===== Configuration =====
    /**
     * Set waveform mode (ECG or EEG)
     * @param mode WaveformMode (from PhysiologicalSimulator)
     */
    void setWaveformMode(PhysiologicalSimulator::WaveformMode mode);

    /**
     * Enable/disable specific channel
     * @param channel Channel number (1-8)
     * @param enabled true to enable, false to power down
     */
    void setChannelEnabled(uint8_t channel, bool enabled);

    /**
     * Set channel gain
     * @param channel Channel number (1-8)
     * @param gain Gain value (1, 2, 3, 4, 6, 8, or 12)
     */
    void setChannelGain(uint8_t channel, uint8_t gain);

    /**
     * Enable/disable lead-off detection for channel
     * @param channel Channel number (1-8)
     * @param enabled true to enable lead-off detection
     */
    void setLeadOffDetection(uint8_t channel, bool enabled);

    // ===== Data Acquisition =====
    /**
     * Call this every 2ms (500 Hz) to update ADC samples
     * Reads from PhysiologicalSimulator and converts to 24-bit ADC format
     */
    void update();

    /**
     * Check if new data is ready (DRDY pin simulation)
     * @return true if DRDY is LOW (data ready)
     */
    bool isDataReady();

    /**
     * Read raw 24-bit ADC samples for all channels
     * Clears DRDY flag after read
     *
     * @param samples Array[8] to fill with 24-bit signed samples
     *                Range: -8388608 to +8388607
     */
    void readChannelData(int32_t samples[8]);

    /**
     * Read single channel sample
     * @param channel Channel number (1-8)
     * @return 24-bit signed ADC value (-8388608 to +8388607)
     */
    int32_t readChannel(uint8_t channel);

    // ===== Lead-Off Detection =====
    /**
     * Get lead-off status for channel
     * @param channel Channel number (1-8)
     * @return true if electrode is disconnected
     */
    bool isLeadOff(uint8_t channel);

    /**
     * Get lead-off status for all channels
     * @return 8-bit mask (bit 0 = CH1, bit 7 = CH8)
     */
    uint8_t getLeadOffStatus();

    // ===== SPI Simulation =====
    /**
     * Write to ADS1298 register (SPI command simulation)
     * @param regAddr Register address (0x00-0x17)
     * @param value Byte to write
     */
    void writeRegister(uint8_t regAddr, uint8_t value);

    /**
     * Read from ADS1298 register (SPI command simulation)
     * @param regAddr Register address (0x00-0x17)
     * @return Register value
     */
    uint8_t readRegister(uint8_t regAddr);

    /**
     * Send SPI command (WAKEUP, STANDBY, RESET, START, STOP, etc.)
     * @param cmd Command byte (0x02-0x0A)
     */
    void sendCommand(uint8_t cmd);

    // ===== Diagnostic Methods =====
    /**
     * Get current sample rate
     * @return Sample rate in Hz (250, 500, 1000, 2000, etc.)
     */
    int getSampleRate();

    /**
     * Check if ADS1298 is in conversion mode
     * @return true if START command sent and acquiring data
     */
    bool isRunning();

    /**
     * Get number of samples collected since begin()
     * @return Sample count (for debugging)
     */
    unsigned long getSampleCount();

private:
    // ===== References =====
    PhysiologicalSimulator* physio;  // Shared physiological state

    // ===== Register Map =====
    uint8_t registers[24];  // ADS1298 register array (0x00-0x17)

    // ===== State =====
    bool dataReady;               // DRDY pin state
    bool running;                 // Conversion mode active
    unsigned long lastSampleTime; // For 500 Hz timing
    unsigned long sampleCount;    // Total samples collected

    // ===== Channel Configuration =====
    bool channelEnabled[8];       // CH1-CH8 enabled flags
    uint8_t channelGain[8];       // Gain per channel (1,2,3,4,6,8,12)
    bool leadOffEnabled[8];       // Lead-off detection per channel
    bool leadOffStatus[8];        // Lead-off detected per channel

    // ===== ADC Data Buffers =====
    int32_t adcSamples[8];        // Latest 24-bit samples (CH1-CH8)

    // ===== Waveform Mode =====
    PhysiologicalSimulator::WaveformMode currentMode;  // MODE_ECG or MODE_EEG

    // ===== Constants =====
    static const uint8_t DEVICE_ID = 0x92;  // ADS1298 ID register value
    static const int DEFAULT_SAMPLE_RATE = 500;  // Hz

    // ADC resolution: 24-bit signed
    static const int32_t ADC_MAX = 8388607;   // 2^23 - 1
    static const int32_t ADC_MIN = -8388608;  // -2^23

    // Reference voltage
    static constexpr float VREF = 2.4;  // Volts

    // ===== SPI Command Opcodes =====
    static const uint8_t CMD_WAKEUP  = 0x02;
    static const uint8_t CMD_STANDBY = 0x04;
    static const uint8_t CMD_RESET   = 0x06;
    static const uint8_t CMD_START   = 0x08;
    static const uint8_t CMD_STOP    = 0x0A;

    // ===== Register Addresses =====
    static const uint8_t REG_ID       = 0x00;
    static const uint8_t REG_CONFIG1  = 0x01;
    static const uint8_t REG_CONFIG2  = 0x02;
    static const uint8_t REG_CONFIG3  = 0x03;
    static const uint8_t REG_LOFF     = 0x04;
    static const uint8_t REG_CH1SET   = 0x05;
    static const uint8_t REG_CH8SET   = 0x0C;
    static const uint8_t REG_LOFF_SENSP = 0x0F;
    static const uint8_t REG_LOFF_SENSN = 0x10;
    static const uint8_t REG_LOFF_STATP = 0x12;
    static const uint8_t REG_LOFF_STATN = 0x13;

    // ===== Private Methods =====

    /**
     * Generate new ADC samples from PhysiologicalSimulator
     * Called internally by update() every 2ms
     */
    void generateSamples();

    /**
     * Convert float voltage to 24-bit ADC counts
     * Formula: ADC = voltage / (VREF * 2 / gain) * 2^23
     *
     * @param voltage Input voltage in volts (-2.4V to +2.4V)
     * @param gain Channel gain (1, 2, 3, 4, 6, 8, or 12)
     * @return 24-bit signed ADC value
     */
    int32_t voltageToADC(float voltage, uint8_t gain);

    /**
     * Convert 24-bit ADC counts to float voltage
     * @param adcValue 24-bit signed ADC value
     * @param gain Channel gain (1, 2, 3, 4, 6, 8, or 12)
     * @return Voltage in volts
     */
    float adcToVoltage(int32_t adcValue, uint8_t gain);

    /**
     * Update lead-off detection status
     * Simulates DC current lead-off detection
     */
    void updateLeadOffDetection();

    /**
     * Simulate pacemaker pulse removal
     * Removes 2ms spikes > 200mV from signal
     * @param sample Input ADC sample
     * @return Filtered sample (spike removed)
     */
    int32_t removePacemakerPulse(int32_t sample);

    /**
     * Parse CONFIG1 register to get sample rate
     * @return Sample rate in Hz
     */
    int parseSampleRate();

    /**
     * Initialize default register values
     * Called by begin()
     */
    void initializeRegisters();
};

#endif // ADS1298_SIMULATOR_H
