# ESP32 Hospital Watch - Firmware Changelog

All notable changes to the ESP32 Hospital Watch firmware will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [5.4.0] - 2025-01-10

### Added - Remote Device Configuration & Management
- **17 MQTT Command Handlers** for complete remote device control
- **Configuration Parameters** with NVS persistence:
  - `displayBrightness` (0-100%, default: 100%)
  - `waveformStreamingEnabled` (default: true)
  - `samplingRate` (100-1000 Hz, default: 250 Hz)
  - `vitalsTransmissionInterval` (1-60s, default: 5s)
  - `debugModeEnabled` (default: false)
  - `ledAlertsEnabled` (default: true)
- **Configurable Alert Thresholds** for all vital signs:
  - Heart Rate (HR): min/max
  - SpO2: min/max
  - Temperature: min/max
  - Blood Pressure Systolic: min/max
  - Blood Pressure Diastolic: min/max
  - Respiratory Rate (RR): min/max

### Commands Implemented
#### Configuration Commands (7)
1. `setDisplayBrightness` - Set display brightness (0-100%)
2. `setWaveformStreaming` - Enable/disable ECG/EEG streaming
3. `setSamplingRate` - Set sampling rate (100-1000 Hz)
4. `setVitalsInterval` - Set vitals transmission interval (1-60s)
5. `setDebugMode` - Enable/disable debug logging
6. `setAlertThreshold` - Configure vital sign alert thresholds
7. `setLEDAlerts` - Enable/disable LED visual alerts

#### Management Commands (7)
8. `getDeviceStatus` - Get comprehensive device status (battery, memory, uptime, connectivity, config, vitals)
9. `clearOfflineQueue` - Clear SPIFFS offline message queue
10. `syncTime` - Force NTP time synchronization
11. `setWaveformMode` - Switch between ECG/EEG modes remotely
12. `reboot` - Remote device reboot
13. `unassign` - Unassign device from patient
14. `custom` - Extensible custom command handler

#### Existing Commands (3)
15. `ping` - Health check
16. `waveformCalibrate` - Trigger waveform calibration
17. `assign` - Assign device to patient

### Changed
- **Vitals Transmission Interval**: Now configurable (was hardcoded to 5s)
- **Waveform Streaming**: Can be enabled/disabled remotely (was always on)
- **Sampling Rate**: Adjustable via MQTT (was hardcoded to 250 Hz)
- **Display Brightness**: Remotely controllable via MQTT
- **Command ACK Format**: Enhanced with optional `data` field for status responses

### Technical Details
- **Configuration Persistence**: All settings saved to NVS flash, survive reboots
- **Configuration Loading**: Settings loaded at boot and applied to runtime behavior
- **Validation**: All commands validate parameters with detailed error messages
- **Error Handling**: Commands return success/error status with descriptive messages
- **Integration**: Full compatibility with backend REST API (`device_commands_api.py`)

### Files Modified
- `esp32_hospital_watch_complete.ino`:
  - Lines 268-294: New configuration variables
  - Lines 1050-1394: Command handler functions
  - Lines 2155-2246: MQTT command router
  - Lines 2693-2738: Configuration persistence
  - Lines 1557-1559: Configurable vitals interval
  - Lines 1615: Waveform streaming enable/disable
  - Lines 1003-1029: Enhanced command acknowledgment

---

## [5.3.0] - 2025-01-09

### Added - LVGL Display Integration
- **DisplayManager** class for AMOLED display control
- **UIScreens** class for multi-screen UI management
- **TouchHandler** class for gesture recognition
- **Real-time Vitals Display** on LVGL GUI
- **Touch UI** with 4 screens:
  1. Home Screen - Vitals overview with colored boxes
  2. Waveform Screen - Real-time ECG/EEG waveforms
  3. Alerts Screen - Active alerts list
  4. Settings Screen - Device configuration
- **Connection Status Indicators** on UI
- **Display Brightness Control** helper function (0-100% range)

### Hardware Support
- Waveshare ESP32-S3-Touch-AMOLED-1.64 (280×456 AMOLED)
- FT3168 touch controller via I2C Bus 0
- PN532 NFC module via I2C Bus 1 (separate bus to avoid conflicts)

---

## [5.2.14] - 2025-01-08

### Added - Blood Pressure Monitoring
- **Blood Pressure Vitals**: Systolic and diastolic readings
- **MQTT Transmission**: BP data sent with vitals messages
- **TimescaleDB Storage**: Backend stores BP in `vitals_realtime` table
- Global variables: `bloodPressureSystolic`, `bloodPressureDiastolic`
- Serial debug output includes BP values (e.g., "BP=120/80")

---

## [5.2.13] - 2025-01-07

### Fixed - CRITICAL: Non-Blocking Calibration
- **Bug**: Calibration command caused 3.7s freeze (blocked waveform streaming)
- **Fix**: Non-blocking calibration with flag-based state machine
- **Result**: Waveforms continue streaming during calibration

### Added
- **EEG Calibration Pulse Support**: 100μV calibration pulse for EEG mode
- **Mode-Specific Calibration**: Different pulse amplitudes for ECG (1mV) and EEG (100μV)
- Calibration state tracking: `calibrationRequested`, `calibrationCommandId`, `calibrationStartMillis`

---

## [5.2.12] - 2025-01-06

### Fixed - CRITICAL: Dynamic Mode Switching
- **Bug**: Simulator mode only set at boot, never updated when GPIO pin changed
- **Symptom**: Swapping ECG↔EEG cable → frontend shows correct mode label but wrong waveforms
- **Fix**: Check GPIO pin every 1s before `simulator.update()` and call `setMode()` dynamically
- **Result**: Mode switching now works correctly - waveforms match current GPIO pin state

---

## [5.2.11] - 2025-01-05

### Fixed - MEDICAL ACCURACY: Channel-Specific Frequency Mixing
- **Bug**: All EEG channels used identical frequency weights → identical waveforms
- **Medical Inaccuracy**: Brain regions have different dominant frequencies
- **Fix**: Anatomically correct frequency mixing:
  - **Frontal (Fp1/Fp2)**: Beta-dominant (beta×0.6 + alpha×0.3) - fast oscillations
  - **Central (C3/C4)**: Mixed (alpha×0.5 + beta×0.4)
  - **Occipital (O1/O2)**: Alpha-dominant (alpha×0.8 + beta×0.1) - slow oscillations
- **Result**: Frontal shows fast beta activity, occipital shows slow alpha rhythms

---

## [5.2.10] - 2025-01-04

### Fixed - CRITICAL: EEG Phase Increment Timing
- **Bug**: `generateEEGSample()` called 8 times per sample → phase advanced 8× faster
- **Symptom**: 84 Hz frequency instead of 10.5 Hz (compressed noise, not alpha waves)
- **Fix**: New `generateEEGSampleWithPhase()` method + phase update outside channel loop
- **Result**: EEG now shows smooth 10.5 Hz alpha waves

---

## [5.2.9] - 2025-01-03

### Fixed - CRITICAL: Simulator Mode Initialization
- **Bug**: Simulator defaulted to ECG mode, never changed despite GPIO state
- **Symptom**: GPIO 4 LOW generated ECG waveforms instead of EEG
- **Fix**: Set simulator mode at startup based on `MODE_SELECT_PIN` (GPIO 4)
- **Result**: GPIO 4 LOW → EEG mode, GPIO 4 HIGH → ECG mode

---

## [5.2.8] - 2025-01-02

### Fixed - CRITICAL: DC Offset Removal for Derived Leads
- **Bug**: Derived leads (Lead III, aVR, aVL, aVF) calculated with ADC absolute values
- **Issue**: 24-bit ADC midpoint (8388608) caused incorrect lead derivations
- **Fix**: Subtract ADC midpoint before calculations, then convert back to ADC range
- **Result**: Derived leads now show correct ECG morphology

---

## [5.2.7] - 2025-01-01

### Fixed - CRITICAL: Augmented Lead Formulas
- **Bug**: Incorrect operator precedence in aVL/aVF calculations
- **Issue**: Missing Goldberger amplification (1.5× multiplier)
- **Fix**:
  - Proper operator precedence: `(leadI - leadII) / 2` → `leadI - (leadII / 2)`
  - Goldberger amplification: `(leadI - leadII/2) * 1.5`
- **Result**: Augmented leads (aVR, aVL, aVF) now medically accurate

---

## [5.2.6] - 2024-12-31

### Fixed - CRITICAL: SPIFFS File Deletion
- **Bug**: `SPIFFS.remove()` called with basename instead of full path
- **Root Cause**: V-lead waveform compression (files not deleted, filled SPIFFS)
- **Fix**: Use full file path for `SPIFFS.remove()`
- **Verification**: Added "(deleted)" suffix to log messages

### Added
- **Vitals Sequence Counter**: Message ID for tracking vitals messages

---

## [5.2.5] - 2024-12-30

### Added - Waveform Bandwidth Optimization
- **Delta Encoding**: Store baseline + deltas instead of absolute values
- **Bandwidth Reduction**: 51% savings (9.5 MB/s → 4.6 MB/s for 500 watches)
- **Field Naming**: Standardized to `leadI`, `leadII`, `leadIII`, `Fp1`, `Fp2`, `F3`, `F4`, `C3`, `C4`, `O1`, `O2`
- **Duration Field**: Added 0.1s duration field for 100ms packets

---

## [5.2.4] - 2024-12-29

### Fixed - P0 CRITICAL: Offline Patient Monitoring
- **Bug**: Patient monitoring stopped when WiFi/MQTT disconnected
- **Fix**: Removed `wifiConnected` guards from vitals/waveform generation
- **Result**: Vitals and waveforms continue generating offline (queued to SPIFFS)

### Fixed - P1 MEDIUM: millis() Overflow Protection
- **Bug**: millis() overflows after 49.7 days → timing logic breaks
- **Fix**: Cast all millis() comparisons to `unsigned long`
- **Result**: Device runs correctly for 49.7+ day uptime

### Fixed - P1 MEDIUM: Non-Blocking LED Alerts
- **Bug**: LED alerts used `delay()` → blocked waveform streaming
- **Fix**: State machine for LED flashing (no `delay()` calls)
- **Result**: LED alerts don't interrupt waveform streaming

### Added - P2 LOW: Debug Logging Flag
- **Feature**: `DEBUG_WAVEFORMS` constant to reduce serial spam in production
- **Default**: `false` (minimal logging)

---

## [5.2.3] - 2024-12-28

### Added - Auto WiFi Reconnection
- **Feature**: Auto-reconnect to saved WiFi when network becomes available in captive portal mode
- **Behavior**: Scans for saved SSID every 60s, auto-connects if found
- **UX**: No manual intervention needed when WiFi comes back online

---

## [5.2.2] - 2024-12-27

### Fixed - Bug #1: Offline Queue Early Exit
- **Bug**: `sendVitals()`, `sendAlert()`, `sendWaveformStream()` exited early when MQTT disconnected
- **Fix**: Removed early returns, always queue to SPIFFS when offline

### Fixed - Bug #2: Disconnect Counter Persistence
- **Bug**: `totalDisconnects` persisted across reboots (inflated count)
- **Fix**: Always reset `totalDisconnects = 0` on boot

### Fixed - Bug #5: Device Unresponsive Alert Spam
- **Bug**: `deviceUnresponsiveAlert` sent repeatedly every 5 minutes
- **Fix**: Added `deviceUnresponsiveAlertSent` flag (only triggers once)

### Fixed - Bug #6: Frequent Disconnects Alert Spam
- **Bug**: `frequentDisconnectsAlert` sent repeatedly
- **Fix**: Added `frequentDisconnectsAlertSent` flag (only triggers once)

---

## [5.2.1] - 2024-12-26

### Added - MQTT QoS 1 with Retry Logic
- **QoS 1**: MQTT messages now require acknowledgment
- **Retry Logic**: 3 attempts with exponential backoff (100ms, 200ms, 400ms)
- **Reliability**: Prevents message loss during network instability

### Added - Offline Data Buffering
- **SPIFFS Queue**: Vitals, alerts, and waveforms saved to flash when offline
- **Batch Transmission**: Queued messages sent every 30s when reconnected
- **Persistence**: Data survives device reboots

---

## [5.2.0] - 2024-12-25

### Added - Real-Time Waveform Streaming
- **Micro-Batch Generation**: 10 samples every 20ms at 500 Hz
- **MQTT Streaming**: Waveforms published to `hospital/devices/{deviceId}/stream`
- **ECG**: 8-lead ECG (I, II, III, aVR, aVL, aVF, V1-V6) - NOTE: V-leads currently simulated
- **EEG**: 8-channel EEG (Fp1, Fp2, F3, F4, C3, C4, O1, O2)

### Added - NFC Support
- **PN532 I2C**: NFC reader for badges, wristbands, room tags
- **IRQ Mode**: Interrupt-driven card detection
- **Use Cases**: Staff authentication, patient identification, room tracking

### Changed
- **ArduinoJson**: Upgraded to v7 compatibility

---

## [5.1.0] - 2024-12-24

### Added - Physiological Simulator
- **Realistic Vitals**: Heart rate, SpO2, temperature, respiratory rate, blood pressure
- **Waveform Generation**: Realistic ECG and EEG waveforms
- **PhysiologicalSimulator Class**: Centralized simulation logic

---

## [5.0.0] - 2024-12-23

### Added - Certificate-Based Authentication
- **HTTPS Provisioning**: One-time code for certificate retrieval
- **mTLS**: Mutual TLS for MQTT authentication (port 8883)
- **Certificate Storage**: Client cert, private key, CA cert stored in SPIFFS
- **Security**: Removed hardcoded credentials

### Added - Core Features
- **Captive Portal**: Auto-redirects to WiFi setup page
- **Auto WiFi Scan**: Dropdown list of available networks
- **NTP Sync**: ISO 8601 timestamps for all MQTT messages
- **MQTT Topics**:
  - `hospital/devices/{deviceId}/vitals`
  - `hospital/devices/{deviceId}/alerts`
  - `hospital/devices/{deviceId}/heartbeat`
- **8 Device-Level Alerts**: Critical alerts detected on-device

---

## Version History Summary

| Version | Release Date | Major Changes |
|---------|-------------|---------------|
| **5.4.0** | 2025-01-10 | Remote device configuration (17 MQTT commands) |
| **5.3.0** | 2025-01-09 | LVGL display integration, touch UI |
| **5.2.14** | 2025-01-08 | Blood pressure monitoring |
| **5.2.13** | 2025-01-07 | Non-blocking calibration, EEG calibration pulse |
| **5.2.12** | 2025-01-06 | Dynamic ECG/EEG mode switching |
| **5.2.11** | 2025-01-05 | Anatomically correct EEG frequency mixing |
| **5.2.10** | 2025-01-04 | EEG phase increment timing fix |
| **5.2.9** | 2025-01-03 | Simulator mode initialization fix |
| **5.2.8** | 2025-01-02 | DC offset removal for derived ECG leads |
| **5.2.7** | 2025-01-01 | Augmented lead formula corrections |
| **5.2.6** | 2024-12-31 | SPIFFS deletion fix, vitals sequence counter |
| **5.2.5** | 2024-12-30 | Delta encoding (51% bandwidth reduction) |
| **5.2.4** | 2024-12-29 | Offline monitoring (P0), millis() overflow (P1), non-blocking LED (P1) |
| **5.2.3** | 2024-12-28 | Auto WiFi reconnection |
| **5.2.2** | 2024-12-27 | Offline queue fixes, alert spam prevention |
| **5.2.1** | 2024-12-26 | MQTT QoS 1, offline buffering |
| **5.2.0** | 2024-12-25 | Waveform streaming, NFC support |
| **5.1.0** | 2024-12-24 | Physiological simulator |
| **5.0.0** | 2024-12-23 | Certificate-based auth, captive portal |

---

## Unreleased

### Planned Features
- **V-Lead Measurement**: Replace V-lead simulation with actual chest electrode readings
- **Advanced Alerts**: Machine learning-based arrhythmia detection
- **Battery Optimization**: Deep sleep mode for extended battery life
- **OTA Updates**: Over-the-air firmware updates via MQTT
- **Multi-Language Support**: UI translations
- **Custom Waveform Filters**: User-configurable ECG/EEG filters

---

## Notes

- **Semantic Versioning**: `MAJOR.MINOR.PATCH`
  - **MAJOR**: Breaking changes (e.g., API changes)
  - **MINOR**: New features (backward compatible)
  - **PATCH**: Bug fixes (backward compatible)
- **CRITICAL Fixes**: Fixes that prevent device malfunction or data corruption
- **P0/P1/P2**: Priority levels (P0 = Critical, P1 = High, P2 = Medium)
