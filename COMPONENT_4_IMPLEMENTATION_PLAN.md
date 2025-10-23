# Component 4: Duration/State Tracking Implementation Plan

**Date:** 2025-10-15
**Component:** Duration/State Tracking (8 alerts)
**Estimated Time:** 2-3 days
**Complexity:** Moderate

---

## Overview

Component 4 implements persistent state tracking for patients to detect duration-based conditions and prolonged abnormal states. This requires tracking when conditions start, monitoring duration, and triggering alerts when thresholds are exceeded.

---

## Alerts to Implement (8 total)

### 1. prolongedTachycardia
- **Condition:** Heart rate >100 bpm for >15 minutes
- **Severity:** MEDIUM
- **Logic:** Track when HR first exceeds 100, check if still elevated after 15min

### 2. prolongedBradycardia
- **Condition:** Heart rate <60 bpm for >10 minutes
- **Severity:** MEDIUM
- **Logic:** Track when HR first drops below 60, check duration

### 3. prolongedHypotension
- **Condition:** Systolic BP <90 mmHg for >10 minutes
- **Severity:** HIGH
- **Logic:** Track BP drop onset, monitor duration

### 4. prolongedHypoxia
- **Condition:** SpO2 <90% for >5 minutes
- **Severity:** CRITICAL
- **Logic:** Track hypoxia onset, critical if persists

### 5. prolongedFever
- **Condition:** Temperature >38.3°C for >1 hour
- **Severity:** MEDIUM
- **Logic:** Track fever onset, check hourly duration

### 6. prolongedHypothermia
- **Condition:** Temperature <35°C for >30 minutes
- **Severity:** HIGH
- **Logic:** Track hypothermia onset, critical condition

### 7. noVitalsReceived
- **Condition:** No vitals data for >10 minutes
- **Severity:** HIGH
- **Logic:** Track lastVitalsTimestamp, alert if gap exceeds threshold

### 8. intermittentConnection
- **Condition:** >3 connection drops in 1 hour
- **Severity:** MEDIUM
- **Logic:** Track connection event history, count drops

---

## Implementation Strategy

### Phase 1: Database Schema (Migration 011)

Create `patientStates` table to persist state information:

```sql
CREATE TABLE IF NOT EXISTS patientStates (
    stateId SERIAL PRIMARY KEY,
    patientId TEXT NOT NULL UNIQUE,

    -- Tachycardia state
    tachycardiaStartTime TIMESTAMP,
    tachycardiaAlertSent BOOLEAN DEFAULT FALSE,

    -- Bradycardia state
    bradycardiaStartTime TIMESTAMP,
    bradycardiaAlertSent BOOLEAN DEFAULT FALSE,

    -- Hypotension state
    hypotensionStartTime TIMESTAMP,
    hypotensionAlertSent BOOLEAN DEFAULT FALSE,

    -- Hypoxia state
    hypoxiaStartTime TIMESTAMP,
    hypoxiaAlertSent BOOLEAN DEFAULT FALSE,

    -- Fever state
    feverStartTime TIMESTAMP,
    feverAlertSent BOOLEAN DEFAULT FALSE,

    -- Hypothermia state
    hypothermiaStartTime TIMESTAMP,
    hypothermiaAlertSent BOOLEAN DEFAULT FALSE,

    -- Last vitals received
    lastVitalsTimestamp TIMESTAMP,
    noVitalsAlertSent BOOLEAN DEFAULT FALSE,

    -- Connection drop tracking (JSON array of timestamps)
    connectionDrops JSONB DEFAULT '[]'::jsonb,

    -- Timestamps
    createdAt TIMESTAMP DEFAULT NOW(),
    updatedAt TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (patientId) REFERENCES patients(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_patientstates_patient ON patientStates(patientId);
CREATE INDEX IF NOT EXISTS idx_patientstates_updated ON patientStates(updatedAt);
```

### Phase 2: State Manager Service

Create `state_manager.py` service to handle state persistence:

```python
class StateManager:
    """Manages persistent patient state for duration-based alerts"""

    async def getPatientState(self, patientId: str) -> Optional[PatientState]:
        """Retrieve patient state from database"""

    async def updatePatientState(self, patientId: str, stateUpdates: Dict[str, Any]) -> None:
        """Update specific state fields for a patient"""

    async def resetConditionState(self, patientId: str, condition: str) -> None:
        """Reset specific condition tracking (e.g., after resolved)"""

    async def recordConnectionDrop(self, patientId: str) -> None:
        """Record a connection drop event"""

    async def getConnectionDropCount(self, patientId: str, windowMinutes: int = 60) -> int:
        """Count connection drops within time window"""
```

### Phase 3: Alert Detection Integration

Add `_detectDurationAlerts()` method to alert_detection_service.py:

```python
async def _detectDurationAlerts(
    self,
    vitalsData: Dict[str, Any],
    patientId: str,
    deviceId: str,
    timestamp: datetime,
    patientContext: Optional[PatientContext] = None
) -> List[Alert]:
    """Detect duration-based alerts using persistent state (8 alerts)"""

    from app.services.state_manager import stateManager

    alerts = []

    # Get current patient state
    state = await stateManager.getPatientState(patientId)
    if not state:
        # Initialize state for new patient
        await stateManager.initializePatientState(patientId)
        state = await stateManager.getPatientState(patientId)

    # Update last vitals timestamp
    await stateManager.updatePatientState(patientId, {
        'lastVitalsTimestamp': timestamp
    })

    # 1. Prolonged Tachycardia (HR >100 for >15min)
    if 'heartRate' in vitalsData:
        hr = vitalsData['heartRate']
        if hr > 100:
            if not state.tachycardiaStartTime:
                # Start tracking
                await stateManager.updatePatientState(patientId, {
                    'tachycardiaStartTime': timestamp,
                    'tachycardiaAlertSent': False
                })
            else:
                # Check duration
                duration = (timestamp - state.tachycardiaStartTime).total_seconds() / 60
                if duration > 15 and not state.tachycardiaAlertSent:
                    alerts.append(Alert(...))
                    await stateManager.updatePatientState(patientId, {
                        'tachycardiaAlertSent': True
                    })
        else:
            # Condition resolved
            if state.tachycardiaStartTime:
                await stateManager.resetConditionState(patientId, 'tachycardia')

    # Similar logic for other 7 alerts...

    return alerts
```

### Phase 4: Background Monitoring Task

Create background task to check for noVitalsReceived alert:

```python
# In state_monitor.py
async def monitor_patient_vitals_timeout():
    """Background task to check for patients with no vitals received"""
    while True:
        try:
            from app.core.database import getDbConnection
            from app.services.alert_detection_service import completeAlertDetectionService

            async with getDbConnection() as conn:
                # Find patients with last vitals >10 minutes ago
                rows = await conn.fetch("""
                    SELECT patientId, lastVitalsTimestamp, noVitalsAlertSent
                    FROM patientStates
                    WHERE lastVitalsTimestamp < NOW() - INTERVAL '10 minutes'
                      AND noVitalsAlertSent = FALSE
                """)

                for row in rows:
                    # Generate alert
                    alert = Alert(
                        alertType='noVitalsReceived',
                        severity='high',
                        message=f'No vitals received for >10 minutes',
                        ...
                    )

                    # Broadcast alert
                    await connectionManager.sendAlert(row['patientId'], ...)

                    # Mark as sent
                    await conn.execute("""
                        UPDATE patientStates
                        SET noVitalsAlertSent = TRUE
                        WHERE patientId = $1
                    """, row['patientId'])

        except Exception as e:
            logger.error(f"Error in vitals timeout monitor: {e}")

        # Check every 60 seconds
        await asyncio.sleep(60)
```

---

## Implementation Steps

### Step 1: Create Migration (30 min)
- [ ] Create migrations/011_add_patient_states.sql
- [ ] Create apply_migration_011.py script
- [ ] Apply migration to database
- [ ] Verify tables and indexes created

### Step 2: Create State Manager Service (1-2 hours)
- [ ] Create app/services/state_manager.py
- [ ] Implement PatientState dataclass
- [ ] Implement StateManager class with CRUD methods
- [ ] Add connection drop tracking logic
- [ ] Create singleton instance

### Step 3: Implement Duration Alert Detection (2-3 hours)
- [ ] Add `_detectDurationAlerts()` to alert_detection_service.py
- [ ] Implement logic for all 8 duration-based alerts
- [ ] Add state initialization for new patients
- [ ] Add state reset logic for resolved conditions
- [ ] Integrate into main `detectAlerts()` method

### Step 4: Create Background Monitor (1 hour)
- [ ] Create app/services/state_monitor.py
- [ ] Implement vitals timeout monitoring task
- [ ] Add startup integration in main.py
- [ ] Test background task execution

### Step 5: Testing (2-3 hours)
- [ ] Test each alert type with mock data
- [ ] Verify state persistence across vitals updates
- [ ] Test condition resolution (state reset)
- [ ] Test no vitals received alert
- [ ] Test connection drop counting
- [ ] Verify alerts not re-sent after acknowledged

---

## Success Criteria

- [ ] Migration 011 applied successfully
- [ ] `patientStates` table created with proper schema
- [ ] StateManager service functional
- [ ] All 8 duration alerts implemented
- [ ] Alerts trigger only once per condition occurrence
- [ ] State resets when conditions resolve
- [ ] Background monitor runs successfully
- [ ] No backend errors
- [ ] Alerts broadcast via WebSocket

---

## Estimated Timeline

- **Day 1:** Steps 1-2 (Migration + State Manager)
- **Day 2:** Step 3 (Alert Detection Logic)
- **Day 3:** Steps 4-5 (Background Monitor + Testing)

**Total:** 2-3 days depending on testing complexity

---

## Dependencies

- ✅ Component 1 complete (Historical Vitals Query)
- ✅ Component 3 complete (Impedance Tracking - similar pattern)
- ✅ System Alert Scheduler (similar background task pattern)
- ✅ WebSocket Manager (alert broadcasting)

---

## Notes

- State persistence ensures alerts trigger only once per occurrence
- Conditions automatically reset when vitals return to normal
- Background monitor handles cases where vitals stop entirely
- Connection drop tracking uses JSONB array for flexibility
- All timestamps use PostgreSQL NOW() for consistency

