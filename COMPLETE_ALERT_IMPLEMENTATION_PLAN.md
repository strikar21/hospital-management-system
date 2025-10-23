# Complete Alert System Implementation Plan - ALL 148 Alert Types

**Date:** 2025-10-15
**Objective:** Implement all 148 alert types from COMPREHENSIVE_ALERT_SYSTEM_DESIGN.md
**Current Status:** 12 alerts implemented (8% complete)
**Target:** 100% implementation (148 alerts)

---

## Implementation Strategy

### Architecture Decisions

1. **Backend-Only Implementation First**
   - Implement ALL backend alert detection logic
   - ESP32 firmware alerts will be implemented after backend is complete
   - This allows us to test with mock data before ESP32 hardware integration

2. **Modular Service Structure**
   - Each category gets its own detection method
   - All methods called from main `detectAlerts()` function
   - Clean separation of concerns for maintainability

3. **Patient Context Required**
   - Many alerts need patient demographics (age, weight, medical history)
   - Need to query patients table for context
   - Age-adjusted thresholds, DNR status, etc.

4. **Historical Data Required**
   - Trend alerts need TimescaleDB queries
   - Pattern recognition needs historical waveforms
   - Multi-patient alerts need cross-patient analysis

5. **Advanced ECG/EEG Analysis Integration**
   - Leverage existing ecg_analysis_service.py (Pan-Tompkins)
   - Leverage existing eeg_analysis_service.py (FFT power spectrum)
   - Extend with additional arrhythmia detection algorithms

---

## Current State (What's Already Done)

### ✅ Completed (12 alerts - 8%)

**File:** [hospital-backend/app/services/alert_detection_service.py](hospital-backend/app/services/alert_detection_service.py)

1. **Cardiac Arrest** - HR = 0 (critical)
2. **Severe Bradycardia** - HR < 40 (critical)
3. **Severe Tachycardia** - HR > 150 (critical)
4. **Critical Hypoxia** - SpO2 < 80% (critical)
5. **Severe Hypoxia** - SpO2 < 85% (critical)
6. **Apnea** - RR = 0 (critical)
7. **Severe Respiratory Distress** - RR > 30 (critical)
8. **Severe Respiratory Depression** - RR < 8 (critical)
9. **Critical Battery** - Battery < 5% (critical)
10. **Low Battery** - Battery < 10% (high)
11. **Poor Signal Quality** - Signal quality < 50% (high)

### ✅ Infrastructure Complete

- Alert dataclass with all necessary fields
- WebSocket payload conversion
- MQTT service integration (lines 286-304)
- Real-time broadcasting working

---

## Category-by-Category Implementation Plan

### Category 1: Life-Threatening (16 alerts total)

**Status:** 8/16 complete (50%)

#### Already Done ✅
1. Cardiac Arrest (HR = 0)
2. Severe Bradycardia (HR < 40)
3. Severe Tachycardia (HR > 150)
4. Severe Hypoxia (SpO2 < 85%)
5. Critical Hypoxia (SpO2 < 80%)
6. Apnea (RR = 0)
7. Severe Respiratory Distress (RR > 30)
8. Severe Respiratory Depression (RR < 8)

#### Need to Implement ❌
9. **Ventricular Fibrillation (VF)** - Requires ECG waveform chaos detection
10. **Ventricular Tachycardia (VT)** - Requires wide QRS detection + HR > 100
11. **ST Elevation (STEMI)** - Requires ST segment analysis (already have ST calculation in ecg_analysis_service)
12. **Tonic-Clonic Seizure** - Requires EEG spike-wave detection + accelerometer
13. **Absence Seizure** - Requires EEG 3Hz spike-wave detection
14. **Status Epilepticus** - Requires continuous seizure detection >5 min

**Implementation Requirements:**
- ECG waveform analysis (VF, VT, STEMI)
- EEG waveform analysis (seizures)
- Accelerometer data integration (tonic-clonic)
- Duration tracking (status epilepticus)

---

### Category 2: Urgent Clinical (18 alerts total)

**Status:** 0/18 complete (0%)

#### Moderate Cardiac Issues (7 alerts)
1. **Atrial Fibrillation (AFib)** - Irregular RR intervals + absent P-waves
2. **Atrial Flutter** - Sawtooth pattern detection
3. **Premature Ventricular Contractions (PVCs)** - Wide QRS morphology
4. **Frequent PVCs** - >6 PVCs per minute
5. **Bigeminy/Trigeminy** - Pattern recognition (every 2nd/3rd beat is PVC)
6. **Bradycardia** - HR 40-50 BPM
7. **Tachycardia** - HR 120-150 BPM

#### Moderate Respiratory Issues (3 alerts)
8. **Hypoxia** - SpO2 85-90%
9. **Tachypnea** - RR 25-30 breaths/min
10. **Bradypnea** - RR 8-10 breaths/min

#### Hemodynamic Issues (3 alerts)
11. **Hypotension** - Systolic BP < 90 mmHg
12. **Hypertension** - Systolic BP > 180 mmHg
13. **Hypertensive Crisis** - BP > 200/120 mmHg

**Implementation Requirements:**
- ECG waveform pattern recognition (AFib, flutter, PVCs)
- RR interval variability analysis
- QRS morphology detection
- Blood pressure data integration (if available)

---

### Category 3: Patient Safety (11 alerts total)

**Status:** 0/11 complete (0%)

#### Fall Detection (4 alerts)
1. **Hard Fall** - Accelerometer >3g impact
2. **Soft Fall** - Accelerometer 1-3g impact
3. **Near Fall** - Accelerometer pattern (caught self)
4. **Post-Fall No Movement** - Fall detected + no movement for 30 sec

#### Movement/Activity (5 alerts)
5. **Patient Wandering** - Leaving bed (accelerometer + BLE location)
6. **Excessive Movement** - Agitation (accelerometer variance)
7. **No Movement** - Immobile for 2+ hours
8. **Tremor Detected** - High-frequency accelerometer
9. **Severe Tremor** - High amplitude tremor

**Implementation Requirements:**
- Accelerometer data integration (X, Y, Z axes)
- BLE proximity beacon integration
- Movement pattern recognition
- Duration tracking

---

### Category 4: Device Health (15 alerts total)

**Status:** 2/15 complete (13%)

#### Already Done ✅
1. Critical Battery (<5%)
2. Low Battery (<10%)

#### Need to Implement ❌

**Power/Battery (3 alerts)**
3. **Battery Warning** - <20%
4. **Not Charging** - Plugged but not charging
5. **Charging Slow** - Charging <50mA

**Signal Quality (5 alerts)**
6. **Lead Off** - Electrode disconnected (impedance check)
7. **Poor Signal Quality** - Already done ✅
8. **High Noise** - Noise ratio >0.5
9. **High Impedance** - >10 kOhm
10. **Motion Artifact** - Accelerometer correlation with noise

**Device Status (7 alerts)**
11. **Watch Removed** - All leads off
12. **Overheating** - Internal temp >65°C
13. **Memory Low** - Heap <10%
14. **WiFi Disconnected** - No WiFi connection
15. **Weak WiFi** - RSSI < -80 dBm
16. **Firmware Crash** - Watchdog reset detected

**Implementation Requirements:**
- Impedance data from ESP32
- Charging status data
- Temperature sensor data
- WiFi RSSI data
- Heap memory data
- Reset reason tracking

---

### Category 5: Clinical Workflow (8 alerts total)

**Status:** 0/8 complete (0%)

#### Medication/Treatment (4 alerts)
1. **Medication Due** - Scheduler check (5 min before)
2. **Medication Overdue** - Scheduler check (15 min after)
3. **IV Bag Empty** - Flow rate zero
4. **Treatment Due** - PT/OT scheduler

#### Vital Trend Alerts (5 alerts)
5. **HR Trending Up** - +20% in 1 hour
6. **HR Trending Down** - -20% in 1 hour
7. **SpO2 Declining** - -5% in 30 min
8. **Temperature Rising** - +1°C in 2 hours
9. **BP Trending Up** - Trend analysis

**Implementation Requirements:**
- Integration with medication scheduling system
- TimescaleDB queries for historical vitals
- Trend calculation algorithms
- Percentage change detection over time windows

---

### Category 6: Data Quality (5 alerts total)

**Status:** 0/5 complete (0%)

1. **Data Loss** - Missed packets (sequence gaps)
2. **Out of Sequence** - Packets disordered
3. **Stale Data** - No updates for 30+ seconds
4. **Invalid Data** - Values out of physiological range
5. **Clock Drift** - Timestamp out of sync

**Implementation Requirements:**
- Sequence number tracking in vitals messages
- Timestamp validation
- Last-received tracking per device
- Physiological range validation tables

---

### Category 7: Medical Device Interference (10 alerts total)

**Status:** 0/10 complete (0%)

#### Implanted Devices (5 alerts)
1. **Pacemaker Spike Detected** - Sharp spike in ECG
2. **Pacemaker Malfunction** - Spike without QRS capture
3. **ICD Shock Delivered** - Artifact + rhythm change
4. **Paced Rhythm Change** - Mode switch
5. **Ventricular Pacing Failure** - Spike no capture

#### Equipment Interference (5 alerts)
6. **60Hz Line Noise** - FFT peak at 60Hz
7. **Electrocautery Interference** - Wideband noise burst
8. **Diathermy Interference** - High-freq noise
9. **TENS Unit Interference** - Periodic spikes
10. **MRI Scanner Nearby** - Manual disable flag

**Implementation Requirements:**
- ECG waveform spike detection
- FFT frequency analysis (already have in eeg_analysis_service)
- Noise pattern recognition
- Manual override flags

---

### Category 8: Age-Specific (12 alerts total)

**Status:** 0/12 complete (0%)

#### Pediatric (<18 years) (4 alerts)
1. **Pediatric Bradycardia** - Age-adjusted HR threshold
2. **Pediatric Tachycardia** - Age-adjusted HR threshold
3. **Pediatric Hypotension** - Age-adjusted BP threshold
4. **Growth Spurt Vitals** - Expected changes

#### Neonatal (<28 days) (4 alerts)
5. **Neonatal Apnea** - >10-15 sec (shorter than adult)
6. **Neonatal Bradycardia** - HR <100 BPM
7. **Neonatal Hypothermia** - <36.5°C
8. **Periodic Breathing** - Normal pattern recognition

#### Geriatric (>65 years) (4 alerts)
9. **Geriatric Orthostatic Hypotension** - BP drop on standing
10. **Atypical Presentations** - Silent MI (subtle ST changes)
11. **Polypharmacy Interactions** - Med database check
12. **Delirium Risk** - Multi-factor score

**Implementation Requirements:**
- Patient age from patients table
- Age-based threshold lookup tables
- Posture detection (orthostatic)
- Medication interaction database

---

### Category 9: Location & Context (8 alerts total)

**Status:** 0/8 complete (0%)

#### BLE Proximity (4 alerts)
1. **Patient Left Room** - BLE beacon RSSI drop
2. **Patient in Restricted Area** - Beacon ID check
3. **Patient Near Exit** - Exit beacon RSSI high
4. **Patient in Bathroom Too Long** - Bathroom beacon + timer

#### Time-Based Context (4 alerts)
5. **Sundowning** - Agitation at dusk (movement + time)
6. **Nighttime Wandering** - Movement during sleep hours
7. **Sleep Apnea Events** - Apnea during sleep (time-based)
8. **Nocturnal Hypoxia** - SpO2 drop at night

**Implementation Requirements:**
- BLE beacon integration
- RSSI tracking per beacon
- Time-of-day context
- Room/location mapping

---

### Category 10: Rare Cardiac Events (9 alerts total)

**Status:** 0/9 complete (0%)

#### Genetic/Congenital (5 alerts)
1. **Torsades de Pointes** - Polymorphic VT (twisting QRS)
2. **Brugada Pattern** - Coved ST elevation V1-V3
3. **Long QT Syndrome** - QTc >500ms
4. **Short QT Syndrome** - QTc <340ms
5. **Wolff-Parkinson-White (WPW)** - Short PR + delta wave

#### Structural Heart (4 alerts)
6. **Bundle Branch Block** - Wide QRS pattern
7. **AV Block 2nd Degree** - Dropped beats
8. **AV Block 3rd Degree** - Dissociated P-QRS
9. **Ventricular Escape Rhythm** - Wide QRS slow rate

**Implementation Requirements:**
- QT interval correction (Bazett's formula)
- P-wave to QRS correlation
- PR interval calculation
- Delta wave detection
- QRS morphology analysis

---

### Category 11: Hardware Failures (8 alerts total)

**Status:** 0/8 complete (0%)

#### ADS1298 ADC (5 alerts)
1. **ADC Saturation** - Rail-to-rail values
2. **ADC Channel Failure** - Single channel flatline
3. **SPI Communication Error** - SPI timeout
4. **Reference Voltage Drift** - Baseline shift
5. **Differential Input Saturation** - Asymmetric saturation

#### Sensor Failures (4 alerts)
6. **Pulse Oximeter Sensor Failed** - Invalid perfusion index
7. **Temperature Probe Disconnected** - Out-of-range reading
8. **Accelerometer Stuck** - Constant values
9. **I2C Bus Lockup** - I2C timeout

**Implementation Requirements:**
- Per-channel saturation detection
- Baseline drift tracking
- Sensor validity checks
- Communication error flags from ESP32

---

### Category 12: Network & Connectivity (8 alerts total)

**Status:** 0/8 complete (0%)

#### Network Degradation (5 alerts)
1. **High Latency** - RTT >500ms
2. **Packet Loss** - >5% packet loss
3. **WiFi Roaming** - BSSID change
4. **DNS Failure** - DNS timeout
5. **MQTT Broker Disconnect** - Connection lost

#### Bandwidth Issues (3 alerts)
6. **Network Congestion** - Queue buildup
7. **Waveform Transmission Delayed** - Send buffer full
8. **Real-time Stream Interrupted** - Data gap

**Implementation Requirements:**
- Latency tracking (timestamp differences)
- Sequence number gap detection
- WiFi status from ESP32
- MQTT connection monitoring

---

### Category 13: Patient Behavior (7 alerts total)

**Status:** 0/7 complete (0%)

#### Non-Compliance (4 alerts)
1. **Watch Tampering** - Impedance fluctuation
2. **Repeated Watch Removal** - >3x per day
3. **Electrode Gel Dried** - Impedance increase over time
4. **Patient Wetting Electrodes** - Impedance sudden drop

#### Intentional Interference (3 alerts)
5. **Holding Breath** - SpO2 manipulation pattern
6. **Valsalva Maneuver** - HR drop + strain
7. **Voluntary Hyperventilation** - High RR sustained

**Implementation Requirements:**
- Impedance trend tracking
- Removal event counting
- Pattern recognition (intentional vs physiological)

---

### Category 14: Multi-Patient Scenarios (5 alerts total)

**Status:** 0/5 complete (0%)

#### Device Pool (3 alerts)
1. **Device Pool Depleted** - <10% devices available
2. **No Devices Available** - Inventory = 0
3. **Mass Assignment Required** - >10 patients waiting

#### Outbreak Scenarios (2 alerts)
4. **Multiple Patients Fever** - >5 patients in ward with fever
5. **Respiratory Outbreak** - SpO2 trends across patients

**Implementation Requirements:**
- Device inventory tracking
- Cross-patient analysis
- Ward-based clustering
- Population health queries

---

### Category 15: Metabolic & Endocrine (7 alerts total)

**Status:** 0/7 complete (0%)

#### Metabolic Crises (4 alerts)
1. **Malignant Hyperthermia** - Temp >40°C + tachycardia
2. **Thyroid Storm** - High temp + tachycardia + history
3. **Addisonian Crisis** - Hypotension + bradycardia
4. **Diabetic Ketoacidosis Signs** - Tachycardia + tachypnea

#### Sepsis & Shock (3 alerts)
5. **Septic Shock Pattern** - SIRS criteria (multi-vital)
6. **Early Warning Score** - NEWS/MEWS calculation
7. **Compensated Shock** - Tachycardia + narrowing pulse pressure

**Implementation Requirements:**
- Multi-vital combinations
- SIRS criteria implementation
- NEWS/MEWS scoring algorithms
- Patient medical history integration

---

### Category 16: Special Populations (6 alerts total)

**Status:** 0/6 complete (0%)

#### Psychiatric (3 alerts)
1. **Self-Harm Risk Vitals** - Bradycardia from vagal maneuver
2. **Excited Delirium Pattern** - Tachycardia + hyperthermia
3. **Neuroleptic Malignant Syndrome** - Fever + rigidity proxy

#### Palliative/End-of-Life (2 alerts)
4. **DNR Patient Cardiac Arrest** - Suppress code blue
5. **Comfort Care Vitals Change** - Expected decline (suppress alerts)

#### Bariatric (1 alert)
6. **Obesity Hypoventilation** - Low SpO2 + high RR + BMI

**Implementation Requirements:**
- DNR code status from patients table
- Comfort care flag
- BMI calculation
- Pattern + context correlation

---

### Category 17: Disaster Scenarios (6 alerts total)

**Status:** 0/6 complete (0%)

#### Natural Disasters (3 alerts)
1. **Earthquake Detected** - Accelerometer high g-force pattern
2. **Power Failure** - UPS mode activated
3. **Network Infrastructure Down** - Multiple device loss

#### Hospital Emergencies (3 alerts)
4. **Fire Alarm** - Fire system integration
5. **Active Shooter** - Lockdown mode (manual)
6. **Mass Evacuation Required** - Manual trigger

**Implementation Requirements:**
- Accelerometer pattern recognition
- Server status monitoring
- Manual override flags
- External system integration

---

### Category 18: Regulatory Compliance (9 alerts total)

**Status:** 0/9 complete (0%)

#### Medical Device Compliance (3 alerts)
1. **Device Calibration Overdue** - Maintenance schedule check
2. **Firmware Out of Date** - Version comparison
3. **Security Certificate Expired** - Certificate expiry check

#### Data Integrity (3 alerts)
4. **Data Audit Trail Gap** - Log analysis
5. **Timestamp Manipulation Detected** - Sequence analysis
6. **HIPAA Logging Failure** - Audit system check

#### Quality Assurance (3 alerts)
7. **Consecutive Invalid Readings** - >10 validation failures
8. **Sensor Drift Beyond Tolerance** - Baseline comparison
9. **Data Dropout Pattern** - Systematic loss detection

**Implementation Requirements:**
- Device maintenance schedule database
- Firmware version tracking
- Certificate monitoring
- Audit log integrity checks

---

## Implementation Phases

### Phase 1: Complete Life-Threatening + Device Health (Total: 31 alerts)
**Timeline:** 2-3 days
**Priority:** Critical safety alerts

- [ ] Category 1 remaining (8 alerts): VF, VT, STEMI, seizures
- [ ] Category 4 remaining (13 alerts): All device health alerts
- [ ] Create alerts table in PostgreSQL
- [ ] Integrate alert storage

### Phase 2: Urgent Clinical + Patient Safety (Total: 29 alerts)
**Timeline:** 2-3 days
**Priority:** Essential clinical care

- [ ] Category 2 (18 alerts): AFib, PVCs, moderate vitals
- [ ] Category 3 (11 alerts): Fall detection, movement

### Phase 3: Workflow + Data Quality + Age-Specific (Total: 25 alerts)
**Timeline:** 2-3 days
**Priority:** Clinical workflow and demographics

- [ ] Category 5 (8 alerts): Medication, trends
- [ ] Category 6 (5 alerts): Data quality
- [ ] Category 8 (12 alerts): Age-specific thresholds

### Phase 4: Advanced Cardiac + Medical Devices (Total: 19 alerts)
**Timeline:** 3-4 days
**Priority:** Complex arrhythmias and device interactions

- [ ] Category 7 (10 alerts): Pacemaker, interference
- [ ] Category 10 (9 alerts): Rare cardiac events

### Phase 5: Hardware + Network + Behavior (Total: 23 alerts)
**Timeline:** 2-3 days
**Priority:** System reliability

- [ ] Category 11 (8 alerts): Hardware failures
- [ ] Category 12 (8 alerts): Network issues
- [ ] Category 13 (7 alerts): Patient behavior

### Phase 6: Population Health + Special Cases (Total: 21 alerts)
**Timeline:** 2-3 days
**Priority:** Advanced features

- [ ] Category 9 (8 alerts): Location/context
- [ ] Category 14 (5 alerts): Multi-patient
- [ ] Category 15 (7 alerts): Metabolic emergencies
- [ ] Category 16 (6 alerts): Special populations
- [ ] Category 17 (6 alerts): Disasters
- [ ] Category 18 (9 alerts): Compliance

---

## Technical Architecture Changes Needed

### 1. Alert Detection Service Refactoring

**Current:** Single `detectAlerts()` method with all logic
**New:** Modular category-based methods

```python
class AlertDetectionService:
    def detectAlerts(self, vitalsData, waveformData, patientContext, deviceContext):
        alerts = []

        # Category 1: Life-threatening
        alerts.extend(self._detectLifeThreateningAlerts(vitalsData, waveformData))

        # Category 2: Urgent clinical
        alerts.extend(self._detectUrgentClinicalAlerts(vitalsData, waveformData))

        # Category 3: Patient safety
        alerts.extend(self._detectPatientSafetyAlerts(vitalsData, deviceContext))

        # ... (all 18 categories)

        return alerts
```

### 2. Patient Context Integration

**Need to add:**
```python
async def _getPatientContext(self, patientId: str) -> PatientContext:
    """Query patient demographics and medical history"""
    async with getDbConnection() as conn:
        patient = await conn.fetchrow("""
            SELECT age, weight, height, dob, gender,
                   medicalHistory, codeStatus, comfortCare
            FROM patients WHERE id = $1
        """, patientId)

        return PatientContext(
            age=calculate_age(patient['dob']),
            weight=patient['weight'],
            bmi=calculate_bmi(patient['weight'], patient['height']),
            codeStatus=patient['codeStatus'],  # DNR, Full Code, etc.
            comfortCare=patient['comfortCare']
        )
```

### 3. Historical Data Integration

**Need to add:**
```python
async def _getHistoricalVitals(self, patientId: str, hours: int) -> List[Vitals]:
    """Query TimescaleDB for historical vitals"""
    async with getTimescaleConnection() as conn:
        vitals = await conn.fetch("""
            SELECT * FROM vitals_realtime
            WHERE "patientId" = $1
            AND timestamp > NOW() - INTERVAL '$2 hours'
            ORDER BY timestamp DESC
        """, patientId, hours)

        return vitals
```

### 4. Waveform Analysis Integration

**Current:** Separate waveform handler
**New:** Pass waveform analysis results to alert detection

```python
# In _handleWaveformMessage():
ecgAnalysis = await ecgAnalysisService.analyzeEcg(ecgData)
eegAnalysis = await eegAnalysisService.analyzeEeg(eegData)

# Pass to alert detection
alerts = alertDetectionService.detectWaveformAlerts(
    ecgAnalysis,
    eegAnalysis,
    patientId,
    deviceId
)
```

### 5. Alerts Table Schema

```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "patientId" UUID NOT NULL REFERENCES patients(id),
    "deviceId" VARCHAR(50) NOT NULL,
    "alertType" VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    source VARCHAR(50) NOT NULL,  -- 'ESP32' or 'Backend'
    confidence FLOAT NOT NULL,
    context JSONB,  -- Additional data specific to alert type
    category VARCHAR(50) NOT NULL,  -- 'cardiac', 'respiratory', etc.
    "createdAt" TIMESTAMP NOT NULL DEFAULT NOW(),
    acknowledged BOOLEAN DEFAULT FALSE,
    "acknowledgedBy" UUID REFERENCES staff(id),
    "acknowledgedAt" TIMESTAMP,
    suppressed BOOLEAN DEFAULT FALSE,  -- For DNR, comfort care

    CONSTRAINT alerts_severity_check
        CHECK (severity IN ('critical', 'high', 'medium', 'low'))
);

CREATE INDEX idx_alerts_patient ON alerts("patientId");
CREATE INDEX idx_alerts_device ON alerts("deviceId");
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_type ON alerts("alertType");
CREATE INDEX idx_alerts_acknowledged ON alerts(acknowledged);
CREATE INDEX idx_alerts_created ON alerts("createdAt" DESC);
CREATE INDEX idx_alerts_category ON alerts(category);
```

---

## Testing Strategy

### Unit Tests (Per Category)
- Test each alert type individually
- Mock vitals/waveform data
- Verify correct alert detection
- Verify thresholds

### Integration Tests
- End-to-end MQTT → Detection → WebSocket
- Database storage verification
- Alert acknowledgment flow

### Performance Tests
- Alert detection latency (<100ms)
- WebSocket broadcast performance
- Database write performance
- Memory usage under load

---

## Success Criteria

1. ✅ All 148 alert types implemented
2. ✅ All alerts stored in PostgreSQL
3. ✅ All alerts broadcast via WebSocket
4. ✅ Alert detection latency <100ms average
5. ✅ Zero false negatives for critical alerts
6. ✅ <5% false positives for critical alerts
7. ✅ Comprehensive test coverage (>80%)
8. ✅ Full documentation of all alert types

---

## Next Steps

1. **Immediate:** Refactor alert_detection_service.py for modular architecture
2. **Create:** Patient context queries
3. **Create:** Historical vitals queries
4. **Implement:** Category 1 remaining alerts (VF, VT, STEMI, seizures)
5. **Implement:** Category 4 remaining alerts (device health)
6. **Create:** Alerts table migration
7. **Continue:** Through all 18 categories systematically

---

## Files to Modify/Create

### Modify:
1. `hospital-backend/app/services/alert_detection_service.py` - Expand to all 148 alerts
2. `hospital-backend/app/services/mqtt_service.py` - Add patient context, historical queries
3. `hospital-backend/app/models/patient.py` - Add codeStatus, comfortCare fields if missing

### Create:
1. `hospital-backend/migrations/010_create_alerts_table.sql` - Alerts table
2. `hospital-backend/app/services/alert_storage_service.py` - Alert persistence
3. `hospital-backend/test_all_alerts.py` - Comprehensive test suite
4. `hospital-backend/app/models/alert.py` - Pydantic models for all alert types

---

## Estimated Timeline

- **Phase 1:** 2-3 days (31 alerts)
- **Phase 2:** 2-3 days (29 alerts)
- **Phase 3:** 2-3 days (25 alerts)
- **Phase 4:** 3-4 days (19 alerts)
- **Phase 5:** 2-3 days (23 alerts)
- **Phase 6:** 2-3 days (21 alerts)

**Total:** ~15-21 days for complete implementation

**Current:** Day 1 - Planning complete, starting Phase 1

---

**Let's begin with Phase 1: Life-Threatening + Device Health alerts!**
