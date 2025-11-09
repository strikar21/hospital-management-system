# Remaining Backend Errors - Research Required

## Status Summary

✅ **FIXED**: Alert acknowledge button - now working correctly (returns 200 OK)
⏳ **PENDING**: Case entries datetime comparison error

## Error Details

### Case Entries Endpoint (500 Error)
**Endpoint:** `GET /api/v2/patients/{patient_id}/case-entries?includeStaff=true`

**Error Message:**
```json
{
  "success": false,
  "errorCode": "HTTP_500",
  "message": "can't compare offset-naive and offset-aware datetimes",
  "timestamp": "2025-11-07T11:30:37.469953Z",
  "path": "/api/v2/patients/{patient_id}/case-entries",
  "statusCode": 500
}
```

**Error Type:** Python datetime comparison error

**Root Cause:**
The error "can't compare offset-naive and offset-aware datetimes" occurs when the code tries to compare or sort datetime objects where some have timezone information (offset-aware) and others don't (offset-naive).

**Affected Code Path:**
1. API Endpoint: [patients.py:354-364](hospital-backend/app/api/v2/patients.py#L354-L364)
2. Service Method: `patient_service.get_aggregated_timeline(patient_id)`
3. Repository Method: `patient_repository.get_aggregated_timeline(patient_id)`

**Likely Location of Bug:**
The `get_aggregated_timeline` method probably:
- Fetches data from multiple tables (medications, investigations, therapies, case entries, alerts)
- Sorts these entries by timestamp
- **BUG**: Some tables store timestamps with timezone info, others without
- **ERROR**: When Python tries to sort mixed timezone/non-timezone timestamps

**Files to Investigate:**
- [hospital-backend/app/repositories/patient_repository.py](hospital-backend/app/repositories/patient_repository.py) - `get_aggregated_timeline` method
- [hospital-backend/app/services/patient_service.py](hospital-backend/app/services/patient_service.py) - `get_aggregated_timeline` method

**Common Causes:**
1. Database columns have mixed timezone settings:
   - Some: `TIMESTAMP WITH TIME ZONE` (returns offset-aware)
   - Others: `TIMESTAMP` (returns offset-naive)

2. Python code creates timestamps inconsistently:
   - Some: `datetime.now()` (offset-naive)
   - Others: `datetime.now(timezone.utc)` (offset-aware)

3. Sorting/filtering logic compares mixed datetime types

**Potential Fix:**
Normalize all timestamps to either:
- **Option 1:** Make all offset-aware: `datetime.now(timezone.utc)`
- **Option 2:** Make all offset-naive: `.replace(tzinfo=None)`
- **Option 3:** Use database-level timezone conversion in queries

## Testing Priority

1. ✅ **DONE**: Test alert acknowledge button
   - Expected: Alerts disappear when acknowledged
   - Actual: ✅ Working (returns 200 OK)

2. ⏳ **TODO**: Fix case entries endpoint
   - **Impact:** Medium - breaks patient detail page case history view
   - **User Impact:** Cannot view medical timeline/case sheet
   - **Priority:** Medium (affects single feature, not critical functionality)

## Next Steps

1. Read the `get_aggregated_timeline` method in both repository and service
2. Identify where datetimes are being compared or sorted
3. Add timezone normalization before comparison
4. Test with patient that has mixed case entry types (medications, investigations, alerts, etc.)

## Workaround

Patient detail page will show partial data - patient info and vitals work, but case entries/timeline fails to load.
