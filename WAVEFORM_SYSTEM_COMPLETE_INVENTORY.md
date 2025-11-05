# Waveform System Complete Inventory
**Generated:** 2025-11-02
**Purpose:** Comprehensive list of all waveform-related files, tables, and components

---

## DATABASE TABLES (TimescaleDB)

### 1. `waveform_snapshots` (TimescaleDB Hypertable)
**Location:** `hospital_timeseries` database
**Migration:** `hospital-backend/migrations/010_create_neural_waveform_tables.sql`
**Purpose:** Store multi-channel ECG/EEG waveform data with TimescaleDB optimization

**Columns:**
- `time` (TIMESTAMPTZ) - Snapshot timestamp
- `patientId` (UUID) - Patient identifier
- `deviceId` (VARCHAR) - Device identifier
- `mode` (VARCHAR) - 'ecg' or 'eeg'
- `sampleRate` (INTEGER) - Sampling rate in Hz
- `duration` (INTEGER) - Duration in seconds

**ECG Channels (JSONB):**
- `ecgLimbLeads` - Lead I, II, III (delta-encoded: {baseline, deltas})
- `ecgPrecordialLeads` - V1-V5 (delta-encoded)
- `ecgDerivedLeads` - aVR, aVL, aVF, V6 (delta-encoded)
- `ecgEvents` - Detected ECG events [{timestamp, type, confidence, location}]

**EEG Channels (JSONB):**
- `eegFrontalChannels` - Fp1, Fp2, F3, F4 (delta-encoded)
- `eegCentralChannels` - C3, C4 (delta-encoded)
- `eegOccipitalChannels` - O1, O2 (delta-encoded)
- `eegAnalysis` - {bandPowers, asymmetry, dominantFrequency}

**Quality & Metadata:**
- `quality` (JSONB) - {overall, leadOff, noise, impedance}
- `sequence` (INTEGER) - Message sequence number
- `compression` (VARCHAR) - Compression method
- `metadata` (JSONB) - Additional metadata

**Indexes:**
- `idx_waveform_snapshots_patient_mode_time` - Patient + mode + time
- `idx_waveform_snapshots_device_time` - Device + time
- `idx_waveform_snapshots_mode_time` - Mode + time

**Policies:**
- Retention: 7 years (HIPAA compliance)
- Chunk interval: 1 hour

---

### 2. `vitals_realtime` (TimescaleDB Hypertable)
**Location:** `hospital_timeseries` database
**Migration:** `hospital-backend/migrations/010_create_neural_waveform_tables.sql`
**Purpose:** High-frequency vitals updates with ECG/EEG analysis

**Columns:**
- `time` (TIMESTAMPTZ) - Reading timestamp
- `patientId` (UUID) - Patient identifier
- `deviceId` (VARCHAR) - Device identifier
- `mode` (VARCHAR) - 'ecg' or 'eeg'

**Basic Vitals:**
- `heartRate` (INTEGER) - BPM
- `respiratoryRate` (INTEGER) - Breaths per minute
- `skinTemperature` (DECIMAL) - Celsius
- `oxygenSaturation` (INTEGER) - SpO2 percentage
- `batteryLevel` (INTEGER) - Battery percentage
- `signalQuality` (DECIMAL) - Quality 0-1

**ECG Analysis:**
- `rrInterval` (INTEGER) - RR interval in ms
- `qrsDuration` (INTEGER) - QRS duration in ms
- `qtInterval` (INTEGER) - QT interval in ms
- `axis` (INTEGER) - Heart axis in degrees
- `rhythm` (VARCHAR) - Detected rhythm
- `stSegment` (VARCHAR) - ST segment analysis

**EEG Analysis:**
- `alphaPower` (DECIMAL) - Alpha band power
- `betaPower` (DECIMAL) - Beta band power
- `thetaPower` (DECIMAL) - Theta band power
- `deltaPower` (DECIMAL) - Delta band power
- `gammaPower` (DECIMAL) - Gamma band power
- `dominantFrequency` (DECIMAL) - Dominant frequency
- `seizureActivity` (BOOLEAN) - Seizure detection flag

**Indexes:**
- `idx_vitals_realtime_patient_time` - Patient + time
- `idx_vitals_realtime_device_time` - Device + time

**Policies:**
- Retention: 90 days
- Chunk interval: 30 minutes

---

### 3. `vitals_1min` (Continuous Aggregate)
**Location:** `hospital_timeseries` database
**Migration:** `hospital-backend/migrations/010_create_neural_waveform_tables.sql`
**Purpose:** 1-minute aggregated vitals for trend analysis

**Aggregations:**
- `avg_heart_rate`, `max_heart_rate`, `min_heart_rate`
- `avg_respiratory_rate`
- `avg_temperature`
- `avg_oxygen_saturation`
- `avg_signal_quality`
- `reading_count`

**Refresh Policy:** Every 1 minute

---

### 4. `neural_events` (TimescaleDB Hypertable)
**Location:** `hospital_timeseries` database
**Migration:** `hospital-backend/migrations/010_create_neural_waveform_tables.sql`
**Purpose:** Track arrhythmias, seizures, and other neural events

**Columns:**
- `time` (TIMESTAMPTZ) - Event timestamp
- `patientId` (UUID) - Patient identifier
- `deviceId` (VARCHAR) - Device identifier
- `eventType` (VARCHAR) - Event type (bradycardia, seizure, etc.)
- `severity` (VARCHAR) - low/medium/high/critical
- `confidence` (DECIMAL) - Detection confidence 0-1
- `mode` (VARCHAR) - 'ecg' or 'eeg'
- `sampleRate` (INTEGER) - Sample rate during event
- `duration` (INTEGER) - Event duration
- `context` (JSONB) - Event context (vitals at time of event)
- `waveform` (JSONB) - Waveform snippet around event
- `actions` (JSONB) - Recommended clinical actions
- `acknowledged` (BOOLEAN) - Acknowledgement status
- `acknowledgedBy` (VARCHAR) - Who acknowledged
- `acknowledgedAt` (TIMESTAMPTZ) - When acknowledged
- `resolved` (BOOLEAN) - Resolution status
- `resolvedAt` (TIMESTAMPTZ) - When resolved
- `metadata` (JSONB) - Additional metadata

**Indexes:**
- `idx_neural_events_patient_time` - Patient + time
- `idx_neural_events_type_severity` - Event type + severity + time
- `idx_neural_events_unresolved` - Unresolved events only

**Policies:**
- Retention: 7 years (HIPAA compliance)
- Chunk interval: 24 hours

---

## BACKEND FILES

### Data Models

#### 1. `hospital-backend/app/models/neural_vitals.py`
**Purpose:** Pydantic models for ECG/EEG waveform data structures
**Key Classes:**
- `SignalQuality` - Signal quality metrics
- `ECGAnalysis` - ECG analysis results
- `ECGLeadValues` - Current ECG lead values
- `EEGBandPowers` - EEG frequency band powers
- `EEGAnalysis` - EEG analysis results
- `EEGChannelValues` - Current EEG channel values
- `ChannelData` - Delta-encoded channel data
- `ECGLimbLeads` - ECG limb leads (I, II, III)
- `ECGPrecordialLeads` - ECG precordial leads (V1-V5)
- `ECGDerivedLeads` - ECG derived leads (aVR, aVL, aVF, V6)
- `ECGEvent` - Detected ECG event
- `ECGWaveformData` - Complete 12-lead ECG waveform
- `EEGFrontalChannels` - EEG frontal channels (Fp1, Fp2, F3, F4)
- `EEGCentralChannels` - EEG central channels (C3, C4)
- `EEGOccipitalChannels` - EEG occipital channels (O1, O2)
- `EEGWaveformData` - Complete 8-channel EEG waveform
- `VitalsRealtimeMessage` - Real-time vitals + waveform message (MQTT)
- `WaveformSnapshotMessage` - Waveform snapshot message (MQTT)
- `NeuralEventMessage` - Neural event message (MQTT)
- `VitalsRealtimeDB` - Database model for vitals_realtime
- `WaveformSnapshotDB` - Database model for waveform_snapshots
- `NeuralEventDB` - Database model for neural_events

**Standards:**
- All camelCase naming
- Delta encoding support
- Medical-grade data structures
- MQTT + Database dual models

---

### Services

#### 2. `hospital-backend/app/services/websocket_manager.py`
**Purpose:** WebSocket connection management and real-time data streaming
**Key Functions:**
- `sendWaveformStream()` - Stream waveform data to frontend (line 190)
- `processWaveformData()` - Process waveform before sending (line 353)
- `decompressChannelData()` - Decompress delta-encoded data (line 292)
- `convertADCToMillivolts()` - Convert ADC to mV for ECG (line 312)
- `convertADCToMicrovolts()` - Convert ADC to μV for EEG (line 335)

**Processing Pipeline:**
1. Receive waveform from MQTT
2. Decompress delta encoding (if used)
3. Convert ADC → physical units (mV/μV)
4. Broadcast to WebSocket subscribers

**ESP32 v5.2 Update:**
- Lines 375-437: ESP32 v5.2 sends PLAIN ARRAYS (not delta-encoded)
- Backend passes through RAW ADC arrays unchanged
- Frontend converts ADC → mV/μV (matches ESP32 approach)

---

#### 3. `hospital-backend/app/services/mqtt_service.py`
**Purpose:** MQTT message handling and device data processing
**Waveform References:**
- Handles waveform messages from ESP32 devices
- Routes waveform data to WebSocket manager
- Validates device assignments before streaming

---

#### 4. `hospital-backend/app/services/ecg_analysis_service.py`
**Purpose:** Backend ECG waveform analysis
**Key Features:**
- Arrhythmia detection
- QRS complex analysis
- ST segment analysis
- RR interval calculation
- **ALL medical analysis on backend only**

---

#### 5. `hospital-backend/app/services/eeg_analysis_service.py`
**Purpose:** Backend EEG waveform analysis
**Key Features:**
- Seizure detection
- Band power calculation
- Dominant frequency analysis
- Hemispheric asymmetry
- **ALL medical analysis on backend only**

---

#### 6. `hospital-backend/app/services/alert_detection_service.py`
**Purpose:** Medical alert detection from vitals and waveforms
**Waveform Analysis:**
- Line 8: `WaveformAnalysis` dataclass
- Line 38: `waveformAnalysis` parameter in `detectAlerts()`
- Lines 65-72: Waveform-based alert detection
- Lines 85-92: STEMI detection from ST elevation
- Lines 95-102: Seizure detection from EEG
- Lines 115-125: Atrial fibrillation detection from RR variability
- Lines 138-145: Long QTc interval detection

---

### Migrations

#### 7. `hospital-backend/migrations/010_create_neural_waveform_tables.sql`
**Purpose:** Create TimescaleDB tables for waveform storage
**Tables Created:**
- `waveform_snapshots` (line 8)
- `vitals_realtime` (line 87)
- `vitals_1min` continuous aggregate (line 159)
- `neural_events` (line 202)

**Features:**
- Delta-encoded JSONB storage
- TimescaleDB hypertables
- Compression policies
- Retention policies (7 years HIPAA)
- Continuous aggregates

---

#### 8. `hospital-backend/migrations/010_create_neural_waveform_tables_simple.sql`
**Purpose:** Simplified version without advanced TimescaleDB features
**Use Case:** Development/testing environments

---

## FRONTEND FILES

### Configuration

#### 9. `hospital-display-app/src/config/ecgConfig.ts`
**Purpose:** Single source of truth for all ECG/EEG configuration constants
**Medical Standards:**
- `ECG_SCALE_MM_PER_MV = 10` - 10mm = 1mV (ISO 11073)
- `EEG_SCALE_UV_PER_MM = 50` - 50μV/mm sensitivity
- `PAPER_SPEED_MM_PER_S = 25` - 25mm/s standard
- `SAMPLE_RATE_HZ = 500` - 500Hz sampling rate

**ADC Conversion:**
- `ADC_MIDPOINT = 8388608` - 24-bit ADC zero point
- `ECG_ADC_SCALE_FACTOR = 100000` - ECG scale factor
- `EEG_ADC_SCALE_FACTOR = 1000` - EEG scale factor

**Calibration Pulse:**
- `CALIBRATION_HEAD_DURATION_MS = 200` - Pre-pulse baseline
- `CALIBRATION_PULSE_DURATION_MS = 200` - Pulse duration
- `CALIBRATION_TAIL_DURATION_MS = 200` - Post-pulse baseline
- `CALIBRATION_AMPLITUDE_MV = 1.0` - 1mV standard pulse

**Buffer Settings:**
- `BUFFER_TIME_SECONDS = 12` - 12 seconds circular buffer
- `BUFFER_MAX_SAMPLES = 6000` - 500Hz × 12s

**Layout Options:**
- `LAYOUT_SINGLE = 1` - Single lead view
- `LAYOUT_QUAD = 4` - 4-lead grid
- `LAYOUT_NINE = 9` - 9-lead grid
- `LAYOUT_TWELVE = 12` - 12-lead complete ECG

---

### Utilities

#### 10. `hospital-display-app/src/utils/medicalWaveformUtils.ts`
**Purpose:** Medical-grade waveform rendering utilities
**Key Functions:**

**DPI Detection:**
- `getScreenDPI()` - Auto-detect screen DPI (line 45)
- `mmToPixels()` - Convert mm to pixels (line 88)

**ADC Conversion:**
- `adcToMillivolts()` - Convert ADC to mV for ECG (line 99)
- `adcToMicrovolts()` - Convert ADC to μV for EEG (line 108)

**Waveform Rendering:**
- `renderECGWaveform()` - Render ECG with fixed 10mm/mV scale (line 121)
- `renderEEGWaveform()` - Render EEG with fixed 50μV/mm scale (line 170)
- `renderWaveform()` - Adaptive wrapper (line 219)

**Canvas Rendering:**
- `renderWaveformCanvas()` - Canvas rendering with fixed scale (line 320)
- `renderWaveformSegment()` - Segment rendering for circular buffer (line 412)
- `drawMedicalGrid()` - Medical-grade ECG/EEG grid (line 457)
- `drawCalibrationPulse()` - 1mV calibration pulse (line 533)

**Grid Utilities:**
- `calculateMedicalGridSpacing()` - Grid spacing calculation (line 291)
- `generateECGCalibrationPulse()` - SVG calibration pulse (line 262)

**Medical Standards:**
- Fixed scales (NOT auto-scaling)
- 10mm = 1mV for ECG
- 50μV/mm for EEG
- 25mm/s paper speed
- Real ECG paper grid colors

---

### Services

#### 11. `hospital-display-app/src/services/WebSocketService.ts`
**Purpose:** WebSocket connection management and message routing
**Key Features:**
- Singleton pattern (line 40)
- Auto-reconnect with backoff (line 331)
- Patient subscription management (line 221)
- Message routing to components (line 299)
- Waveform message type support (line 22)

**Waveform Handling:**
- `waveformStream` message type
- Routes waveform data to subscribers
- Supports per-patient subscriptions

---

#### 12. `hospital-display-app/src/services/WaveformCacheService.ts`
**Purpose:** Waveform data caching with IndexedDB persistence
**Key Features:**
- IndexedDB + memory cache (line 24)
- 10-minute TTL (line 23)
- Per-patient/mode caching (line 51)
- Cache hit/miss logging (line 98, 106, 116)

**Functions:**
- `saveWaveform()` - Save to cache (line 58)
- `getWaveform()` - Retrieve from cache (line 92)
- `invalidateCache()` - Clear specific cache (line 178)
- `clearAllCache()` - Clear all cache (line 203)
- `getCacheStats()` - Get cache statistics (line 226)

**Use Cases:**
- Instant waveform display on page load
- Persistence across browser refresh
- Reduced backend load

---

### Components

#### 13. `hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx`
**Purpose:** Single-lead waveform canvas component (ICU monitor style)
**Key Features:**
- Circular buffer rendering (line 43)
- Phase 1: Growing mode (line 138)
- Phase 2: Circular sweep mode (line 154)
- Medical-grade grid (line 103)
- Sweep line at write position (line 220)

**Medical Spacing:**
- DPI-aware rendering (line 106)
- 25mm/s paper speed (line 107)
- Fixed vertical scale (line 116-118)

**Rendering:**
- 60fps animation loop (line 57)
- Erase strip behind sweep line (line 194)
- Two-segment circular rendering (line 157-191)

---

#### 14. `hospital-display-app/src/components/PatientCard/PatientCardWaveform.tsx`
**Purpose:** Mini-waveform display on patient cards
**Key Features:**
- SVG rendering (line 136)
- Lead II (ECG) or F3 (EEG) display (line 46)
- Last 125 samples (0.25 seconds) (line 57)
- Medical-grade fixed scale (line 68-74)
- Click to open full ECG viewer (line 88)

**Display:**
- 250px × 60px viewport (line 70-71)
- Medical grid background (line 144)
- Color coding: green=ECG, blue=EEG (line 154)
- Arrhythmia/seizure alerts (line 97, 110)

---

#### 15. `hospital-display-app/src/components/ECGViewer.tsx`
**Purpose:** Full-screen ECG/EEG viewer (legacy, being phased out)
**Status:** Superseded by `ECGViewerContainer.tsx`

---

#### 16. `hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx`
**Purpose:** Full-screen multi-lead ECG/EEG viewer container
**Key Features:**
- Layout selection (1/4/9/12 leads)
- Speed selection (25/50 mm/s)
- Gain selection
- Pause/resume
- Calibration pulse trigger
- Manages multiple `ECGWaveformCanvas` instances

---

#### 17. `hospital-display-app/src/components/ECGViewer/ECGViewerHeader.tsx`
**Purpose:** ECG viewer control panel
**Controls:**
- Layout selector (1/4/9/12 leads)
- Speed selector (25/50 mm/s)
- Gain selector
- Pause/resume button
- Close button

---

#### 18. `hospital-display-app/src/components/ECGViewer/ECGDisplayGrid.tsx`
**Purpose:** Grid layout for multiple ECG/EEG leads
**Layouts:**
- 1-lead: Full screen single waveform
- 4-lead: 2×2 grid
- 9-lead: 3×3 grid
- 12-lead: 3×4 grid + rhythm strip

---

#### 19. `hospital-display-app/src/components/ErrorBoundary.tsx`
**Purpose:** Error boundary for waveform components
**Features:**
- Catches React rendering errors
- Waveform-specific error handling
- Graceful fallback UI

---

### Hooks

#### 20. `hospital-display-app/src/hooks/useECGViewer.ts`
**Purpose:** ECG/EEG viewer state management hook
**Key Features:**
- WebSocket subscription management
- Waveform buffer management (12-lead arrays)
- Calibration pulse handling
- Data buffer refs for canvas access

**Buffer Structure:**
```typescript
dataBufferRef.current = [
  // ECG leads (indices 0-11)
  [], [], [], [], [], [], [], [], [], [], [], [],
  // EEG channels (indices 12-19)
  [], [], [], [], [], [], [], []
]
```

**Lead Mapping:**
- 0-2: Limb leads (I, II, III)
- 3-7: Precordial leads (V1-V5)
- 8-11: Derived leads (aVR, aVL, aVF, V6)
- 12-19: EEG channels (Fp1, Fp2, F3, F4, C3, C4, O1, O2)

---

#### 21. `hospital-display-app/src/hooks/useWebSocket.ts`
**Purpose:** WebSocket connection hook
**Key Features:**
- Auto-connect on mount
- Connection state tracking
- Message subscription
- Auto-cleanup on unmount

---

#### 22. `hospital-display-app/src/hooks/usePatientData.ts`
**Purpose:** Patient data management with WebSocket integration
**Waveform Features:**
- Subscribes to patient vitals + waveforms
- Updates patient state on waveform events
- Integrates with useECGViewer

---

## ESP32 FIRMWARE FILES

### Simulators

#### 23. `esp32_hospital_watch_complete/PhysiologicalSimulator.cpp`
**Purpose:** Physiological data simulation (ECG, EEG, vitals)
**Key Functions:**
- `generateECGData()` - Generate realistic ECG waveforms
- `generateEEGData()` - Generate realistic EEG waveforms
- `simulateVitals()` - Generate vitals (HR, RR, SpO2, temp)

**Waveform Generation:**
- PQRST complex simulation
- Configurable heart rate variability
- Arrhythmia simulation
- EEG frequency bands (alpha, beta, theta, delta)
- Seizure activity simulation

---

#### 24. `esp32_hospital_watch_complete/PhysiologicalSimulator.h`
**Purpose:** PhysiologicalSimulator header file
**Constants:**
- Sample rates
- Amplitude ranges
- Frequency bands
- Noise levels

---

#### 25. `esp32_hospital_watch_complete/ADS1298Simulator.cpp`
**Purpose:** ADS1298 8-channel ECG ADC simulator
**Key Features:**
- 8-channel 24-bit ADC simulation
- Differential input simulation
- Gain simulation
- Noise injection

---

#### 26. `esp32_hospital_watch_complete/ADS1298Simulator.h`
**Purpose:** ADS1298Simulator header file

---

#### 27. `esp32_hospital_watch_complete/MAX86178Simulator.cpp`
**Purpose:** MAX86178 PPG/ECG sensor simulator
**Key Features:**
- PPG waveform simulation
- Multi-wavelength LED simulation
- SpO2 calculation
- Heart rate from PPG

---

#### 28. `esp32_hospital_watch_complete/MAX86178Simulator.h`
**Purpose:** MAX86178Simulator header file

---

#### 29. `esp32_hospital_watch_complete/BMI323Simulator.cpp`
**Purpose:** BMI323 accelerometer/gyroscope simulator
**Key Features:**
- 3-axis acceleration
- Fall detection
- Tremor simulation
- Activity level

---

#### 30. `esp32_hospital_watch_complete/BMI323Simulator.h`
**Purpose:** BMI323Simulator header file

---

#### 31. `esp32_hospital_watch_complete/STS40Simulator.cpp`
**Purpose:** STS40 temperature sensor simulator
**Key Features:**
- Skin temperature simulation
- Fever simulation
- Hypothermia simulation

---

#### 32. `esp32_hospital_watch_complete/STS40Simulator.h`
**Purpose:** STS40Simulator header file

---

#### 33. `esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino`
**Purpose:** Main ESP32 firmware (Arduino sketch)
**Waveform Features:**
- 500Hz sampling rate
- MQTT waveform streaming
- Calibration pulse generation
- 1-second waveform snapshots
- Plain array transmission (v5.2+)

**MQTT Topics:**
- `hospital/devices/{deviceId}/vitals` - Combined vitals + waveform (1s intervals)
- `hospital/devices/{deviceId}/waveform` - Waveform snapshots (10s intervals)
- `hospital/devices/{deviceId}/event` - Neural events (arrhythmias, seizures)

**Calibration Pulse:**
- Head: 200ms flat baseline (0mV)
- Pulse: 200ms at 1mV
- Tail: 200ms flat baseline (0mV)
- Total: 600ms
- Triggered by WebSocket request

---

## DOCUMENTATION FILES

#### 34. `ECG_EEG_WAVEFORM_COMPLETE_AUDIT_2025.md`
**Purpose:** Complete waveform system audit
**Contents:**
- Architecture overview
- Data flow diagrams
- Implementation status
- Known issues
- Future roadmap

---

#### 35. `WAVEFORM_STREAMING_EXPLAINED.md`
**Purpose:** Waveform streaming architecture explanation
**Contents:**
- MQTT → Backend → WebSocket flow
- Message format specifications
- Timing diagrams
- Performance considerations

---

#### 36. `WAVEFORM_STREAMING_WORKING_SUMMARY.md`
**Purpose:** Current working state summary
**Contents:**
- What's working
- What's tested
- What's remaining
- Known bugs

---

#### 37. `WAVEFORM_DATA_PERSISTENCE.md`
**Purpose:** Waveform caching and persistence strategy
**Contents:**
- IndexedDB architecture
- Cache invalidation
- Performance metrics
- Browser compatibility

---

#### 38. `WAVEFORM_RENDERING_DIAGNOSIS.md`
**Purpose:** Waveform rendering troubleshooting guide
**Contents:**
- Common rendering issues
- Debug checklist
- Performance profiling
- Fix recipes

---

#### 39. `WAVEFORM_DISAPPEARS_BUG.md`
**Purpose:** Documentation of waveform disappearance bug
**Status:** FIXED
**Root Cause:** Circular buffer write position calculation
**Fix:** Lines 125-136 in ECGWaveformCanvas.tsx

---

#### 40. `WAVEFORM_NOT_FLOWING_DIAGNOSIS.md`
**Purpose:** Waveform streaming flow diagnosis
**Common Causes:**
- WebSocket not connected
- No patient subscription
- Device not assigned
- MQTT not connected

---

#### 41. `ESP32_WAVEFORM_AMPLITUDE_ANALYSIS.md`
**Purpose:** ESP32 waveform amplitude analysis
**Contents:**
- ADC range analysis
- Scale factor calculation
- Amplitude verification
- Calibration procedures

---

#### 42. `ACTUAL_WAVEFORM_SIZE_CALCULATIONS.md`
**Purpose:** Actual waveform data size calculations
**Contents:**
- Bytes per sample
- Bandwidth requirements
- Storage requirements
- Compression ratios

---

#### 43. `ECG_WAVEFORM_RENDERING_STATUS_AND_FIXES.md`
**Purpose:** ECG waveform rendering status
**Contents:**
- Current rendering approach
- Fixes applied
- Remaining issues
- Future improvements

---

#### 44. `CALIBRATION_PULSE_ANALYSIS.md`
**Purpose:** Calibration pulse analysis
**Contents:**
- Medical standard (1mV, 200ms)
- Implementation details
- Verification procedures
- Troubleshooting

---

#### 45. `CALIBRATION_PULSE_SCALING_BUG.md`
**Purpose:** Calibration pulse scaling bug documentation
**Status:** FIXED
**Root Cause:** Incorrect amplitude scaling
**Fix:** Use mmToPixels() for medical-grade accuracy

---

#### 46. `CALIBRATION_PULSE_TAIL_FIX.md`
**Purpose:** Calibration pulse tail fix documentation
**Status:** FIXED
**Root Cause:** Missing tail segment
**Fix:** Added 200ms tail after pulse

---

#### 47. `SWEEP_LINE_BUG_FIXED.md`
**Purpose:** Sweep line position bug fix
**Status:** FIXED
**Root Cause:** Incorrect write position calculation
**Fix:** Use modulo for circular buffer wrap

---

#### 48. `SWEEP_LINE_BUG_FIX_PLAN.md`
**Purpose:** Sweep line fix implementation plan
**Status:** COMPLETED

---

#### 49. `GRID_SCALING_ANALYSIS.md`
**Purpose:** Medical grid scaling analysis
**Contents:**
- DPI detection
- Pixel-to-mm conversion
- Grid spacing calculations
- Cross-platform compatibility

---

#### 50. `BUG_VERIFICATION_WITH_MATH.md`
**Purpose:** Mathematical verification of bug fixes
**Contents:**
- Geometry calculations
- Scale factor derivations
- Test case results
- Proof of correctness

---

#### 51. `ACTUAL_BUG_CALCULATIONS.md`
**Purpose:** Actual bug root cause calculations
**Contents:**
- Mathematical analysis
- Before/after comparisons
- Measurement data
- Verification tests

---

#### 52. `ECG_ARCHITECTURAL_ANALYSIS_AND_BUGS.md`
**Purpose:** ECG architecture analysis and bug catalog
**Contents:**
- System architecture
- Component interactions
- Known bugs
- Fix priorities

---

#### 53. `ECG_BUGS_CORRECTED_FINAL.md`
**Purpose:** Final list of corrected ECG bugs
**Status:** All fixed
**Bugs Fixed:**
- Calibration pulse scaling
- Sweep line position
- Grid alignment
- Horizontal compression
- Auto-sizing issues

---

#### 54. `ECG_BUGS_STATUS_AND_FIX_PLAN.md`
**Purpose:** ECG bug status and fix roadmap
**Status:** All critical bugs fixed

---

#### 55. `ECG_BUGS_P3_DROPDOWN_REMOVAL_COMPLETE.md`
**Purpose:** P3 dropdown removal completion report
**Status:** COMPLETED
**Change:** Removed confusing P3 dropdown, simplified UI

---

#### 56. `ECG_VIEWER_ACTUAL_RESEARCH.md`
**Purpose:** ECG viewer research and analysis
**Contents:**
- Medical standards research
- Competitor analysis
- Best practices
- Implementation recommendations

---

#### 57. `ECG_VIEWER_COMPREHENSIVE_AUDIT.md`
**Purpose:** Comprehensive ECG viewer audit
**Contents:**
- Full system audit
- All components
- Data flow
- Performance analysis

---

#### 58. `ECG_CRITICAL_BUGS_FIXED.md`
**Purpose:** Critical ECG bug fix summary
**Bugs Fixed:**
- Phase 1 rendering
- Circular buffer wrap
- Calibration pulse
- Grid scaling

---

#### 59. `ECG_AUTOSIZE_CALCULATION.md`
**Purpose:** ECG auto-sizing calculation analysis
**Conclusion:** Auto-sizing NOT appropriate for medical ECG

---

#### 60. `ECG_AUTOSIZE_IMPLEMENTATION_COMPLETE.md`
**Purpose:** Auto-sizing removal completion
**Status:** REMOVED
**Reason:** Medical ECG requires fixed 10mm/mV scale

---

#### 61. `ECG_HALF_SCREEN_DIAGNOSIS.md`
**Purpose:** Half-screen ECG bug diagnosis
**Status:** FIXED
**Root Cause:** Incorrect viewport calculation

---

#### 62. `ECG_HALF_SCREEN_ROOT_CAUSE_ANALYSIS.md`
**Purpose:** Half-screen bug root cause analysis
**Status:** FIXED

---

#### 63. `ECG_CONFIGURATION_AUDIT.md`
**Purpose:** ECG configuration audit
**Findings:** Scattered constants, inconsistent values

---

#### 64. `ECG_CONFIGURATION_CENTRALIZATION_COMPLETE.md`
**Purpose:** Configuration centralization completion
**Status:** COMPLETED
**Result:** All constants in `ecgConfig.ts`

---

#### 65. `FULLSCREEN_ECG_RENDERING_STATUS.md`
**Purpose:** Full-screen ECG rendering status
**Status:** WORKING
**Features:** 1/4/9/12 lead layouts, medical-grade rendering

---

#### 66. `HORIZONTAL_COMPRESSION_BUG_DIAGNOSIS.md`
**Purpose:** Horizontal compression bug diagnosis
**Status:** FIXED
**Root Cause:** Incorrect DPI scaling

---

#### 67. `HORIZONTAL_COMPRESSION_ROOT_CAUSE.md`
**Purpose:** Horizontal compression root cause analysis
**Status:** FIXED
**Fix:** Use detected DPI for accurate spacing

---

#### 68. `WHY_FIXED_SCALES_NOT_AUTO_SIZING.md`
**Purpose:** Explanation of fixed vs auto-scaling
**Key Points:**
- Auto-scaling destroys diagnostic information
- Medical ECG requires fixed 10mm/mV
- QRS amplitude is diagnostic
- Fixed scales are international standard

---

#### 69. `DEBUG_HORIZONTAL_COMPRESSION.md`
**Purpose:** Debug log for horizontal compression
**Status:** Issue resolved

---

#### 70. `CALIBRATION_TRIGGER_FIX_COMPLETE.md`
**Purpose:** Calibration trigger fix completion
**Status:** COMPLETED
**Fix:** WebSocket triggers calibration pulse

---

#### 71. `CALIBRATION_AND_PQRST_SPECIFICATIONS.md`
**Purpose:** Medical calibration and PQRST specifications
**Contents:**
- ISO standards
- Medical requirements
- Implementation specs
- Verification procedures

---

#### 72. `CALIBRATION_PULSE_GRID_SQUARES.md`
**Purpose:** Calibration pulse grid square analysis
**Contents:**
- 1mV = 2 big squares (5mm each)
- Visual verification
- Cross-platform testing

---

#### 73. `ESP32_CALIBRATION_IMPLEMENTATION_COMPLETE.md`
**Purpose:** ESP32 calibration implementation completion
**Status:** COMPLETED
**Version:** ESP32 v5.1+

---

#### 74. `ESP32_CALIBRATION_PULSE_IMPLEMENTATION_PLAN.md`
**Purpose:** ESP32 calibration pulse implementation plan
**Status:** COMPLETED

---

## TEST & UTILITY FILES

#### 75. `add_waveform_streaming.txt`
**Purpose:** Waveform streaming implementation notes
**Contents:** Implementation checklist, test procedures

---

#### 76. `hospital-backend/test_combined_message_validation.py`
**Purpose:** Test combined vitals + waveform message validation
**Tests:**
- Pydantic model validation
- JSONB serialization
- Delta encoding/decoding
- ADC conversion

---

#### 77. `hospital-backend/check_vitals_tables.py`
**Purpose:** Check vitals and waveform table status
**Checks:**
- Table existence
- Schema validation
- Index verification
- Hypertable status

---

## TYPES & TRANSFORMERS

#### 78. `hospital-display-app/src/types/PatientTypes.ts`
**Purpose:** Patient data type definitions
**Waveform Types:**
- Vitals with ECG/EEG readings
- Waveform data structures
- Alert types

---

#### 79. `hospital-display-app/src/utils/transformers/VitalTransformer.ts`
**Purpose:** Transform backend vitals to frontend format
**Waveform Handling:**
- ECG reading transformation
- EEG reading transformation
- Maintains camelCase consistency

---

#### 80. `hospital-display-app/src/utils/logger.ts`
**Purpose:** Logging utility for waveform debugging
**Features:**
- Conditional logging
- Waveform-specific log levels
- Performance tracking

---

## SUMMARY

### Total Files: **80 files**

### Breakdown by Category:
- **Database Tables:** 4 tables
- **Backend Files:** 8 files
- **Frontend Config:** 1 file
- **Frontend Utilities:** 1 file
- **Frontend Services:** 2 files
- **Frontend Components:** 7 files
- **Frontend Hooks:** 3 files
- **ESP32 Firmware:** 13 files
- **Documentation:** 40 files
- **Test/Utility:** 3 files
- **Types/Transformers:** 2 files

### Key Technologies:
- **Database:** PostgreSQL + TimescaleDB (hypertables, continuous aggregates)
- **Backend:** Python + FastAPI + Pydantic
- **Frontend:** React + TypeScript + Canvas API
- **Firmware:** Arduino C++ (ESP32)
- **Communication:** MQTT + WebSocket
- **Storage:** IndexedDB (browser cache)

### Medical Standards Compliance:
- **ECG:** ISO 11073 (10mm = 1mV, 25mm/s)
- **EEG:** Standard clinical (50μV/mm sensitivity)
- **Calibration:** 1mV, 200ms pulse (medical standard)
- **Retention:** 7 years (HIPAA compliance)

### Data Flow:
```
ESP32 Devices (500Hz sampling)
  ↓ MQTT
Backend (mqtt_service.py)
  ↓ Process & Validate
WebSocket Manager (websocket_manager.py)
  ↓ Broadcast
Frontend WebSocket Service
  ↓ Route Messages
React Components (useECGViewer hook)
  ↓ Update Buffers
Canvas Rendering (ECGWaveformCanvas.tsx)
  ↓ 60fps Animation
Medical-Grade Display
```

### Current Status:
✅ **FULLY OPERATIONAL**
- Real-time waveform streaming
- Medical-grade rendering
- Calibration pulse
- Circular buffer sweep
- Multi-lead layouts (1/4/9/12)
- IndexedDB caching
- Alert detection
- Backend analysis

---

**End of Inventory**
