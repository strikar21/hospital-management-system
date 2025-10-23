/*
 * Physiological Simulator for ESP32 Hospital Watch
 * Generates realistic human vital signs and ECG waveforms
 *
 * Features:
 * - Smooth vital sign transitions with natural variation
 * - 4 activity states (resting, light activity, exercise, sleep)
 * - Realistic 3-lead ECG with PQRST morphology
 * - Delta-encoded waveform streaming
 *
 * Author: Claude/Anthropic
 * Date: 2025-10-22
 */

#ifndef PHYSIOLOGICAL_SIMULATOR_H
#define PHYSIOLOGICAL_SIMULATOR_H

#include <Arduino.h>

class PhysiologicalSimulator {
public:
    // Activity states
    enum ActivityState {
        RESTING = 0,
        LIGHT_ACTIVITY = 1,
        EXERCISE = 2,
        SLEEP = 3
    };

    // Constructor
    PhysiologicalSimulator();

    // Initialize simulator
    void begin();

    // Update vitals (call every 1 second)
    void update();

    // Getters for current vitals
    float getHeartRate();           // BPM
    float getTemperature();         // Fahrenheit
    int getOxygenSaturation();      // %
    int getRespiratoryRate();       // breaths/min
    float getSignalQuality();       // 0.0-100.0

    // ECG waveform generation
    void generateECGSample(int lead, int32_t& sample);
    void fillSampleBuffer(int32_t buffer[3][50]);

    // State control (optional - for manual testing)
    void setActivityState(ActivityState state);
    ActivityState getCurrentState();

private:
    // State machine
    ActivityState currentState;
    unsigned long stateStartTime;
    unsigned long stateDuration;  // ms per state (5 minutes default)

    // Current vital signs (with smooth transitions)
    float currentHeartRate;
    float targetHeartRate;
    float currentRespRate;
    float targetRespRate;
    float currentTemp;
    float targetTemp;
    float currentSpO2;
    float targetSpO2;
    float currentQuality;

    // Perlin noise state (for natural variation)
    float noiseX;
    float noiseDelta;

    // ECG synthesis state
    float ecgPhase;         // 0.0-1.0 (current position in cardiac cycle)
    float ecgCycleTime;     // ms since last R-peak
    int sampleCounter;      // For 500 Hz timing

    // Helper methods
    void updateTargetVitals();
    void applySmoothing(float alpha = 0.1);
    void addNaturalVariation();
    float generatePQRST(float phase, int lead);
    float perlinNoise();
};

#endif // PHYSIOLOGICAL_SIMULATOR_H
