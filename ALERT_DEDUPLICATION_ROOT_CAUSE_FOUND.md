# Alert Deduplication - Root Cause Analysis

## Date: 2025-11-07

## Problem Summary
Alert acknowledgement button works (returns 200 OK), but alerts don't disappear from the patient card because there are 100K+ duplicate alerts being created every second.

## Investigation Findings

### Finding 1: I Fixed the Wrong File
I added deduplication logic to `vital_alert_service.py` but this service is **NOT being used** for creating vital alerts.

The actual alert creation happens in:
- **`mqtt_service.py` lines 636-645** - This is where ALL alerts are created and stored

### Finding 2: Current Alert Counts (Database Evidence)
Query results from `patient_alerts` table:

```
Type: bradypnea            | Status: active          | Count: 6,731
Type: tachycardia          | Status: active          | Count: 100,698
Type: tachycardia          | Status: acknowledged    | Count: 10
Type: tachypnea            | Status: active          | Count: 106,864
Type: earlyWarningScoreMedium | Status: active       | Count: 86,143
```

**Result:** Over 100,000 duplicate tachycardia alerts, 106,864 duplicate tachypnea alerts!

### Finding 3: Table Schema Mismatch
The `patient_alerts` table does NOT have these columns:
- `vitalType`
- `vitalValue`
- `thresholdValue`

My deduplication code in `vital_alert_service.py` was trying to query these non-existent columns, so it was FAILING SILENTLY and falling through to create new alerts every time.

### Finding 4: Actual Alert Creation Flow

**Correct Flow:**
```
ESP32 → MQTT → mqtt_service.py → alert_detection_service.py → detectAlerts()
                      ↓
                mqtt_service.py line 632: alerts = await alertDetectionService.detectAlerts(...)
                      ↓
                mqtt_service.py lines 636-645: FOR EACH ALERT: INSERT INTO patient_alerts
                      ↓
                (NO DEDUPLICATION CHECK - creates duplicate every second)
```

**What I mistakenly fixed:**
```
vital_alert_service.py → _create_alert()
  ↓
  (This code path is NEVER EXECUTED for vital alerts)
```

### Finding 5: Why 100K+ Duplicates?
- ESP32 sends vitals every 1 second
- Backend runs alert detection every second
- Alert detection finds tachycardia (HR > 120)
- Backend creates NEW alert (no deduplication check)
- **After 30 hours:** 30 hours × 3600 sec/hour = 108,000 alerts

## The Fix (Correct Location)

Need to add deduplication to **`mqtt_service.py` lines 636-645** BEFORE the INSERT statement:

```python
# Store alerts in database and broadcast via WebSocket
async with getDbConnection() as conn:
    for alert in alerts:
        # CHECK FOR EXISTING ALERT (DEDUPLICATION)
        existing_alert = await conn.fetchrow('''
            SELECT id, status
            FROM patient_alerts
            WHERE "patientId" = $1
              AND type = $2
              AND status IN ('active', 'acknowledged')
            ORDER BY "createdAt" DESC
            LIMIT 1
        ''', patientId, alert.alertType)

        if existing_alert:
            # Alert already exists - just update timestamp
            await conn.execute('''
                UPDATE patient_alerts
                SET "updatedAt" = NOW()
                WHERE id = $1
            ''', existing_alert['id'])
            continue  # Skip INSERT

        # No existing alert - create new one
        alert_id = str(uuid.uuid4())
        await conn.execute('''
            INSERT INTO patient_alerts
            (id, "patientId", "deviceId", type, severity, message, source, "alertTimestamp", status, "createdAt", "updatedAt")
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active', NOW(), NOW())
        ''', alert_id, patientId, deviceId, alert.alertType, alert.severity, alert.message, alert.source, datetime.now())
```

## Action Required

1. **Remove my broken fix** from `vital_alert_service.py` (lines 177-201)
2. **Add correct deduplication** to `mqtt_service.py` (lines 636-645)
3. **Delete duplicate alerts** from database (optional - could be 500K+ rows)
4. **Restart backend** and verify deduplication works

## Files to Fix

### File 1: `hospital-backend/app/services/mqtt_service.py`
**Lines:** 636-645
**Change:** Add deduplication check before INSERT

### File 2: `hospital-backend/app/services/vital_alert_service.py`
**Lines:** 177-213
**Change:** Revert to original code (remove broken deduplication that queries non-existent columns)

## Testing Plan

After fix:
1. Acknowledge an alert → Alert count should decrease
2. Wait 10 seconds → No new duplicate alerts should appear
3. Check database → Only 1 active alert per vital type per patient
