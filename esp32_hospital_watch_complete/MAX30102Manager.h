/**
 * MAX30102Manager.h
 *
 * Wrapper around the SparkFun MAX3010x library for the ESP32 Hospital Watch.
 * Provides HR, SpO2, and die temperature from a MAX30102 finger sensor.
 *
 * Hardware: MAX30102 connected via I2C
 * Library:  SparkFun MAX3010x Sensor Library
 *           platformio.ini → lib_deps: sparkfun/SparkFun MAX3010x Sensor Library
 *
 * I2C PINS — change these to match your hardware wiring.
 * Must NOT conflict with existing buses:
 *   Shared Bus 0 (touch + IMU): SDA=GPIO47, SCL=GPIO48  (ESP-IDF driver)
 *   Shared Bus 1 (NFC PN532):   SDA=GPIO16, SCL=GPIO17
 *
 * @version 1.0.0
 */

#ifndef MAX30102_MANAGER_H
#define MAX30102_MANAGER_H

#include <Arduino.h>
#include <Wire.h>
#include "MAX30105.h"       // SparkFun MAX3010x
#include "spo2_algorithm.h" // SparkFun SpO2 algorithm
#include "heartRate.h"      // SparkFun beat-detection algorithm

// ── I2C pin configuration ──────────────────────────────────────────────────
// Adjust to match your actual wiring.
#ifndef MAX30102_SDA_PIN
#define MAX30102_SDA_PIN  4   // GPIO 4 (was MODE_SELECT_PIN — now free)
#endif
#ifndef MAX30102_SCL_PIN
#define MAX30102_SCL_PIN  5   // GPIO 5
#endif

// ── Algorithm buffer ──────────────────────────────────────────────────────
// SpO2 algorithm needs at least 100 samples. Keep at 100.
#define MAX30102_BUFFER_LEN  100

class MAX30102Manager {
public:
    MAX30102Manager()
        : _heartRate(0), _spO2(0), _dieTemp(0.0f),
          _valid(false), _connected(false), _bufIdx(0)
    {}

    // ── Initialization ─────────────────────────────────────────────────────
    /**
     * Initialize the sensor on a dedicated TwoWire bus (Wire1).
     * Wire1.begin(sda, scl) is called here so the caller only needs begin().
     *
     * @param sda_pin   SDA GPIO (default MAX30102_SDA_PIN)
     * @param scl_pin   SCL GPIO (default MAX30102_SCL_PIN)
     * @return true if sensor found and configured
     */
    bool begin(int sda_pin = MAX30102_SDA_PIN, int scl_pin = MAX30102_SCL_PIN) {
        // Use Wire1 so we don't interfere with any existing Wire (Wire0) usage
        Wire1.begin(sda_pin, scl_pin);

        if (!_sensor.begin(Wire1, I2C_SPEED_FAST)) {
            Serial.println("❌ MAX30102 not found — check SDA/SCL wiring and power");
            _connected = false;
            return false;
        }

        // Sensor configuration:
        //   LED power   : 60 mA  (safe for finger clip; reduce for reflective wrist use)
        //   Sample avg  : 4      (4-sample hardware averaging → effective 25 SPS at 100 SPS ODR)
        //   LED mode    : 2      (red + IR — SpO2 mode)
        //   Sample rate : 100 SPS
        //   Pulse width : 411 µs (18-bit ADC resolution)
        //   ADC range   : 4096 nA full-scale
        _sensor.setup(60, 4, 2, 100, 411, 4096);
        _sensor.setPulseAmplitudeRed(60);
        _sensor.setPulseAmplitudeIR(60);
        _sensor.setPulseAmplitudeGreen(0); // MAX30102 has no green channel

        _bufIdx    = 0;
        _valid     = false;
        _connected = true;
        Serial.printf("✅ MAX30102 initialized (SDA=GPIO%d, SCL=GPIO%d)\n", sda_pin, scl_pin);
        return true;
    }

    // ── Sampling ───────────────────────────────────────────────────────────
    /**
     * Read available samples from the sensor FIFO and run the algorithm
     * once the buffer is full (every MAX30102_BUFFER_LEN samples).
     *
     * Call this every loop iteration (or at least every few ms).
     *
     * @return true when HR/SpO2 were recalculated (every ~4 seconds at 25 eff. SPS)
     */
    bool update() {
        if (!_connected) return false;

        bool updated = false;

        while (_sensor.available()) {
            _irBuf[_bufIdx]  = _sensor.getIR();
            _redBuf[_bufIdx] = _sensor.getRed();
            _sensor.nextSample();
            _bufIdx++;

            if (_bufIdx >= MAX30102_BUFFER_LEN) {
                _runAlgorithm();
                _bufIdx  = 0;
                updated  = true;
            }
        }

        return updated;
    }

    // ── Getters ────────────────────────────────────────────────────────────
    /** Last computed heart rate in BPM. 0 if not yet valid. */
    int   getHeartRate()     const { return _heartRate; }

    /** Last computed SpO2 in %. 0 if not yet valid. */
    int   getSpO2()          const { return _spO2; }

    /**
     * Sensor die temperature in °C.
     * NOTE: This is NOT skin/body temperature — it reflects the chip's
     *       internal die temp (~30–38 °C range, close to finger skin temp
     *       but not clinically accurate). Use a dedicated temp sensor
     *       (e.g. MAX30205, MLX90614) for accurate skin temperature.
     */
    float getDieTemperature() const { return _dieTemp; }

    /**
     * true if the last algorithm run produced valid HR and SpO2.
     * Becomes false if the finger is removed or signal is too noisy.
     */
    bool  isValid()           const { return _valid; }

    /** true if sensor responded on I2C during begin(). */
    bool  isConnected()       const { return _connected; }

    /**
     * Most recent raw IR value (for waveform display).
     * Returns 0 if not connected.
     */
    uint32_t getLatestIR() {
        if (!_connected) return 0;
        return _sensor.getIR();
    }

private:
    MAX30105 _sensor;

    uint32_t _irBuf[MAX30102_BUFFER_LEN];
    uint32_t _redBuf[MAX30102_BUFFER_LEN];
    int      _bufIdx;

    int   _heartRate;
    int   _spO2;
    float _dieTemp;
    bool  _valid;
    bool  _connected;

    void _runAlgorithm() {
        int32_t  hrRaw   = 0;
        int8_t   hrValid = 0;
        int32_t  spO2Raw = 0;
        int8_t   spValid = 0;

        maxim_heart_rate_and_oxygen_saturation(
            _irBuf, MAX30102_BUFFER_LEN,
            _redBuf,
            &spO2Raw, &spValid,
            &hrRaw,   &hrValid
        );

        if (hrValid && hrRaw > 20 && hrRaw < 220) {
            _heartRate = (int)hrRaw;
        }
        if (spValid && spO2Raw > 70 && spO2Raw <= 100) {
            _spO2 = (int)spO2Raw;
        }
        _valid = (hrValid == 1 && spValid == 1);

        // Read die temperature once per algorithm cycle
        _dieTemp = _sensor.readTemperature(); // °C
    }
};

#endif // MAX30102_MANAGER_H
