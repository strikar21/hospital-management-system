# Alert Deduplication - Medically Safe Implementation

## User's Critical Question
**"If you acknowledge tachypnea and it happens again, then it gets ignored?"**

**Answer: NO! That would be dangerous. We need smarter logic.**

## Medical Alert Lifecycle

### Scenario 1: Ongoing Condition (Current Problem)
```
Time 0s:  RR = 26 → Create tachypnea alert
Time 1s:  RR = 27 → ❌ CURRENT: Creates duplicate alert
                    ✅ SHOULD: Update existing alert timestamp
Time 2s:  RR = 28 → ❌ CURRENT: Creates duplicate alert
                    ✅ SHOULD: Update existing alert timestamp
Nurse acknowledges alert at Time 3s
Time 4s:  RR = 27 → ❌ CURRENT: Creates duplicate alert
                    ✅ SHOULD: Keep acknowledged alert, don't create new (still ongoing)
```

### Scenario 2: Condition Resolves and Returns (Your Question!)
```
Time 0s:   RR = 26 → Create tachypnea alert
Time 10s:  RR = 28 → Update existing alert
Nurse acknowledges at Time 15s
Time 20s:  RR = 18 → ✅ AUTO-RESOLVE alert (condition cleared)
Time 30s:  RR = 19 → No alert (normal)
Time 40s:  RR = 26 → ✅ CREATE NEW ALERT (new episode!)
```

### Scenario 3: Severity Escalation
```
Time 0s:  RR = 25 → Create MEDIUM tachypnea alert
Time 10s: RR = 26 → Update existing alert
Time 20s: RR = 35 → ✅ CREATE NEW HIGH/CRITICAL alert (severity increased!)
```

## Proper Implementation

### Alert States
```sql
CREATE TYPE alert_status AS ENUM (
  'active',        -- Unacknowledged, condition still present
  'acknowledged',  -- Staff aware, condition still present
  'resolved',      -- Condition no longer present (auto or manual)
  'escalated'      -- Replaced by higher severity alert
);
```

### Deduplication Logic (Medical-Safe)

```python
async def detect_and_manage_alert(
    patient_id: str,
    alert_type: str,
    severity: str,
    current_vitals: dict,
    threshold_check: bool  # Is condition currently present?
) -> Optional[str]:
    """
    Medical-safe alert management:
    1. Don't spam duplicates for ongoing conditions
    2. Auto-resolve when condition clears
    3. Create new alert when condition returns after resolution
    4. Escalate when severity increases
    """

    # Get most recent alert of this type (any status)
    existing = await get_latest_alert(patient_id, alert_type)

    if threshold_check:  # Condition IS present
        if not existing:
            # No previous alert → Create new
            return await create_alert(patient_id, alert_type, severity, current_vitals)

        elif existing.status == 'resolved':
            # Condition returned after resolution → Create NEW alert (new episode)
            return await create_alert(patient_id, alert_type, severity, current_vitals)

        elif existing.status in ['active', 'acknowledged']:
            # Condition ongoing
            if severity_increased(existing.severity, severity):
                # Severity escalated → Mark old as escalated, create new critical
                await mark_escalated(existing.id)
                return await create_alert(patient_id, alert_type, severity, current_vitals)
            else:
                # Same ongoing condition → Just update timestamp
                await update_alert_timestamp(existing.id, current_vitals)
                return existing.id

    else:  # Condition is NOT present
        if existing and existing.status in ['active', 'acknowledged']:
            # Condition cleared → Auto-resolve
            await auto_resolve_alert(existing.id)

        return None


async def get_latest_alert(patient_id: str, alert_type: str):
    """Get most recent alert of this type, regardless of status"""
    return await db.fetchrow('''
        SELECT id, status, severity, "createdAt", "resolvedAt"
        FROM patient_alerts
        WHERE "patientId" = $1 AND type = $2
        ORDER BY "createdAt" DESC
        LIMIT 1
    ''', patient_id, alert_type)


async def auto_resolve_alert(alert_id: str):
    """Automatically resolve alert when condition clears"""
    await db.execute('''
        UPDATE patient_alerts
        SET status = 'resolved',
            "resolvedAt" = NOW(),
            "resolvedBy" = 'SYSTEM',
            "updatedAt" = NOW()
        WHERE id = $1
    ''', alert_id)
```

## Example Timeline

### Patient with Tachypnea
```
09:00:00 - RR 26 → Alert A created (MEDIUM, active)
09:00:01 - RR 27 → Alert A updated
09:00:02 - RR 28 → Alert A updated
09:00:05 - Nurse acknowledges Alert A (status: acknowledged)
09:00:10 - RR 27 → Alert A updated (still acknowledged, not creating new)
09:00:30 - RR 19 → Alert A auto-resolved (status: resolved)
09:01:00 - RR 18 → No alert (normal)
09:05:00 - RR 26 → Alert B created (NEW episode! Different from Alert A)
09:05:10 - RR 35 → Alert B marked escalated, Alert C created (CRITICAL)
```

## Benefits

✅ **No duplicate spam** - One active alert per condition type per patient
✅ **Medical safety** - New episodes create new alerts
✅ **Severity escalation** - Critical changes create new alerts
✅ **Auto-resolution** - Clears alerts when condition resolves
✅ **Proper acknowledgement** - Staff can acknowledge ongoing conditions
✅ **Audit trail** - Full history of alert lifecycle

## Database Schema Changes Needed

Add to `patient_alerts` table:
```sql
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "resolvedAt" TIMESTAMP;
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "resolvedBy" VARCHAR(50);
ALTER TABLE patient_alerts ADD COLUMN IF NOT EXISTS "escalatedToAlertId" UUID;
```

Update status enum:
```sql
-- Current: 'active', 'acknowledged'
-- Add: 'resolved', 'escalated'
```

## Frontend Impact

**No changes needed!** Frontend already:
- Filters by `!alert.isAcknowledged` (won't show resolved alerts)
- Refetches data after acknowledgement
- Displays alerts by severity

The count will now correctly decrease when:
1. Staff acknowledges alert (status: active → acknowledged)
2. Condition resolves (status: acknowledged → resolved, no longer in unacknowledged list)

## Implementation Priority

**High** - This affects medical safety and user experience:
1. Prevents alert fatigue from spam
2. Ensures new episodes are caught
3. Allows proper severity escalation
4. Provides clear audit trail

## Answer to Your Question

> "If you acknowledge tachypnea and it happens again, then it gets ignored?"

**NO!** Here's what happens:

1. **During same episode** (RR stays high):
   - First detection → Create alert
   - You acknowledge it
   - RR still high → **Don't create new alert** (same episode, already acknowledged)

2. **After resolution** (RR returns to normal then goes high again):
   - RR normal → Auto-resolve alert
   - Later RR high again → **CREATE NEW ALERT** (new episode, needs attention!)

3. **Severity increases**:
   - RR 25 (medium) → Alert exists
   - RR 35 (critical) → **CREATE NEW CRITICAL ALERT** (escalation!)

The key is tracking the **alert lifecycle**, not just existence.
