/*
 * Physiological Simulator Implementation
 * Generates realistic human vital signs and ECG waveforms
 */

#include "PhysiologicalSimulator.h"

// Constructor
PhysiologicalSimulator::PhysiologicalSimulator() {
    currentState = RESTING;
    stateStartTime = 0;
    stateDuration = 300000;  // 5 minutes per state (demo mode)

    // Initialize vitals to resting state defaults
    currentHeartRate = 72.0;
    targetHeartRate = 72.0;
    currentRespRate = 14.0;
    targetRespRate = 14.0;
    currentTemp = 97.5;  // Fahrenheit
    targetTemp = 97.5;
    currentSpO2 = 98.0;
    targetSpO2 = 98.0;
    currentQuality = 90.0;

    // Noise state
    noiseX = 0.0;
    noiseDelta = 0.05;

    // ECG state
    ecgPhase = 0.0;
    ecgCycleTime = 0.0;
    sampleCounter = 0;
}

// Initialize simulator
void PhysiologicalSimulator::begin() {
    stateStartTime = millis();
    updateTargetVitals();

    Serial.println("✅ Physiological Simulator initialized");
    Serial.println("   State: RESTING");
    Serial.println("   Auto-cycle: 5 min per state");
}

// Update vitals (call every 1 second)
void PhysiologicalSimulator::update() {
    // State machine - auto-cycle through states (demo mode)
    if (millis() - stateStartTime > stateDuration) {
        // Cycle to next state
        currentState = (ActivityState)((currentState + 1) % 4);
        stateStartTime = millis();
        updateTargetVitals();

        // Debug output
        const char* stateNames[] = {"RESTING", "LIGHT_ACTIVITY", "EXERCISE", "SLEEP"};
        Serial.println("🔄 State transition: " + String(stateNames[currentState]));
    }

    // Apply smooth transitions (exponential moving average)
    applySmoothing();

    // Add natural variation (Perlin-like noise)
    addNaturalVariation();
}

// Getters
float PhysiologicalSimulator::getHeartRate() {
    return constrain(currentHeartRate, 40.0, 180.0);
}

float PhysiologicalSimulator::getTemperature() {
    return constrain(currentTemp, 95.0, 104.0);  // Fahrenheit
}

int PhysiologicalSimulator::getOxygenSaturation() {
    return constrain((int)currentSpO2, 88, 100);
}

int PhysiologicalSimulator::getRespiratoryRate() {
    return constrain((int)currentRespRate, 8, 35);
}

float PhysiologicalSimulator::getSignalQuality() {
    return constrain(currentQuality, 70.0, 100.0);
}

// State control
void PhysiologicalSimulator::setActivityState(ActivityState state) {
    currentState = state;
    stateStartTime = millis();
    updateTargetVitals();
}

PhysiologicalSimulator::ActivityState PhysiologicalSimulator::getCurrentState() {
    return currentState;
}

// ====================================
// PRIVATE HELPER METHODS
// ====================================

void PhysiologicalSimulator::updateTargetVitals() {
    // Set target vitals based on current state
    switch (currentState) {
        case RESTING:
            // Normal resting state
            targetHeartRate = 68.0 + random(-5, 6);      // 63-73 BPM
            targetRespRate = 14.0 + random(-2, 3);       // 12-16 breaths/min
            targetTemp = 97.5 + random(-5, 6) * 0.1;     // 97.0-98.0°F
            targetSpO2 = 98.0 + random(-1, 3);           // 97-100%
            currentQuality = 88.0 + random(-5, 8);       // 83-95%
            break;

        case LIGHT_ACTIVITY:
            // Light walking, casual movement
            targetHeartRate = 90.0 + random(-8, 9);      // 82-98 BPM
            targetRespRate = 18.0 + random(-2, 3);       // 16-20 breaths/min
            targetTemp = 98.2 + random(-3, 4) * 0.1;     // 97.9-98.5°F
            targetSpO2 = 97.0 + random(-1, 3);           // 96-99%
            currentQuality = 85.0 + random(-5, 8);       // 80-92%
            break;

        case EXERCISE:
            // Moderate to vigorous exercise
            targetHeartRate = 130.0 + random(-15, 16);   // 115-145 BPM
            targetRespRate = 25.0 + random(-3, 4);       // 22-28 breaths/min
            targetTemp = 99.5 + random(-5, 6) * 0.1;     // 99.0-100.0°F
            targetSpO2 = 95.0 + random(-2, 4);           // 93-98%
            currentQuality = 78.0 + random(-5, 8);       // 73-85%
            break;

        case SLEEP:
            // Deep sleep
            targetHeartRate = 58.0 + random(-5, 6);      // 53-63 BPM
            targetRespRate = 12.0 + random(-2, 3);       // 10-14 breaths/min
            targetTemp = 96.8 + random(-5, 6) * 0.1;     // 96.3-97.3°F
            targetSpO2 = 98.0 + random(-1, 3);           // 97-100%
            currentQuality = 90.0 + random(-3, 6);       // 87-95%
            break;
    }
}

void PhysiologicalSimulator::applySmoothing(float alpha) {
    // Exponential moving average for smooth transitions
    // alpha = 0.1 means ~10 seconds to reach 63% of target
    currentHeartRate += alpha * (targetHeartRate - currentHeartRate);
    currentRespRate += alpha * (targetRespRate - currentRespRate);
    currentTemp += alpha * (targetTemp - currentTemp);
    currentSpO2 += alpha * (targetSpO2 - currentSpO2);
}

void PhysiologicalSimulator::addNaturalVariation() {
    // Generate Perlin-like noise for natural variation
    float noise = perlinNoise();

    // Apply noise with different magnitudes for each vital
    currentHeartRate += noise * 2.5;     // ±2-3 BPM variation
    currentRespRate += noise * 1.0;      // ±1 breath/min variation
    currentTemp += noise * 0.15;         // ±0.15°F variation
    currentSpO2 += noise * 0.8;          // ±0-1% variation
    currentQuality += noise * 4.0;       // ±3-5% variation

    // Physiological coupling: HR affects RR (respiratory sinus arrhythmia)
    float hrVariation = (currentHeartRate - targetHeartRate) / targetHeartRate;
    currentRespRate += hrVariation * 2.0;  // HR ↑ → RR ↑
}

float PhysiologicalSimulator::perlinNoise() {
    // Pseudo-Perlin noise using sine waves
    noiseX += noiseDelta;
    float noise = sin(noiseX) * cos(noiseX * 0.7) * sin(noiseX * 0.3);
    return noise;  // Returns ~-1.0 to 1.0
}

// ====================================
// ECG WAVEFORM GENERATION
// ====================================

void PhysiologicalSimulator::generateECGSample(int lead, int32_t& sample) {
    // Calculate cardiac cycle timing based on current heart rate
    float cycleDuration = 60000.0 / currentHeartRate;  // ms per beat
    float phase = ecgCycleTime / cycleDuration;         // 0.0-1.0

    // Generate PQRST complex
    float amplitude = generatePQRST(phase, lead);

    // Convert to 24-bit ADC units (midpoint 8388608, range ±1.0V)
    // ECG amplitude typically ±1.0 mV, ADC sensitivity ~10 μV per LSB
    sample = 8388608 + (int32_t)(amplitude * 100000);

    // Add realistic noise (~10 μV RMS)
    sample += random(-50, 51);

    // Update ECG timing (500 Hz = 2ms per sample)
    ecgCycleTime += 2.0;
    if (ecgCycleTime >= cycleDuration) {
        ecgCycleTime = 0.0;  // New beat - reset to P wave
    }
}

float PhysiologicalSimulator::generatePQRST(float phase, int lead) {
    // Generate realistic ECG waveform with P-QRS-T morphology
    // Phase: 0.0-1.0 represents one complete cardiac cycle

    float amplitude = 0.0;

    // P wave (0-8% of cycle, ~80ms)
    if (phase < 0.08) {
        float t = phase / 0.08;  // Normalize to 0-1
        amplitude = 0.15 * sin(t * PI);  // Smooth bump
    }
    // PR segment (8-16% of cycle, ~80ms) - isoelectric
    else if (phase < 0.16) {
        amplitude = 0.0;
    }
    // QRS complex (16-24% of cycle, ~80ms)
    else if (phase < 0.24) {
        float t = (phase - 0.16) / 0.08;

        if (t < 0.25) {
            // Q wave (initial negative deflection)
            amplitude = -0.15 * (t / 0.25);
        }
        else if (t < 0.55) {
            // R wave (sharp positive spike)
            float r_t = (t - 0.25) / 0.30;
            amplitude = -0.15 + 1.7 * sin(r_t * PI);  // Peak at ~1.5 mV
        }
        else {
            // S wave (final negative deflection)
            float s_t = (t - 0.55) / 0.45;
            amplitude = -0.25 * (1.0 - s_t);
        }
    }
    // ST segment (24-32% of cycle, ~80ms) - isoelectric
    else if (phase < 0.32) {
        amplitude = 0.0;
    }
    // T wave (32-56% of cycle, ~240ms)
    else if (phase < 0.56) {
        float t = (phase - 0.32) / 0.24;
        amplitude = 0.30 * sin(t * PI);  // Smooth positive wave
    }
    // Rest of cycle - isoelectric
    else {
        amplitude = 0.0;
    }

    // Apply lead-specific morphology
    // Einthoven's triangle: Lead I + Lead III = Lead II
    float leadMultiplier = 1.0;
    switch (lead) {
        case 0:  // Lead I
            leadMultiplier = 0.75;
            break;
        case 1:  // Lead II (reference - largest amplitude)
            leadMultiplier = 1.0;
            break;
        case 2:  // Lead III
            leadMultiplier = 0.60;
            break;
    }

    return amplitude * leadMultiplier;
}

void PhysiologicalSimulator::fillSampleBuffer(int32_t buffer[3][50]) {
    // Generate 50 samples for each of 3 leads (100ms at 500 Hz)
    for (int i = 0; i < 50; i++) {
        for (int lead = 0; lead < 3; lead++) {
            generateECGSample(lead, buffer[lead][i]);
        }
    }
}
