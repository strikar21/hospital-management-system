/**
 * MAX86178Simulator.cpp
 *
 * Implementation of MAX86178 3-LED PPG + BioZ simulator
 */

#include "MAX86178Simulator.h"

// ===== Constructor =====
MAX86178Simulator::MAX86178Simulator(PhysiologicalSimulator* physioSim) {
    physio = physioSim;
    currentMode = MODE_MULTI;
    lastUpdateTime = 0;
    ppgPhase = 0.0;
    bufferIndex = 0;

    greenSample = PPG_BASELINE;
    redSample = PPG_BASELINE;
    irSample = PPG_BASELINE;

    cachedHeartRate = 75;
    cachedSpO2 = 98;
    cachedRespiratoryRate = 16;
    cachedPerfusionIndex = 2.5;
    cachedWatchWorn = true;

    // Initialize buffers
    for (int i = 0; i < BUFFER_SIZE; i++) {
        greenBuffer[i] = PPG_BASELINE;
        redBuffer[i] = PPG_BASELINE;
        irBuffer[i] = PPG_BASELINE;
    }
}

// ===== Initialization =====
void MAX86178Simulator::begin() {
    Serial.println("[MAX86178] 3-LED PPG + BioZ initialized");
    Serial.print("[MAX86178] I2C Address: 0x");
    Serial.println(I2C_ADDRESS, HEX);
    Serial.println("[MAX86178] LEDs: Red (660nm) + Green (537nm) + IR (880nm)");
    Serial.println("[MAX86178] Green LED enabled for equitable healthcare");
    Serial.print("[MAX86178] Sample Rate: ");
    Serial.print(SAMPLE_RATE_HZ);
    Serial.println(" Hz");
}

// ===== Configuration =====
void MAX86178Simulator::setLEDMode(LEDMode mode) {
    currentMode = mode;

    Serial.print("[MAX86178] LED Mode: ");
    switch (mode) {
        case MODE_RED_IR:
            Serial.println("Red + IR (traditional SpO2)");
            break;
        case MODE_GREEN:
            Serial.println("Green only (best HR on dark skin)");
            break;
        case MODE_MULTI:
            Serial.println("All 3 LEDs (multi-wavelength SpO2)");
            break;
    }
}

MAX86178Simulator::LEDMode MAX86178Simulator::getLEDMode() {
    return currentMode;
}

// ===== Update =====
void MAX86178Simulator::update() {
    unsigned long now = millis();

    // Check if it's time for next sample (100 Hz = 10ms period)
    if (now - lastUpdateTime < UPDATE_PERIOD_MS) {
        return;
    }
    lastUpdateTime = now;

    // Generate PPG samples based on current mode
    switch (currentMode) {
        case MODE_RED_IR:
            greenSample = PPG_BASELINE;  // Green LED off
            redSample = generateRedPPG();
            irSample = generateIRPPG();
            break;
        case MODE_GREEN:
            greenSample = generateGreenPPG();
            redSample = PPG_BASELINE;    // Red LED off
            irSample = PPG_BASELINE;     // IR LED off
            break;
        case MODE_MULTI:
            greenSample = generateGreenPPG();
            redSample = generateRedPPG();
            irSample = generateIRPPG();
            break;
    }

    // Store samples in buffers
    greenBuffer[bufferIndex] = greenSample;
    redBuffer[bufferIndex] = redSample;
    irBuffer[bufferIndex] = irSample;

    bufferIndex = (bufferIndex + 1) % BUFFER_SIZE;

    // Update cached vitals every 320ms (full buffer)
    if (bufferIndex == 0) {
        cachedHeartRate = detectHeartRatePPG(greenBuffer);

        // Calculate SpO2 from red/IR
        float redDC = PPG_BASELINE;
        float redAC = 15000;  // Typical AC amplitude
        float irDC = PPG_BASELINE;
        float irAC = 10000;
        cachedSpO2 = calculateSpO2(redAC, redDC, irAC, irDC);

        cachedPerfusionIndex = calculatePerfusionIndex(greenBuffer);
        cachedRespiratoryRate = physio->getRespiratoryRate();
        cachedWatchWorn = detectProximity();
    }
}

// ===== Raw PPG Samples =====
int32_t MAX86178Simulator::getGreenSample() {
    return greenSample;
}

int32_t MAX86178Simulator::getRedSample() {
    return redSample;
}

int32_t MAX86178Simulator::getIRSample() {
    return irSample;
}

// ===== Derived Vitals =====
int MAX86178Simulator::getHeartRate() {
    return cachedHeartRate;
}

int MAX86178Simulator::getSpO2() {
    return cachedSpO2;
}

int MAX86178Simulator::getRespiratoryRate() {
    return cachedRespiratoryRate;
}

// ===== Advanced Features =====
float MAX86178Simulator::getPerfusionIndex() {
    return cachedPerfusionIndex;
}

bool MAX86178Simulator::isWatchWorn() {
    return cachedWatchWorn;
}

float MAX86178Simulator::getBioimpedance() {
    return generateBioimpedance();
}

// ===== Diagnostic Methods =====
uint8_t MAX86178Simulator::getI2CAddress() {
    return I2C_ADDRESS;
}

int MAX86178Simulator::getSampleRate() {
    return SAMPLE_RATE_HZ;
}

// ===== Private Methods =====

int32_t MAX86178Simulator::generateGreenPPG() {
    // Green LED (537nm) PPG - BEST for heart rate on all skin tones
    // 2.5× better accuracy on dark skin (Fitzpatrick III-VI)

    float HR = physio->getHeartRate();
    float cycleDuration = 60.0 / HR;  // Seconds per beat

    ppgPhase += (UPDATE_PERIOD_MS / 1000.0) / cycleDuration;
    if (ppgPhase >= 1.0) ppgPhase -= 1.0;

    // Green LED has higher AC modulation (3-5%)
    float perfusion = 0.03;  // 3% modulation
    int32_t ppgAmplitude = PPG_BASELINE * perfusion;

    // Generate pulsatile waveform (systolic peak + dicrotic notch)
    float systolic = sin(ppgPhase * 2 * PI);
    float dicrotic = 0.3 * sin(ppgPhase * 2 * PI - PI/3);  // Dicrotic notch
    float pulsatile = ppgAmplitude * (systolic + dicrotic);

    int32_t sample = PPG_BASELINE + (int32_t)pulsatile;

    // Add noise
    sample = addPPGNoise(sample);

    // Clamp to 20-bit range
    sample = constrain(sample, 0, PPG_MAX);

    return sample;
}

int32_t MAX86178Simulator::generateRedPPG() {
    // Red LED (660nm) PPG - for SpO2 measurement
    // Higher absorption by oxygenated hemoglobin

    float HR = physio->getHeartRate();
    float SpO2 = physio->getOxygenSaturation();
    float cycleDuration = 60.0 / HR;

    ppgPhase += (UPDATE_PERIOD_MS / 1000.0) / cycleDuration;
    if (ppgPhase >= 1.0) ppgPhase -= 1.0;

    // Red LED AC modulation depends on SpO2
    float perfusion = 0.02 * (SpO2 / 100.0);  // 2% at 100% SpO2
    int32_t ppgAmplitude = PPG_BASELINE * perfusion;

    float pulsatile = ppgAmplitude * sin(ppgPhase * 2 * PI);

    int32_t sample = PPG_BASELINE + (int32_t)pulsatile;
    sample = addPPGNoise(sample);
    sample = constrain(sample, 0, PPG_MAX);

    return sample;
}

int32_t MAX86178Simulator::generateIRPPG() {
    // IR LED (880nm) PPG - for SpO2 measurement
    // Lower absorption by oxygenated hemoglobin

    float HR = physio->getHeartRate();
    float SpO2 = physio->getOxygenSaturation();
    float cycleDuration = 60.0 / HR;

    ppgPhase += (UPDATE_PERIOD_MS / 1000.0) / cycleDuration;
    if (ppgPhase >= 1.0) ppgPhase -= 1.0;

    // IR LED AC modulation (typically lower than red)
    float perfusion = 0.015 * (SpO2 / 100.0);  // 1.5% at 100% SpO2
    int32_t ppgAmplitude = PPG_BASELINE * perfusion;

    float pulsatile = ppgAmplitude * sin(ppgPhase * 2 * PI);

    int32_t sample = PPG_BASELINE + (int32_t)pulsatile;
    sample = addPPGNoise(sample);
    sample = constrain(sample, 0, PPG_MAX);

    return sample;
}

int MAX86178Simulator::detectHeartRatePPG(int32_t* buffer) {
    // Simple peak detection on PPG buffer
    // Count peaks in 320ms window (32 samples @ 100 Hz)

    int peakCount = 0;
    int32_t threshold = PPG_BASELINE + 5000;  // Above baseline

    bool inPeak = false;
    for (int i = 1; i < BUFFER_SIZE - 1; i++) {
        if (buffer[i] > threshold &&
            buffer[i] > buffer[i-1] &&
            buffer[i] > buffer[i+1]) {
            if (!inPeak) {
                peakCount++;
                inPeak = true;
            }
        } else {
            inPeak = false;
        }
    }

    // Convert to BPM (320ms window)
    // HR = (peaks / 0.32s) * 60s = peaks * 187.5
    int HR = peakCount * 188;

    // Sanity check
    if (HR < 40 || HR > 200) {
        HR = physio->getHeartRate();  // Fallback to physio sim
    }

    return HR;
}

int MAX86178Simulator::calculateSpO2(float redAC, float redDC, float irAC, float irDC) {
    // Ratio of ratios method
    // R = (AC_red / DC_red) / (AC_ir / DC_ir)

    float redRatio = redAC / redDC;
    float irRatio = irAC / irDC;

    float R = redRatio / irRatio;

    // Empirical formula: SpO2 = 110 - 25 * R
    int SpO2 = (int)(110.0 - 25.0 * R);

    // Clamp to valid range
    SpO2 = constrain(SpO2, 70, 100);

    return SpO2;
}

float MAX86178Simulator::calculatePerfusionIndex(int32_t* buffer) {
    // Perfusion Index = (AC / DC) * 100%
    // AC = peak-to-peak amplitude
    // DC = baseline (mean)

    // Calculate DC (mean)
    int64_t sum = 0;
    for (int i = 0; i < BUFFER_SIZE; i++) {
        sum += buffer[i];
    }
    float DC = (float)sum / BUFFER_SIZE;

    // Calculate AC (peak-to-peak / 2)
    int32_t maxVal = buffer[0];
    int32_t minVal = buffer[0];
    for (int i = 1; i < BUFFER_SIZE; i++) {
        if (buffer[i] > maxVal) maxVal = buffer[i];
        if (buffer[i] < minVal) minVal = buffer[i];
    }
    float AC = (maxVal - minVal) / 2.0;

    // Calculate Perfusion Index
    float perfusionIdx = (AC / DC) * 100.0;

    // Typical range: 0.3% to 20%
    // < 0.5% = shock/sepsis (CRITICAL)
    perfusionIdx = constrain(perfusionIdx, 0.0, 20.0);

    return perfusionIdx;
}

float MAX86178Simulator::generateBioimpedance() {
    // Thoracic bioimpedance for respiratory monitoring
    // Impedance changes with breathing (lung volume)

    int RR = physio->getRespiratoryRate();
    float breathCycle = 60.0 / RR;  // Seconds per breath

    static float breathPhase = 0.0;
    breathPhase += (UPDATE_PERIOD_MS / 1000.0) / breathCycle;
    if (breathPhase >= 1.0) breathPhase -= 1.0;

    // Baseline impedance: 25-35 Ohms
    float baselineZ = 30.0;

    // Modulation: ±2 Ohms with breathing
    float modulationZ = 2.0 * sin(breathPhase * 2 * PI);

    float impedance = baselineZ + modulationZ;

    return impedance;
}

bool MAX86178Simulator::detectProximity() {
    // Proximity detection - check if watch is worn
    // Real hardware uses LED reflection
    // We simulate 95% worn, 5% off (random removal)

    if (random(100) < 95) {
        return true;  // Watch worn
    } else {
        return false;  // Watch removed
    }
}

int32_t MAX86178Simulator::addPPGNoise(int32_t sample) {
    // Add realistic noise:
    // - Motion artifact (low frequency)
    // - Ambient light (DC offset)
    // - Electronic noise (white)

    // White noise: ±500 counts
    int32_t noise = random(-500, 501);

    // Motion artifact (simulate occasionally)
    if (random(100) < 5) {  // 5% chance
        noise += random(-2000, 2001);
    }

    return sample + noise;
}
