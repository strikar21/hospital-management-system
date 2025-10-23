# Infrastructure Difficulty Analysis - Without BLE and Medical Scheduling

**Question:** Is it difficult to implement the 6 additional infrastructure components (48 alerts)?

**Short Answer:** No, 4 out of 6 components are straightforward. Only 2 are complex.

---

## Difficulty Breakdown

### ✅ STRAIGHTFORWARD (4 components - 29 alerts)

#### 1. **Historical Vitals Query System** - 12 alerts ⭐ EASY
**Why It's Easy:**
- We already have TimescaleDB with vitals data
- Just need to write SQL queries with window functions
- No new infrastructure required
- No new database schema needed

**What We Need:**
```python
# Just add query methods to existing database service
async def getVitalsHistory(patientId: str, vitalType: str, hours: int):
    query = """
        SELECT timestamp, value
        FROM vitals
        WHERE patientId = $1 AND vitalType = $2
          AND timestamp > NOW() - INTERVAL '%s hours'
        ORDER BY timestamp DESC
    """
    return await db.fetch(query, patientId, vitalType, hours)

# Calculate trends
def calculateTrend(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    return (values[-1] - values[0]) / values[0]  # Percentage change
```

**Estimated Time:** 1-2 days
**Complexity:** ⭐ Easy - just database queries and math

---

#### 2. **Cross-Patient Analysis** - 5 alerts ⭐ EASY
**Why It's Easy:**
- We already have devices table with status
- We already have patients table with vitals
- Just need aggregation queries

**What We Need:**
```python
# Device pool status
async def getDevicePoolStatus():
    query = """
        SELECT
            COUNT(*) FILTER (WHERE assignedTo IS NULL) as available,
            COUNT(*) as total
        FROM devices
        WHERE deviceType = 'ESP32_WATCH'
    """
    result = await db.fetchOne(query)
    availability_pct = result['available'] / result['total']
    return availability_pct

# Count patients with fever in ward
async def countPatientsWithCondition(wardId: str, condition: str):
    query = """
        SELECT COUNT(DISTINCT p.patientId)
        FROM patients p
        JOIN vitals v ON p.patientId = v.patientId
        WHERE p.wardId = $1
          AND v.vitalType = 'temperature'
          AND v.value > 38.3
          AND v.timestamp > NOW() - INTERVAL '1 hour'
    """
    return await db.fetchVal(query, wardId)
```

**Estimated Time:** 1 day
**Complexity:** ⭐ Easy - just SQL queries

---

#### 3. **Impedance Trend Tracking** - 4 alerts ⭐ MODERATE
**Why It's Moderate:**
- Need to store impedance readings (simple table)
- Need to calculate trends (same as vitals trends)
- Need to track watch removal events (simple table)

**What We Need:**
```sql
-- Simple table additions
CREATE TABLE impedanceReadings (
    readingId SERIAL PRIMARY KEY,
    patientId VARCHAR(50),
    deviceId VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    impedance FLOAT NOT NULL
);

CREATE TABLE watchRemovalEvents (
    eventId SERIAL PRIMARY KEY,
    patientId VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    duration INTEGER
);
```

**Estimated Time:** 1-2 days
**Complexity:** ⭐⭐ Moderate - needs new tables but logic is simple

---

#### 4. **Duration/State Tracking** - 8 alerts ⭐⭐ MODERATE
**Why It's Moderate:**
- Need to track when conditions start/stop
- Need to persist state to survive restarts
- Logic is straightforward (just timers)

**What We Need:**
```python
# In-memory state management
class PatientStateManager:
    def __init__(self):
        self.states = {}  # patientId -> state dict

    def trackCondition(self, patientId: str, condition: str, active: bool):
        if patientId not in self.states:
            self.states[patientId] = {}

        if active:
            if condition not in self.states[patientId]:
                self.states[patientId][condition] = {
                    'startTime': datetime.now(),
                    'alerted': False
                }
        else:
            if condition in self.states[patientId]:
                del self.states[patientId][condition]

    def checkDuration(self, patientId: str, condition: str, thresholdSeconds: int) -> bool:
        if patientId not in self.states or condition not in self.states[patientId]:
            return False

        state = self.states[patientId][condition]
        duration = (datetime.now() - state['startTime']).total_seconds()

        if duration > thresholdSeconds and not state['alerted']:
            state['alerted'] = True
            return True
        return False

# Usage example
stateManager = PatientStateManager()

# In vitals processing
if heartRate > 100:
    stateManager.trackCondition(patientId, 'tachycardia', True)
    if stateManager.checkDuration(patientId, 'tachycardia', 21600):  # 6 hours
        alerts.append(Alert(alertType='prolongedTachycardia', ...))
else:
    stateManager.trackCondition(patientId, 'tachycardia', False)
```

**Database Persistence (optional for restart recovery):**
```sql
CREATE TABLE patientStates (
    patientId VARCHAR(50),
    condition VARCHAR(50),
    startTime TIMESTAMP,
    alerted BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (patientId, condition)
);
```

**Estimated Time:** 2-3 days
**Complexity:** ⭐⭐ Moderate - needs state management but straightforward logic

---

### ⚠️ COMPLEX (2 components - 19 alerts)

#### 5. **Device Maintenance Tracking** - 9 alerts ⭐⭐⭐ COMPLEX
**Why It's Complex:**
- Requires new database schema with multiple tables
- Needs audit log integrity checking (cryptographic checksums)
- Requires timestamp manipulation detection
- Needs firmware version tracking and update management
- Regulatory compliance requirements

**What Makes It Hard:**
```python
# Audit log integrity - requires cryptographic verification
def verifyAuditLogIntegrity(deviceId: str) -> bool:
    """Check for gaps, sequence breaks, checksum failures"""
    query = """
        SELECT sequenceNumber, checksum, eventData
        FROM deviceAuditLog
        WHERE deviceId = $1
        ORDER BY sequenceNumber
    """
    logs = await db.fetch(query, deviceId)

    for i in range(1, len(logs)):
        # Check sequence continuity
        if logs[i]['sequenceNumber'] != logs[i-1]['sequenceNumber'] + 1:
            return False  # Gap detected

        # Verify checksum
        expected_checksum = hashlib.sha256(
            f"{logs[i]['sequenceNumber']}{logs[i]['eventData']}{logs[i-1]['checksum']}".encode()
        ).hexdigest()
        if logs[i]['checksum'] != expected_checksum:
            return False  # Tampering detected

    return True

# Timestamp manipulation detection - requires clock sync tracking
def detectTimestampManipulation(deviceId: str) -> bool:
    """Detect if device time has been manipulated"""
    # Need to compare device timestamps vs server timestamps
    # Need to track clock drift over time
    # Need to detect sudden jumps backward/forward
    # Complex statistical analysis required
    pass
```

**New Schema Required:**
- deviceMaintenance table (calibration, firmware, certificates)
- deviceAuditLog table (with sequence numbers and checksums)
- firmwareVersions table (available versions, deadlines)
- calibrationSchedule table (device-specific schedules)

**Estimated Time:** 5-7 days
**Complexity:** ⭐⭐⭐⭐ Complex - regulatory compliance, cryptography, multiple tables

---

#### 6. **Advanced Waveform Pattern Recognition** - 10 alerts ⭐⭐⭐⭐⭐ VERY COMPLEX
**Why It's VERY Complex:**
- Requires digital signal processing (DSP) expertise
- Needs advanced algorithms (FFT, wavelet transforms, pattern matching)
- Pacemaker spike detection is non-trivial
- Interference detection requires frequency analysis
- High false positive/negative risk

**What Makes It Hard:**
```python
# Pacemaker spike detection - HARD
def detectPacemakerSpikes(ecgWaveform: np.ndarray, sampleRate: int) -> List[int]:
    """
    Detect pacemaker spikes in ECG waveform
    - Spikes are <2ms duration, >2mV amplitude
    - Need to distinguish from QRS complexes
    - Need to handle noise and artifacts
    """
    # Step 1: High-pass filter to isolate spikes (>50Hz)
    from scipy.signal import butter, filtfilt
    nyquist = sampleRate / 2
    high_cutoff = 50 / nyquist
    b, a = butter(4, high_cutoff, btype='high')
    filtered = filtfilt(b, a, ecgWaveform)

    # Step 2: Detect sharp edges (derivative threshold)
    derivative = np.diff(filtered)
    threshold = np.std(derivative) * 5

    # Step 3: Find spike candidates
    spike_candidates = np.where(np.abs(derivative) > threshold)[0]

    # Step 4: Verify spike characteristics
    confirmed_spikes = []
    for idx in spike_candidates:
        if idx + 5 < len(ecgWaveform):
            spike_segment = ecgWaveform[idx:idx+5]
            width = self._measurePulseWidth(spike_segment)
            amplitude = np.max(np.abs(spike_segment))

            if width < 0.002 and amplitude > 2.0:  # <2ms, >2mV
                confirmed_spikes.append(idx)

    return confirmed_spikes

# ICD shock detection - MODERATE
def detectICDShock(ecgWaveform: np.ndarray) -> bool:
    """Detect ICD shock (easier - just massive amplitude)"""
    max_amplitude = np.max(np.abs(ecgWaveform))
    return max_amplitude > 10.0  # Way beyond physiological

# 60Hz noise detection - MODERATE
def detect60HzNoise(ecgWaveform: np.ndarray, sampleRate: int) -> bool:
    """Detect 60Hz line noise via FFT"""
    fft = np.fft.fft(ecgWaveform)
    freqs = np.fft.fftfreq(len(ecgWaveform), 1/sampleRate)

    # Find power at 60Hz
    idx_60hz = np.argmin(np.abs(freqs - 60))
    power_60hz = np.abs(fft[idx_60hz]) ** 2

    # Compare to total power
    total_power = np.sum(np.abs(fft) ** 2)
    noise_ratio = power_60hz / total_power

    return noise_ratio > 0.15  # >15% of signal is 60Hz

# Electrocautery detection - HARD
def detectElectrocauteryInterference(ecgWaveform: np.ndarray) -> bool:
    """
    Electrocautery creates burst noise at 300-500kHz
    Very difficult to detect with 250Hz ECG sampling
    - Signal is aliased into ECG frequency range
    - Creates broadband noise across all frequencies
    - Need time-frequency analysis (wavelet transform)
    """
    # This requires wavelet transform - very complex
    from scipy.signal import cwt, ricker
    scales = np.arange(1, 128)
    coefficients = cwt(ecgWaveform, ricker, scales)

    # Look for sudden bursts of energy across all scales
    energy = np.sum(coefficients ** 2, axis=0)
    bursts = np.where(energy > np.mean(energy) + 3*np.std(energy))[0]

    # Electrocautery creates characteristic burst pattern
    if len(bursts) > 10:
        # Check if bursts are periodic (typical usage pattern)
        burst_intervals = np.diff(bursts)
        if np.std(burst_intervals) < np.mean(burst_intervals) * 0.3:
            return True

    return False
```

**Dependencies:**
- NumPy (already have)
- SciPy (need to install)
- Advanced DSP knowledge
- Extensive testing with real medical device data
- Risk of false positives/negatives

**Estimated Time:** 7-10 days (assumes DSP expertise)
**Complexity:** ⭐⭐⭐⭐⭐ Very Complex - requires specialized expertise

---

## Summary

### Easy to Implement (30 alerts in 4-6 days)
1. ✅ Historical Vitals Query - 12 alerts (1-2 days)
2. ✅ Cross-Patient Analysis - 5 alerts (1 day)
3. ✅ Impedance Trend Tracking - 4 alerts (1-2 days)
4. ✅ Duration/State Tracking - 8 alerts (2-3 days)

**Total: 29 alerts, 4-6 days**

### Complex to Implement (19 alerts in 12-17 days)
5. ⚠️ Device Maintenance Tracking - 9 alerts (5-7 days)
6. ⚠️ Advanced Waveform Analysis - 10 alerts (7-10 days)

**Total: 19 alerts, 12-17 days**

### Not Implemented Yet (20 alerts, waiting on external systems)
7. ❌ BLE Beacon System - 8 alerts
8. ❌ Medical Scheduling - 8 alerts
9. ❌ External System Integration - 4 alerts (fire alarm, active shooter, MRI)

---

## Recommendation

**Phase 1: Quick Wins (4-6 days) - DO FIRST**
- Implement the 4 straightforward infrastructure components
- Get 29 more alerts working
- Total alerts: 80 + 29 = **109/148 (74%)**

**Phase 2: Complex (12-17 days) - DO LATER**
- Device Maintenance Tracking (9 alerts)
- Advanced Waveform Analysis (10 alerts)
- Total alerts: 109 + 19 = **128/148 (86%)**

**Phase 3: External Dependencies (TBD)**
- BLE Beacons (8 alerts)
- Medical Scheduling (8 alerts)
- External Systems (4 alerts)
- Total alerts: 128 + 20 = **148/148 (100%)**

---

## Answer to Your Question

**"Is it difficult to do all without those 2 (BLE and scheduling)?"**

**NO**, it's not difficult!

- **4 out of 6 components are straightforward** (29 alerts in 4-6 days)
- **2 out of 6 components are complex** (19 alerts in 12-17 days)

**We can easily add 29 alerts in less than a week** with the 4 easy components.

The 2 complex ones (Device Maintenance and Advanced Waveform) are technically challenging but not impossible - they just require more time and specialized knowledge (especially the waveform analysis).

**Recommended Next Step:**
Start with Phase 1 (4 easy components) to quickly get to 109/148 alerts (74%). Then decide if we want to tackle the complex components or wait for BLE/scheduling infrastructure.
