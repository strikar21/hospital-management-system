# Device Visibility Fix - Root Cause Analysis

## Problem
Frontend showed 0 devices even though 3 devices existed in database:
- `TEST_WATCH_001`
- `ESP32_WATCH_002`
- `ESP32_WATCH_003`

Backend logs showed:
```
✅ Retrieved 0 devices (total: 0, filters: 3)
```

## Root Cause
The frontend was sending filter parameters with value `"all"`:
```
GET /api/v2/devices/?status=available&deviceType=all&location=all
```

The backend device API ([app/api/v2/devices.py](hospital-backend/app/api/v2/devices.py#L58-L73)) was treating `"all"` as a literal filter value:
```python
if deviceType:  # "all" is truthy
    where_clauses.append(f'"deviceType" = ${param_counter}')
    params.append(deviceType)  # Added WHERE deviceType = 'all'
```

This created a SQL query looking for devices with `deviceType = 'all'`, which don't exist in the database. All devices have specific types like `'watch'`, `'tablet'`, etc.

## Fix Applied
Modified [app/api/v2/devices.py:58-73](hospital-backend/app/api/v2/devices.py#L58-L73) to ignore `"all"` as a filter value:

```python
# Device type filter
if deviceType and deviceType.lower() != 'all':
    where_clauses.append(f'"deviceType" = ${param_counter}')
    params.append(deviceType)
    param_counter += 1

# Status filter
if status and status.lower() != 'all':
    where_clauses.append(f'status = ${param_counter}')
    params.append(status)
    param_counter += 1

# Location filter
if location and location.lower() != 'all':
    where_clauses.append(f'location ILIKE ${param_counter}')
    params.append(f'%{location}%')
    param_counter += 1
```

Now when frontend sends `deviceType=all`, the backend treats it as "no filter" and returns all device types.

## Verification
- ✅ Database has 3 devices
- ✅ `devices_enriched` view returns 3 devices
- ✅ API filter logic fixed to handle "all" value
- 🔄 Backend auto-reloaded with fix (FastAPI hot reload)
- ⏳ Waiting to verify frontend now shows devices

## Files Modified
- [hospital-backend/app/api/v2/devices.py](hospital-backend/app/api/v2/devices.py):
  - Lines 58-73: Fixed filter logic to ignore "all" as filter value
  - Lines 155-166: Fixed database query calls to use `conn.fetch()` directly

## Additional Fix - Database Query Mismatch
After fixing the "all" filter issue, discovered another bug:
- **Problem:** Query used `$1, $2` placeholders but called `fetchAll()` which expects `?` placeholders
- **Error:** `TypeError: fetchAll() takes from 2 to 3 positional arguments but 4 were given`
- **Fix:** Changed to call `conn.fetch()` and `conn.fetchrow()` directly since query already has PostgreSQL-style placeholders

## Testing
After this fix, frontend should:
1. See all 3 devices in device lists
2. Be able to assign devices to patients
3. Complete the ESP32 HMAC authentication workflow testing
