# Additional Infrastructure Requirements for Complete Alert System

**Status:** 80+ alerts implemented (54%), 68 alerts remaining (46%)

**Already Known Requirements:**
1. ✓ BLE Beacon System - For location/context alerts (Category 9)
2. ✓ Medical Scheduling System - For medication/treatment timing alerts (Category 5)

---

## Additional Infrastructure Needed (6 Categories)

### 1. **Historical Vitals Query System (TimescaleDB)**
**Purpose:** Trend analysis and early warning scores
**Required For:** 12 alerts across multiple categories
**Complexity:** Medium - requires TimescaleDB query optimization

**Specific Requirements:**
- Query last N hours of vitals data per patient
- Calculate trends (slope, rate of change)
- Compare current vs baseline values
- Window functions for moving averages

**Alerts Dependent On This:**
- Heart rate trending up (+20% in 1 hour)
- Heart rate trending down (-20% in 1 hour)
- SpO2 declining (-5% in 30 minutes)
- Temperature rising (+1°C in 2 hours)
- Blood pressure trending up
- Early warning scores (NEWS2, MEWS, PEWS)
- Respiratory rate trending up
- Prolonged tachycardia (HR >100 for >6 hours)
- Prolonged bradycardia (HR <60 for >6 hours)
- Sustained hypoxia (SpO2 <92% for >15 minutes)
- Persistent fever (temp >38.3°C for >4 hours)
- Nocturnal hypoxia detection

**Implementation Notes:**
```python
# Example query structure needed
async def getHistoricalVitals(
    patientId: str,
    vitalType: str,
    hoursBack: int = 24
) -> List[Dict[str, Any]]:
    """Query TimescaleDB for historical vitals"""
    query = """
        SELECT time_bucket('5 minutes', timestamp) AS bucket,
               AVG(value) as avgValue,
               MIN(value) as minValue,
               MAX(value) as maxValue
        FROM vitals
        WHERE patientId = $1
          AND vitalType = $2
          AND timestamp > NOW() - INTERVAL '%s hours'
        GROUP BY bucket
        ORDER BY bucket DESC
    """
    # Execute and return results
```

---

### 2. **Cross-Patient Database Analysis**
**Purpose:** Multi-patient scenarios and inventory management
**Required For:** 5 alerts (Category 14)
**Complexity:** Medium - requires efficient database queries

**Specific Requirements:**
- Query device pool availability across facility
- Count patients meeting specific criteria (fever, SpO2 drop)
- Track device inventory in real-time
- Ward-level aggregation queries

**Alerts Dependent On This:**
- Device pool depleted (<10% available)
- No devices available (inventory = 0)
- Mass assignment required (>10 patients admitted)
- Multiple patients with fever (>5 in ward)
- Respiratory outbreak pattern (>3 patients SpO2 declining)

**Implementation Notes:**
```python
# Example queries needed
async def getDevicePoolStatus() -> Dict[str, Any]:
    """Get current device pool availability"""
    query = """
        SELECT
            COUNT(*) FILTER (WHERE status = 'available') as available,
            COUNT(*) FILTER (WHERE status = 'assigned') as assigned,
            COUNT(*) as total
        FROM devices
        WHERE deviceType = 'ESP32_WATCH'
    """

async def getWardPatientConditions(
    wardId: str,
    condition: str
) -> int:
    """Count patients in ward meeting condition"""
    if condition == 'fever':
        query = """
            SELECT COUNT(DISTINCT p.patientId)
            FROM patients p
            JOIN vitals v ON p.patientId = v.patientId
            WHERE p.wardId = $1
              AND v.vitalType = 'temperature'
              AND v.value > 38.3
              AND v.timestamp > NOW() - INTERVAL '1 hour'
        """
```

---

### 3. **Device Maintenance Tracking Database**
**Purpose:** Regulatory compliance and device lifecycle management
**Required For:** 9 alerts (Category 18)
**Complexity:** High - requires new database schema

**Specific Requirements:**
- Device calibration schedule and last calibration date
- Firmware version tracking and update deadlines
- Security certificate expiration dates
- Audit log storage and integrity verification
- Sensor drift tracking over time
- Data dropout pattern analysis

**Database Schema Needed:**
```sql
-- New table: deviceMaintenance
CREATE TABLE deviceMaintenance (
    deviceId VARCHAR(50) PRIMARY KEY,
    lastCalibrationDate TIMESTAMP,
    nextCalibrationDue TIMESTAMP,
    calibrationIntervalDays INTEGER DEFAULT 90,
    firmwareVersion VARCHAR(20),
    firmwareUpdateAvailable VARCHAR(20),
    firmwareUpdateDeadline TIMESTAMP,
    securityCertExpiry TIMESTAMP,
    consecutiveInvalidReadings INTEGER DEFAULT 0,
    sensorDriftValue FLOAT DEFAULT 0.0,
    lastMaintenanceDate TIMESTAMP,
    maintenanceNotes TEXT
);

-- New table: deviceAuditLog
CREATE TABLE deviceAuditLog (
    logId SERIAL PRIMARY KEY,
    deviceId VARCHAR(50),
    patientId VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    eventType VARCHAR(100),
    eventData JSONB,
    sequenceNumber INTEGER,
    checksum VARCHAR(64),
    UNIQUE(deviceId, sequenceNumber)
);
```

**Alerts Dependent On This:**
- Device calibration overdue (>90 days)
- Firmware out of date (critical update available)
- Security certificate expired
- Data audit trail gap detected
- Timestamp manipulation detected
- HIPAA logging failure
- Consecutive invalid readings (>10)
- Sensor drift beyond tolerance
- Data dropout pattern (>10% missing)

**Implementation Notes:**
```python
async def checkDeviceMaintenance(deviceId: str) -> List[Alert]:
    """Check all maintenance-related alerts"""
    query = """
        SELECT * FROM deviceMaintenance
        WHERE deviceId = $1
    """
    maintenance = await db.fetchOne(query, deviceId)

    alerts = []

    # Calibration overdue
    if maintenance.nextCalibrationDue < datetime.now():
        alerts.append(Alert(...))

    # Firmware out of date
    if maintenance.firmwareUpdateDeadline and \
       maintenance.firmwareUpdateDeadline < datetime.now():
        alerts.append(Alert(...))

    # Certificate expired
    if maintenance.securityCertExpiry < datetime.now():
        alerts.append(Alert(...))

    return alerts
```

---

### 4. **Advanced Waveform Pattern Recognition**
**Purpose:** Detect complex device interference and pacemaker behavior
**Required For:** 10 alerts (Category 7)
**Complexity:** Very High - requires DSP algorithms

**Specific Requirements:**
- Pacemaker spike detection (sharp vertical artifacts in ECG)
- ICD shock detection (massive amplitude spike)
- 60Hz line noise detection via FFT
- High-frequency interference detection (electrocautery, diathermy, TENS)
- Pacemaker rate vs intrinsic rate comparison
- Capture failure detection
- Sensing failure detection

**Algorithms Needed:**
```python
class AdvancedWaveformAnalyzer:
    def detectPacemakerSpikes(self, ecgWaveform: np.ndarray, sampleRate: int = 250) -> bool:
        """Detect pacemaker spikes in ECG waveform"""
        # Look for sharp vertical spikes (duration < 2ms, amplitude > 2mV)
        diff = np.diff(ecgWaveform)
        spikes = np.where(np.abs(diff) > 2.0)[0]

        # Check spike width (should be < 2ms = 0.5 samples at 250Hz)
        for spike_idx in spikes:
            if spike_idx + 2 < len(ecgWaveform):
                spike_width = self._measureSpikeWidth(ecgWaveform[spike_idx:spike_idx+5])
                if spike_width < 0.002:  # 2ms
                    return True
        return False

    def detectICDShock(self, ecgWaveform: np.ndarray) -> bool:
        """Detect ICD shock delivery (massive amplitude spike)"""
        # ICD shocks are 10-40 Joules, appear as massive artifacts
        max_amplitude = np.max(np.abs(ecgWaveform))
        if max_amplitude > 10.0:  # 10mV is way beyond physiological
            return True
        return False

    def detect60HzNoise(self, ecgWaveform: np.ndarray, sampleRate: int = 250) -> bool:
        """Detect 60Hz line noise via FFT"""
        fft = np.fft.fft(ecgWaveform)
        freqs = np.fft.fftfreq(len(ecgWaveform), 1/sampleRate)

        # Check power at 60Hz and harmonics (120Hz, 180Hz)
        power_60hz = np.abs(fft[np.argmin(np.abs(freqs - 60))])
        power_120hz = np.abs(fft[np.argmin(np.abs(freqs - 120))])

        total_power = np.sum(np.abs(fft))

        if (power_60hz + power_120hz) / total_power > 0.15:  # >15% of signal
            return True
        return False

    def detectElectrocauteryInterference(self, ecgWaveform: np.ndarray, sampleRate: int = 250) -> bool:
        """Detect electrocautery (high frequency 300-500kHz burst noise)"""
        # Electrocautery creates broadband high-frequency noise
        fft = np.fft.fft(ecgWaveform)
        freqs = np.fft.fftfreq(len(ecgWaveform), 1/sampleRate)

        # Check high frequency power (>100Hz)
        high_freq_mask = freqs > 100
        high_freq_power = np.sum(np.abs(fft[high_freq_mask]))
        total_power = np.sum(np.abs(fft))

        if high_freq_power / total_power > 0.30:  # >30% high frequency
            return True
        return False
```

**Alerts Dependent On This:**
- Pacemaker spike detected
- Pacemaker malfunction (missing spikes)
- ICD shock delivered
- Paced rhythm change
- Ventricular pacing failure
- 60Hz line noise interference
- Electrocautery interference
- Diathermy interference
- TENS unit interference
- MRI-induced interference

**Note:** Most medical devices (electrocautery, MRI) will require BLE proximity detection PLUS waveform analysis for accurate detection.

---

### 5. **Duration Tracking and State Management System**
**Purpose:** Track time-based conditions and alert durations
**Required For:** 8 alerts across multiple categories
**Complexity:** Medium - requires in-memory state management

**Specific Requirements:**
- Track when conditions start and end
- Maintain state across multiple vitals messages
- Persist state to database for recovery after restart
- Timer-based alert triggering

**State Management Schema:**
```python
@dataclass
class PatientState:
    """Persistent patient state for duration tracking"""
    patientId: str
    deviceId: str

    # Seizure tracking
    seizureStartTime: Optional[datetime] = None
    seizureOngoing: bool = False

    # Movement tracking
    lastMovementTime: Optional[datetime] = None
    noMovementAlertSent: bool = False

    # Post-fall tracking
    fallDetectedTime: Optional[datetime] = None
    postFallNoMovement: bool = False

    # Bathroom tracking
    bathroomEntryTime: Optional[datetime] = None
    inBathroom: bool = False

    # Apnea tracking
    apneaStartTime: Optional[datetime] = None
    apneaOngoing: bool = False

    # Tachycardia/bradycardia prolonged
    tachycardiaStartTime: Optional[datetime] = None
    bradycardiaStartTime: Optional[datetime] = None

    # Sustained hypoxia
    hypoxiaStartTime: Optional[datetime] = None

    # Persistent fever
    feverStartTime: Optional[datetime] = None

class StateManager:
    """Manage patient states in memory and database"""

    def __init__(self):
        self.states: Dict[str, PatientState] = {}

    async def loadPatientState(self, patientId: str) -> PatientState:
        """Load patient state from database"""
        if patientId in self.states:
            return self.states[patientId]

        # Load from database
        query = "SELECT * FROM patientStates WHERE patientId = $1"
        row = await db.fetchOne(query, patientId)

        if row:
            state = PatientState(**row)
        else:
            state = PatientState(patientId=patientId, deviceId='')

        self.states[patientId] = state
        return state

    async def savePatientState(self, state: PatientState):
        """Persist patient state to database"""
        query = """
            INSERT INTO patientStates (patientId, deviceId, ...)
            VALUES ($1, $2, ...)
            ON CONFLICT (patientId) DO UPDATE SET ...
        """
        await db.execute(query, state.patientId, state.deviceId, ...)
```

**Database Schema:**
```sql
CREATE TABLE patientStates (
    patientId VARCHAR(50) PRIMARY KEY,
    deviceId VARCHAR(50),
    seizureStartTime TIMESTAMP,
    seizureOngoing BOOLEAN DEFAULT FALSE,
    lastMovementTime TIMESTAMP,
    noMovementAlertSent BOOLEAN DEFAULT FALSE,
    fallDetectedTime TIMESTAMP,
    postFallNoMovement BOOLEAN DEFAULT FALSE,
    bathroomEntryTime TIMESTAMP,
    inBathroom BOOLEAN DEFAULT FALSE,
    apneaStartTime TIMESTAMP,
    apneaOngoing BOOLEAN DEFAULT FALSE,
    tachycardiaStartTime TIMESTAMP,
    bradycardiaStartTime TIMESTAMP,
    hypoxiaStartTime TIMESTAMP,
    feverStartTime TIMESTAMP,
    updatedAt TIMESTAMP DEFAULT NOW()
);
```

**Alerts Dependent On This:**
- Status epilepticus (seizure >5 minutes)
- Post-fall no movement (30 seconds)
- No movement detected (immobile >2 hours)
- Patient in bathroom too long (>10 minutes)
- Apnea duration exceeds threshold
- Prolonged tachycardia (>6 hours)
- Prolonged bradycardia (>6 hours)
- Sustained hypoxia (>15 minutes)
- Persistent fever (>4 hours)

**Implementation Example:**
```python
async def checkDurationBasedAlerts(
    vitalsData: Dict[str, Any],
    patientId: str,
    state: PatientState
) -> List[Alert]:
    """Check all duration-based alerts"""
    alerts = []
    now = datetime.now()

    # Status epilepticus
    if waveformAnalysis.seizureActivity:
        if not state.seizureOngoing:
            state.seizureStartTime = now
            state.seizureOngoing = True
        elif state.seizureStartTime:
            duration = (now - state.seizureStartTime).total_seconds()
            if duration > 300:  # 5 minutes
                alerts.append(Alert(
                    alertType='statusEpilepticus',
                    severity='critical',
                    message=f'STATUS EPILEPTICUS - Seizure ongoing for {duration:.0f} seconds',
                    ...
                ))
    else:
        state.seizureOngoing = False
        state.seizureStartTime = None

    # No movement
    if accelerometerData and accelerometerData.movementDetected:
        state.lastMovementTime = now
        state.noMovementAlertSent = False
    elif state.lastMovementTime:
        duration = (now - state.lastMovementTime).total_seconds()
        if duration > 7200 and not state.noMovementAlertSent:  # 2 hours
            alerts.append(Alert(
                alertType='noMovementDetected',
                severity='medium',
                message=f'No movement detected for {duration/3600:.1f} hours',
                ...
            ))
            state.noMovementAlertSent = True

    # Persistent fever
    temp = vitalsData.get('temperature', 0)
    if temp > 38.3:
        if not state.feverStartTime:
            state.feverStartTime = now
        else:
            duration = (now - state.feverStartTime).total_seconds()
            if duration > 14400:  # 4 hours
                alerts.append(Alert(
                    alertType='persistentFever',
                    severity='high',
                    message=f'Persistent fever (>38.3°C) for {duration/3600:.1f} hours',
                    ...
                ))
    else:
        state.feverStartTime = None

    await stateManager.savePatientState(state)
    return alerts
```

---

### 6. **Impedance Trend Tracking System**
**Purpose:** Detect electrode issues and patient behavior via impedance
**Required For:** 4 alerts (Category 13)
**Complexity:** Medium - requires historical impedance data

**Specific Requirements:**
- Store impedance readings over time
- Calculate impedance trends (increasing/decreasing)
- Count watch removal events per day
- Detect sudden impedance changes (tampering)

**Database Schema:**
```sql
-- Extend vitals table or create impedance table
CREATE TABLE impedanceReadings (
    readingId SERIAL PRIMARY KEY,
    patientId VARCHAR(50),
    deviceId VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    impedance FLOAT NOT NULL,
    INDEX idx_patient_time (patientId, timestamp DESC)
);

-- Track watch removal events
CREATE TABLE watchRemovalEvents (
    eventId SERIAL PRIMARY KEY,
    patientId VARCHAR(50),
    deviceId VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    duration INTEGER,  -- seconds
    reason VARCHAR(50)  -- 'patient_removed', 'clinician_removed', 'automatic'
);
```

**Alerts Dependent On This:**
- Watch tampering detected (impedance fluctuation >50% within 5 min)
- Repeated watch removal (>3 times per day)
- Electrode gel dried (impedance increasing >20% over 4 hours)
- Patient wetting electrodes (impedance dropping >30% suddenly)

**Implementation Example:**
```python
async def checkImpedanceAlerts(
    impedance: float,
    patientId: str,
    deviceId: str
) -> List[Alert]:
    """Check impedance-based alerts"""
    alerts = []

    # Get recent impedance readings
    query = """
        SELECT timestamp, impedance
        FROM impedanceReadings
        WHERE patientId = $1
          AND timestamp > NOW() - INTERVAL '4 hours'
        ORDER BY timestamp DESC
    """
    history = await db.fetch(query, patientId)

    if len(history) < 2:
        return alerts

    # Check for tampering (rapid fluctuation)
    recent_5min = [r for r in history if (datetime.now() - r['timestamp']).total_seconds() < 300]
    if len(recent_5min) > 5:
        impedances = [r['impedance'] for r in recent_5min]
        fluctuation = (max(impedances) - min(impedances)) / min(impedances)
        if fluctuation > 0.5:  # >50% variation
            alerts.append(Alert(
                alertType='watchTampering',
                severity='medium',
                message='Watch tampering detected - rapid impedance fluctuation',
                ...
            ))

    # Check for dried gel (increasing impedance)
    if len(history) > 20:
        old_avg = np.mean([r['impedance'] for r in history[-20:-10]])
        new_avg = np.mean([r['impedance'] for r in history[-10:]])
        increase_pct = (new_avg - old_avg) / old_avg
        if increase_pct > 0.20:  # >20% increase
            alerts.append(Alert(
                alertType='electrodeGelDried',
                severity='low',
                message=f'Electrode gel dried - impedance increased {increase_pct*100:.0f}%',
                ...
            ))

    # Check for wetting (sudden drop)
    if len(history) > 2:
        prev_impedance = history[1]['impedance']
        if (prev_impedance - impedance) / prev_impedance > 0.30:  # >30% sudden drop
            alerts.append(Alert(
                alertType='patientWettingElectrodes',
                severity='low',
                message='Patient may have wet electrodes - sudden impedance drop',
                ...
            ))

    # Count watch removals today
    removal_query = """
        SELECT COUNT(*)
        FROM watchRemovalEvents
        WHERE patientId = $1
          AND timestamp > CURRENT_DATE
    """
    removal_count = await db.fetchVal(removal_query, patientId)
    if removal_count > 3:
        alerts.append(Alert(
            alertType='repeatedWatchRemoval',
            severity='medium',
            message=f'Patient has removed watch {removal_count} times today',
            ...
        ))

    return alerts
```

---

## Summary Table

| Infrastructure Component | Alerts Affected | Complexity | Implementation Time | Dependencies |
|-------------------------|-----------------|------------|---------------------|--------------|
| 1. Historical Vitals Query | 12 alerts | Medium | 3-4 days | TimescaleDB queries |
| 2. Cross-Patient Analysis | 5 alerts | Medium | 2-3 days | PostgreSQL queries |
| 3. Device Maintenance DB | 9 alerts | High | 5-7 days | New schema + migration |
| 4. Advanced Waveform Analysis | 10 alerts | Very High | 7-10 days | DSP algorithms, NumPy |
| 5. Duration/State Tracking | 8 alerts | Medium | 3-4 days | New schema + state manager |
| 6. Impedance Trend Tracking | 4 alerts | Medium | 2-3 days | Impedance data storage |
| **Already Known:** | | | | |
| 7. BLE Beacon System | 8 alerts | High | 5-7 days | BLE hardware, proximity detection |
| 8. Medical Scheduling | 8 alerts | Medium | 3-4 days | Medication/treatment schedules |

**Total Infrastructure Components:** 8
**Total Additional Alerts:** 48 alerts (plus 20 from BLE + scheduling)
**Total Estimated Time:** 30-42 days (assuming sequential implementation)

---

## Implementation Priority Recommendation

### Phase 1 (Quick Wins - 7-10 days)
1. Historical Vitals Query (12 alerts)
2. Cross-Patient Analysis (5 alerts)
3. Impedance Trend Tracking (4 alerts)

**Result:** 21 more alerts = 101/148 total (68%)

### Phase 2 (Medium Effort - 10-14 days)
4. Duration/State Tracking (8 alerts)
5. Medical Scheduling (8 alerts)

**Result:** 16 more alerts = 117/148 total (79%)

### Phase 3 (High Effort - 12-17 days)
6. Device Maintenance DB (9 alerts)
7. BLE Beacon System (8 alerts)

**Result:** 17 more alerts = 134/148 total (90%)

### Phase 4 (Very High Complexity - 7-10 days)
8. Advanced Waveform Analysis (10 alerts)

**Result:** 10 more alerts = 144/148 total (97%)

**Remaining 4 alerts require external integrations:**
- Fire alarm system integration
- Active shooter alert system
- Mass evacuation protocol
- MRI machine status monitoring

---

## Notes

- **BLE Beacons** are needed for location detection (room tracking, bathroom presence, proximity to medical devices)
- **Medical Scheduling** is needed for medication/treatment timing alerts
- All other infrastructure is internal to our system
- Some alerts may require combination of multiple infrastructure components
- Performance optimization (caching, indexing) will be critical as system scales
