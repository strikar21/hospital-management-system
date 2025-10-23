# Phase Alert Infrastructure Implementation Plan

**Goal:** Implement 38 alerts across 5 infrastructure components (excluding waveform analysis, BLE, and medical scheduling)

**Current Status:** 80 alerts implemented (54%)
**After This Phase:** 118 alerts implemented (80%)
**Timeline:** 6-9 days

---

## What We're Implementing

### ✅ Included (5 components - 38 alerts)
1. Historical Vitals Query System - 12 alerts
2. Cross-Patient Analysis - 5 alerts
3. Impedance Trend Tracking - 4 alerts
4. Duration/State Tracking - 8 alerts
5. Device Maintenance Tracking - 9 alerts

### ❌ Excluded (Deferred to Later)
- Advanced Waveform Pattern Recognition - 10 alerts (DSP complexity)
- BLE Beacon System - 8 alerts (hardware dependency)
- Medical Scheduling System - 8 alerts (external system)
- External System Integration - 4 alerts (fire alarm, active shooter, MRI)

**Total Excluded:** 30 alerts (deferred)

---

## Implementation Breakdown

### **Component 1: Historical Vitals Query System**
**Alerts:** 12
**Estimated Time:** 1-2 days
**Complexity:** Easy

#### Alerts to Implement:
1. Heart rate trending up (+20% in 1 hour)
2. Heart rate trending down (-20% in 1 hour)
3. SpO2 declining (-5% in 30 minutes)
4. Temperature rising (+1°C in 2 hours)
5. Blood pressure trending up
6. Respiratory rate trending up
7. Prolonged tachycardia (HR >100 for >6 hours)
8. Prolonged bradycardia (HR <60 for >6 hours)
9. Sustained hypoxia (SpO2 <92% for >15 minutes)
10. Persistent fever (temp >38.3°C for >4 hours)
11. Nocturnal hypoxia (SpO2 drops at night)
12. Early warning score calculation (NEWS2/MEWS/PEWS)

#### Implementation Steps:

**Step 1.1: Add Historical Query Methods to Database Service**
File: `hospital-backend/app/core/database.py`

```python
async def getHistoricalVitals(
    patientId: str,
    vitalType: str,
    hoursBack: int = 24
) -> List[Dict[str, Any]]:
    """Query TimescaleDB for historical vitals"""
    query = """
        SELECT timestamp, value
        FROM vitals
        WHERE patientId = $1
          AND vitalType = $2
          AND timestamp > NOW() - INTERVAL '%s hours'
        ORDER BY timestamp ASC
    """
    async with get_db() as conn:
        rows = await conn.fetch(query, patientId, vitalType, hoursBack)
        return [dict(row) for row in rows]

async def getVitalsTimeBuckets(
    patientId: str,
    vitalType: str,
    hoursBack: int = 24,
    bucketMinutes: int = 5
) -> List[Dict[str, Any]]:
    """Get vitals aggregated into time buckets"""
    query = """
        SELECT time_bucket('%s minutes', timestamp) AS bucket,
               AVG(value) as avgValue,
               MIN(value) as minValue,
               MAX(value) as maxValue,
               COUNT(*) as count
        FROM vitals
        WHERE patientId = $1
          AND vitalType = $2
          AND timestamp > NOW() - INTERVAL '%s hours'
        GROUP BY bucket
        ORDER BY bucket ASC
    """
    async with get_db() as conn:
        rows = await conn.fetch(query, bucketMinutes, patientId, vitalType, hoursBack)
        return [dict(row) for row in rows]
```

**Step 1.2: Add Trend Analysis Methods to Alert Service**
File: `hospital-backend/app/services/alert_detection_service.py`

```python
def _calculateTrend(self, values: List[float]) -> float:
    """Calculate percentage change from first to last value"""
    if len(values) < 2:
        return 0.0
    return ((values[-1] - values[0]) / values[0]) * 100

def _calculateSlope(self, timestamps: List[datetime], values: List[float]) -> float:
    """Calculate rate of change using linear regression"""
    if len(values) < 2:
        return 0.0

    # Convert timestamps to seconds since first reading
    x = np.array([(t - timestamps[0]).total_seconds() for t in timestamps])
    y = np.array(values)

    # Simple linear regression
    n = len(x)
    slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
    return slope

async def _detectTrendAlerts(
    self,
    vitalsData: Dict[str, Any],
    patientId: str,
    deviceId: str,
    timestamp: datetime,
    patientContext: Optional[PatientContext] = None
) -> List[Alert]:
    """Detect trend-based alerts requiring historical data"""
    alerts = []

    heartRate = vitalsData.get('heartRate', 0)
    oxygenSaturation = vitalsData.get('oxygenSaturation', 0)
    temperature = vitalsData.get('temperature', 0)
    respiratoryRate = vitalsData.get('respiratoryRate', 0)

    # Heart rate trending up (20% in 1 hour)
    hr_history = await db.getHistoricalVitals(patientId, 'heartRate', hoursBack=1)
    if len(hr_history) > 5:
        hr_values = [r['value'] for r in hr_history]
        hr_trend = self._calculateTrend(hr_values)
        if hr_trend > 20:
            alerts.append(Alert(
                alertType='heartRateTrendingUp',
                severity='medium',
                message=f'Heart rate trending up ({hr_trend:.1f}% increase in 1 hour)',
                source='Backend',
                confidence=0.85,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'trendPercentage': hr_trend, 'values': hr_values[-5:]},
                category='cardiac'
            ))

    # Heart rate trending down (20% in 1 hour)
    if len(hr_history) > 5:
        hr_values = [r['value'] for r in hr_history]
        hr_trend = self._calculateTrend(hr_values)
        if hr_trend < -20:
            alerts.append(Alert(
                alertType='heartRateTrendingDown',
                severity='medium',
                message=f'Heart rate trending down ({abs(hr_trend):.1f}% decrease in 1 hour)',
                source='Backend',
                confidence=0.85,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'trendPercentage': hr_trend, 'values': hr_values[-5:]},
                category='cardiac'
            ))

    # SpO2 declining (5% in 30 minutes)
    spo2_history = await db.getHistoricalVitals(patientId, 'oxygenSaturation', hoursBack=0.5)
    if len(spo2_history) > 3:
        spo2_values = [r['value'] for r in spo2_history]
        spo2_trend = self._calculateTrend(spo2_values)
        if spo2_trend < -5:
            alerts.append(Alert(
                alertType='oxygenSaturationDeclining',
                severity='high',
                message=f'SpO2 declining ({abs(spo2_trend):.1f}% decrease in 30 minutes)',
                source='Backend',
                confidence=0.90,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'trendPercentage': spo2_trend, 'values': spo2_values[-5:]},
                category='respiratory'
            ))

    # Temperature rising (1°C in 2 hours)
    temp_history = await db.getHistoricalVitals(patientId, 'temperature', hoursBack=2)
    if len(temp_history) > 5:
        temp_values = [r['value'] for r in temp_history]
        temp_change = temp_values[-1] - temp_values[0]
        if temp_change > 1.0:
            alerts.append(Alert(
                alertType='temperatureRising',
                severity='medium',
                message=f'Temperature rising rapidly ({temp_change:.1f}°C in 2 hours)',
                source='Backend',
                confidence=0.85,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'temperatureChange': temp_change, 'values': temp_values[-5:]},
                category='metabolic'
            ))

    # Respiratory rate trending up
    rr_history = await db.getHistoricalVitals(patientId, 'respiratoryRate', hoursBack=1)
    if len(rr_history) > 5:
        rr_values = [r['value'] for r in rr_history]
        rr_trend = self._calculateTrend(rr_values)
        if rr_trend > 25:
            alerts.append(Alert(
                alertType='respiratoryRateTrendingUp',
                severity='medium',
                message=f'Respiratory rate trending up ({rr_trend:.1f}% increase)',
                source='Backend',
                confidence=0.80,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'trendPercentage': rr_trend, 'values': rr_values[-5:]},
                category='respiratory'
            ))

    # Early Warning Score (NEWS2)
    news2_score = self._calculateNEWS2Score(
        heartRate=heartRate,
        oxygenSaturation=oxygenSaturation,
        temperature=temperature,
        respiratoryRate=respiratoryRate,
        systolicBP=vitalsData.get('systolicBP', 120),
        supplementalO2=False,
        consciousness='Alert'
    )

    if news2_score >= 7:
        alerts.append(Alert(
            alertType='earlyWarningScoreHigh',
            severity='critical',
            message=f'NEWS2 Score critically high: {news2_score} (threshold: 7)',
            source='Backend',
            confidence=0.95,
            patientId=patientId,
            deviceId=deviceId,
            timestamp=timestamp,
            context={'news2Score': news2_score},
            category='clinical'
        ))
    elif news2_score >= 5:
        alerts.append(Alert(
            alertType='earlyWarningScoreMedium',
            severity='high',
            message=f'NEWS2 Score elevated: {news2_score} (threshold: 5)',
            source='Backend',
            confidence=0.90,
            patientId=patientId,
            deviceId=deviceId,
            timestamp=timestamp,
            context={'news2Score': news2_score},
            category='clinical'
        ))

    return alerts

def _calculateNEWS2Score(
    self,
    respiratoryRate: float,
    oxygenSaturation: float,
    systolicBP: float,
    heartRate: float,
    temperature: float,
    supplementalO2: bool,
    consciousness: str
) -> int:
    """Calculate NEWS2 (National Early Warning Score 2)"""
    score = 0

    # Respiratory rate scoring
    if respiratoryRate <= 8:
        score += 3
    elif respiratoryRate <= 11:
        score += 1
    elif respiratoryRate <= 20:
        score += 0
    elif respiratoryRate <= 24:
        score += 2
    else:
        score += 3

    # SpO2 scoring (Scale 1 - no hypercapnic respiratory failure)
    if oxygenSaturation <= 91:
        score += 3
    elif oxygenSaturation <= 93:
        score += 2
    elif oxygenSaturation <= 95:
        score += 1
    else:
        score += 0

    # Supplemental oxygen
    if supplementalO2:
        score += 2

    # Systolic BP scoring
    if systolicBP <= 90:
        score += 3
    elif systolicBP <= 100:
        score += 2
    elif systolicBP <= 110:
        score += 1
    elif systolicBP <= 219:
        score += 0
    else:
        score += 3

    # Heart rate scoring
    if heartRate <= 40:
        score += 3
    elif heartRate <= 50:
        score += 1
    elif heartRate <= 90:
        score += 0
    elif heartRate <= 110:
        score += 1
    elif heartRate <= 130:
        score += 2
    else:
        score += 3

    # Temperature scoring
    if temperature <= 35.0:
        score += 3
    elif temperature <= 36.0:
        score += 1
    elif temperature <= 38.0:
        score += 0
    elif temperature <= 39.0:
        score += 1
    else:
        score += 2

    # Consciousness scoring
    if consciousness != 'Alert':
        score += 3

    return score
```

**Step 1.3: Update detectAlerts() to Call Trend Detection**
File: `hospital-backend/app/services/alert_detection_service.py`

```python
async def detectAlerts(
    self,
    vitalsData: Dict[str, Any],
    patientId: str,
    deviceId: str,
    patientContext: Optional[PatientContext] = None,
    waveformAnalysis: Optional[WaveformAnalysis] = None,
    deviceContext: Optional[DeviceContext] = None,
    accelerometerData: Optional[AccelerometerData] = None
) -> List[Alert]:
    """Detect ALL alerts from comprehensive input data"""
    alerts = []
    timestamp = datetime.now()

    # ... existing category detections ...

    # NEW: Trend-based alerts (requires historical data)
    trend_alerts = await self._detectTrendAlerts(
        vitalsData, patientId, deviceId, timestamp, patientContext
    )
    alerts.extend(trend_alerts)

    return alerts
```

---

### **Component 2: Cross-Patient Analysis**
**Alerts:** 5
**Estimated Time:** 1 day
**Complexity:** Easy

#### Alerts to Implement:
1. Device pool depleted (<10% available)
2. No devices available (inventory = 0)
3. Mass assignment required (>10 patients admitted)
4. Multiple patients with fever (>5 in ward)
5. Respiratory outbreak pattern (>3 patients SpO2 declining)

#### Implementation Steps:

**Step 2.1: Add Cross-Patient Query Methods to Database Service**
File: `hospital-backend/app/core/database.py`

```python
async def getDevicePoolStatus() -> Dict[str, Any]:
    """Get current device pool availability"""
    query = """
        SELECT
            COUNT(*) FILTER (WHERE assignedTo IS NULL) as available,
            COUNT(*) FILTER (WHERE assignedTo IS NOT NULL) as assigned,
            COUNT(*) as total
        FROM devices
        WHERE deviceType = 'ESP32_WATCH'
    """
    async with get_db() as conn:
        result = await conn.fetchrow(query)
        return {
            'available': result['available'],
            'assigned': result['assigned'],
            'total': result['total'],
            'availabilityPercent': (result['available'] / result['total'] * 100) if result['total'] > 0 else 0
        }

async def countPatientsWithCondition(
    wardId: Optional[str],
    condition: str,
    timeWindowMinutes: int = 60
) -> int:
    """Count patients meeting a condition in specified time window"""

    if condition == 'fever':
        query = """
            SELECT COUNT(DISTINCT p.patientId)
            FROM patients p
            JOIN vitals v ON p.patientId = v.patientId
            WHERE ($1::VARCHAR IS NULL OR p.wardId = $1)
              AND v.vitalType = 'temperature'
              AND v.value > 38.3
              AND v.timestamp > NOW() - INTERVAL '%s minutes'
        """
    elif condition == 'spo2_declining':
        query = """
            WITH patient_spo2_trends AS (
                SELECT
                    p.patientId,
                    FIRST_VALUE(v.value) OVER (PARTITION BY p.patientId ORDER BY v.timestamp ASC) as first_spo2,
                    LAST_VALUE(v.value) OVER (PARTITION BY p.patientId ORDER BY v.timestamp DESC) as last_spo2
                FROM patients p
                JOIN vitals v ON p.patientId = v.patientId
                WHERE ($1::VARCHAR IS NULL OR p.wardId = $1)
                  AND v.vitalType = 'oxygenSaturation'
                  AND v.timestamp > NOW() - INTERVAL '%s minutes'
            )
            SELECT COUNT(DISTINCT patientId)
            FROM patient_spo2_trends
            WHERE (first_spo2 - last_spo2) / first_spo2 > 0.05
        """
    else:
        return 0

    async with get_db() as conn:
        result = await conn.fetchval(query, wardId, timeWindowMinutes)
        return result or 0

async def countRecentAdmissions(hoursBack: int = 24) -> int:
    """Count patients admitted in recent time period"""
    query = """
        SELECT COUNT(*)
        FROM patients
        WHERE admissionDate > NOW() - INTERVAL '%s hours'
          AND status = 'active'
    """
    async with get_db() as conn:
        result = await conn.fetchval(query, hoursBack)
        return result or 0
```

**Step 2.2: Add Cross-Patient Alert Detection Method**
File: `hospital-backend/app/services/alert_detection_service.py`

```python
async def detectSystemLevelAlerts(self) -> List[Alert]:
    """Detect system-level alerts that span multiple patients"""
    alerts = []
    timestamp = datetime.now()

    # Device pool status
    pool_status = await db.getDevicePoolStatus()

    if pool_status['available'] == 0:
        alerts.append(Alert(
            alertType='noDevicesAvailable',
            severity='critical',
            message='CRITICAL: No devices available in pool - cannot assign to new patients',
            source='Backend',
            confidence=1.0,
            patientId='SYSTEM',
            deviceId='SYSTEM',
            timestamp=timestamp,
            context=pool_status,
            category='system'
        ))
    elif pool_status['availabilityPercent'] < 10:
        alerts.append(Alert(
            alertType='devicePoolDepleted',
            severity='high',
            message=f'Device pool critically low: {pool_status["available"]} available ({pool_status["availabilityPercent"]:.1f}%)',
            source='Backend',
            confidence=0.95,
            patientId='SYSTEM',
            deviceId='SYSTEM',
            timestamp=timestamp,
            context=pool_status,
            category='system'
        ))

    # Mass admissions
    recent_admissions = await db.countRecentAdmissions(hoursBack=4)
    if recent_admissions > 10:
        alerts.append(Alert(
            alertType='massAssignmentRequired',
            severity='high',
            message=f'Mass admission event: {recent_admissions} patients admitted in 4 hours',
            source='Backend',
            confidence=0.90,
            patientId='SYSTEM',
            deviceId='SYSTEM',
            timestamp=timestamp,
            context={'admissionCount': recent_admissions},
            category='workflow'
        ))

    # Multiple patients with fever (ward-level)
    fever_count_ward = await db.countPatientsWithCondition(None, 'fever', timeWindowMinutes=60)
    if fever_count_ward > 5:
        alerts.append(Alert(
            alertType='multiplePatientsWithFever',
            severity='medium',
            message=f'{fever_count_ward} patients with fever - potential outbreak',
            source='Backend',
            confidence=0.85,
            patientId='SYSTEM',
            deviceId='SYSTEM',
            timestamp=timestamp,
            context={'feverCount': fever_count_ward},
            category='epidemiology'
        ))

    # Respiratory outbreak pattern
    spo2_declining_count = await db.countPatientsWithCondition(None, 'spo2_declining', timeWindowMinutes=60)
    if spo2_declining_count > 3:
        alerts.append(Alert(
            alertType='respiratoryOutbreakPattern',
            severity='high',
            message=f'{spo2_declining_count} patients with declining SpO2 - respiratory outbreak suspected',
            source='Backend',
            confidence=0.80,
            patientId='SYSTEM',
            deviceId='SYSTEM',
            timestamp=timestamp,
            context={'affectedPatients': spo2_declining_count},
            category='epidemiology'
        ))

    return alerts
```

**Step 2.3: Create Periodic System Alert Check**
File: `hospital-backend/app/services/alert_detection_service.py`

```python
async def runSystemAlertCheck(self):
    """Periodic check for system-level alerts (run every 5 minutes)"""
    try:
        system_alerts = await self.detectSystemLevelAlerts()

        # Broadcast system alerts via WebSocket
        for alert in system_alerts:
            alert_payload = self.createAlertPayload(alert)
            await connectionManager.broadcastSystemAlert(alert_payload)

            # TODO: Store in database
            logger.info(f"System Alert: {alert.alertType} - {alert.message}")

    except Exception as e:
        logger.error(f"Error in system alert check: {e}")
```

**Step 2.4: Add Periodic Task Scheduler**
File: `hospital-backend/main.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.alert_detection_service import completeAlertDetectionService

# Create scheduler
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # ... existing startup code ...

    # Schedule system-level alert checks every 5 minutes
    scheduler.add_job(
        completeAlertDetectionService.runSystemAlertCheck,
        'interval',
        minutes=5,
        id='system_alert_check'
    )
    scheduler.start()
    logger.info("✅ System alert scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    scheduler.shutdown()
    logger.info("System alert scheduler stopped")
```

---

### **Component 3: Impedance Trend Tracking**
**Alerts:** 4
**Estimated Time:** 1-2 days
**Complexity:** Moderate

#### Alerts to Implement:
1. Watch tampering detected (impedance fluctuation >50% within 5 min)
2. Repeated watch removal (>3 times per day)
3. Electrode gel dried (impedance increasing >20% over 4 hours)
4. Patient wetting electrodes (impedance dropping >30% suddenly)

#### Implementation Steps:

**Step 3.1: Create Impedance Tables**
File: `hospital-backend/migrations/010_add_impedance_tracking.sql`

```sql
-- Impedance readings table
CREATE TABLE IF NOT EXISTS impedanceReadings (
    readingId SERIAL PRIMARY KEY,
    patientId VARCHAR(50) NOT NULL,
    deviceId VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    impedance FLOAT NOT NULL,
    FOREIGN KEY (patientId) REFERENCES patients(patientId) ON DELETE CASCADE,
    FOREIGN KEY (deviceId) REFERENCES devices(deviceId) ON DELETE CASCADE
);

CREATE INDEX idx_impedance_patient_time ON impedanceReadings(patientId, timestamp DESC);
CREATE INDEX idx_impedance_device_time ON impedanceReadings(deviceId, timestamp DESC);

-- Watch removal events table
CREATE TABLE IF NOT EXISTS watchRemovalEvents (
    eventId SERIAL PRIMARY KEY,
    patientId VARCHAR(50) NOT NULL,
    deviceId VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    duration INTEGER,  -- seconds watch was off
    reason VARCHAR(50),  -- 'patient_removed', 'clinician_removed', 'automatic'
    FOREIGN KEY (patientId) REFERENCES patients(patientId) ON DELETE CASCADE,
    FOREIGN KEY (deviceId) REFERENCES devices(deviceId) ON DELETE CASCADE
);

CREATE INDEX idx_removal_patient_time ON watchRemovalEvents(patientId, timestamp DESC);
```

**Step 3.2: Apply Migration**
```python
# hospital-backend/apply_migration_010_impedance.py
import asyncio
import asyncpg
from app.core.config import settings

async def apply_migration():
    conn = await asyncpg.connect(settings.DATABASE_URL)

    with open('migrations/010_add_impedance_tracking.sql', 'r') as f:
        migration_sql = f.read()

    await conn.execute(migration_sql)
    print("✅ Migration 010 applied: impedance tracking tables created")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(apply_migration())
```

**Step 3.3: Add Impedance Storage in MQTT Service**
File: `hospital-backend/app/services/mqtt_service.py`

```python
# In handleVitalsMessage() method, after storing vitals:

# Store impedance reading if present
if hasattr(vitalsMsg, 'impedance') and vitalsMsg.impedance:
    impedance_query = """
        INSERT INTO impedanceReadings (patientId, deviceId, timestamp, impedance)
        VALUES ($1, $2, $3, $4)
    """
    await conn.execute(
        impedance_query,
        patientId,
        deviceId,
        timestamp,
        vitalsMsg.impedance
    )
```

**Step 3.4: Add Impedance Alert Detection Methods**
File: `hospital-backend/app/services/alert_detection_service.py`

```python
async def _detectImpedanceAlerts(
    self,
    impedance: float,
    patientId: str,
    deviceId: str,
    timestamp: datetime
) -> List[Alert]:
    """Detect impedance-based alerts"""
    alerts = []

    # Get recent impedance history
    query = """
        SELECT timestamp, impedance
        FROM impedanceReadings
        WHERE patientId = $1
          AND timestamp > NOW() - INTERVAL '4 hours'
        ORDER BY timestamp DESC
        LIMIT 100
    """
    history = await db.fetch(query, patientId)

    if len(history) < 2:
        return alerts

    # Check for tampering (rapid fluctuation in 5 minutes)
    recent_5min = [r for r in history if (timestamp - r['timestamp']).total_seconds() < 300]
    if len(recent_5min) > 5:
        impedances = [r['impedance'] for r in recent_5min]
        fluctuation = (max(impedances) - min(impedances)) / min(impedances)
        if fluctuation > 0.5:  # >50% variation
            alerts.append(Alert(
                alertType='watchTampering',
                severity='medium',
                message=f'Watch tampering detected - {fluctuation*100:.0f}% impedance fluctuation in 5 minutes',
                source='Backend',
                confidence=0.85,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'fluctuationPercent': fluctuation * 100, 'impedanceValues': impedances},
                category='patient_behavior'
            ))

    # Check for dried gel (increasing impedance over 4 hours)
    if len(history) > 20:
        old_avg = np.mean([r['impedance'] for r in history[-20:-10]])
        new_avg = np.mean([r['impedance'] for r in history[-10:]])
        increase_pct = (new_avg - old_avg) / old_avg
        if increase_pct > 0.20:  # >20% increase
            alerts.append(Alert(
                alertType='electrodeGelDried',
                severity='low',
                message=f'Electrode gel dried - impedance increased {increase_pct*100:.0f}%',
                source='Backend',
                confidence=0.80,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'increasePercent': increase_pct * 100, 'oldAvg': old_avg, 'newAvg': new_avg},
                category='device_quality'
            ))

    # Check for wetting (sudden drop >30%)
    if len(history) > 1:
        prev_impedance = history[1]['impedance']
        if (prev_impedance - impedance) / prev_impedance > 0.30:  # >30% sudden drop
            alerts.append(Alert(
                alertType='patientWettingElectrodes',
                severity='low',
                message=f'Patient may have wet electrodes - sudden {((prev_impedance - impedance) / prev_impedance)*100:.0f}% impedance drop',
                source='Backend',
                confidence=0.75,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'previousImpedance': prev_impedance, 'currentImpedance': impedance},
                category='patient_behavior'
            ))

    # Count watch removals today
    removal_query = """
        SELECT COUNT(*)
        FROM watchRemovalEvents
        WHERE patientId = $1
          AND timestamp > CURRENT_DATE
    """
    removal_count = await db.fetchval(removal_query, patientId)
    if removal_count and removal_count > 3:
        alerts.append(Alert(
            alertType='repeatedWatchRemoval',
            severity='medium',
            message=f'Patient has removed watch {removal_count} times today',
            source='Backend',
            confidence=0.90,
            patientId=patientId,
            deviceId=deviceId,
            timestamp=timestamp,
            context={'removalCount': removal_count},
            category='patient_behavior'
        ))

    return alerts
```

**Step 3.5: Integrate into Main detectAlerts()**
File: `hospital-backend/app/services/alert_detection_service.py`

```python
async def detectAlerts(
    self,
    vitalsData: Dict[str, Any],
    patientId: str,
    deviceId: str,
    # ... other params ...
) -> List[Alert]:
    """Detect ALL alerts"""
    alerts = []
    timestamp = datetime.now()

    # ... existing detections ...

    # NEW: Impedance alerts
    if 'impedance' in vitalsData:
        impedance_alerts = await self._detectImpedanceAlerts(
            vitalsData['impedance'], patientId, deviceId, timestamp
        )
        alerts.extend(impedance_alerts)

    return alerts
```

---

### **Component 4: Duration/State Tracking**
**Alerts:** 8
**Estimated Time:** 2-3 days
**Complexity:** Moderate

#### Alerts to Implement:
1. Status epilepticus (seizure >5 minutes)
2. Post-fall no movement (30 seconds)
3. No movement detected (immobile >2 hours)
4. Patient in bathroom too long (>10 minutes)
5. Prolonged tachycardia (HR >100 for >6 hours) - **covered in Component 1**
6. Prolonged bradycardia (HR <60 for >6 hours) - **covered in Component 1**
7. Sustained hypoxia (SpO2 <92% for >15 minutes) - **covered in Component 1**
8. Persistent fever (temp >38.3°C for >4 hours) - **covered in Component 1**

**Note:** 4 of these are already covered in Component 1 (Historical Vitals), so we'll implement the remaining 4 unique duration-based alerts.

#### Implementation Steps:

**Step 4.1: Create Patient States Table**
File: `hospital-backend/migrations/011_add_patient_states.sql`

```sql
-- Patient states for duration tracking
CREATE TABLE IF NOT EXISTS patientStates (
    patientId VARCHAR(50) PRIMARY KEY,
    deviceId VARCHAR(50),

    -- Seizure tracking
    seizureStartTime TIMESTAMP,
    seizureOngoing BOOLEAN DEFAULT FALSE,

    -- Movement tracking
    lastMovementTime TIMESTAMP,
    noMovementAlertSent BOOLEAN DEFAULT FALSE,

    -- Post-fall tracking
    fallDetectedTime TIMESTAMP,
    postFallNoMovement BOOLEAN DEFAULT FALSE,

    -- Bathroom tracking
    bathroomEntryTime TIMESTAMP,
    inBathroom BOOLEAN DEFAULT FALSE,

    -- Metadata
    updatedAt TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (patientId) REFERENCES patients(patientId) ON DELETE CASCADE,
    FOREIGN KEY (deviceId) REFERENCES devices(deviceId) ON DELETE SET NULL
);

CREATE INDEX idx_patient_states_updated ON patientStates(updatedAt DESC);
```

**Step 4.2: Create State Manager Class**
File: `hospital-backend/app/services/state_manager.py`

```python
"""Patient state management for duration-based alerts"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
import asyncpg
from app.core.database import get_db
import logging

logger = logging.getLogger(__name__)

@dataclass
class PatientState:
    """Persistent patient state for duration tracking"""
    patientId: str
    deviceId: str = ''

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

    # Metadata
    updatedAt: datetime = field(default_factory=datetime.now)

class StateManager:
    """Manage patient states in memory and database"""

    def __init__(self):
        self.states: Dict[str, PatientState] = {}

    async def loadPatientState(self, patientId: str) -> PatientState:
        """Load patient state from database or create new"""
        if patientId in self.states:
            return self.states[patientId]

        # Load from database
        query = """
            SELECT * FROM patientStates
            WHERE patientId = $1
        """
        async with get_db() as conn:
            row = await conn.fetchrow(query, patientId)

            if row:
                state = PatientState(
                    patientId=row['patientid'],
                    deviceId=row['deviceid'] or '',
                    seizureStartTime=row['seizurestarttime'],
                    seizureOngoing=row['seizureongoing'],
                    lastMovementTime=row['lastmovementtime'],
                    noMovementAlertSent=row['nomovementalertsent'],
                    fallDetectedTime=row['falldetectedtime'],
                    postFallNoMovement=row['postfallnomovement'],
                    bathroomEntryTime=row['bathrooomentrytime'],
                    inBathroom=row['inbathroom'],
                    updatedAt=row['updatedat']
                )
            else:
                state = PatientState(patientId=patientId)

            self.states[patientId] = state
            return state

    async def savePatientState(self, state: PatientState):
        """Persist patient state to database"""
        state.updatedAt = datetime.now()

        query = """
            INSERT INTO patientStates (
                patientId, deviceId,
                seizureStartTime, seizureOngoing,
                lastMovementTime, noMovementAlertSent,
                fallDetectedTime, postFallNoMovement,
                bathroomEntryTime, inBathroom,
                updatedAt
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (patientId) DO UPDATE SET
                deviceId = EXCLUDED.deviceId,
                seizureStartTime = EXCLUDED.seizureStartTime,
                seizureOngoing = EXCLUDED.seizureOngoing,
                lastMovementTime = EXCLUDED.lastMovementTime,
                noMovementAlertSent = EXCLUDED.noMovementAlertSent,
                fallDetectedTime = EXCLUDED.fallDetectedTime,
                postFallNoMovement = EXCLUDED.postFallNoMovement,
                bathroomEntryTime = EXCLUDED.bathroomEntryTime,
                inBathroom = EXCLUDED.inBathroom,
                updatedAt = EXCLUDED.updatedAt
        """

        async with get_db() as conn:
            await conn.execute(
                query,
                state.patientId,
                state.deviceId,
                state.seizureStartTime,
                state.seizureOngoing,
                state.lastMovementTime,
                state.noMovementAlertSent,
                state.fallDetectedTime,
                state.postFallNoMovement,
                state.bathroomEntryTime,
                state.inBathroom,
                state.updatedAt
            )

        # Update in-memory cache
        self.states[state.patientId] = state

# Global state manager instance
stateManager = StateManager()
```

**Step 4.3: Add Duration Alert Detection Methods**
File: `hospital-backend/app/services/alert_detection_service.py`

```python
from app.services.state_manager import stateManager, PatientState

async def _detectDurationAlerts(
    self,
    vitalsData: Dict[str, Any],
    patientId: str,
    deviceId: str,
    timestamp: datetime,
    waveformAnalysis: Optional[WaveformAnalysis] = None,
    accelerometerData: Optional[AccelerometerData] = None
) -> List[Alert]:
    """Detect duration-based alerts"""
    alerts = []

    # Load patient state
    state = await stateManager.loadPatientState(patientId)
    state.deviceId = deviceId

    # Status epilepticus (seizure >5 minutes)
    if waveformAnalysis and waveformAnalysis.seizureActivity:
        if not state.seizureOngoing:
            state.seizureStartTime = timestamp
            state.seizureOngoing = True
            logger.info(f"Seizure started for patient {patientId}")
        elif state.seizureStartTime:
            duration = (timestamp - state.seizureStartTime).total_seconds()
            if duration > 300:  # 5 minutes
                alerts.append(Alert(
                    alertType='statusEpilepticus',
                    severity='critical',
                    message=f'STATUS EPILEPTICUS - Seizure ongoing for {duration/60:.1f} minutes',
                    source='Backend',
                    confidence=0.95,
                    patientId=patientId,
                    deviceId=deviceId,
                    timestamp=timestamp,
                    context={'durationSeconds': duration},
                    category='neurological'
                ))
    else:
        if state.seizureOngoing:
            logger.info(f"Seizure ended for patient {patientId}")
        state.seizureOngoing = False
        state.seizureStartTime = None

    # Movement detection
    if accelerometerData and accelerometerData.movementDetected:
        state.lastMovementTime = timestamp
        state.noMovementAlertSent = False
        state.postFallNoMovement = False
    elif state.lastMovementTime:
        duration = (timestamp - state.lastMovementTime).total_seconds()

        # No movement detected (>2 hours)
        if duration > 7200 and not state.noMovementAlertSent:
            alerts.append(Alert(
                alertType='noMovementDetected',
                severity='medium',
                message=f'No movement detected for {duration/3600:.1f} hours',
                source='Backend',
                confidence=0.85,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'durationHours': duration/3600},
                category='patient_safety'
            ))
            state.noMovementAlertSent = True

    # Post-fall no movement (30 seconds)
    if accelerometerData and accelerometerData.fallDetected:
        if not state.fallDetectedTime:
            state.fallDetectedTime = timestamp
            state.postFallNoMovement = True
            logger.info(f"Fall detected for patient {patientId}")
    elif state.postFallNoMovement:
        if state.fallDetectedTime:
            duration = (timestamp - state.fallDetectedTime).total_seconds()
            if duration > 30:
                alerts.append(Alert(
                    alertType='postFallNoMovement',
                    severity='critical',
                    message=f'FALL DETECTED - No movement for {duration:.0f} seconds after fall',
                    source='Backend',
                    confidence=0.90,
                    patientId=patientId,
                    deviceId=deviceId,
                    timestamp=timestamp,
                    context={'durationSeconds': duration},
                    category='patient_safety'
                ))
                state.postFallNoMovement = False
                state.fallDetectedTime = None

    # Bathroom duration (>10 minutes)
    # Note: This requires BLE beacon to know when patient enters/exits bathroom
    # For now, we'll mark as TODO and track the state
    # TODO: Integrate with BLE beacon system
    if state.inBathroom and state.bathroomEntryTime:
        duration = (timestamp - state.bathroomEntryTime).total_seconds()
        if duration > 600:  # 10 minutes
            alerts.append(Alert(
                alertType='patientInBathroomTooLong',
                severity='medium',
                message=f'Patient in bathroom for {duration/60:.0f} minutes',
                source='Backend',
                confidence=0.80,
                patientId=patientId,
                deviceId=deviceId,
                timestamp=timestamp,
                context={'durationMinutes': duration/60},
                category='patient_safety'
            ))

    # Save updated state
    await stateManager.savePatientState(state)

    return alerts
```

**Step 4.4: Integrate into Main detectAlerts()**
File: `hospital-backend/app/services/alert_detection_service.py`

```python
async def detectAlerts(
    self,
    vitalsData: Dict[str, Any],
    patientId: str,
    deviceId: str,
    patientContext: Optional[PatientContext] = None,
    waveformAnalysis: Optional[WaveformAnalysis] = None,
    deviceContext: Optional[DeviceContext] = None,
    accelerometerData: Optional[AccelerometerData] = None
) -> List[Alert]:
    """Detect ALL alerts"""
    alerts = []
    timestamp = datetime.now()

    # ... existing detections ...

    # NEW: Duration-based alerts
    duration_alerts = await self._detectDurationAlerts(
        vitalsData, patientId, deviceId, timestamp,
        waveformAnalysis, accelerometerData
    )
    alerts.extend(duration_alerts)

    return alerts
```

---

### **Component 5: Device Maintenance Tracking**
**Alerts:** 9
**Estimated Time:** 5-7 days
**Complexity:** High

#### Alerts to Implement:
1. Device calibration overdue (>90 days)
2. Firmware out of date (critical update available)
3. Security certificate expired
4. Data audit trail gap detected
5. Timestamp manipulation detected
6. HIPAA logging failure
7. Consecutive invalid readings (>10)
8. Sensor drift beyond tolerance
9. Data dropout pattern (>10% missing)

#### Implementation Steps:

**Step 5.1: Create Device Maintenance Tables**
File: `hospital-backend/migrations/012_add_device_maintenance.sql`

```sql
-- Device maintenance tracking
CREATE TABLE IF NOT EXISTS deviceMaintenance (
    deviceId VARCHAR(50) PRIMARY KEY,

    -- Calibration tracking
    lastCalibrationDate TIMESTAMP,
    nextCalibrationDue TIMESTAMP,
    calibrationIntervalDays INTEGER DEFAULT 90,
    calibrationStatus VARCHAR(20) DEFAULT 'current',  -- 'current', 'due', 'overdue'

    -- Firmware tracking
    firmwareVersion VARCHAR(20),
    firmwareUpdateAvailable VARCHAR(20),
    firmwareUpdateDeadline TIMESTAMP,
    firmwareStatus VARCHAR(20) DEFAULT 'current',  -- 'current', 'update_available', 'critical'

    -- Security
    securityCertExpiry TIMESTAMP,
    securityCertStatus VARCHAR(20) DEFAULT 'valid',  -- 'valid', 'expiring_soon', 'expired'

    -- Data quality tracking
    consecutiveInvalidReadings INTEGER DEFAULT 0,
    sensorDriftValue FLOAT DEFAULT 0.0,
    dataDropoutRate FLOAT DEFAULT 0.0,  -- Percentage of missing data

    -- Last maintenance
    lastMaintenanceDate TIMESTAMP,
    maintenanceNotes TEXT,

    -- Metadata
    createdAt TIMESTAMP DEFAULT NOW(),
    updatedAt TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (deviceId) REFERENCES devices(deviceId) ON DELETE CASCADE
);

-- Device audit log for HIPAA compliance
CREATE TABLE IF NOT EXISTS deviceAuditLog (
    logId SERIAL PRIMARY KEY,
    deviceId VARCHAR(50) NOT NULL,
    patientId VARCHAR(50),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    eventType VARCHAR(100) NOT NULL,  -- 'vitals_received', 'assignment', 'unassignment', 'calibration', etc.
    eventData JSONB,
    sequenceNumber INTEGER NOT NULL,
    checksum VARCHAR(64),  -- SHA-256 of (sequenceNumber + eventData + previousChecksum)

    UNIQUE(deviceId, sequenceNumber),
    FOREIGN KEY (deviceId) REFERENCES devices(deviceId) ON DELETE CASCADE
);

CREATE INDEX idx_audit_device_seq ON deviceAuditLog(deviceId, sequenceNumber DESC);
CREATE INDEX idx_audit_device_time ON deviceAuditLog(deviceId, timestamp DESC);

-- Firmware versions table
CREATE TABLE IF NOT EXISTS firmwareVersions (
    versionId SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE NOT NULL,
    releaseDate TIMESTAMP NOT NULL,
    isCritical BOOLEAN DEFAULT FALSE,
    updateDeadline TIMESTAMP,
    releaseNotes TEXT,
    createdAt TIMESTAMP DEFAULT NOW()
);

-- Insert current firmware version
INSERT INTO firmwareVersions (version, releaseDate, isCritical)
VALUES ('1.0.0', NOW(), FALSE)
ON CONFLICT (version) DO NOTHING;
```

**Step 5.2: Create Device Maintenance Service**
File: `hospital-backend/app/services/device_maintenance_service.py`

```python
"""Device maintenance tracking and compliance"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncpg
from app.core.database import get_db
import logging

logger = logging.getLogger(__name__)

class DeviceMaintenanceService:
    """Handle device maintenance tracking and alerts"""

    async def initializeDeviceMaintenance(self, deviceId: str):
        """Initialize maintenance record for new device"""
        query = """
            INSERT INTO deviceMaintenance (
                deviceId,
                lastCalibrationDate,
                nextCalibrationDue,
                firmwareVersion,
                securityCertExpiry
            )
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (deviceId) DO NOTHING
        """

        now = datetime.now()
        async with get_db() as conn:
            await conn.execute(
                query,
                deviceId,
                now,
                now + timedelta(days=90),
                '1.0.0',
                now + timedelta(days=365)
            )

    async def getDeviceMaintenance(self, deviceId: str) -> Optional[Dict[str, Any]]:
        """Get maintenance record for device"""
        query = """
            SELECT * FROM deviceMaintenance
            WHERE deviceId = $1
        """
        async with get_db() as conn:
            row = await conn.fetchrow(query, deviceId)
            return dict(row) if row else None

    async def recordCalibration(self, deviceId: str, notes: str = ''):
        """Record device calibration"""
        now = datetime.now()
        query = """
            UPDATE deviceMaintenance
            SET lastCalibrationDate = $1,
                nextCalibrationDue = $2,
                calibrationStatus = 'current',
                lastMaintenanceDate = $1,
                maintenanceNotes = $3,
                updatedAt = $1
            WHERE deviceId = $4
        """
        async with get_db() as conn:
            await conn.execute(
                query,
                now,
                now + timedelta(days=90),
                notes,
                deviceId
            )

        # Log in audit trail
        await self.logAuditEvent(deviceId, None, 'calibration', {'notes': notes})

    async def updateFirmwareVersion(self, deviceId: str, version: str):
        """Update device firmware version"""
        query = """
            UPDATE deviceMaintenance
            SET firmwareVersion = $1,
                firmwareStatus = 'current',
                updatedAt = $2
            WHERE deviceId = $3
        """
        async with get_db() as conn:
            await conn.execute(query, version, datetime.now(), deviceId)

        # Log in audit trail
        await self.logAuditEvent(deviceId, None, 'firmware_update', {'version': version})

    async def logAuditEvent(
        self,
        deviceId: str,
        patientId: Optional[str],
        eventType: str,
        eventData: Dict[str, Any]
    ):
        """Log event in audit trail with integrity checking"""

        # Get last sequence number and checksum
        query = """
            SELECT sequenceNumber, checksum
            FROM deviceAuditLog
            WHERE deviceId = $1
            ORDER BY sequenceNumber DESC
            LIMIT 1
        """

        async with get_db() as conn:
            last_row = await conn.fetchrow(query, deviceId)

            if last_row:
                next_seq = last_row['sequencenumber'] + 1
                prev_checksum = last_row['checksum']
            else:
                next_seq = 1
                prev_checksum = ''

            # Calculate checksum
            checksum_input = f"{next_seq}{json.dumps(eventData, sort_keys=True)}{prev_checksum}"
            checksum = hashlib.sha256(checksum_input.encode()).hexdigest()

            # Insert audit log
            insert_query = """
                INSERT INTO deviceAuditLog (
                    deviceId, patientId, timestamp, eventType, eventData,
                    sequenceNumber, checksum
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """

            await conn.execute(
                insert_query,
                deviceId,
                patientId,
                datetime.now(),
                eventType,
                json.dumps(eventData),
                next_seq,
                checksum
            )

    async def verifyAuditLogIntegrity(self, deviceId: str) -> bool:
        """Verify audit log integrity (no gaps, valid checksums)"""
        query = """
            SELECT sequenceNumber, eventData, checksum
            FROM deviceAuditLog
            WHERE deviceId = $1
            ORDER BY sequenceNumber ASC
        """

        async with get_db() as conn:
            rows = await conn.fetch(query, deviceId)

            if len(rows) == 0:
                return True  # No logs yet, valid

            # Check sequence continuity
            for i in range(len(rows)):
                if rows[i]['sequencenumber'] != i + 1:
                    logger.error(f"Audit log gap detected for device {deviceId} at sequence {i+1}")
                    return False

            # Verify checksums
            prev_checksum = ''
            for row in rows:
                checksum_input = f"{row['sequencenumber']}{row['eventdata']}{prev_checksum}"
                expected_checksum = hashlib.sha256(checksum_input.encode()).hexdigest()

                if row['checksum'] != expected_checksum:
                    logger.error(f"Audit log checksum mismatch for device {deviceId} at sequence {row['sequencenumber']}")
                    return False

                prev_checksum = row['checksum']

            return True

    async def detectTimestampManipulation(self, deviceId: str) -> bool:
        """Detect if device timestamps have been manipulated"""
        # Check for backwards time jumps or inconsistencies
        query = """
            SELECT timestamp, eventType
            FROM deviceAuditLog
            WHERE deviceId = $1
            ORDER BY sequenceNumber DESC
            LIMIT 100
        """

        async with get_db() as conn:
            rows = await conn.fetch(query, deviceId)

            if len(rows) < 2:
                return False

            # Check for backwards time jumps
            for i in range(len(rows) - 1):
                if rows[i]['timestamp'] < rows[i+1]['timestamp']:
                    logger.error(f"Timestamp manipulation detected for device {deviceId}")
                    return True

            return False

    async def updateDataQualityMetrics(
        self,
        deviceId: str,
        invalidReading: bool = False,
        resetInvalidCount: bool = False,
        sensorDrift: Optional[float] = None,
        dropoutRate: Optional[float] = None
    ):
        """Update data quality metrics for device"""

        if resetInvalidCount:
            query = """
                UPDATE deviceMaintenance
                SET consecutiveInvalidReadings = 0,
                    updatedAt = $1
                WHERE deviceId = $2
            """
            async with get_db() as conn:
                await conn.execute(query, datetime.now(), deviceId)

        elif invalidReading:
            query = """
                UPDATE deviceMaintenance
                SET consecutiveInvalidReadings = consecutiveInvalidReadings + 1,
                    updatedAt = $1
                WHERE deviceId = $2
            """
            async with get_db() as conn:
                await conn.execute(query, datetime.now(), deviceId)

        if sensorDrift is not None:
            query = """
                UPDATE deviceMaintenance
                SET sensorDriftValue = $1,
                    updatedAt = $2
                WHERE deviceId = $3
            """
            async with get_db() as conn:
                await conn.execute(query, sensorDrift, datetime.now(), deviceId)

        if dropoutRate is not None:
            query = """
                UPDATE deviceMaintenance
                SET dataDropoutRate = $1,
                    updatedAt = $2
                WHERE deviceId = $3
            """
            async with get_db() as conn:
                await conn.execute(query, dropoutRate, datetime.now(), deviceId)

# Global instance
deviceMaintenanceService = DeviceMaintenanceService()
```

**Step 5.3: Add Maintenance Alert Detection**
File: `hospital-backend/app/services/alert_detection_service.py`

```python
from app.services.device_maintenance_service import deviceMaintenanceService

async def detectDeviceMaintenanceAlerts(self, deviceId: str) -> List[Alert]:
    """Detect device maintenance-related alerts"""
    alerts = []
    timestamp = datetime.now()

    # Get maintenance record
    maintenance = await deviceMaintenanceService.getDeviceMaintenance(deviceId)
    if not maintenance:
        return alerts

    # Calibration overdue
    if maintenance['nextcalibrationdue'] and maintenance['nextcalibrationdue'] < timestamp:
        days_overdue = (timestamp - maintenance['nextcalibrationdue']).days
        alerts.append(Alert(
            alertType='deviceCalibrationOverdue',
            severity='high',
            message=f'Device calibration overdue by {days_overdue} days',
            source='Backend',
            confidence=1.0,
            patientId='SYSTEM',
            deviceId=deviceId,
            timestamp=timestamp,
            context={'daysOverdue': days_overdue, 'lastCalibration': str(maintenance['lastcalibrationdate'])},
            category='device_maintenance'
        ))

    # Firmware out of date
    if maintenance['firmwarestatus'] == 'critical':
        alerts.append(Alert(
            alertType='firmwareOutOfDate',
            severity='high',
            message=f'Critical firmware update required for device {deviceId}',
            source='Backend',
            confidence=1.0,
            patientId='SYSTEM',
            deviceId=deviceId,
            timestamp=timestamp,
            context={
                'currentVersion': maintenance['firmwareversion'],
                'availableVersion': maintenance['firmwareupdateavailable'],
                'deadline': str(maintenance['firmwareupdatedeadline'])
            },
            category='device_maintenance'
        ))

    # Security certificate expired
    if maintenance['securitycertexpiry'] and maintenance['securitycertexpiry'] < timestamp:
        alerts.append(Alert(
            alertType='securityCertificateExpired',
            severity='critical',
            message=f'Security certificate expired for device {deviceId}',
            source='Backend',
            confidence=1.0,
            patientId='SYSTEM',
            deviceId=deviceId,
            timestamp=timestamp,
            context={'expiryDate': str(maintenance['securitycertexpiry'])},
            category='security'
        ))

    # Consecutive invalid readings
    if maintenance['consecutiveinvalidreadings'] > 10:
        alerts.append(Alert(
            alertType='consecutiveInvalidReadings',
            severity='high',
            message=f'Device {deviceId} has {maintenance["consecutiveinvalidreadings"]} consecutive invalid readings',
            source='Backend',
            confidence=0.95,
            patientId='SYSTEM',
            deviceId=deviceId,
            timestamp=timestamp,
            context={'invalidCount': maintenance['consecutiveinvalidreadings']},
            category='device_quality'
        ))

    # Sensor drift
    if maintenance['sensordriftvalue'] and abs(maintenance['sensordriftvalue']) > 0.1:
        alerts.append(Alert(
            alertType='sensorDriftBeyondTolerance',
            severity='medium',
            message=f'Sensor drift detected: {maintenance["sensordriftvalue"]:.2f}',
            source='Backend',
            confidence=0.85,
            patientId='SYSTEM',
            deviceId=deviceId,
            timestamp=timestamp,
            context={'driftValue': maintenance['sensordriftvalue']},
            category='device_quality'
        ))

    # Data dropout
    if maintenance['datadropoutrate'] and maintenance['datadropoutrate'] > 10:
        alerts.append(Alert(
            alertType='dataDropoutPattern',
            severity='medium',
            message=f'High data dropout rate: {maintenance["datadropoutrate"]:.1f}%',
            source='Backend',
            confidence=0.90,
            patientId='SYSTEM',
            deviceId=deviceId,
            timestamp=timestamp,
            context={'dropoutRate': maintenance['datadropoutrate']},
            category='device_quality'
        ))

    # Audit trail integrity
    integrity_valid = await deviceMaintenanceService.verifyAuditLogIntegrity(deviceId)
    if not integrity_valid:
        alerts.append(Alert(
            alertType='dataAuditTrailGap',
            severity='critical',
            message=f'Audit trail integrity violation for device {deviceId}',
            source='Backend',
            confidence=1.0,
            patientId='SYSTEM',
            deviceId=deviceId,
            timestamp=timestamp,
            context={},
            category='compliance'
        ))

    # Timestamp manipulation
    timestamp_manipulated = await deviceMaintenanceService.detectTimestampManipulation(deviceId)
    if timestamp_manipulated:
        alerts.append(Alert(
            alertType='timestampManipulationDetected',
            severity='critical',
            message=f'Timestamp manipulation detected for device {deviceId}',
            source='Backend',
            confidence=0.95,
            patientId='SYSTEM',
            deviceId=deviceId,
            timestamp=timestamp,
            context={},
            category='security'
        ))

    return alerts
```

**Step 5.4: Add Periodic Maintenance Check**
File: `hospital-backend/main.py`

```python
from app.services.device_maintenance_service import deviceMaintenanceService
from app.services.alert_detection_service import completeAlertDetectionService

async def checkDeviceMaintenanceAlerts():
    """Periodic check for device maintenance alerts (run every hour)"""
    try:
        # Get all active devices
        query = "SELECT deviceId FROM devices WHERE status != 'decommissioned'"
        async with get_db() as conn:
            devices = await conn.fetch(query)

        for device in devices:
            device_id = device['deviceid']

            # Check maintenance alerts
            alerts = await completeAlertDetectionService.detectDeviceMaintenanceAlerts(device_id)

            # Broadcast alerts
            for alert in alerts:
                alert_payload = completeAlertDetectionService.createAlertPayload(alert)
                await connectionManager.broadcastSystemAlert(alert_payload)
                logger.info(f"Maintenance Alert: {alert.alertType} - {alert.message}")

    except Exception as e:
        logger.error(f"Error in device maintenance check: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # ... existing code ...

    # Schedule device maintenance checks every hour
    scheduler.add_job(
        checkDeviceMaintenanceAlerts,
        'interval',
        hours=1,
        id='device_maintenance_check'
    )
    logger.info("✅ Device maintenance scheduler started")
```

---

## Testing Plan

### Component 1: Historical Vitals Query
- Insert test vitals data with trends (increasing HR, decreasing SpO2)
- Verify trend calculations are accurate
- Test NEWS2 score calculation with known values
- Verify alerts trigger at correct thresholds

### Component 2: Cross-Patient Analysis
- Create multiple test patients with varying conditions
- Test device pool depletion scenarios
- Test fever outbreak detection
- Test mass admission detection

### Component 3: Impedance Trend Tracking
- Insert impedance readings with tampering patterns
- Test rapid fluctuation detection
- Test gel drying detection
- Test watch removal counting

### Component 4: Duration/State Tracking
- Test seizure duration tracking
- Test movement detection and no-movement alerts
- Test fall detection and post-fall monitoring
- Verify state persistence across restarts

### Component 5: Device Maintenance
- Test calibration overdue detection
- Test firmware update tracking
- Test audit log integrity verification
- Test timestamp manipulation detection

---

## Success Criteria

1. ✅ All 5 infrastructure components implemented
2. ✅ All 38 alerts functional and tested
3. ✅ Database migrations applied successfully
4. ✅ Periodic schedulers running for system/maintenance checks
5. ✅ State management persisting correctly
6. ✅ Alert notifications broadcasting via WebSocket
7. ✅ Backend starts without errors
8. ✅ All existing 80 alerts still functional

**Final Alert Count:** 118/148 (80%)

---

## Timeline

- **Days 1-2:** Component 1 (Historical Vitals)
- **Day 3:** Component 2 (Cross-Patient Analysis)
- **Days 4-5:** Component 3 (Impedance Tracking)
- **Days 6-7:** Component 4 (Duration/State Tracking)
- **Days 8-9:** Component 5 (Device Maintenance) - if time allows

**Estimated Total:** 6-9 days

---

## Dependencies

### Required Python Packages:
```bash
pip install apscheduler  # For periodic task scheduling
pip install numpy  # For trend calculations
```

### Database Requirements:
- PostgreSQL with TimescaleDB extension (already have)
- 3 new migrations (impedance, patient states, device maintenance)

### Backend Modifications:
- Update MQTT service to pass historical data
- Add periodic schedulers
- Initialize maintenance records for existing devices
- Update WebSocket manager for system-level alerts

---

## Notes

- **BLE Beacons Deferred:** Bathroom duration tracking needs BLE but we'll track the state for when BLE is available
- **Waveform Analysis Deferred:** Seizure detection requires EEG waveform analysis which is deferred
- **Medical Scheduling Deferred:** Will implement when medication scheduling system is ready
- **External Systems Deferred:** Fire alarm, active shooter, MRI integration require external APIs

**This plan focuses on backend infrastructure that we fully control and can implement independently.**
