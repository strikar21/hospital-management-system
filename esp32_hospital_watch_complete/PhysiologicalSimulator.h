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

    // Waveform modes
    enum WaveformMode {
        MODE_ECG = 0,  // Cardiac monitoring (PQRST waves)
        MODE_EEG = 1   // Brain activity monitoring (Alpha/Beta/Theta/Delta waves)
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

    // ✅ NEW: Advanced vitals
    int getBloodPressureSystolic();     // mmHg
    int getBloodPressureDiastolic();    // mmHg
    float getBioimpedance();            // Ohms
    float getTremorIntensity();         // 0.0-10.0 scale
    float getECGReading();              // Representative ECG amplitude in mV
    float getEEGReading();              // Representative EEG amplitude in μV
    float getIMUFallRisk();             // IMU-based fall risk 0.0-10.0

    // Waveform mode control
    void setMode(WaveformMode mode);
    void setWaveformMode(WaveformMode mode);  // Alias for setMode() (for sensor simulator compatibility)
    WaveformMode getMode();

    // Waveform generation (mode-dependent)
    void generateECGSample(int lead, int32_t& sample);  // Deprecated: kept for compatibility
    void generateECGSampleWithPhase(int lead, float phase, int32_t& sample);  // ✅ NEW: Phase-based generation
    void generateEEGSample(int channel, int32_t& sample);  // Deprecated: increments phase internally (8× per sample bug)
    void generateEEGSampleWithPhase(int channel, int32_t& sample);  // ✅ v5.2.10: Phase-based EEG generation (fixed timing)
    void fillSampleBuffer(int32_t buffer[8][10]);  // 8 channels × 10 samples (20ms at 500Hz - micro-batch)

    // ✅ NEW: Calibration pulse control (extended for better visibility)
    void startCalibrationPulse();  // Trigger hardware calibration pulse (1000ms flat → 1000ms 1mV pulse → 1000ms flat)
    bool isCalibrationActive();    // Check if calibration is currently running

    // State control (optional - for manual testing)
    void setActivityState(ActivityState state);
    ActivityState getCurrentState();

private:
    // Waveform mode
    WaveformMode currentMode;

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

    // ✅ NEW: Advanced vitals state
    float currentBPSystolic;
    float targetBPSystolic;
    float currentBPDiastolic;
    float targetBPDiastolic;
    float currentBioZ;
    float targetBioZ;
    float currentTremor;
    float targetTremor;
    float recentECGAmplitude;      // Representative ECG value for display
    float recentEEGAmplitude;      // Representative EEG value for display
    float currentIMUFallRisk;
    float targetIMUFallRisk;

    // Perlin noise state (for natural variation)
    float noiseX;
    float noiseDelta;

    // ECG synthesis state
    float ecgPhase;         // 0.0-1.0 (current position in cardiac cycle)
    float ecgCycleTime;     // ms since last R-peak
    int sampleCounter;      // For 500 Hz timing

    // EEG synthesis state
    float eegPhase;         // 0.0-1.0 (phase for waveform generation)
    float alphaPhase;       // Phase tracker for alpha waves (8-13 Hz)
    float betaPhase;        // Phase tracker for beta waves (13-30 Hz)
    float thetaPhase;       // Phase tracker for theta waves (4-8 Hz)
    float deltaPhase;       // Phase tracker for delta waves (0.5-4 Hz)

    // ✅ NEW: Calibration pulse state (extended for better visibility)
    bool calibrationActive;         // Is calibration pulse currently running?
    unsigned long calibrationStartTime;  // When calibration started (ms)
    unsigned long calibrationDuration;   // Total calibration duration: 3000ms (1000ms head + 1000ms pulse + 1000ms tail)

    // Helper methods
    void updateTargetVitals();
    void applySmoothing(float alpha = 0.1);
    void addNaturalVariation();
    float generatePQRST(float phase, int lead);
    float applyLeadVectors(float P, float Q, float R, float S, float T, int lead);  // ✅ NEW: Component-based lead vectors
    float generateEEGWaveform(float phase, int channel);
    float perlinNoise();
};

#endif // PHYSIOLOGICAL_SIMULATOR_H
