# Patient Card Header - Dashboard Analysis

## Current Header Layout (90px height)

### File Location
[PatientCardHeader.tsx](hospital-display-app/src/components/PatientCard/PatientCardHeader.tsx)

---

## What's Currently Displayed

### Left Section (Main Patient Info)
1. **Patient Name** (Line 47)
   - Font: semibold, text-base
   - Color: text-gray-900
   - Truncated if too long

2. **Watch Status Indicator** (Lines 50-81)
   - **If watch assigned & connected**: Green watch icon + green dot (clickable for details)
   - **If watch assigned & disconnected**: Amber watch icon + amber dot (clickable for details)
   - **If no watch assigned**: Gray WiFi-off icon + gray dot

3. **Inline Alerts** (Lines 84-124) - Shows top 2 critical alerts
   - **Alert Badges**: Colored pills with emojis and message
     - Critical: 🚨 Red background (bg-red-100, text-red-700)
     - High: ⚠️ Orange background (bg-orange-100, text-orange-700)
     - Medium: ⚡ Yellow background (bg-yellow-100, text-yellow-700)
   - **Acknowledge Button**: Green checkmark button to acknowledge visible alerts
     - Skips certain alert types (fall-risk, arrhythmia, seizure)

4. **Age & Gender** (Lines 127-138)
   - Format: "XXy, [gender]"
   - Additional watch status badge inline

5. **Department** (Lines 140-142)
   - Text: xs, gray-600
   - Truncated if too long

### Right Section (Status & Metadata)
1. **Action Buttons** (Lines 146-166)
   - **Bedside Mode Button**: Purple eye icon (clickable)
   - **Status Badge**: Rounded pill showing patient status (STABLE, CRITICAL, etc.)
     - Color varies by status using `getStatusColor()` utility

2. **Bed Location** (Lines 168-170)
   - Format: "Bed [number] • [ward]"
   - Text: xs, gray-600

3. **Last Updated Time** (Lines 171-173)
   - Format: "Updated: [time]"
   - Shows `vitals.lastDataReceived` timestamp
   - Text: xs, gray-500

---

## Key Features

### Interactive Elements
- **Watch icon** - Click to view watch details modal
- **Bedside mode button** - Enter full-screen patient monitoring
- **Acknowledge alerts button** - Acknowledge top 2 visible alerts only

### Medical Safety Features
- **Alert filtering** - Cannot acknowledge certain critical alerts (fall-risk, arrhythmia, seizure)
- **Audit logging** - All interactions logged via `auditService`
- **Status visibility** - Clear visual indicators for device connectivity

### Layout Details
- **Total Height**: 90px (fixed, flex-shrink-0)
- **Border**: Bottom border to separate from content below
- **Padding**: 2 (p-2)
- **Responsive**: Truncates text, limits alert display to top 2

---

## Data Sources

### Patient Object Properties Used
```typescript
- patient.name
- patient.assignedDeviceId
- patient.deviceStatus ('connected' | 'disconnected')
- patient.age
- patient.gender
- patient.department
- patient.bedNumber
- patient.ward
- patient.status
- patient.vitals?.lastDataReceived
- patient.id (for audit logging)
```

### Props
- `unacknowledgedAlerts[]` - Array of unacknowledged alerts
- `currentUser` - Current logged-in user
- `onBedsideMode()` - Callback for bedside mode
- `onAcknowledgeAlert()` - Callback for acknowledging alerts
- `onViewWatchDetails()` - Callback for watch details modal

---

## Current Issues/Observations

### Strengths
✅ Clean, medical-grade information display
✅ Clear visual hierarchy
✅ Interactive elements for critical actions
✅ Audit trail for all interactions
✅ Safety filters on alert acknowledgment

### Potential Improvements
- Could add MRN (Medical Record Number) if available
- Could show admission date/time
- Could display primary diagnosis if needed
- Alert count indicator if more than 2 alerts exist
