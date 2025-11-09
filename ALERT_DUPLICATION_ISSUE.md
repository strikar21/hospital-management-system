# Alert Acknowledgement Issue - Root Cause Found

## Problem Description
When acknowledging alerts, the count doesn't decrease and acknowledged alerts don't disappear from the patient card.

## Root Cause: Backend Alert Duplication

The alert acknowledgement system IS working correctly:
- ✅ Frontend sends acknowledgement request
- ✅ Backend processes acknowledgement (200 OK)
- ✅ Database updates alert status to 'acknowledged'
- ✅ Frontend refetches patient data

**BUT**: The backend alert detection service is creating **duplicate alerts** every second for ongoing conditions.

## Evidence

### Database Query Results
```
Recent ACTIVE alerts (unacknowledged):
- 10+ tachypnea alerts, all status='active', all acknowledgedBy=None
- All created within the last few minutes
- All for the same patient and same condition

Acknowledged alerts:
- 6 watchTampering and earlyWarningScoreHigh alerts
- All status='acknowledged', acknowledgedBy='NUR0001'
- Acknowledgements working correctly
```

### Backend Behavior
Every ~1 second, the backend:
1. Receives vitals from ESP32 watch
2. Runs alert detection
3. **Creates a NEW alert** for tachypnea (RR > 24/min)
4. Doesn't check if an unacknowledged alert already exists
5. Result: 10+ duplicate "tachypnea" alerts pile up

## Impact on User Experience

**What the user sees:**
1. Click acknowledge button on alert
2. Backend successfully acknowledges it (status='acknowledged')
3. Frontend refetches data
4. **Alert count stays the same** because 9 other duplicate alerts exist
5. Looks like acknowledgement didn't work, but it did!

## The Real Bug

**File:** `hospital-backend/app/services/alert_detection_service.py`

The alert detection service needs **deduplication logic**:

```python
# CURRENT (BAD):
def detect_alerts(patient_id, vitals):
    if vitals.respiratoryRate > 24:
        create_alert('tachypnea', ...)  # ❌ Always creates new alert

# SHOULD BE:
def detect_alerts(patient_id, vitals):
    if vitals.respiratoryRate > 24:
        # Check if unacknowledged alert already exists
        existing = get_active_alert(patient_id, 'tachypnea')
        if not existing:
            create_alert('tachypnea', ...)  # ✅ Only create if none exists
        else:
            update_alert_timestamp(existing.id)  # ✅ Update existing
```

## Solution

### Option 1: Prevent Duplicate Alert Creation (Recommended)
Add deduplication logic to alert detection service:
- Before creating an alert, check if an active (unacknowledged) alert of the same type exists
- If yes, update its timestamp instead of creating new
- If no, create new alert

### Option 2: Auto-Acknowledge Previous Alerts
When creating a new alert of the same type:
- Auto-acknowledge all previous unacknowledged alerts of that type
- This way only the latest alert shows

### Option 3: Group Alerts by Type in Frontend
Frontend groups alerts by type and shows count:
- "Tachypnea (x10)" instead of 10 separate alerts
- Less ideal, doesn't fix root cause

## Recommended Fix

**Backend changes needed in `alert_detection_service.py`:**

```python
async def create_alert_if_not_exists(
    patient_id: str,
    alert_type: str,
    severity: str,
    message: str,
    metadata: dict = None
) -> dict:
    """
    Create alert only if no unacknowledged alert of same type exists
    This prevents alert spam for ongoing conditions
    """
    async with get_db_connection() as conn:
        # Check for existing active alert of same type
        existing = await conn.fetchrow('''
            SELECT id, "createdAt"
            FROM patient_alerts
            WHERE "patientId" = $1
              AND type = $2
              AND status = 'active'
            ORDER BY "createdAt" DESC
            LIMIT 1
        ''', patient_id, alert_type)

        if existing:
            # Update timestamp of existing alert
            await conn.execute('''
                UPDATE patient_alerts
                SET "updatedAt" = NOW()
                WHERE id = $1
            ''', existing['id'])
            return {'id': existing['id'], 'existed': True}
        else:
            # Create new alert
            alert_id = str(uuid.uuid4())
            await conn.execute('''
                INSERT INTO patient_alerts
                (id, "patientId", type, severity, message, status, metadata, "createdAt", "updatedAt")
                VALUES ($1, $2, $3, $4, $5, 'active', $6, NOW(), NOW())
            ''', alert_id, patient_id, alert_type, severity, message, metadata)
            return {'id': alert_id, 'existed': False}
```

## Testing After Fix

1. Acknowledge an alert
2. Wait 2-3 seconds for frontend to refetch
3. **Expected:** Alert count decreases by 1
4. **Expected:** Acknowledged alert disappears
5. **Expected:** Other critical alerts move up to be visible

## Files to Modify

1. **Backend:**
   - `hospital-backend/app/services/alert_detection_service.py` - Add deduplication logic
   - Test with patient 081a5294-da91-4c74-bb8a-e5062f5851dd

2. **Frontend:** No changes needed - already working correctly

## Current Status

- ✅ Alert acknowledgement API working
- ✅ Database updates working
- ✅ Frontend refetch working
- ❌ **Backend creating duplicate alerts** (needs fix)

The user experience will be fixed once backend alert deduplication is implemented.
