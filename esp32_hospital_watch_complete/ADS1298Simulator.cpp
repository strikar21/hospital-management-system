/**
 * ADS1298Simulator.cpp
 *
 * Implementation of ADS1298 8-channel 24-bit ECG/EEG ADC simulator
 */

#include "ADS1298Simulator.h"

// ===== Constructor =====
ADS1298Simulator::ADS1298Simulator(PhysiologicalSimulator* physioSim) {
    physio = physioSim;
    dataReady = false;
    running = false;
    lastSampleTime = 0;
    sampleCount = 0;
    currentMode = PhysiologicalSimulator::MODE_ECG;

    // Initialize channel arrays
    for (int i = 0; i < 8; i++) {
        channelEnabled[i] = true;
        channelGain[i] = 6;  // Default gain
        leadOffEnabled[i] = true;
        leadOffStatus[i] = false;
        adcSamples[i] = 0;
    }
}

// ===== Initialization =====
void ADS1298Simulator::begin() {
    // Initialize register map
    initializeRegisters();

    // Start conversion
    running = true;
    lastSampleTime = micros();

    Serial.println("[ADS1298] 8-Channel 24-Bit ECG/EEG ADC initialized");
    Serial.print("[ADS1298] Device ID: 0x");
    Serial.println(DEVICE_ID, HEX);
    Serial.print("[ADS1298] Sample Rate: ");
    Serial.print(getSampleRate());
    Serial.println(" Hz");
    Serial.println("[ADS1298] All 8 channels enabled");
    Serial.println("[ADS1298] Gain: 6 (±400mV input range)");
    Serial.println("[ADS1298] Lead-off detection enabled");
}

// ===== Configuration =====
void ADS1298Simulator::setWaveformMode(PhysiologicalSimulator::WaveformMode mode) {
    currentMode = mode;
    physio->setWaveformMode(mode);

    Serial.print("[ADS1298] Waveform Mode: ");
    if (mode == PhysiologicalSimulator::MODE_ECG) {
        Serial.println("ECG (8-lead)");
    } else {
        Serial.println("EEG (8-channel)");
    }
}

void ADS1298Simulator::setChannelEnabled(uint8_t channel, bool enabled) {
    if (channel < 1 || channel > 8) return;

    channelEnabled[channel - 1] = enabled;

    // Update CHnSET register (bit 7 = power down)
    uint8_t regAddr = REG_CH1SET + (channel - 1);
    if (enabled) {
        registers[regAddr] &= ~0x80;  // Clear bit 7 (power up)
    } else {
        registers[regAddr] |= 0x80;   // Set bit 7 (power down)
    }
}

void ADS1298Simulator::setChannelGain(uint8_t channel, uint8_t gain) {
    if (channel < 1 || channel > 8) return;

    // Map gain to register value
    uint8_t gainCode;
    switch (gain) {
        case 1:  gainCode = 0b000; break;
        case 2:  gainCode = 0b001; break;
        case 3:  gainCode = 0b010; break;
        case 4:  gainCode = 0b011; break;
        case 6:  gainCode = 0b100; break;  // Default
        case 8:  gainCode = 0b101; break;
        case 12: gainCode = 0b110; break;
        default: return;  // Invalid gain
    }

    channelGain[channel - 1] = gain;

    // Update CHnSET register (bits 4-6)
    uint8_t regAddr = REG_CH1SET + (channel - 1);
    registers[regAddr] = (registers[regAddr] & 0x8F) | (gainCode << 4);
}

void ADS1298Simulator::setLeadOffDetection(uint8_t channel, bool enabled) {
    if (channel < 1 || channel > 8) return;

    leadOffEnabled[channel - 1] = enabled;

    // Update LOFF_SENSP register (positive sense)
    if (enabled) {
        registers[REG_LOFF_SENSP] |= (1 << (channel - 1));
    } else {
        registers[REG_LOFF_SENSP] &= ~(1 << (channel - 1));
    }
}

// ===== Data Acquisition =====
void ADS1298Simulator::update() {
    if (!running) {
        return;  // Not in conversion mode
    }

    // PhysiologicalSimulator must be updated first (in main loop)
    // Generate new ADC samples at 500 Hz
    generateSamples();
}

bool ADS1298Simulator::isDataReady() {
    return dataReady;
}

void ADS1298Simulator::readChannelData(int32_t samples[8]) {
    if (!dataReady) {
        // No new data, return old samples
        memcpy(samples, adcSamples, sizeof(adcSamples));
        return;
    }

    // Copy latest samples
    memcpy(samples, adcSamples, sizeof(adcSamples));

    // Clear DRDY flag
    dataReady = false;
}

int32_t ADS1298Simulator::readChannel(uint8_t channel) {
    if (channel < 1 || channel > 8) return 0;
    return adcSamples[channel - 1];
}

// ===== Lead-Off Detection =====
bool ADS1298Simulator::isLeadOff(uint8_t channel) {
    if (channel < 1 || channel > 8) return false;
    return leadOffStatus[channel - 1];
}

uint8_t ADS1298Simulator::getLeadOffStatus() {
    uint8_t status = 0;
    for (int i = 0; i < 8; i++) {
        if (leadOffStatus[i]) {
            status |= (1 << i);
        }
    }
    return status;
}

// ===== SPI Simulation =====
void ADS1298Simulator::writeRegister(uint8_t regAddr, uint8_t value) {
    if (regAddr >= 0x00 && regAddr <= 0x17) {
        registers[regAddr] = value;

        // Special handling for specific registers
        if (regAddr == REG_CONFIG1) {
            // Sample rate changed, restart timer
        } else if (regAddr >= REG_CH1SET && regAddr <= REG_CH8SET) {
            // Update channel configuration
            uint8_t ch = regAddr - REG_CH1SET;  // 0-7
            channelEnabled[ch] = !(value & 0x80);  // Bit 7 = power down
            uint8_t gainCode = (value >> 4) & 0x07;  // Bits 4-6 = gain

            // Decode gain
            const uint8_t gainMap[] = {1, 2, 3, 4, 6, 8, 12, 1};
            channelGain[ch] = gainMap[gainCode];
        }
    }
}

uint8_t ADS1298Simulator::readRegister(uint8_t regAddr) {
    if (regAddr >= 0x00 && regAddr <= 0x17) {
        // Special case: LOFF_STATP/LOFF_STATN (lead-off status)
        if (regAddr == REG_LOFF_STATP || regAddr == REG_LOFF_STATN) {
            // Return current lead-off status
            uint8_t status = 0;
            for (int i = 0; i < 8; i++) {
                if (leadOffStatus[i]) {
                    status |= (1 << i);
                }
            }
            return status;
        }
        return registers[regAddr];
    }
    return 0x00;
}

void ADS1298Simulator::sendCommand(uint8_t cmd) {
    switch (cmd) {
        case CMD_WAKEUP:
            // Exit standby, resume conversions
            break;
        case CMD_STANDBY:
            // Enter low-power mode
            running = false;
            break;
        case CMD_RESET:
            // Reset all registers
            initializeRegisters();
            sampleCount = 0;
            break;
        case CMD_START:
            // Start continuous conversion
            running = true;
            lastSampleTime = micros();
            break;
        case CMD_STOP:
            // Stop conversion
            running = false;
            dataReady = false;
            break;
    }
}

// ===== Diagnostic Methods =====
int ADS1298Simulator::getSampleRate() {
    return parseSampleRate();
}

bool ADS1298Simulator::isRunning() {
    return running;
}

unsigned long ADS1298Simulator::getSampleCount() {
    return sampleCount;
}

// ===== Private Methods =====

void ADS1298Simulator::generateSamples() {
    // Check if it's time for next sample (500 Hz = 2ms period)
    unsigned long now = micros();
    if (now - lastSampleTime < 2000) {
        return;  // Not time yet
    }
    lastSampleTime = now;

    // Generate samples for all 8 channels
    for (int ch = 0; ch < 8; ch++) {
        if (!channelEnabled[ch]) {
            adcSamples[ch] = 0;
            continue;
        }

        // Get waveform sample from PhysiologicalSimulator
        int32_t rawSample;
        physio->generateECGSample(ch + 1, rawSample);  // Lead 1-8

        // rawSample is already in ADC counts from PhysiologicalSimulator
        // PhysiologicalSimulator uses gain=6 and generates 24-bit values
        // We need to apply our configured gain

        // Convert to voltage (assuming PhysiologicalSimulator uses gain=6)
        float voltage = adcToVoltage(rawSample, 6);

        // Re-convert with our configured gain
        int32_t adcValue = voltageToADC(voltage, channelGain[ch]);

        // Apply pacemaker pulse removal (if enabled)
        adcValue = removePacemakerPulse(adcValue);

        // Store sample
        adcSamples[ch] = adcValue;
    }

    // Update lead-off detection
    updateLeadOffDetection();

    // Set DRDY flag (data ready)
    dataReady = true;
    sampleCount++;
}

int32_t ADS1298Simulator::voltageToADC(float voltage, uint8_t gain) {
    // Clamp to input range
    float maxVoltage = VREF / gain;
    voltage = constrain(voltage, -maxVoltage, maxVoltage);

    // Convert to ADC counts
    // LSB size = (VREF * 2) / (gain * 2^24)
    float lsb = (VREF * 2.0) / (gain * 16777216.0);  // 2^24 = 16777216
    int32_t adcValue = (int32_t)(voltage / lsb);

    // Clamp to 24-bit range
    adcValue = constrain(adcValue, ADC_MIN, ADC_MAX);

    return adcValue;
}

float ADS1298Simulator::adcToVoltage(int32_t adcValue, uint8_t gain) {
    // Calculate LSB size
    float lsb = (VREF * 2.0) / (gain * 16777216.0);

    // Convert ADC counts to voltage
    float voltage = adcValue * lsb;

    return voltage;
}

void ADS1298Simulator::updateLeadOffDetection() {
    for (int ch = 0; ch < 8; ch++) {
        if (!leadOffEnabled[ch]) {
            leadOffStatus[ch] = false;
            continue;
        }

        // Simulate random lead-off events (1% probability per update)
        // In real hardware, this would be voltage threshold detection
        if (random(100) < 1) {
            leadOffStatus[ch] = true;
        } else {
            leadOffStatus[ch] = false;
        }

        // If lead is off, set ADC sample to rail value
        if (leadOffStatus[ch]) {
            adcSamples[ch] = ADC_MAX;  // Positive rail (lead off)
        }
    }

    // Update LOFF_STATP and LOFF_STATN registers
    uint8_t statusP = 0;
    uint8_t statusN = 0;
    for (int i = 0; i < 8; i++) {
        if (leadOffStatus[i]) {
            statusP |= (1 << i);  // Assume positive lead off
        }
    }
    registers[REG_LOFF_STATP] = statusP;
    registers[REG_LOFF_STATN] = statusN;
}

int32_t ADS1298Simulator::removePacemakerPulse(int32_t sample) {
    // ADS1298 has hardware pacemaker detection that removes 2ms spikes > 200mV
    // We simulate this by detecting large amplitude transients

    static int32_t prevSample[8] = {0};
    static int ch = 0;

    // Calculate derivative (change from previous sample)
    int32_t delta = abs(sample - prevSample[ch]);

    // If change > 200mV equivalent, this is a pacemaker spike
    int32_t threshold = abs(voltageToADC(0.2, 6));  // 200mV at gain=6

    if (delta > threshold) {
        // Replace with previous sample (removes spike)
        sample = prevSample[ch];
    }

    prevSample[ch] = sample;
    ch = (ch + 1) % 8;

    return sample;
}

int ADS1298Simulator::parseSampleRate() {
    uint8_t config1 = registers[REG_CONFIG1];
    uint8_t rate = config1 & 0x07;  // Bits 2-0

    // Sample rate lookup table
    const int rates[] = {
        32000,  // 000: High-resolution mode (32 kSPS)
        16000,  // 001: 16 kSPS
        8000,   // 010: 8 kSPS
        4000,   // 011: 4 kSPS
        2000,   // 100: 2 kSPS
        1000,   // 101: 1 kSPS
        500,    // 110: 500 SPS (WE USE THIS)
        250     // 111: 250 SPS
    };

    return rates[rate];
}

void ADS1298Simulator::initializeRegisters() {
    // ID register
    registers[REG_ID] = DEVICE_ID;  // 0x92 for ADS1298

    // CONFIG1: Sample rate = 500 Hz
    // Bit 7 = 0 (single-shot mode off)
    // Bits 2-0 = 110 (500 SPS)
    registers[REG_CONFIG1] = 0x06;

    // CONFIG2: Test signals off, internal reference
    // Bit 5 = 1 (internal reference buffer enabled)
    registers[REG_CONFIG2] = 0x20;

    // CONFIG3: Enable internal reference
    // Bit 7 = 1 (reference buffer enabled)
    registers[REG_CONFIG3] = 0xE0;

    // LOFF: Lead-off detection settings
    // Bits 2-4 = 010 (6 nA current)
    // Bit 0-1 = 00 (DC lead-off)
    registers[REG_LOFF] = 0x10;

    // CH1SET - CH8SET: All channels enabled, gain=6, normal input
    // Bit 7 = 0 (power up)
    // Bits 4-6 = 100 (gain=6)
    // Bits 0-2 = 000 (normal electrode input)
    for (int i = REG_CH1SET; i <= REG_CH8SET; i++) {
        registers[i] = 0x40;  // Gain=6, powered up, normal input
    }

    // LOFF_SENSP: Lead-off positive sense (all enabled)
    registers[REG_LOFF_SENSP] = 0xFF;

    // LOFF_SENSN: Lead-off negative sense (all enabled)
    registers[REG_LOFF_SENSN] = 0xFF;

    // LOFF_FLIP: Lead-off current direction (default)
    registers[0x11] = 0x00;

    // LOFF_STATP: Lead-off positive status (updated dynamically)
    registers[REG_LOFF_STATP] = 0x00;

    // LOFF_STATN: Lead-off negative status (updated dynamically)
    registers[REG_LOFF_STATN] = 0x00;
}
