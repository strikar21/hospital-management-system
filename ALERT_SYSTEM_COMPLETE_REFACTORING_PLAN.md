# Alert System - Complete Refactoring Plan

## Date: 2025-11-07

## Current Problems

### Problem 1: Schema Mismatch
- `patient_alerts` table lacks columns: `vitalType`, `vitalValue`, `thresholdValue`, `createdBy`
- `vital_alert_service.py` tries to INSERT into non-existent columns → FAILS SILENTLY
- Code path in `vital_alert_service.py` is NEVER used for vital alerts

### Problem 2: No Deduplication
- `mqtt_service.py:636-645` creates NEW alert every second
- Result: **100,000+ duplicate alerts** in database
- User acknowledges 1 alert → 99,999 duplicates still show as "active"

### Problem 3: No Auto-Resolution
- Alerts stay "active" forever, even when condition resolves
- No logic to mark alerts as "resolved" when vitals return to normal

### Problem 4: Fragmented Alert Creation
- Alerts created in 3 different places:
  1. `mqtt_service.py:641-645` - Vital alerts from alert_detection_service
  2. `arrhythmia_detection_service.py:223-229` - Arrhythmia alerts
  3. Other scattered locations
- No centralized alert management service

## Architecture Analysis

### Current Data Flow
```
ESP32 → MQTT → mqtt_service.py:455 _handleVitalsMessageNew()
                     ↓
                alert_detection_service.py:212 detectAlerts()
                     ↓
                Returns List[Alert] (148 alert types)
                     ↓
                mqtt_service.py:636-645 FOR EACH alert:
                     INSERT INTO patient_alerts (no dedup check)
                     ↓
                WebSocket broadcast to frontend
```

### Alert Detection Service
- **Complete implementation** with 148 alert types across 18 categories
- Returns `Alert` dataclass with: `alertType`, `severity`, `message`, `source`, `confidence`, `context`
- Works correctly - problem is in STORAGE layer

### patient_alerts Table Schema
```sql
CREATE TABLE patient_alerts (
    id TEXT PRIMARY KEY,
    "patientId" TEXT NOT NULL,
    "deviceId" TEXT,
    type TEXT NOT NULL,              -- 'tachycardia', 'seizure', etc.
    severity TEXT NOT NULL,           -- 'critical', 'high', 'medium', 'low'
    message TEXT NOT NULL,
    source TEXT NOT NULL,             -- 'ESP32' or 'Backend'
    "alertTimestamp" TIMESTAMP NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'acknowledged', 'resolved'
    "acknowledgedBy" TEXT,
    "acknowledgedAt" TIMESTAMP,
    "createdAt" TIMESTAMP DEFAULT NOW(),
    "updatedAt" TIMESTAMP DEFAULT NOW()
);
```

**Missing Columns for Proper Medical Tracking:**
- `vitalType` TEXT - Which vital triggered alert (e.g., 'heartRate', 'respiratoryRate')
- `vitalValue` FLOAT - Actual vital reading that triggered alert
- `thresholdValue` FLOAT - Threshold that was exceeded
- `createdBy` TEXT - Device ID that created the alert
- `resolvedAt` TIMESTAMP - When condition cleared
- `category` TEXT - Alert category ('cardiac', 'respiratory', 'neurological', etc.)
- `confidence` FLOAT - Confidence score (0.0-1.0)
- `context` JSONB - Additional metadata from alert detection

## Refactoring Plan

### Phase 1: Database Schema Migration ✅

**File:** `hospital-backend/migrations/021_enhance_patient_alerts_table.sql`

```sql
-- Migration 021: Enhance patient_alerts table for proper medical tracking and deduplication

-- Add missing columns for medical context
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "vitalType" TEXT;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "vitalValue" FLOAT;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "thresholdValue" FLOAT;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "createdBy" TEXT;  -- Device ID
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "resolvedAt" TIMESTAMP;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS confidence FLOAT;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS context JSONB;

-- Add 'resolved' to status enum (current values: 'active', 'acknowledged')
-- Status lifecycle: active → acknowledged → resolved
COMMENT ON COLUMN patient_alerts.status IS 'Alert lifecycle status: active (new), acknowledged (staff aware), resolved (condition cleared)';

-- Add indexes for deduplication queries
CREATE INDEX IF NOT EXISTS idx_patient_alerts_dedup
    ON patient_alerts("patientId", type, status)
    WHERE status IN ('active', 'acknowledged');

-- Add index for vital-specific alerts
CREATE INDEX IF NOT EXISTS idx_patient_alerts_vital
    ON patient_alerts("patientId", "vitalType", status)
    WHERE "vitalType" IS NOT NULL;

-- Add comment for documentation
COMMENT ON TABLE patient_alerts IS 'Persistent clinical alert storage with full lifecycle tracking (active → acknowledged → resolved)';
```

### Phase 2: Create Centralized Alert Management Service ✅

**File:** `hospital-backend/app/services/alert_manager_service.py` (NEW)

This service will:
1. ✅ Centralize ALL alert creation
2. ✅ Implement deduplication logic
3. ✅ Handle alert lifecycle (active → acknowledged → resolved)
4. ✅ Auto-resolve alerts when conditions clear
5. ✅ Provide medical-safe deduplication strategy

**Key Functions:**
```python
class AlertManagerService:
    async def createOrUpdateAlert(
        self,
        alert: Alert,  # From alert_detection_service
        patientId: str,
        deviceId: str,
        conn: asyncpg.Connection
    ) -> Optional[str]:
        """
        Create new alert OR update existing alert with deduplication.

        Deduplication Strategy:
        1. Check for existing active/acknowledged alert of same type
        2. If exists: Update timestamp + vitalValue (no new alert)
        3. If not exists: Create new alert
        4. Return alert ID (or None if updated existing)
        """

    async def resolveAlert(
        self,
        patientId: str,
        alertType: str,
        conn: asyncpg.Connection
    ) -> bool:
        """
        Mark alert as resolved when condition clears.
        Status: active/acknowledged → resolved
        """

    async def checkForResolution(
        self,
        patientId: str,
        currentVitals: Dict[str, float],
        conn: asyncpg.Connection
    ) -> List[str]:
        """
        Check if any active alerts should be auto-resolved.
        Returns list of resolved alert IDs.
        """
```

### Phase 3: Refactor mqtt_service.py ✅

**Current Code (Lines 632-652):**
```python
alerts = await alertDetectionService.detectAlerts(vitalsDict, patientId, deviceId)

# Store alerts in database and broadcast via WebSocket
async with getDbConnection() as conn:
    for alert in alerts:
        # Generate unique alert ID
        alert_id = str(uuid.uuid4())

        # Store alert in patient_alerts table
        await conn.execute('''
            INSERT INTO patient_alerts
            (id, "patientId", "deviceId", type, severity, message, source, "alertTimestamp", status, "createdAt", "updatedAt")
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active', NOW(), NOW())
        ''', alert_id, patientId, deviceId, alert.alertType, alert.severity, alert.message, alert.source, datetime.now())

        # Broadcast with ID for frontend acknowledgment tracking
        alertPayload = alertDetectionService.createAlertPayload(alert)
        alertPayload['id'] = alert_id
        await connectionManager.sendAlert(patientId, alertPayload)

        logger.debug(f"Alert stored: {alert.alertType} (ID: {alert_id}) for patient {patientId}")
```

**Refactored Code:**
```python
# Import new service
from .alert_manager_service import alertManagerService

# Detect alerts
alerts = await alertDetectionService.detectAlerts(vitalsDict, patientId, deviceId)

# Store/update alerts with deduplication and broadcast
async with getDbConnection() as conn:
    for alert in alerts:
        # Use centralized alert manager (handles deduplication)
        alertId = await alertManagerService.createOrUpdateAlert(
            alert, patientId, deviceId, conn
        )

        # Only broadcast if NEW alert created (not duplicate update)
        if alertId:
            alertPayload = alertDetectionService.createAlertPayload(alert)
            alertPayload['id'] = alertId
            await connectionManager.sendAlert(patientId, alertPayload)
            logger.warning(f"🚨 New alert: {alertId} - {alert.severity} - {alert.message}")

    # Check for auto-resolution (vitals returned to normal)
    resolvedAlertIds = await alertManagerService.checkForResolution(
        patientId, vitalsDict, conn
    )

    # Broadcast resolution to frontend
    for resolvedId in resolvedAlertIds:
        await connectionManager.sendAlertResolved(patientId, resolvedId)
```

### Phase 4: Remove Broken vital_alert_service.py Code ✅

**File:** `hospital-backend/app/services/vital_alert_service.py`

**Lines to Revert:** 177-213 (my broken deduplication code)

**Action:** Remove the broken deduplication logic that queries non-existent `vitalType` column

**Note:** This entire service may be DEPRECATED since alerts are now created via `alert_detection_service.py` + `alert_manager_service.py`

### Phase 5: Clean Up Duplicate Alerts ✅

**Script:** `hospital-backend/cleanup_duplicate_alerts.py` (NEW)

```python
"""
Clean up 500K+ duplicate alerts from database.
Keep only the MOST RECENT alert per (patientId, type, status) combination.
"""

import asyncio
import asyncpg

async def cleanup_duplicates():
    conn = await asyncpg.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')

    # For each (patientId, type, status), keep newest alert, delete rest
    result = await conn.execute('''
        DELETE FROM patient_alerts
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY "patientId", type, status
                           ORDER BY "createdAt" DESC
                       ) as rn
                FROM patient_alerts
            ) t
            WHERE t.rn > 1
        )
    ''')

    print(f"✅ Deleted {result.split()[-1]} duplicate alerts")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(cleanup_duplicates())
```

### Phase 6: Testing & Validation ✅

**Test Cases:**

1. **Deduplication Test:**
   - Acknowledge alert → Check count decreases
   - Wait 10 seconds → Verify no new duplicates created
   - Database should have only 1 active alert per type per patient

2. **Auto-Resolution Test:**
   - Create tachycardia alert (HR > 120)
   - Lower HR to 80 BPM
   - Verify alert status changes to 'resolved'
   - Verify frontend removes resolved alert

3. **New Episode Detection:**
   - Tachycardia alert → acknowledge
   - HR returns to normal (auto-resolve)
   - HR spikes again above 120
   - Verify NEW alert is created (not deduplicated)

4. **Severity Escalation:**
   - Medium severity alert (HR 125)
   - HR increases to 180 (critical)
   - Verify severity is UPDATED in existing alert
   - Verify WebSocket notifies of escalation

## Medical Safety Considerations

### Alert Lifecycle States
```
┌─────────┐  Staff         ┌──────────────┐  Vitals      ┌──────────┐
│ active  │ ─acknowledges→ │ acknowledged │ ─normalize→  │ resolved │
└─────────┘                └──────────────┘              └──────────┘
     │                            │
     │                            │
     └────────────vitals normalize────────────┘
```

### Deduplication Rules (Medical-Safe)

**Rule 1: Same Ongoing Episode**
- Patient has active tachycardia alert (HR 125)
- HR stays elevated (127, 126, 128)
- **Action:** UPDATE existing alert timestamp, don't create new
- **Reason:** Same ongoing episode, not a new medical event

**Rule 2: Condition Resolves**
- Patient has active/acknowledged tachycardia
- HR returns to normal (<100 for 60 seconds)
- **Action:** Mark alert as 'resolved', auto-clear from frontend
- **Reason:** Medical condition cleared

**Rule 3: New Episode After Resolution**
- Previous tachycardia alert was resolved
- HR spikes again above 120
- **Action:** CREATE new alert (not a duplicate)
- **Reason:** New medical episode requires new alert

**Rule 4: Severity Escalation**
- Medium alert (HR 125) exists
- HR increases to 180 (critical)
- **Action:** UPDATE severity + message, broadcast escalation
- **Reason:** Same episode but worsening condition

### Time-Based Resolution Criteria
```python
RESOLUTION_CRITERIA = {
    'tachycardia': {'normal_hr': (60, 100), 'duration': 60},  # 60s normal
    'tachypnea': {'normal_rr': (12, 20), 'duration': 60},
    'hypoxia': {'normal_spo2': (95, 100), 'duration': 30},
    'fever': {'normal_temp': (36.5, 37.5), 'duration': 120},
    # Critical alerts require longer stability
    'severeHypoxia': {'normal_spo2': (95, 100), 'duration': 120},
}
```

## Implementation Order

1. ✅ **Day 1:** Create migration 021, apply to database
2. ✅ **Day 1:** Create `alert_manager_service.py` with full logic
3. ✅ **Day 1:** Refactor `mqtt_service.py` to use new service
4. ✅ **Day 1:** Remove broken code from `vital_alert_service.py`
5. ✅ **Day 1:** Test deduplication with live ESP32
6. ✅ **Day 2:** Implement auto-resolution logic
7. ✅ **Day 2:** Test complete alert lifecycle
8. ✅ **Day 2:** Run cleanup script to remove duplicates
9. ✅ **Day 2:** Monitor production for 24 hours

## Success Metrics

- ✅ Alert count decreases immediately after acknowledgement
- ✅ No duplicate alerts created (max 1 active per type per patient)
- ✅ Alerts auto-resolve when conditions clear
- ✅ New episodes create new alerts after resolution
- ✅ Database size reduced from 500K+ alerts to <1000 alerts
- ✅ Frontend performance improved (no lag from 100K alerts)

## Rollback Plan

If refactoring fails:
1. Revert `mqtt_service.py` to direct INSERT (no dedup)
2. Revert database migration 021
3. Deploy previous working version
4. Analyze failure and create new plan

## Files to Create/Modify

### New Files:
1. `hospital-backend/migrations/021_enhance_patient_alerts_table.sql`
2. `hospital-backend/app/services/alert_manager_service.py`
3. `hospital-backend/cleanup_duplicate_alerts.py`

### Modified Files:
1. `hospital-backend/app/services/mqtt_service.py` (lines 632-658)
2. `hospital-backend/app/services/vital_alert_service.py` (remove lines 177-213)
3. `hospital-backend/app/services/websocket_manager.py` (add `sendAlertResolved` method)

## Estimated Effort

- **Development:** 4-6 hours
- **Testing:** 2-3 hours
- **Deployment:** 1 hour
- **Monitoring:** 24 hours
- **Total:** ~2 days

## Questions to Resolve

1. ❓ Should we delete 500K+ duplicate alerts or mark them as 'duplicate'?
2. ❓ Should alerts auto-resolve after X minutes even if vitals don't normalize?
3. ❓ Should severity escalation create a new alert or update existing?
4. ❓ Should we add alert fatigue prevention (max alerts per patient)?

---

**Status:** Ready for implementation
**Reviewed By:** [User approval needed]
**Approved:** [Pending]
