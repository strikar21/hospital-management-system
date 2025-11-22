/**
 * BMI323Simulator.cpp
 *
 * Implementation of BMI323 6-axis IMU simulator with tremor/fall detection
 */

#include "BMI323Simulator.h"
#include <math.h>

// ===== Constructor =====
BMI323Simulator::BMI323Simulator(PhysiologicalSimulator* physioSim) {
    physio = physioSim;
    currentActivity = STILL;
    fallState = NORMAL;
    lastUpdateTime = 0;
    lastMovementTime = millis();

    motionPhase = 0.0;
    stepCount = 0;
    doubleTapFlag = false;

    accelX = 0;
    accelY = 0;
    accelZ = ACCEL_LSB_PER_G;  // 1g gravity at rest

    gyroX = 0;
    gyroY = 0;
    gyroZ = 0;

    fftIndex = 0;
    currentTremorIntensity = 0.0;
    freefallStartTime = 0;
    impactTime = 0;
    currentFallRisk = 0.0;

    // Initialize FFT buffer
    for (int i = 0; i < FFT_SIZE; i++) {
        accelMagHistory[i] = 1.0;  // 1g at rest
    }
}

// ===== Initialization =====
void BMI323Simulator::begin() {
    Serial.println("[BMI323] 6-Axis IMU initialized");
    Serial.print("[BMI323] I2C Address: 0x");
    Serial.println(I2C_ADDRESS, HEX);
    Serial.print("[BMI323] Accel Range: ±");
    Serial.print(ACCEL_RANGE_G);
    Serial.println("g");
    Serial.print("[BMI323] Gyro Range: ±");
    Serial.print(GYRO_RANGE_DPS);
    Serial.println(" dps");
    Serial.print("[BMI323] Sample Rate: ");
    Serial.print(SAMPLE_RATE_HZ);
    Serial.println(" Hz");
    Serial.println("[BMI323] Features: Step Counter, Tap Detection, Tremor Analysis, Fall Detection");
}

// ===== Update =====
void BMI323Simulator::update() {
    unsigned long now = micros();

    // Check if it's time for next sample (1600 Hz ≈ 625 µs period)
    if (now - lastUpdateTime < UPDATE_PERIOD_US) {
        return;
    }
    lastUpdateTime = now;

    // Get tremor intensity from PhysiologicalSimulator
    float tremorLevel = physio->getTremorIntensity();

    // Generate motion based on current activity
    if (tremorLevel > 0.1) {
        generateTremorMotion();
    } else {
        switch (currentActivity) {
            case STILL:
                generateStillMotion();
                break;
            case WALKING:
                generateWalkingMotion();
                break;
            case RUNNING:
                generateRunningMotion();
                break;
            case FALL_DETECTED:
                // Fall motion handled by fall detection
                break;
        }
    }

    // Calculate acceleration magnitude for FFT
    float accelMag = sqrt(
        pow(accelX / (float)ACCEL_LSB_PER_G, 2) +
        pow(accelY / (float)ACCEL_LSB_PER_G, 2) +
        pow(accelZ / (float)ACCEL_LSB_PER_G, 2)
    );

    accelMagHistory[fftIndex] = accelMag;
    fftIndex = (fftIndex + 1) % FFT_SIZE;

    // Update tremor analysis every 128 samples (80ms @ 1600 Hz)
    if (fftIndex == 0) {
        updateTremorAnalysis();
    }

    // Update fall detection
    updateFallDetection();

    // Update step counter
    updateStepCounter();

    // Update tap detection
    updateTapDetection();

    // Track last movement time
    if (abs(accelX) > 100 || abs(accelY) > 100 ||
        abs(gyroX) > 100 || abs(gyroY) > 100 || abs(gyroZ) > 100) {
        lastMovementTime = millis();
    }
}

// ===== Raw IMU Data =====
void BMI323Simulator::readAccel(int16_t& x, int16_t& y, int16_t& z) {
    x = accelX;
    y = accelY;
    z = accelZ;
}

void BMI323Simulator::readGyro(int16_t& x, int16_t& y, int16_t& z) {
    x = gyroX;
    y = gyroY;
    z = gyroZ;
}

// ===== Built-in Features =====
uint32_t BMI323Simulator::getStepCount() {
    return stepCount;
}

bool BMI323Simulator::detectDoubleTap() {
    bool result = doubleTapFlag;
    doubleTapFlag = false;  // Clear flag
    return result;
}

unsigned long BMI323Simulator::getLastMovementTime() {
    return millis() - lastMovementTime;
}

// ===== ESP32-Side Processing =====
float BMI323Simulator::getTremorIntensity() {
    return currentTremorIntensity;
}

float BMI323Simulator::getFallRisk() {
    return currentFallRisk;
}

String BMI323Simulator::getFallRiskCategory() {
    if (currentFallRisk >= 9.0) return "critical";
    if (currentFallRisk >= 7.0) return "high";
    if (currentFallRisk >= 4.0) return "medium";
    return "low";
}

BMI323Simulator::FallState BMI323Simulator::getFallState() {
    return fallState;
}

// ===== Activity Recognition =====
void BMI323Simulator::setActivity(ActivityState state) {
    currentActivity = state;
}

BMI323Simulator::ActivityState BMI323Simulator::getActivity() {
    return currentActivity;
}

// ===== Diagnostic Methods =====
uint8_t BMI323Simulator::getI2CAddress() {
    return I2C_ADDRESS;
}

int BMI323Simulator::getSampleRate() {
    return SAMPLE_RATE_HZ;
}

// ===== Private Methods =====

void BMI323Simulator::generateStillMotion() {
    // Stationary - only gravity on Z-axis
    accelX = addIMUNoise(0);
    accelY = addIMUNoise(0);
    accelZ = addIMUNoise(ACCEL_LSB_PER_G);  // 1g gravity

    gyroX = addIMUNoise(0);
    gyroY = addIMUNoise(0);
    gyroZ = addIMUNoise(0);
}

void BMI323Simulator::generateWalkingMotion() {
    // Walking motion pattern
    // Frequency: ~1.67 Hz (100 steps/min)

    float stepFrequency = 1.67;  // Hz
    motionPhase += (UPDATE_PERIOD_US / 1000000.0) * stepFrequency;
    if (motionPhase >= 1.0) motionPhase -= 1.0;

    // Vertical acceleration (heel strike pattern)
    float zAccel = 1.0 + 0.3 * sin(2 * PI * motionPhase);  // 1g ± 0.3g

    // Forward/backward sway
    float xAccel = 0.15 * sin(2 * PI * motionPhase + PI/2);

    // Side-to-side sway
    float yAccel = 0.1 * sin(4 * PI * motionPhase);  // Double frequency

    // Convert to LSB (4096 LSB/g)
    accelX = addIMUNoise((int16_t)(xAccel * ACCEL_LSB_PER_G));
    accelY = addIMUNoise((int16_t)(yAccel * ACCEL_LSB_PER_G));
    accelZ = addIMUNoise((int16_t)(zAccel * ACCEL_LSB_PER_G));

    // Gyroscope (body rotation during walking)
    gyroX = addIMUNoise((int16_t)(20.0 * sin(2 * PI * motionPhase) * GYRO_LSB_PER_DPS));
    gyroY = addIMUNoise((int16_t)(15.0 * sin(4 * PI * motionPhase) * GYRO_LSB_PER_DPS));
    gyroZ = addIMUNoise((int16_t)(10.0 * sin(2 * PI * motionPhase + PI) * GYRO_LSB_PER_DPS));
}

void BMI323Simulator::generateRunningMotion() {
    // Running - similar to walking but higher amplitude and frequency

    float stepFrequency = 2.5;  // Hz (150 steps/min)
    motionPhase += (UPDATE_PERIOD_US / 1000000.0) * stepFrequency;
    if (motionPhase >= 1.0) motionPhase -= 1.0;

    // Higher vertical acceleration
    float zAccel = 1.0 + 0.8 * sin(2 * PI * motionPhase);  // 1g ± 0.8g

    float xAccel = 0.4 * sin(2 * PI * motionPhase + PI/2);
    float yAccel = 0.2 * sin(4 * PI * motionPhase);

    accelX = addIMUNoise((int16_t)(xAccel * ACCEL_LSB_PER_G));
    accelY = addIMUNoise((int16_t)(yAccel * ACCEL_LSB_PER_G));
    accelZ = addIMUNoise((int16_t)(zAccel * ACCEL_LSB_PER_G));

    // Higher gyroscope values
    gyroX = addIMUNoise((int16_t)(50.0 * sin(2 * PI * motionPhase) * GYRO_LSB_PER_DPS));
    gyroY = addIMUNoise((int16_t)(40.0 * sin(4 * PI * motionPhase) * GYRO_LSB_PER_DPS));
    gyroZ = addIMUNoise((int16_t)(30.0 * sin(2 * PI * motionPhase + PI) * GYRO_LSB_PER_DPS));
}

void BMI323Simulator::generateTremorMotion() {
    // Tremor overlaid on normal motion
    // Tremor frequency: 4-12 Hz (Parkinsonian tremor ~4-6 Hz)

    float tremorLevel = physio->getTremorIntensity();
    float tremorFreq = 5.0;  // Hz (typical Parkinsonian)

    static float tremorPhase = 0.0;
    tremorPhase += (UPDATE_PERIOD_US / 1000000.0) * tremorFreq;
    if (tremorPhase >= 1.0) tremorPhase -= 1.0;

    // Tremor amplitude (scaled by intensity 0-10)
    float tremorAmplitude = 0.05 * tremorLevel;  // Up to 0.5g

    float tremorX = tremorAmplitude * sin(2 * PI * tremorPhase);
    float tremorY = tremorAmplitude * sin(2 * PI * tremorPhase + PI/3);
    float tremorZ = tremorAmplitude * sin(2 * PI * tremorPhase + 2*PI/3);

    // Base motion (still or walking)
    generateStillMotion();  // Start with still

    // Add tremor
    accelX += (int16_t)(tremorX * ACCEL_LSB_PER_G);
    accelY += (int16_t)(tremorY * ACCEL_LSB_PER_G);
    accelZ += (int16_t)(tremorZ * ACCEL_LSB_PER_G);
}

void BMI323Simulator::updateTremorAnalysis() {
    // Simplified FFT for tremor detection
    // Analyze 4-12 Hz frequency band

    float tremorPower = analyzeTremorFFT();

    // Scale to 0-10 intensity
    currentTremorIntensity = constrain(tremorPower * 20.0, 0.0, 10.0);
}

void BMI323Simulator::updateFallDetection() {
    // Calculate total acceleration magnitude
    float accelMag = sqrt(
        pow(accelX / (float)ACCEL_LSB_PER_G, 2) +
        pow(accelY / (float)ACCEL_LSB_PER_G, 2) +
        pow(accelZ / (float)ACCEL_LSB_PER_G, 2)
    );

    switch (fallState) {
        case NORMAL:
            currentFallRisk = 0.0;

            // Detect freefall (accel < 0.5g)
            if (accelMag < 0.5) {
                fallState = FREEFALL;
                freefallStartTime = millis();
                currentFallRisk = 5.0;
            }
            break;

        case FREEFALL:
            // Detect impact (accel > 3g)
            if (accelMag > 3.0) {
                fallState = IMPACT;
                impactTime = millis();
                currentFallRisk = 8.0;
            }

            // Timeout if no impact after 500ms
            if (millis() - freefallStartTime > 500) {
                fallState = NORMAL;
            }
            break;

        case IMPACT:
            // Check if lying still after impact
            if (detectLyingOrientation() && (millis() - impactTime > 5000)) {
                fallState = LYING;
                currentFallRisk = 10.0;  // CRITICAL
            }

            // Timeout if recovered within 5 seconds
            if (millis() - impactTime > 5000 && !detectLyingOrientation()) {
                fallState = NORMAL;
                currentFallRisk = 2.0;  // Recovered
            }
            break;

        case LYING:
            currentFallRisk = 10.0;  // CRITICAL - needs help

            // Reset if movement detected (helped up)
            if (accelMag > 1.2 || abs(gyroX) > 500 || abs(gyroY) > 500) {
                fallState = NORMAL;
                currentFallRisk = 0.0;
            }
            break;
    }
}

bool BMI323Simulator::detectLyingOrientation() {
    // Check if body is horizontal (fallen)
    // Look for Z-axis close to 0g (lying on side) or ±1g (lying on back/front)

    float zAccel = abs(accelZ / (float)ACCEL_LSB_PER_G);
    float xyAccel = sqrt(
        pow(accelX / (float)ACCEL_LSB_PER_G, 2) +
        pow(accelY / (float)ACCEL_LSB_PER_G, 2)
    );

    // Lying on back/front: Z ≈ ±1g, XY ≈ 0
    if (abs(zAccel - 1.0) < 0.3 && xyAccel < 0.3) {
        return true;
    }

    // Lying on side: Z ≈ 0, X or Y ≈ ±1g
    if (zAccel < 0.3 && xyAccel > 0.7 && xyAccel < 1.3) {
        return true;
    }

    return false;
}

void BMI323Simulator::updateStepCounter() {
    // Bosch step counter algorithm simulation
    // Detect heel strikes from vertical acceleration peaks

    static int16_t lastZ = ACCEL_LSB_PER_G;
    static bool inStep = false;

    int16_t threshold = ACCEL_LSB_PER_G + 1000;  // 1.25g threshold

    if (accelZ > threshold && accelZ > lastZ && !inStep) {
        stepCount++;
        inStep = true;
    }

    if (accelZ < threshold) {
        inStep = false;
    }

    lastZ = accelZ;
}

void BMI323Simulator::updateTapDetection() {
    // Tap detection - look for sharp transients

    static int16_t lastAccelMag = ACCEL_LSB_PER_G;
    static unsigned long lastTapTime = 0;

    int16_t accelMagInt = sqrt(
        (int32_t)accelX * accelX +
        (int32_t)accelY * accelY +
        (int32_t)accelZ * accelZ
    );

    int16_t delta = abs(accelMagInt - lastAccelMag);

    // Tap threshold: sudden change > 2g
    if (delta > (2 * ACCEL_LSB_PER_G)) {
        unsigned long now = millis();

        // Double-tap: second tap within 500ms
        if (now - lastTapTime < 500) {
            doubleTapFlag = true;
        }

        lastTapTime = now;
    }

    lastAccelMag = accelMagInt;
}

int16_t BMI323Simulator::addIMUNoise(int16_t sample) {
    // White noise: ±50 LSB
    int16_t noise = random(-50, 51);
    return sample + noise;
}

float BMI323Simulator::analyzeTremorFFT() {
    // Simplified FFT analysis for tremor (4-12 Hz band)
    // In production, use arduinoFFT library

    // For simulation, estimate tremor power from variance
    float mean = 0.0;
    for (int i = 0; i < FFT_SIZE; i++) {
        mean += accelMagHistory[i];
    }
    mean /= FFT_SIZE;

    float variance = 0.0;
    for (int i = 0; i < FFT_SIZE; i++) {
        variance += pow(accelMagHistory[i] - mean, 2);
    }
    variance /= FFT_SIZE;

    // High variance in 80ms window → tremor
    float tremorPower = sqrt(variance);

    return tremorPower;
}
