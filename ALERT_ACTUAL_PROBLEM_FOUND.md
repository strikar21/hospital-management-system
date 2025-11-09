# Alert Acknowledgement - ACTUAL PROBLEM FOUND

## What You're Experiencing
You click "Acknowledge" on an alert, but you can still click it again multiple times. The alert doesn't disappear.

## What I Thought Was Wrong
I thought the backend wasn't providing `isAcknowledged` field. I added it, but the problem persists.

## What's ACTUALLY Wrong

### The Real Data Flow

1. **You click "Acknowledge" on alert `d9cedad7` (tachypnea)**
   - Backend: `UPDATE patient_alerts SET status='acknowledged'` ✅
   - Alert status in DB: `acknowledged` ✅

2. **Backend detects vitals improved (respiratory rate normalized)**
   - Backend: `UPDATE patient_alerts SET status='resolved'` (auto-resolution)
   - Alert status in DB: `resolved`

3. **Frontend refreshes patient list**
   - Backend SQL query: `WHERE status IN ('active', 'acknowledged')`
   - Alert `d9cedad7` has `status='resolved'` - **NOT RETURNED** ❌

4. **Backend creates NEW alert for same condition**
   - Patient still has high HR/RR (vitals simulator)
   - New alert created with `status='active'`
   - New alert ID (different from `d9cedad7`)

5. **Frontend displays NEW alert**
   - You see an alert that looks the same
   - But it's actually a DIFFERENT alert with a different ID
   - You click "Acknowledge" again
   - Cycle repeats...

## Evidence

### Alert You Clicked Multiple Times
```
Alert ID: d9cedad7-f2dd-4b1d-9abe-709dc9c9e94e
Type: tachypnea
Status: resolved (auto-resolved after acknowledgement)
AcknowledgedBy: NUR0001
AcknowledgedAt: 2025-11-08 00:01:12
```

### Current Active Alerts (What You're Seeing Now)
```
5 active alerts:
- watchTampering (created 12:45:01)
- electrodeGelDried (created 12:44:57)
- earlyWarningScoreMedium (created 12:44:32)
- patientWettingElectrodes (created 12:39:36)
- earlyWarningScoreHigh (created 12:24:28)

2 acknowledged alerts:
- watchTampering (created 11:34:32, acknowledged)
- earlyWarningScoreHigh (created 11:23:57, acknowledged)
```

## The Root Problem

### Problem 1: Alert Auto-Resolution Race Condition
When you acknowledge an alert:
1. Status changes to `'acknowledged'` ✅
2. Backend continues monitoring vitals
3. If vitals improve, status changes to `'resolved'`
4. SQL query excludes resolved alerts
5. Alert disappears from API response
6. BUT patient vitals deteriorate again
7. NEW alert created with same type
8. Appears as if acknowledgement didn't work!

### Problem 2: Alert Lifecycle Confusion
**Three States:**
- `active`: Unacknowledged, needs attention
- `acknowledged`: Staff aware, but condition persists
- `resolved`: Condition cleared (auto-resolved by backend)

**Problem:** Our SQL filters out `resolved` alerts entirely!
```sql
WHERE status IN ('active', 'acknowledged')  -- Excludes resolved!
```

**This means:**
- Acknowledged alerts that get auto-resolved DISAPPEAR
- Backend creates new alerts for ongoing conditions
- User sees "new" alert that looks identical
- Creates illusion that acknowledgement didn't work

## Solutions (Choose One)

### Option 1: Don't Auto-Resolve Acknowledged Alerts
**Change:** Once acknowledged, keep status as `acknowledged` until manually resolved by staff

**Pros:**
- ✅ Acknowledged alerts stay acknowledged
- ✅ Staff retains control
- ✅ No surprise disappearances

**Cons:**
- ❌ Alert list gets cluttered with old acknowledged alerts
- ❌ Staff must manually clear resolved alerts

### Option 2: Show Acknowledged Alerts Differently
**Change:** Frontend shows acknowledged alerts in a separate section (collapsed by default)

**Pros:**
- ✅ Acknowledged alerts don't clutter main view
- ✅ Staff can still see what was acknowledged
- ✅ Auto-resolution works normally

**Cons:**
- ❌ Requires frontend changes
- ❌ More UI complexity

### Option 3: Prevent Duplicate Alerts (RECOMMENDED)
**Change:** Before creating new alert, check if similar alert exists (acknowledged OR resolved) within last N minutes

**Logic:**
```python
# Before creating new alert:
existing = db.query("""
    SELECT id FROM patient_alerts
    WHERE patientId = $1
      AND type = $2
      AND (status = 'acknowledged' OR
           (status = 'resolved' AND resolvedAt > NOW() - INTERVAL '10 minutes'))
""")

if existing:
    # Update existing alert instead of creating new one
    db.update("UPDATE patient_alerts SET status='active', updatedAt=NOW() WHERE id=...")
else:
    # Create new alert
    db.insert("INSERT INTO patient_alerts...")
```

**Pros:**
- ✅ No duplicate alerts for same condition
- ✅ Acknowledged alerts stay acknowledged until condition truly clears
- ✅ Backend owns alert lifecycle
- ✅ No frontend changes needed

**Cons:**
- ❌ Requires backend alert creation logic changes
- ❌ Need to define "duplicate" window (5 min? 10 min? 30 min?)

### Option 4: Change `isAcknowledged` Logic
**Change:** `isAcknowledged = True` if status is `acknowledged` OR user has acknowledged ANY alert of this type recently

**This won't fix the duplicate alert problem, so NOT RECOMMENDED**

## Recommendation

**Option 3** is the best solution because:
1. Fixes the root cause (duplicate alert creation)
2. No frontend changes required
3. More intelligent alert management
4. Better user experience

## Implementation Plan for Option 3

### Step 1: Modify Alert Creation Logic
**File:** `hospital-backend/app/services/alert_manager_service.py` or `alert_detection_service.py`

**Before Creating Alert:**
```python
# Check for recent similar alerts
recent_alert = await conn.fetchrow("""
    SELECT id, status
    FROM patient_alerts
    WHERE "patientId" = $1
      AND type = $2
      AND ("createdAt" > NOW() - INTERVAL '15 minutes'
           OR (status = 'acknowledged' AND "acknowledgedAt" > NOW() - INTERVAL '1 hour'))
    ORDER BY "createdAt" DESC
    LIMIT 1
""", patient_id, alert_type)

if recent_alert:
    if recent_alert['status'] in ['acknowledged', 'resolved']:
        # Don't create duplicate - condition already known
        logger.info(f"Skipping duplicate alert {alert_type} for {patient_id} - recently acknowledged")
        return
    else:
        # Update existing active alert
        await conn.execute("""
            UPDATE patient_alerts
            SET "updatedAt" = NOW(), message = $1
            WHERE id = $2
        """, new_message, recent_alert['id'])
        return

# Create new alert (only if no recent similar alert exists)
```

### Step 2: Test
1. Restart backend
2. Acknowledge an alert
3. Wait for vitals to trigger same condition again
4. Verify NO new alert is created
5. Verify acknowledged alert stays acknowledged

## Current Status

❌ **Issue NOT Fixed** - Need to implement Option 3 (prevent duplicate alerts)

The `isAcknowledged` field was added correctly, but the real problem is duplicate alert creation creating an infinite loop of "new" alerts that look identical.
