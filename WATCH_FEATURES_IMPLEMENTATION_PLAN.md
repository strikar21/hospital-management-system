# Watch Features - Complete Implementation Plan

**Date**: 2025-10-15
**Status**: Ready for Implementation

---

## Overview

Fixing three watch-related issues:
1. **Issue #3**: Device reassignment blocking (400 Bad Request) - **HIGH PRIORITY**
2. **Issue #1**: No watch details in patient detail view - **MEDIUM PRIORITY**
3. **Issue #2**: Watch details modal from dashboard - **LOWER PRIORITY**

---

## Issue #3: Device Reassignment Blocking (HIGH PRIORITY)

### Problem
Backend rejects assignment if patient already has a watch, even when user wants to swap watches.

### Root Cause
[watch_management.py:148-154](hospital-backend/app/api/v1/watch_management.py#L148-L154) - Hard rejection on existing assignment

### Solution: Auto-Unassign on Reassignment

**Why this approach?**
- Seamless UX (single API call)
- Atomic transaction (ACID guarantees)
- Complete audit trail (both unassign + assign logged)
- Backend-only change (no frontend impact)

### Implementation Steps

1. **Modify assign endpoint** in `watch_management.py` (lines 148-154)
2. **When existing assignment found**: Auto-unassign first, then proceed with new assignment
3. **Log both actions** for audit trail
4. **Use database transaction** to ensure atomicity

### Exact Code Changes

**File**: `hospital-backend/app/api/v1/watch_management.py`

**Location**: Lines 148-154

**Current Code**:
```python
# Check if patient already has a watch assigned
existingAssignment = await conn.fetchrow(
    "SELECT * FROM deviceassignments WHERE \"patientId\" = $1 AND status = 'active'",
    patientId
)
if existingAssignment:
    raise HTTPException(status_code=400, detail="Patient already has a watch assigned")
```

**New Code**:
```python
# Check if patient already has a watch assigned
existingAssignment = await conn.fetchrow(
    "SELECT * FROM deviceassignments WHERE \"patientId\" = $1 AND status = 'active'",
    patientId
)
if existingAssignment:
    # AUTO-UNASSIGN: Mark old watch as inactive and update device status
    oldDeviceId = existingAssignment['deviceId']

    await conn.execute("""
        UPDATE deviceassignments
        SET status = 'inactive',
            "unassignedAt" = $1,
            "unassignedBy" = $2,
            "unassignmentReason" = 'Auto-unassigned for reassignment'
        WHERE \"patientId\" = $3 AND status = 'active'
    """, now, assignedBy, patientId)

    # Update old device status to available
    await conn.execute(
        "UPDATE devices SET status = 'available', \"updatedAt\" = $1 WHERE id = $2",
        now, oldDeviceId
    )

    logger.info(f"🔄 Auto-unassigned existing watch {oldDeviceId} for reassignment by {assignedBy}")
```

**Important**: The `now` variable is already defined on line 156, so we can use it directly.

### Testing Checklist
- [ ] Patient with Watch A, assign Watch B → succeeds
- [ ] Watch A status becomes 'available'
- [ ] Watch B status becomes 'assigned'
- [ ] Device assignments table shows 2 records: old (inactive), new (active)
- [ ] Unassignment reason: "Auto-unassigned for reassignment"
- [ ] assignedBy and unassignedBy properly logged

---

## Issue #1: Watch Details in Patient Detail View (MEDIUM PRIORITY)

### Problem
Patient detail page shows no device information section.

### Solution
Add "Device & Monitoring" section in PatientOverview.tsx after Patient Information section.

### Implementation Steps

1. **Add device section** after line 49 in PatientOverview.tsx
2. **Show device info** only when patient has assigned device
3. **Display fields**: deviceId, status, battery, lastSeen
4. **Format timestamps** for better readability

### Exact Code Changes

**File**: `hospital-display-app/src/components/PatientDetail/PatientOverview.tsx`

**Location**: After line 49 (after Patient Information div closes)

**New Code**:
```tsx
{/* Device & Monitoring Section */}
{patient.assignedDeviceId && (
  <div className="bg-blue-50 rounded-lg p-3 mb-2 flex-shrink-0">
    <h3 className="text-sm font-semibold text-blue-800 mb-2">📟 Assigned Watch</h3>
    <div className="grid grid-cols-4 gap-3 text-xs">
      <div>
        <span className="font-medium text-gray-600">Device ID:</span>{' '}
        <span className="text-gray-900">{patient.assignedDeviceId}</span>
      </div>
      <div>
        <span className="font-medium text-gray-600">Status:</span>
        <span className={`ml-1 px-2 py-0.5 rounded font-medium ${
          patient.deviceStatus === 'connected'
            ? 'bg-green-100 text-green-800'
            : 'bg-amber-100 text-amber-800'
        }`}>
          {patient.deviceStatus === 'connected' ? 'Connected' : 'Disconnected'}
        </span>
      </div>
      <div>
        <span className="font-medium text-gray-600">Battery:</span>{' '}
        <span className={`font-medium ${
          (patient.deviceBatteryLevel || 0) <= 20 ? 'text-red-600' :
          (patient.deviceBatteryLevel || 0) <= 40 ? 'text-amber-600' :
          'text-green-600'
        }`}>
          {patient.deviceBatteryLevel || '--'}%
        </span>
      </div>
      <div>
        <span className="font-medium text-gray-600">Last Seen:</span>{' '}
        <span className="text-gray-900">
          {patient.deviceLastSeen
            ? new Date(patient.deviceLastSeen).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit'
              })
            : '--'}
        </span>
      </div>
    </div>
  </div>
)}
```

**Note**: Patient type already has these fields defined:
- `assignedDeviceId?: string` (line 24)
- `deviceStatus?: 'connected' | 'disconnected' | 'offline' | 'lowBattery'` (line 25)
- `deviceBattery?: number` (line 26)

We need to add `deviceBatteryLevel` and `deviceLastSeen` to match backend response.

### Additional Type Updates

**File**: `hospital-display-app/src/types/PatientTypes.ts`

**Location**: After line 26

**New Code**:
```typescript
deviceBatteryLevel?: number;  // Device battery level (0-100) - matches backend field
deviceLastSeen?: string;      // Device last seen timestamp - matches backend field
```

### Testing Checklist
- [ ] Patient with watch shows device section
- [ ] Connection status displays correctly (green/amber)
- [ ] Battery level shows correct percentage with color coding
- [ ] Last seen timestamp formatted properly
- [ ] Patient without watch - section hidden

---

## Issue #2: Watch Details Modal (LOWER PRIORITY)

### Problem
No way to view detailed watch information from dashboard.

### Solution
Create clickable watch icon that opens detailed modal.

### Implementation Steps

#### Phase A: Make Watch Icon Clickable

1. **Add click handler** to watch icon in PatientCardHeader.tsx
2. **Add onViewWatchDetails prop** to PatientCardHeader
3. **Prevent event bubbling** (stopPropagation)

**File**: `hospital-display-app/src/components/PatientCard/PatientCardHeader.tsx`

**Location**: Lines 47-65 (Watch Status Indicator section)

**Changes**:

1. **Add prop to interface** (line 16):
```typescript
interface PatientCardHeaderProps {
  patient: patient;
  currentUser: user;
  onBedsideMode: (patient: patient) => void;
  unacknowledgedAlerts?: any[];
  onAcknowledgeAlert?: (patient: patient, alertId: string) => void;
  onViewWatchDetails?: (patient: patient) => void;  // NEW
}
```

2. **Update component signature** (line 21):
```typescript
export const PatientCardHeader: React.FC<PatientCardHeaderProps> = React.memo(({
  patient,
  currentUser,
  onBedsideMode,
  unacknowledgedAlerts = [],
  onAcknowledgeAlert,
  onViewWatchDetails  // NEW
}) => {
```

3. **Make watch icon clickable** (replace lines 48-59):
```tsx
{patient.assignedDeviceId ? (
  patient.deviceStatus === 'connected' ? (
    <div
      className="flex items-center space-x-1 cursor-pointer hover:bg-green-100 rounded px-1 py-0.5 transition-colors"
      title="Watch connected - Click for details"
      onClick={(e) => {
        e.stopPropagation();
        onViewWatchDetails?.(patient);
      }}
    >
      <Watch className="w-3 h-3 text-green-600" />
      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
    </div>
  ) : (
    <div
      className="flex items-center space-x-1 cursor-pointer hover:bg-amber-100 rounded px-1 py-0.5 transition-colors"
      title="Watch disconnected - Click for details"
      onClick={(e) => {
        e.stopPropagation();
        onViewWatchDetails?.(patient);
      }}
    >
      <Watch className="w-3 h-3 text-amber-600" />
      <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
    </div>
  )
) : (
  <div className="flex items-center space-x-1" title="No watch assigned">
    <WifiOff className="w-3 h-3 text-gray-400" />
    <div className="w-2 h-2 bg-gray-300 rounded-full"></div>
  </div>
)}
```

#### Phase B: Create Watch Details Modal Component

**File**: `hospital-display-app/src/components/WatchDetailsModal.tsx` (NEW)

**Content**:
```tsx
/**
 * WatchDetailsModal - Detailed watch information modal
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Shows detailed device information, connection status, and battery
 */

import React from 'react';
import { X, Watch, Battery, Signal, Calendar, User } from 'lucide-react';
import { patient } from '../types';

interface WatchDetailsModalProps {
  patient: patient;
  onClose: () => void;
}

export const WatchDetailsModal: React.FC<WatchDetailsModalProps> = ({
  patient,
  onClose
}) => {
  if (!patient.assignedDeviceId) return null;

  const getBatteryIcon = (level: number) => {
    if (level > 80) return '🔋';
    if (level > 60) return '🔋';
    if (level > 40) return '🔋';
    if (level > 20) return '⚡';
    return '🪫';
  };

  const getTimeSinceLastSeen = (lastSeen?: string) => {
    if (!lastSeen) return 'Unknown';
    const now = new Date();
    const then = new Date(lastSeen);
    const diffMs = now.getTime() - then.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Watch className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Watch Details</h2>
              <p className="text-sm text-gray-600">{patient.assignedDeviceId}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Close"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Patient Info */}
        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Assigned Patient</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-600">Name:</span>{' '}
              <span className="text-gray-900">{patient.name}</span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Location:</span>{' '}
              <span className="text-gray-900">
                {patient.roomNumber}, Bed {patient.bedNumber}
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Department:</span>{' '}
              <span className="text-gray-900">{patient.department}</span>
            </div>
            <div>
              <span className="font-medium text-gray-600">Ward:</span>{' '}
              <span className="text-gray-900">{patient.ward}</span>
            </div>
          </div>
        </div>

        {/* Device Status */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Signal className="w-4 h-4 text-blue-600" />
              <span className="text-xs font-medium text-gray-600">Connection</span>
            </div>
            <div className={`text-lg font-bold ${
              patient.deviceStatus === 'connected'
                ? 'text-green-600'
                : 'text-amber-600'
            }`}>
              {patient.deviceStatus === 'connected' ? 'Connected' : 'Disconnected'}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {getTimeSinceLastSeen(patient.deviceLastSeen)}
            </div>
          </div>

          <div className="bg-green-50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Battery className="w-4 h-4 text-green-600" />
              <span className="text-xs font-medium text-gray-600">Battery</span>
            </div>
            <div className={`text-lg font-bold ${
              (patient.deviceBatteryLevel || 0) <= 20 ? 'text-red-600' :
              (patient.deviceBatteryLevel || 0) <= 40 ? 'text-amber-600' :
              'text-green-600'
            }`}>
              {getBatteryIcon(patient.deviceBatteryLevel || 0)} {patient.deviceBatteryLevel || '--'}%
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {(patient.deviceBatteryLevel || 0) <= 20 ? 'Critical' :
               (patient.deviceBatteryLevel || 0) <= 40 ? 'Low' : 'Good'}
            </div>
          </div>

          <div className="bg-purple-50 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Calendar className="w-4 h-4 text-purple-600" />
              <span className="text-xs font-medium text-gray-600">Last Seen</span>
            </div>
            <div className="text-lg font-bold text-purple-600">
              {patient.deviceLastSeen
                ? new Date(patient.deviceLastSeen).toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })
                : '--:--'}
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {patient.deviceLastSeen
                ? new Date(patient.deviceLastSeen).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric'
                  })
                : 'Unknown'}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
```

#### Phase C: Wire Up Modal in Parent Component

**File**: `hospital-display-app/src/components/PatientCard/PatientCardContainer.tsx`

**Changes**:

1. **Import modal**:
```typescript
import { WatchDetailsModal } from '../WatchDetailsModal';
```

2. **Add modal state**:
```typescript
const [watchDetailsPatient, setWatchDetailsPatient] = useState<patient | null>(null);
```

3. **Add handler**:
```typescript
const handleViewWatchDetails = (patient: patient) => {
  setWatchDetailsPatient(patient);
};
```

4. **Pass prop to PatientCardHeader**:
```tsx
<PatientCardHeader
  patient={patient}
  currentUser={currentUser}
  onBedsideMode={onBedsideMode}
  unacknowledgedAlerts={unacknowledgedAlerts}
  onAcknowledgeAlert={onAcknowledgeAlert}
  onViewWatchDetails={handleViewWatchDetails}  // NEW
/>
```

5. **Render modal**:
```tsx
{watchDetailsPatient && (
  <WatchDetailsModal
    patient={watchDetailsPatient}
    onClose={() => setWatchDetailsPatient(null)}
  />
)}
```

### Testing Checklist
- [ ] Click watch icon opens modal
- [ ] Modal shows complete device information
- [ ] Connection status displays correctly
- [ ] Battery level with color coding
- [ ] Last seen timestamp formatted
- [ ] Modal closes properly (X button and backdrop click)
- [ ] Patient without watch - no modal

---

## Implementation Order

1. **Issue #3 (Backend)** - 15 minutes
   - Modify watch_management.py assign endpoint
   - Test device reassignment

2. **Issue #1 (Frontend)** - 30 minutes
   - Update PatientTypes.ts with new fields
   - Add device section to PatientOverview.tsx
   - Test display with connected watch

3. **Issue #2 (Frontend)** - 60 minutes
   - Make watch icon clickable
   - Create WatchDetailsModal component
   - Wire up modal in PatientCardContainer
   - Test modal interaction

**Total Estimated Time**: ~2 hours

---

## Testing Strategy

### Manual Testing
1. Start backend and frontend
2. Ensure Thomas Brown has ESP32_WATCH_003 assigned
3. Test Issue #3: Try to assign different watch to Thomas Brown
4. Test Issue #1: Open Thomas Brown's patient detail view
5. Test Issue #2: Click watch icon on dashboard patient card

### Database Verification
```sql
-- Check device assignments after reassignment
SELECT * FROM deviceassignments WHERE "patientId" = '081a5294-da91-4c74-bb8a-e5062f5851dd' ORDER BY "assignedAt" DESC;

-- Check device status
SELECT id, "serialNumber", status FROM devices WHERE "deviceType" = 'watch';
```

---

## Files to Modify

### Backend
1. `hospital-backend/app/api/v1/watch_management.py` - Lines 148-154

### Frontend
1. `hospital-display-app/src/types/PatientTypes.ts` - Add deviceBatteryLevel, deviceLastSeen
2. `hospital-display-app/src/components/PatientDetail/PatientOverview.tsx` - Add device section
3. `hospital-display-app/src/components/PatientCard/PatientCardHeader.tsx` - Make icon clickable
4. `hospital-display-app/src/components/WatchDetailsModal.tsx` - NEW FILE
5. `hospital-display-app/src/components/PatientCard/PatientCardContainer.tsx` - Wire up modal

---

## Ready to Implement ✅

All research complete. All files identified. All code changes planned. Ready for user approval.
