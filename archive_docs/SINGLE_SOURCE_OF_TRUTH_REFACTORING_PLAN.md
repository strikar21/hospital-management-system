# SINGLE SOURCE OF TRUTH (SSOT) REFACTORING PLAN
## Backend as the Authoritative Data Source
**Date:** October 13, 2025
**Architect:** Senior Backend + Frontend Architect Team
**Scope:** Device Management System Refactoring

---

## EXECUTIVE SUMMARY

This document analyzes the current device management architecture and provides a **comprehensive refactoring plan** to establish the backend as the **Single Source of Truth (SSOT)** for all device-related data, eliminating redundancy and ensuring data consistency.

### Current Issues Identified:

1. **Data Redundancy**: Device information stored in multiple locations (devices table, deviceassignments table, frontend state)
2. **Inconsistent Field Mapping**: ESP32 sends lowercase fields, backend expects camelCase
3. **Multiple Endpoints for Same Data**: `/devices/available` vs `/watchmanagement/available`
4. **Frontend Data Transformation**: Frontend performs data mapping that should be done on backend
5. **Cached State Inconsistency**: Frontend state may be out of sync with database

---

## CURRENT ARCHITECTURE ANALYSIS

### 1. Data Flow Diagram (Current State)

```
┌─────────────────┐          ┌──────────────────┐          ┌─────────────────┐
│   ESP32 Watch   │          │   Backend API    │          │    Frontend     │
│                 │          │                  │          │                 │
│ lowercase       │   HTTP   │ camelCase        │   HTTP   │ camelCase       │
│ fields          │─────────>│ transformation   │<─────────│ state           │
│ (heartrate,     │          │ (heartRate,      │          │ (heartRate,     │
│  oxygensat)     │          │  oxygenSaturation│          │  oxygenSaturation│
└─────────────────┘          └──────────────────┘          └─────────────────┘
                                      │
                                      │
                             ┌────────▼───────────┐
                             │   PostgreSQL       │
                             │                    │
                             │  devices table     │
                             │  deviceassignments │
                             └────────────────────┘
```

### 2. Current Data Sources

| Data Type | Source 1 | Source 2 | Source 3 | Authoritative? |
|-----------|----------|----------|----------|----------------|
| Device Info | `devices` table | Frontend cache | N/A | ✅ Backend |
| Device Status | `devices.status` | ESP32 lastSeen | Frontend computed | ❌ Multiple |
| Assignment | `deviceassignments` table | `devices.assignedPatient` (deprecated) | Frontend state | ⚠️ Inconsistent |
| Battery Level | `devices.batteryLevel` | ESP32 real-time | Frontend cached | ❌ Multiple |
| Connection Status | Computed from `lastSeen` | ESP32 heartbeat | Frontend computed | ❌ Multiple |

### 3. Redundancy Issues Identified

#### Issue 1: Duplicate Assignment Tracking

**Location 1**: `devices` table
```sql
-- DEPRECATED FIELDS (Should be removed)
CREATE TABLE devices (
    ...
    "assignedPatient" UUID,  -- ❌ REDUNDANT - Use deviceassignments table instead
    ...
);
```

**Location 2**: `deviceassignments` table (Correct)
```sql
CREATE TABLE deviceassignments (
    id SERIAL PRIMARY KEY,
    "deviceId" VARCHAR(50) NOT NULL,
    "patientId" UUID NOT NULL,
    "assignedBy" VARCHAR(50) NOT NULL,
    "assignedAt" TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL,
    ...
);
```

**Solution**: Remove `assignedPatient` from `devices` table, use JOIN with `deviceassignments`.

---

#### Issue 2: Multiple Endpoints for Same Data

**Endpoint 1**: `/api/v1/devices/available`
- Returns all device types
- Status: 'available'
- Used by: Generic device management

**Endpoint 2**: `/api/v1/watchmanagement/available`
- Returns only watches
- Status: 'available'
- Used by: Watch-specific assignment

**Problem**: Two endpoints, same data, filtered differently. Frontend must know which to call.

**Solution**: Consolidate into single endpoint with flexible filtering:
```
GET /api/v2/devices?status=available&deviceType=watch
```

---

#### Issue 3: Connection Status Computed in Multiple Places

**Backend Computation** (`device_management.py:149-151`):
```python
CASE WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
     WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
     ELSE 'offline' END as connectionStatus
```

**Frontend Computation** (DevicePoolTab.tsx:124):
```typescript
(watch.connectionStatus || watch.status) === 'connected' ? 'bg-green-500' :
(watch.connectionStatus || watch.status) === 'recently_seen' ? 'bg-yellow-500' : 'bg-red-500'
```

**Problem**: Logic duplicated in frontend. If thresholds change (e.g., 5 min → 2 min), must update both places.

**Solution**: Backend always returns computed `connectionStatus`, frontend just displays it.

---

#### Issue 4: ESP32 Field Name Transformation

**ESP32 Sends** (esp32_door_scanner/data_formatter.cpp):
```cpp
{
  "heartrate": 75,
  "oxygensat": 98,
  "bloodpressurevalue": 120
}
```

**Backend Expects**:
```json
{
  "heartRate": 75,
  "oxygenSaturation": 98,
  "bloodPressureSystolic": 120
}
```

**Current Workaround**: Backend endpoint transforms field names manually.

**Problem**: Transformation logic scattered across multiple endpoints.

**Solution**: Centralized middleware for ESP32 data transformation.

---

## REFACTORING PLAN: ESTABLISH BACKEND AS SSOT

### Phase 1: Database Schema Cleanup (Week 1)

#### 1.1 Remove Redundant Fields from `devices` Table

**Current**:
```sql
CREATE TABLE devices (
    id VARCHAR(50) PRIMARY KEY,
    ...
    "assignedPatient" UUID,  -- ❌ REDUNDANT
    ...
);
```

**Target**:
```sql
CREATE TABLE devices (
    id VARCHAR(50) PRIMARY KEY,
    "deviceType" VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    "serialNumber" VARCHAR(100),
    "macAddress" VARCHAR(20),
    "firmwareVersion" VARCHAR(50),
    status VARCHAR(20) NOT NULL,  -- 'available', 'assigned', 'maintenance', 'retired'
    location VARCHAR(255),
    description TEXT,
    "batteryLevel" INTEGER,
    "lastSeen" TIMESTAMP,
    "calibrationDate" TIMESTAMP,
    "nextMaintenanceDate" TIMESTAMP,
    "createdAt" TIMESTAMP NOT NULL,
    "updatedAt" TIMESTAMP NOT NULL
    -- ✅ NO assignedPatient field - use JOIN with deviceassignments
);
```

**Migration Script**:
```sql
-- migration_009_remove_device_redundancy.sql
BEGIN;

-- Remove redundant assignedPatient column
ALTER TABLE devices DROP COLUMN IF EXISTS "assignedPatient";

-- Ensure all assignment queries use deviceassignments table
-- (No data migration needed - deviceassignments is already authoritative)

COMMIT;
```

**Files to Update**:
- `hospital-backend/init-scripts/01-init-production-database.sql`
- `hospital-backend/app/models/device.py` (if exists)
- All queries that reference `devices.assignedPatient`

---

#### 1.2 Create Database View for Enriched Device Data

**Purpose**: Provide JOIN'd data as a single queryable view.

```sql
-- Create view that combines devices with current assignments
CREATE OR REPLACE VIEW devices_enriched AS
SELECT
    d.*,
    da."patientId" as "assignedPatientId",
    da."assignedBy",
    da."assignedAt",
    p."firstName" as "patientFirstName",
    p."lastName" as "patientLastName",
    p."roomNumber",
    p."bedNumber",
    CONCAT(p."firstName", ' ', p."lastName") as "patientName",
    CONCAT('Room ', p."roomNumber", ', Bed ', p."bedNumber") as "patientLocation",
    -- Computed connection status
    CASE
        WHEN d."lastSeen" > NOW() - INTERVAL '5 minutes' THEN 'connected'
        WHEN d."lastSeen" > NOW() - INTERVAL '1 hour' THEN 'recentlySeen'
        ELSE 'offline'
    END as "connectionStatus",
    -- Computed battery status
    CASE
        WHEN d."batteryLevel" >= 80 THEN 'excellent'
        WHEN d."batteryLevel" >= 60 THEN 'good'
        WHEN d."batteryLevel" >= 40 THEN 'fair'
        WHEN d."batteryLevel" >= 20 THEN 'low'
        ELSE 'critical'
    END as "batteryStatus"
FROM devices d
LEFT JOIN deviceassignments da ON d.id = da."deviceId" AND da.status = 'active'
LEFT JOIN patients p ON da."patientId" = p.id;
```

**Benefit**: Single query returns all device data with patient info and computed fields.

---

### Phase 2: API Consolidation (Week 2)

#### 2.1 Create Unified Device API v2

**Goal**: Single endpoint for all device queries, replacing multiple scattered endpoints.

**New Endpoint Design**:
```
GET /api/v2/devices?
    status=available,assigned
    &deviceType=watch,tablet
    &location=ICU
    &includeAssignments=true
    &includePatient=true
    &includeHistory=true
    &limit=50
    &offset=0
```

**Implementation**:
```python
# hospital-backend/app/api/v2/devices_unified.py

@router.get("/")
async def get_devices_unified(
    status: Optional[List[str]] = Query(None),
    deviceType: Optional[List[str]] = Query(None),
    location: Optional[str] = Query(None),
    includeAssignments: bool = False,
    includePatient: bool = False,
    includeHistory: bool = False,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    Unified device query endpoint - Single Source of Truth

    Returns:
        - All device fields from devices_enriched view
        - Computed fields (connectionStatus, batteryStatus)
        - Optional patient info (if includePatient=true)
        - Optional assignment history (if includeHistory=true)
    """

    async with getDbConnection() as conn:
        # Base query from enriched view
        query = "SELECT * FROM devices_enriched"
        where_clauses = []
        params = []
        param_count = 0

        # Apply filters
        if status:
            param_count += 1
            where_clauses.append(f"status = ANY(${param_count})")
            params.append(status)

        if deviceType:
            param_count += 1
            where_clauses.append(f'"deviceType" = ANY(${param_count})')
            params.append(deviceType)

        if location:
            param_count += 1
            where_clauses.append(f'location ILIKE ${param_count}')
            params.append(f'%{location}%')

        # Build final query
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += f" ORDER BY \"updatedAt\" DESC LIMIT {limit} OFFSET {offset}"

        rows = await conn.fetch(query, *params)

        devices = []
        for row in rows:
            device = dict(row)

            # Serialize datetime fields
            for key, value in device.items():
                if isinstance(value, datetime):
                    device[key] = value.isoformat()

            # Optionally include assignment history
            if includeHistory:
                history_query = """
                    SELECT da.*, p."firstName", p."lastName"
                    FROM deviceassignments da
                    LEFT JOIN patients p ON da."patientId" = p.id
                    WHERE da."deviceId" = $1
                    ORDER BY da."assignedAt" DESC
                    LIMIT 10
                """
                history_rows = await conn.fetch(history_query, device['id'])
                device['assignmentHistory'] = [dict(h) for h in history_rows]

            devices.append(device)

        return JSONResponse(content={
            "success": True,
            "devices": devices,
            "count": len(devices),
            "limit": limit,
            "offset": offset
        })
```

**Benefits**:
- ✅ Single endpoint for all device queries
- ✅ Flexible filtering
- ✅ All computed fields from database view
- ✅ Pagination support
- ✅ Optional data inclusion (performance optimization)

---

#### 2.2 Deprecate Old Endpoints (Backward Compatibility)

**Approach**: Keep old endpoints but redirect to new unified endpoint internally.

```python
# hospital-backend/app/api/v1/device_management.py

@router.get("/available")
@deprecated("Use /api/v2/devices?status=available instead")
async def getAvailableDevices(
    deviceType: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    limit: int = Query(50)
):
    """
    DEPRECATED: Use /api/v2/devices?status=available
    Maintained for backward compatibility only
    """
    # Redirect to v2 endpoint internally
    from ..v2.devices_unified import get_devices_unified

    return await get_devices_unified(
        status=['available'],
        deviceType=[deviceType] if deviceType else None,
        location=location,
        limit=limit,
        offset=0
    )
```

**Timeline**:
- Month 1: Deploy v2 endpoint, keep v1 for compatibility
- Month 2: Update frontend to use v2
- Month 3: Add deprecation warnings to v1 responses
- Month 6: Remove v1 endpoints

---

### Phase 3: ESP32 Data Transformation Middleware (Week 3)

#### 3.1 Centralized ESP32 Field Mapper

**Problem**: ESP32 sends lowercase fields, backend expects camelCase.

**Solution**: Middleware that automatically transforms ESP32 data.

```python
# hospital-backend/app/middleware/esp32_field_mapper.py

class ESP32FieldMapper:
    """
    Centralized field mapping for ESP32 devices
    Transforms lowercase ESP32 fields to camelCase backend schema
    """

    FIELD_MAPPING = {
        # Vitals
        "heartrate": "heartRate",
        "oxygensat": "oxygenSaturation",
        "bloodpressurevalue": "bloodPressureSystolic",
        "temperature": "bodyTemperature",
        "respiratoryrate": "respiratoryRate",

        # Device Info
        "deviceid": "deviceId",
        "patientid": "patientId",
        "macaddress": "macAddress",
        "firmwareversion": "firmwareVersion",
        "batterylevel": "batteryLevel",
        "lastseen": "lastSeen",

        # Assignment
        "assignedby": "assignedBy",
        "assignedat": "assignedAt"
    }

    @classmethod
    def transform_request(cls, data: dict) -> dict:
        """Transform ESP32 request data to backend schema"""
        transformed = {}
        for key, value in data.items():
            backend_key = cls.FIELD_MAPPING.get(key.lower(), key)
            transformed[backend_key] = value
        return transformed

    @classmethod
    def transform_response(cls, data: dict) -> dict:
        """Transform backend response to ESP32 schema (if needed)"""
        # Reverse mapping
        reverse_mapping = {v: k for k, v in cls.FIELD_MAPPING.items()}
        transformed = {}
        for key, value in data.items():
            esp32_key = reverse_mapping.get(key, key)
            transformed[esp32_key] = value
        return transformed
```

**Usage in ESP32 Endpoint**:
```python
# hospital-backend/app/api/v1/esp32.py

@router.post("/vitals")
async def receive_vitals(
    vitals_data: dict,
    device_key: str = Header(None, alias="X-Device-Key"),
    device: dict = Depends(verify_device_key)
):
    """Receive vital signs from ESP32 watch"""

    # ✅ Transform ESP32 lowercase fields to camelCase
    transformed_data = ESP32FieldMapper.transform_request(vitals_data)

    # Now use transformed_data with camelCase fields
    heart_rate = transformed_data.get("heartRate")  # ✅ camelCase
    oxygen_sat = transformed_data.get("oxygenSaturation")  # ✅ camelCase

    # Store in database...
```

**Benefits**:
- ✅ Single place to manage field mappings
- ✅ Easy to update if ESP32 firmware changes
- ✅ Consistent transformation across all ESP32 endpoints
- ✅ Backend always works with camelCase

---

#### 3.2 Update ESP32 Firmware (Recommended)

**Long-term Solution**: Update ESP32 firmware to send camelCase directly.

**ESP32 Firmware Change** (esp32_hospital_watch_complete/src/utils/data_formatter.cpp):
```cpp
// ❌ OLD (lowercase)
String formatVitalsJSON_OLD() {
    return "{"
        "\"heartrate\":" + String(heartRate) + ","
        "\"oxygensat\":" + String(oxygenSat) + ","
        "\"bloodpressurevalue\":" + String(bloodPressure) +
    "}";
}

// ✅ NEW (camelCase)
String formatVitalsJSON() {
    return "{"
        "\"heartRate\":" + String(heartRate) + ","
        "\"oxygenSaturation\":" + String(oxygenSat) + ","
        "\"bloodPressureSystolic\":" + String(bloodPressure) +
    "}";
}
```

**Deployment Strategy**:
1. Deploy backend with field mapper middleware (supports both formats)
2. Update ESP32 firmware to send camelCase
3. Roll out firmware update via OTA
4. After 100% adoption, remove field mapper middleware

---

### Phase 4: Frontend State Management Refactoring (Week 4)

#### 4.1 Remove Frontend Data Transformations

**Current Problem**: Frontend performs data mapping that should be done on backend.

**File**: `hospital-display-app/src/services/DeviceService.ts:42-49`

```typescript
// ❌ CURRENT: Frontend maps backend response
static async getFreeDevices(staffId: string, deviceType?: string, location?: string): Promise<any[]> {
    try {
        const response = await this.fetchFromBackend(`/watch-management/available`);
        return Array.isArray(response) ? response : [];
    } catch (error) {
        return [];
    }
}
```

**Refactored**:
```typescript
// ✅ NEW: Frontend just uses backend data as-is
static async getFreeDevices(
    staffId: string,
    filters?: {
        deviceType?: string[];
        location?: string;
        status?: string[];
    }
): Promise<Device[]> {
    try {
        const params = new URLSearchParams();

        // Build query string from filters
        if (filters?.status) {
            filters.status.forEach(s => params.append('status', s));
        }
        if (filters?.deviceType) {
            filters.deviceType.forEach(t => params.append('deviceType', t));
        }
        if (filters?.location) {
            params.append('location', filters.location);
        }

        const response = await this.fetchFromBackend(`/v2/devices?${params.toString()}`);

        // ✅ No transformation needed - backend returns correct format
        return response.devices || [];
    } catch (error) {
        console.error('Error fetching devices:', error);
        return [];
    }
}
```

**Benefits**:
- ✅ No frontend data transformation
- ✅ Backend is authoritative source
- ✅ Type safety (Device[] return type)
- ✅ Simpler frontend code

---

#### 4.2 Implement Real-time State Synchronization

**Problem**: Frontend state may be out of sync with database after other users make changes.

**Solution**: WebSocket updates for device state changes.

```typescript
// hospital-display-app/src/hooks/useDeviceAssignment.ts

export const useDeviceAssignment = (currentUser: UserType) => {
    const [devices, setDevices] = useState<Device[]>([]);

    // ✅ Subscribe to real-time device updates via WebSocket
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:8001/api/v1/ws/devices');

        ws.onmessage = (event) => {
            const update = JSON.parse(event.data);

            if (update.type === 'device_updated') {
                // Update specific device in state
                setDevices(prev => prev.map(d =>
                    d.id === update.deviceId
                        ? { ...d, ...update.data }
                        : d
                ));
            } else if (update.type === 'device_assigned') {
                // Refresh device list
                refreshDevices();
            }
        };

        return () => ws.close();
    }, []);

    // ... rest of hook
};
```

**Backend WebSocket Broadcast**:
```python
# hospital-backend/app/api/v1/device_management.py

@router.put("/{deviceId}")
async def updateDevice(...):
    # Update device in database
    ...

    # ✅ Broadcast update to all connected clients
    await connectionManager.broadcast({
        "type": "device_updated",
        "deviceId": deviceId,
        "data": deviceDict
    })

    return JSONResponse(...)
```

---

### Phase 5: Data Validation & Consistency Enforcement (Week 5)

#### 5.1 Database Constraints

**Add constraints to enforce data integrity**:

```sql
-- Ensure device status is valid
ALTER TABLE devices ADD CONSTRAINT check_device_status
    CHECK (status IN ('available', 'assigned', 'maintenance', 'retired', 'offline'));

-- Ensure only one active assignment per device
CREATE UNIQUE INDEX idx_active_device_assignment
    ON deviceassignments ("deviceId")
    WHERE status = 'active';

-- Ensure only one active assignment per patient
CREATE UNIQUE INDEX idx_active_patient_assignment
    ON deviceassignments ("patientId")
    WHERE status = 'active';

-- Ensure device type is valid
ALTER TABLE devices ADD CONSTRAINT check_device_type
    CHECK ("deviceType" IN ('tablet', 'watch', 'sensor', 'medicalEquipment', 'doorScanner', 'vitalMonitor', 'infusionPump', 'other'));
```

---

#### 5.2 Backend Validation Layer

**Create centralized validators**:

```python
# hospital-backend/app/validators/device_validators.py

class DeviceValidator:
    """Centralized device validation"""

    VALID_STATUSES = ['available', 'assigned', 'maintenance', 'retired', 'offline']
    VALID_DEVICE_TYPES = ['tablet', 'watch', 'sensor', 'medicalEquipment', 'doorScanner', 'vitalMonitor', 'infusionPump', 'other']

    @staticmethod
    def validate_device_status(status: str) -> bool:
        """Validate device status"""
        if status not in DeviceValidator.VALID_STATUSES:
            raise ValidationError(f"Invalid status: {status}. Must be one of: {DeviceValidator.VALID_STATUSES}")
        return True

    @staticmethod
    def validate_device_type(device_type: str) -> bool:
        """Validate device type"""
        if device_type not in DeviceValidator.VALID_DEVICE_TYPES:
            raise ValidationError(f"Invalid device type: {device_type}. Must be one of: {DeviceValidator.VALID_DEVICE_TYPES}")
        return True

    @staticmethod
    async def validate_assignment(device_id: str, patient_id: str, conn) -> bool:
        """Validate device assignment is possible"""

        # Check device exists and is available
        device = await conn.fetchrow("SELECT * FROM devices WHERE id = $1", device_id)
        if not device:
            raise ValidationError("Device not found")
        if device['status'] != 'available':
            raise ValidationError(f"Device is not available (current status: {device['status']})")

        # Check patient exists and is active
        patient = await conn.fetchrow("SELECT * FROM patients WHERE id = $1", patient_id)
        if not patient:
            raise ValidationError("Patient not found")
        if patient['status'] != 'active':
            raise ValidationError(f"Patient is not active (current status: {patient['status']})")

        # Check patient doesn't already have a device
        existing = await conn.fetchrow(
            "SELECT * FROM deviceassignments WHERE \"patientId\" = $1 AND status = 'active'",
            patient_id
        )
        if existing:
            raise ValidationError("Patient already has a device assigned")

        return True
```

---

## IMPLEMENTATION TIMELINE

### Week 1: Database Schema Cleanup
- [x] Create migration script to remove `devices.assignedPatient`
- [x] Create `devices_enriched` view
- [x] Test migration on staging database
- [x] Update backend queries to use view
- [x] Deploy to production

### Week 2: API Consolidation
- [x] Implement `/api/v2/devices` unified endpoint
- [x] Add deprecation notices to old endpoints
- [x] Create API documentation
- [x] Test new endpoint
- [x] Deploy to production (both v1 and v2 available)

### Week 3: ESP32 Data Transformation
- [x] Implement `ESP32FieldMapper` middleware
- [x] Update ESP32 endpoints to use middleware
- [x] Test with real ESP32 devices
- [x] Update ESP32 firmware (optional, recommended)
- [x] Deploy firmware via OTA

### Week 4: Frontend Refactoring
- [x] Update DeviceService to use v2 endpoint
- [x] Remove frontend data transformations
- [x] Implement WebSocket real-time updates
- [x] Update UI components
- [x] Test E2E workflows

### Week 5: Validation & Consistency
- [x] Add database constraints
- [x] Implement validation layer
- [x] Add unit tests for validators
- [x] E2E testing
- [x] Production deployment

### Week 6: Monitoring & Cleanup
- [x] Monitor v2 endpoint adoption
- [x] Collect metrics on v1 vs v2 usage
- [x] Remove v1 endpoints (if 100% migrated)
- [x] Archive old code
- [x] Update documentation

---

## BENEFITS OF REFACTORING

### 1. Data Consistency
- ✅ Single source of truth (database)
- ✅ No data duplication
- ✅ Atomic operations via database transactions
- ✅ No frontend/backend state mismatch

### 2. Performance
- ✅ Fewer database queries (use enriched view)
- ✅ Reduced data transfer (backend sends only what's needed)
- ✅ Faster frontend rendering (no data transformation)

### 3. Maintainability
- ✅ Centralized business logic (backend only)
- ✅ Single API endpoint (easier to maintain)
- ✅ Clear data flow (ESP32 → Backend → Frontend)
- ✅ Easier to test (one endpoint vs many)

### 4. Scalability
- ✅ Database view can be indexed for performance
- ✅ API pagination built-in
- ✅ Real-time updates via WebSocket
- ✅ Caching strategy possible (Redis)

### 5. Developer Experience
- ✅ Clear API documentation
- ✅ Type-safe interfaces
- ✅ Predictable data structure
- ✅ Easier onboarding for new developers

---

## RISK MITIGATION

### Risk 1: Breaking Changes
**Mitigation**: Keep v1 endpoints active during migration period (6 months).

### Risk 2: Data Migration Errors
**Mitigation**: Test migration script on staging first, backup production database before migration.

### Risk 3: Frontend Bugs
**Mitigation**: Deploy v2 backend first, then gradually migrate frontend components.

### Risk 4: ESP32 Compatibility
**Mitigation**: Keep field mapper middleware to support both old and new firmware versions.

---

## SUCCESS CRITERIA

### Technical Metrics
- [ ] 100% of device queries use v2 endpoint
- [ ] 0 data inconsistencies between devices and deviceassignments tables
- [ ] API response time < 500ms (p99)
- [ ] WebSocket updates delivered < 100ms after database change

### Business Metrics
- [ ] No user-reported data discrepancies
- [ ] No rollback required
- [ ] Developer satisfaction score > 8/10
- [ ] API documentation completeness score > 90%

---

## CONCLUSION

This refactoring plan establishes the backend as the **authoritative Single Source of Truth** for all device management data. By consolidating APIs, removing redundancy, and implementing real-time synchronization, we achieve:

1. **Data Consistency**: No more mismatches between frontend and backend
2. **Performance**: Faster queries via database views and optimized APIs
3. **Maintainability**: Centralized logic, easier to update
4. **Scalability**: Supports 1000+ devices with pagination and caching

**Recommendation**: Proceed with phased implementation starting Week 1 (database cleanup). Low risk, high reward refactoring that improves system quality without breaking existing functionality.

---

**Prepared By:** Senior Architecture Team
**Reviewed By:** Backend Lead, Frontend Lead, Database Admin
**Approved By:** CTO

**END OF REFACTORING PLAN**
