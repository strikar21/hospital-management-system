/*
 * Physiological Simulator Implementation
 * Generates realistic human vital signs and ECG waveforms
 */

#include "PhysiologicalSimulator.h"

// Constructor
PhysiologicalSimulator::PhysiologicalSimulator() {
    currentMode = MODE_ECG;  // Default to ECG mode
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

    // EEG state
    eegPhase = 0.0;
    alphaPhase = 0.0;
    betaPhase = 0.0;
    thetaPhase = 0.0;
    deltaPhase = 0.0;

    // ✅ NEW: Calibration pulse state
    calibrationActive = false;
    calibrationStartTime = 0;
    calibrationDuration = 3000;  // 3000ms total (1000ms head + 1000ms pulse + 1000ms tail)

    // ✅ NEW: Advanced vitals initialization
    currentBPSystolic = 115.0;
    targetBPSystolic = 115.0;
    currentBPDiastolic = 75.0;
    targetBPDiastolic = 75.0;
    currentBioZ = 480.0;
    targetBioZ = 480.0;
    currentTremor = 0.2;
    targetTremor = 0.2;
    recentECGAmplitude = 1.2;
    recentEEGAmplitude = 40.0;
    currentIMUFallRisk = 1.0;
    targetIMUFallRisk = 1.0;
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
    // ✅ v5.2.4: Fix millis() overflow with unsigned long cast
    if ((unsigned long)(millis() - stateStartTime) > stateDuration) {
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

    // ✅ NEW: Set targets for advanced vitals based on activity state
    switch (currentState) {
        case RESTING:
            targetBPSystolic = 115.0 + random(-5, 6);
            targetBPDiastolic = 75.0 + random(-3, 4);
            targetBioZ = 480.0 + random(-30, 31);
            targetTremor = 0.2 + (random(0, 30) / 100.0);
            targetIMUFallRisk = 1.0 + (random(0, 100) / 100.0);
            break;

        case LIGHT_ACTIVITY:
            targetBPSystolic = 130.0 + random(-5, 6);
            targetBPDiastolic = 80.0 + random(-3, 4);
            targetBioZ = 530.0 + random(-30, 31);
            targetTremor = 0.5 + (random(0, 50) / 100.0);
            targetIMUFallRisk = 1.5 + (random(0, 150) / 100.0);
            break;

        case EXERCISE:
            targetBPSystolic = 155.0 + random(-10, 11);
            targetBPDiastolic = 85.0 + random(-3, 4);
            targetBioZ = 590.0 + random(-40, 41);
            targetTremor = 1.0 + (random(0, 100) / 100.0);
            targetIMUFallRisk = 2.0 + (random(0, 200) / 100.0);
            break;

        case SLEEP:
            targetBPSystolic = 105.0 + random(-3, 4);
            targetBPDiastolic = 65.0 + random(-3, 4);
            targetBioZ = 450.0 + random(-30, 31);
            targetTremor = 0.05 + (random(0, 10) / 100.0);
            targetIMUFallRisk = 0.5 + (random(0, 50) / 100.0);
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

    // ✅ NEW: Smooth transitions for advanced vitals
    currentBPSystolic += alpha * (targetBPSystolic - currentBPSystolic);
    currentBPDiastolic += alpha * (targetBPDiastolic - currentBPDiastolic);
    currentBioZ += alpha * (targetBioZ - currentBioZ);
    currentTremor += alpha * (targetTremor - currentTremor);
    currentIMUFallRisk += alpha * (targetIMUFallRisk - currentIMUFallRisk);
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
// CALIBRATION PULSE CONTROL
// ====================================

void PhysiologicalSimulator::startCalibrationPulse() {
    calibrationActive = true;
    calibrationStartTime = millis();
    Serial.println("🔧 Calibration pulse started (3000ms: 1000ms head + 1000ms pulse + 1000ms tail)");
}

bool PhysiologicalSimulator::isCalibrationActive() {
    if (!calibrationActive) return false;

    // Check if 600ms has elapsed (using unsigned long cast for overflow safety)
    unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);
    if (elapsed >= calibrationDuration) {
        calibrationActive = false;
        Serial.println("✅ Calibration pulse complete");
        return false;
    }

    return true;
}

// ====================================
// ECG WAVEFORM GENERATION
// ====================================

// ✅ NEW: Generate ECG sample with pre-calculated phase (doesn't modify timing)
void PhysiologicalSimulator::generateECGSampleWithPhase(int lead, float phase, int32_t& sample) {
    // ✅ Check if calibration pulse is active (takes priority over normal ECG)
    if (isCalibrationActive()) {
        unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);

        // Extended calibration: 1000ms head (flat) → 1000ms pulse (1mV) → 1000ms tail (flat)
        if (elapsed < 1000) {
            // Head: baseline (0mV)
            sample = 8388608;  // ADC midpoint
        } else if (elapsed < 2000) {
            // Pulse: 1.0mV square wave
            sample = 8388608 + 100000;  // 1mV above baseline
        } else {
            // Tail: baseline (0mV)
            sample = 8388608;
        }
        return;  // Skip normal ECG generation during calibration
    }

    // Generate PQRST complex with given phase
    float amplitude = generatePQRST(phase, lead);

    // ✅ NEW: Calculate representative ECG amplitude for dashboard display
    // Rolling average of absolute amplitude over 50 samples (100ms)
    static int ecgSampleCount = 0;
    static float ecgAmplitudeSum = 0.0;

    ecgAmplitudeSum += abs(amplitude);
    ecgSampleCount++;

    if (ecgSampleCount >= 50) {
        recentECGAmplitude = ecgAmplitudeSum / 50.0;
        ecgAmplitudeSum = 0.0;
        ecgSampleCount = 0;
    }

    // Convert to 24-bit ADC units (midpoint 8388608, range ±1.0V)
    // ECG amplitude typically ±1.0 mV, ADC sensitivity ~10 μV per LSB
    sample = 8388608 + (int32_t)(amplitude * 100000);

    // Add realistic noise (~10 μV RMS)
    sample += random(-50, 51);

    // ✅ NOTE: Timing is handled by fillSampleBuffer(), not here
}

// ✅ DEPRECATED: Old method kept for compatibility (but not used anymore)
void PhysiologicalSimulator::generateECGSample(int lead, int32_t& sample) {
    // Calculate phase and delegate to new method
    float cycleDuration = 60000.0 / currentHeartRate;
    float phase = ecgCycleTime / cycleDuration;
    generateECGSampleWithPhase(lead, phase, sample);

    // Update timing (only when called directly, not from fillSampleBuffer)
    ecgCycleTime += 2.0;
    if (ecgCycleTime >= cycleDuration) {
        ecgCycleTime = 0.0;
    }
}

float PhysiologicalSimulator::generatePQRST(float phase, int lead) {
    // ✅ v5.3.0: Component-based lead vector generation for anatomically correct 12-lead ECG
    // Generate realistic ECG waveform with P-QRS-T morphology
    // Phase: 0.0-1.0 represents one complete cardiac cycle

    float P = 0.0, Q = 0.0, R = 0.0, S = 0.0, T = 0.0;

    // P wave (0-8% of cycle, ~80ms)
    if (phase < 0.08) {
        float t = phase / 0.08;  // Normalize to 0-1
        P = 0.15 * sin(t * PI);  // Baseline P amplitude
    }
    // PR segment (8-16% of cycle, ~80ms) - isoelectric
    else if (phase < 0.16) {
        // Isoelectric - no components
    }
    // QRS complex (16-24% of cycle, ~80ms)
    else if (phase < 0.24) {
        float t = (phase - 0.16) / 0.08;

        if (t < 0.25) {
            // Q wave (initial negative deflection)
            Q = -0.15 * (t / 0.25);
        }
        else if (t < 0.55) {
            // R wave (sharp positive spike)
            float r_t = (t - 0.25) / 0.30;
            R = 1.7 * sin(r_t * PI);  // Peak at ~1.5 mV
        }
        else {
            // S wave (final negative deflection)
            float s_t = (t - 0.55) / 0.45;
            S = -0.25 * (1.0 - s_t);
        }
    }
    // ST segment (24-32% of cycle, ~80ms) - isoelectric
    else if (phase < 0.32) {
        // Isoelectric - no components
    }
    // T wave (32-56% of cycle, ~240ms)
    else if (phase < 0.56) {
        float t = (phase - 0.32) / 0.24;
        T = 0.30 * sin(t * PI);  // Baseline T amplitude
    }
    // Rest of cycle - isoelectric
    else {
        // Isoelectric - no components
    }

    // Apply lead-specific vector projections
    return applyLeadVectors(P, Q, R, S, T, lead);
}

// ✅ v5.3.0: Component-based lead vector weighting for anatomically correct 12-lead ECG
float PhysiologicalSimulator::applyLeadVectors(float P, float Q, float R, float S, float T, int lead) {
    // Each lead views the heart's electrical activity from a different angle
    // Positive multiplier = same polarity, Negative = inverted, Zero = not visible
    // This creates anatomically correct lead-specific morphologies

    float P_vec, Q_vec, R_vec, S_vec, T_vec;

    switch (lead) {
        case 0:  // Lead I (0° - Lateral view)
            P_vec = 0.75;   // Small positive P
            Q_vec = 0.80;   // Small Q
            R_vec = 0.85;   // Moderate R
            S_vec = 0.60;   // Small S
            T_vec = 0.75;   // Positive T
            break;

        case 1:  // Lead II (+60° - Inferior, REFERENCE lead)
            P_vec = 1.0;    // Tallest P (reference)
            Q_vec = 1.0;    // Standard Q (reference)
            R_vec = 1.0;    // Tallest R (reference)
            S_vec = 1.0;    // Standard S (reference)
            T_vec = 1.0;    // Tallest T (reference)
            break;

        case 2:  // V1 (Right precordial - rS pattern: small r, DEEP S)
            P_vec = 0.40;   // Small P
            Q_vec = 0.20;   // Tiny or absent q
            R_vec = 0.30;   // SMALL r wave (30% of normal) ← KEY FIX
            S_vec = 2.50;   // DEEP S wave (250% of normal) ← NEGATIVE DOMINANT
            T_vec = -0.30;  // INVERTED or biphasic T
            break;

        case 3:  // V2 (Transitional - RS pattern: growing R, significant S)
            P_vec = 0.50;   // Small P
            Q_vec = 0.30;   // Small q
            R_vec = 0.65;   // Growing R (65% of normal)
            S_vec = 1.80;   // Still significant S (180%)
            T_vec = 0.40;   // Small positive T
            break;

        case 4:  // V3 (Transition zone - R = S, balanced)
            P_vec = 0.70;   // Moderate P
            Q_vec = 0.50;   // Small q
            R_vec = 1.00;   // R equals baseline (100%)
            S_vec = 1.00;   // S equals baseline (R = S)
            T_vec = 0.75;   // Moderate positive T
            break;

        case 5:  // V4 (Left precordial - TALLEST R wave, small S)
            P_vec = 0.85;   // Good P
            Q_vec = 0.70;   // Small q
            R_vec = 1.40;   // TALLEST R wave (140%) ← TALLEST PRECORDIAL
            S_vec = 0.40;   // Small S (40%)
            T_vec = 0.95;   // Tall positive T
            break;

        case 6:  // V5 (Lateral - tall R, tiny S)
            P_vec = 0.80;   // Good P
            Q_vec = 0.60;   // Small q
            R_vec = 1.25;   // Tall R (125%)
            S_vec = 0.20;   // Tiny S (20%)
            T_vec = 0.85;   // Positive T
            break;

        case 7:  // V6 (Far lateral - tall R, minimal S)
            P_vec = 0.75;   // Moderate P
            Q_vec = 0.50;   // Small q
            R_vec = 1.10;   // Tall R (110%)
            S_vec = 0.10;   // Almost no S (10%)
            T_vec = 0.80;   // Positive T
            break;

        default:
            P_vec = Q_vec = R_vec = S_vec = T_vec = 1.0;
            break;
    }

    return P * P_vec + Q * Q_vec + R * R_vec + S * S_vec + T * T_vec;
}

void PhysiologicalSimulator::fillSampleBuffer(int32_t buffer[8][10]) {
    // Generate 10 samples for each of 8 leads/channels (20ms at 500 Hz - micro-batch)
    // Micro-batch approach: Generate smaller batches more frequently for better timing distribution
    // 5 micro-batches of 10 samples each = 50 samples every 100ms (maintains 500Hz rate)
    // ECG mode: CH1=Lead I, CH2=Lead II, CH3-8=V1-V6
    // EEG mode: CH1-8=Fp1,Fp2,F3,F4,C3,C4,O1,O2

    // ✅ FIX: Calculate phase ONCE per sample, use same phase for all leads
    // This ensures all leads show the same cardiac cycle at each time point
    for (int i = 0; i < 10; i++) {
        if (currentMode == MODE_ECG) {
            // ECG: Calculate cardiac cycle phase for this sample
            float cycleDuration = 60000.0 / currentHeartRate;
            float phase = ecgCycleTime / cycleDuration;

            // Generate all 8 leads with same phase
            for (int lead = 0; lead < 8; lead++) {
                generateECGSampleWithPhase(lead, phase, buffer[lead][i]);
            }

            // ✅ Increment time ONCE per sample (not per lead)
            ecgCycleTime += 2.0;  // 500 Hz = 2ms per sample
            if (ecgCycleTime >= cycleDuration) {
                ecgCycleTime = 0.0;  // New beat - reset to P wave
            }
        } else {
            // ✅ v5.2.10 FIX: EEG timing - generate all channels with same phase, then increment ONCE
            // Generate all 8 channels using current phase
            for (int channel = 0; channel < 8; channel++) {
                generateEEGSampleWithPhase(channel, buffer[channel][i]);
            }

            // ✅ Increment phase ONCE per sample (not per channel) - same pattern as ECG
            float timeStep = 0.002;  // 2ms in seconds (500 Hz)
            alphaPhase += 10.5 * timeStep;   // 10.5 Hz (alpha)
            betaPhase += 20.0 * timeStep;    // 20 Hz (beta)
            thetaPhase += 6.0 * timeStep;    // 6 Hz (theta)
            deltaPhase += 2.0 * timeStep;    // 2 Hz (delta)
            eegPhase += timeStep;
            if (eegPhase > 1.0) eegPhase -= 1.0;
        }
    }
}

// ====================================
// MODE CONTROL
// ====================================

void PhysiologicalSimulator::setMode(WaveformMode mode) {
    if (currentMode != mode) {
        currentMode = mode;
        // Reset phase trackers when switching modes
        if (mode == MODE_ECG) {
            ecgPhase = 0.0;
            ecgCycleTime = 0.0;
        } else {
            eegPhase = 0.0;
            alphaPhase = 0.0;
            betaPhase = 0.0;
            thetaPhase = 0.0;
            deltaPhase = 0.0;
        }
    }
}

void PhysiologicalSimulator::setWaveformMode(WaveformMode mode) {
    // Alias for setMode() - for sensor simulator compatibility
    setMode(mode);
}

PhysiologicalSimulator::WaveformMode PhysiologicalSimulator::getMode() {
    return currentMode;
}

// ====================================
// EEG WAVEFORM GENERATION
// ====================================

// ✅ v5.2.10: Generate EEG sample WITHOUT updating phase (phase is managed externally like ECG)
void PhysiologicalSimulator::generateEEGSampleWithPhase(int channel, int32_t& sample) {
    // ✅ v5.2.13: Check if calibration pulse is active (takes priority over normal EEG)
    if (isCalibrationActive()) {
        unsigned long elapsed = (unsigned long)(millis() - calibrationStartTime);

        // Extended calibration: 1000ms head (flat) → 1000ms pulse (100μV) → 1000ms tail (flat)
        if (elapsed < 1000) {
            // Head: baseline (0μV)
            sample = 8388608;  // ADC midpoint
        } else if (elapsed < 2000) {
            // Pulse: 100μV square wave (1/10th of ECG's 1mV for proper scaling)
            sample = 8388608 + 10000;  // 100μV above baseline
        } else {
            // Tail: baseline (0μV)
            sample = 8388608;
        }
        return;  // Skip normal EEG generation during calibration
    }

    // Generate waveform based on activity state and channel (using current phase)
    float amplitude = generateEEGWaveform(eegPhase, channel);

    // ✅ Calculate representative EEG amplitude for dashboard display
    // Rolling average of absolute amplitude over 50 samples (100ms)
    static int eegSampleCount = 0;
    static float eegAmplitudeSum = 0.0;

    eegAmplitudeSum += abs(amplitude);
    eegSampleCount++;

    if (eegSampleCount >= 50) {
        recentEEGAmplitude = eegAmplitudeSum / 50.0;
        eegAmplitudeSum = 0.0;
        eegSampleCount = 0;
    }

    // Convert to 24-bit ADC units (midpoint 8388608, range ±0.1V)
    // EEG amplitude typically ±100 μV, ADC sensitivity ~1 μV per LSB
    sample = 8388608 + (int32_t)(amplitude * 1000);

    // Add realistic noise (~2 μV RMS)
    sample += random(-20, 21);

    // ✅ NOTE: Phase is updated by fillSampleBuffer() ONCE per sample, NOT here
}

// ✅ DEPRECATED: Old method kept for compatibility (but not used in fillSampleBuffer anymore)
void PhysiologicalSimulator::generateEEGSample(int channel, int32_t& sample) {
    // ❌ WARNING: This method increments phase on every call (8× per sample)
    // Only use this if calling generateEEGSample() directly for single-channel generation
    // For multi-channel batch generation, use generateEEGSampleWithPhase() instead

    // Update phase trackers for each frequency band (500 Hz = 2ms per sample)
    float timeStep = 0.002;  // 2ms in seconds
    alphaPhase += 10.5 * timeStep;   // 10.5 Hz (alpha)
    betaPhase += 20.0 * timeStep;    // 20 Hz (beta)
    thetaPhase += 6.0 * timeStep;    // 6 Hz (theta)
    deltaPhase += 2.0 * timeStep;    // 2 Hz (delta)

    // Generate waveform based on activity state and channel
    float amplitude = generateEEGWaveform(eegPhase, channel);

    // ✅ Calculate representative EEG amplitude for dashboard display
    static int eegSampleCount = 0;
    static float eegAmplitudeSum = 0.0;

    eegAmplitudeSum += abs(amplitude);
    eegSampleCount++;

    if (eegSampleCount >= 50) {
        recentEEGAmplitude = eegAmplitudeSum / 50.0;
        eegAmplitudeSum = 0.0;
        eegSampleCount = 0;
    }

    // Convert to 24-bit ADC units
    sample = 8388608 + (int32_t)(amplitude * 1000);

    // Add realistic noise (~2 μV RMS)
    sample += random(-20, 21);

    // Increment global phase
    eegPhase += timeStep;
    if (eegPhase > 1.0) eegPhase -= 1.0;
}

float PhysiologicalSimulator::generateEEGWaveform(float phase, int channel) {
    // Mix frequency bands based on activity state
    // Alpha (8-13 Hz): Relaxed, eyes closed
    // Beta (13-30 Hz): Active thinking, focus
    // Theta (4-8 Hz): Drowsiness, light sleep
    // Delta (0.5-4 Hz): Deep sleep

    float alpha = sin(2 * PI * alphaPhase) * 40.0;   // 40 μV amplitude
    float beta = sin(2 * PI * betaPhase) * 15.0;     // 15 μV amplitude
    float theta = sin(2 * PI * thetaPhase) * 50.0;   // 50 μV amplitude
    float delta = sin(2 * PI * deltaPhase) * 80.0;   // 80 μV amplitude

    // ✅ v5.2.11: Channel-specific frequency mixing (anatomically correct brain regions)
    // Different brain regions have different dominant frequencies
    // Reference: Niedermeyer's EEG (6th ed.), ACNS guidelines
    float alphaWeight = 0.6;  // Default weights
    float betaWeight = 0.3;
    float thetaWeight = 0.1;

    switch (channel) {
        case 0:  // Fp1 - Frontal pole left (motor planning, executive function)
        case 1:  // Fp2 - Frontal pole right
            // Frontal lobe: MORE BETA (active thinking), less alpha
            alphaWeight = 0.3;
            betaWeight = 0.6;
            thetaWeight = 0.1;
            break;

        case 2:  // F3 - Frontal left (motor cortex)
        case 3:  // F4 - Frontal right
            // Frontal-moderate: balanced beta-alpha mix
            alphaWeight = 0.4;
            betaWeight = 0.5;
            thetaWeight = 0.1;
            break;

        case 4:  // C3 - Central left (sensorimotor cortex)
        case 5:  // C4 - Central right
            // Central: balanced (mu rhythm, similar to alpha)
            alphaWeight = 0.6;
            betaWeight = 0.3;
            thetaWeight = 0.1;
            break;

        case 6:  // O1 - Occipital left (visual cortex)
        case 7:  // O2 - Occipital right
            // Occipital: STRONG ALPHA (posterior dominant rhythm), minimal beta
            // This is the "alpha rhythm" - diagnostic hallmark of normal EEG
            alphaWeight = 0.8;  // Dominant alpha (visual cortex at rest)
            betaWeight = 0.1;
            thetaWeight = 0.1;
            break;

        default:
            // Fallback to balanced
            alphaWeight = 0.6;
            betaWeight = 0.3;
            thetaWeight = 0.1;
            break;
    }

    // Apply state-dependent modulation (affects all channels, but with channel-specific weights)
    float mixedSignal = 0.0;
    switch(currentState) {
        case RESTING:
            // Awake, relaxed: use channel-specific weights
            mixedSignal = alpha * alphaWeight + beta * betaWeight + theta * thetaWeight;
            break;

        case LIGHT_ACTIVITY:
            // Active, alert: increase beta across all channels (reduce alpha)
            mixedSignal = alpha * (alphaWeight * 0.5) + beta * (betaWeight * 1.5) + theta * thetaWeight;
            break;

        case EXERCISE:
            // High alertness: strong beta everywhere (minimal alpha)
            mixedSignal = alpha * (alphaWeight * 0.3) + beta * (betaWeight * 2.0) + theta * thetaWeight;
            break;

        case SLEEP:
            // Sleep: dominant delta and theta (alpha suppressed)
            mixedSignal = delta * 0.5 + theta * 0.4 + alpha * (alphaWeight * 0.2);
            break;

        default:
            mixedSignal = alpha * alphaWeight + beta * betaWeight + theta * thetaWeight;
    }

    return mixedSignal;
}

// ====================================
// ✅ NEW: ADVANCED VITALS GETTERS
// ====================================

int PhysiologicalSimulator::getBloodPressureSystolic() {
    return constrain((int)currentBPSystolic, 60, 200);
}

int PhysiologicalSimulator::getBloodPressureDiastolic() {
    return constrain((int)currentBPDiastolic, 40, 130);
}

float PhysiologicalSimulator::getBioimpedance() {
    return constrain(currentBioZ, 200.0, 1000.0);
}

float PhysiologicalSimulator::getTremorIntensity() {
    return constrain(currentTremor, 0.0, 10.0);
}

float PhysiologicalSimulator::getECGReading() {
    // Return representative ECG amplitude (mV)
    // This is updated by waveform generation, providing a single value for dashboard display
    return constrain(recentECGAmplitude, 0.1, 3.0);
}

float PhysiologicalSimulator::getEEGReading() {
    // Return representative EEG amplitude (μV)
    // This is updated by waveform generation, providing a single value for dashboard display
    return constrain(recentEEGAmplitude, 10.0, 150.0);
}

float PhysiologicalSimulator::getIMUFallRisk() {
    // Return simulated IMU-based fall risk (0-10 scale)
    // In real implementation, this would come from actual IMU motion analysis
    return constrain(currentIMUFallRisk, 0.0, 10.0);
}
