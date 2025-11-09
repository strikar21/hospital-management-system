# Patient Card Header - 3-Column Implementation Plan

## Layout: 30% - 40% - 30% (Option C - Comprehensive Monitoring)

---

## LEFT Column (30%) - Patient Demographics

```tsx
<div className="w-[30%] flex flex-col justify-between">
  {/* Top Row: Name, Age, Gender */}
  <div>
    <h3 className="font-semibold text-sm text-gray-900 truncate">
      {patient.name}
    </h3>
    <span className="text-xs text-gray-600">
      {patient.age}y, {patient.gender}
    </span>
  </div>

  {/* Middle Row: MRN, Department */}
  <div className="text-xs text-gray-600">
    <div>MRN: {patient.mrn || 'N/A'}</div>
    <div className="truncate">{patient.department}</div>
  </div>

  {/* Bottom Row: Ward, Bed, Diagnosis */}
  <div className="text-xs text-gray-600">
    <div>{patient.ward} • Bed {patient.bedNumber}</div>
    <div className="truncate" title={patient.diagnosis}>
      {patient.diagnosis}
    </div>
  </div>
</div>
```

---

## CENTER Column (40%) - Alerts Display

```tsx
<div className="w-[40%] flex flex-col items-center justify-center px-2">
  {unacknowledgedAlerts.length > 0 ? (
    <>
      {/* Alert Display - Top 2-3 based on criticality */}
      <div className="flex flex-col space-y-1 w-full">
        {unacknowledgedAlerts
          .sort((a, b) => {
            const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
            return severityOrder[a.severity] - severityOrder[b.severity];
          })
          .slice(0, 3)
          .map((alert) => (
            <div
              key={alert.id}
              className={`text-xs px-2 py-1 rounded flex items-center ${
                alert.severity === 'critical' ? 'bg-red-100 text-red-700' :
                alert.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                'bg-yellow-100 text-yellow-700'
              }`}
            >
              <span className="flex-shrink-0">
                {alert.severity === 'critical' ? '🚨' :
                 alert.severity === 'high' ? '⚠️' : '⚡'}
              </span>
              <span className="ml-1 truncate">{alert.message}</span>
            </div>
          ))}
      </div>

      {/* Alert Counter */}
      {unacknowledgedAlerts.length > 3 && (
        <div className="text-xs text-gray-500 mt-1">
          Showing 3 of {unacknowledgedAlerts.length} alerts
        </div>
      )}

      {/* Acknowledge Button */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          unacknowledgedAlerts
            .slice(0, 3)
            .forEach(alert => {
              if (!alert.id.includes('fall-risk') &&
                  !alert.id.includes('arrhythmia') &&
                  !alert.id.includes('seizure')) {
                handleAcknowledgeClick(e, alert.id);
              }
            });
        }}
        className="mt-2 px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs flex items-center"
        title="Acknowledge visible alerts"
      >
        <CheckCircle className="w-3 h-3 mr-1" />
        Acknowledge
      </button>
    </>
  ) : (
    <div className="text-xs text-gray-400 italic">No alerts</div>
  )}
</div>
```

---

## RIGHT Column (30%) - Comprehensive Monitoring

```tsx
<div className="w-[30%] flex flex-col justify-between items-end">
  {/* Top: Watch Vitals Status */}
  <div
    className="cursor-pointer hover:bg-gray-50 rounded px-2 py-1 transition-colors"
    onClick={(e) => {
      e.stopPropagation();
      onViewWatchDetails?.(patient);
    }}
  >
    <div className="flex items-center space-x-2">
      {patient.assignedDeviceId ? (
        <>
          <Watch className={`w-4 h-4 ${
            patient.deviceStatus === 'connected' ? 'text-green-600' : 'text-amber-600'
          }`} />
          <div className="text-xs text-right">
            <div className={
              patient.deviceStatus === 'connected' ? 'text-green-700' : 'text-amber-700'
            }>
              {patient.deviceStatus === 'connected' ? 'Connected' : 'Disconnected'}
            </div>
            {patient.deviceBatteryLevel !== undefined && (
              <div className="text-gray-600">
                Battery: {patient.deviceBatteryLevel}%
              </div>
            )}
            {patient.vitals?.dataQualityScore !== undefined && (
              <div className="text-gray-600">
                Quality: {Math.round(patient.vitals.dataQualityScore * 100)}%
              </div>
            )}
          </div>
        </>
      ) : (
        <>
          <WifiOff className="w-4 h-4 text-gray-400" />
          <span className="text-xs text-gray-500">No device</span>
        </>
      )}
    </div>
  </div>

  {/* Middle: Clinical Status */}
  <div className="flex flex-col items-end space-y-1">
    {/* Patient Status Badge */}
    <div className={`px-3 py-1 rounded-full text-xs font-medium border ${
      getStatusColor(patient.status)
    }`}>
      {patient.status.toUpperCase()}
    </div>

    {/* Code Status */}
    {patient.codeStatus && (
      <div className={`text-xs px-2 py-0.5 rounded ${
        patient.codeStatus === 'dnr' || patient.codeStatus === 'dnrcca' || patient.codeStatus === 'comfortcare'
          ? 'bg-purple-100 text-purple-700 border border-purple-300'
          : 'bg-blue-100 text-blue-700'
      }`}>
        {patient.codeStatus === 'fullcode' ? 'Full Code' :
         patient.codeStatus === 'dnr' ? 'DNR' :
         patient.codeStatus === 'dnrcca' ? 'DNR/CCA' :
         'Comfort Care'}
      </div>
    )}

    {/* Active Problems Count */}
    {patient.activeProblems && patient.activeProblems.length > 0 && (
      <div className="text-xs text-gray-600">
        {patient.activeProblems.length} active problem{patient.activeProblems.length !== 1 ? 's' : ''}
      </div>
    )}
  </div>

  {/* Bottom: Actions & Attending */}
  <div className="flex flex-col items-end space-y-1">
    {/* Bedside Mode Button */}
    <button
      onClick={(e) => {
        e.stopPropagation();
        onBedsideMode(patient);
        auditService.logPatientInteraction(
          'enterBedsideMode',
          patient.id,
          'entered bedside mode',
          { mode: 'bedside' }
        );
      }}
      className="p-1.5 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded transition-colors"
      title="Enter Bedside Mode"
    >
      <Eye className="w-4 h-4" />
    </button>

    {/* Attending Physician */}
    {patient.attendingPhysicianName && (
      <div className="text-xs text-gray-600 text-right truncate max-w-full">
        Dr. {patient.attendingPhysicianName}
      </div>
    )}

    {/* Last Updated */}
    <div className="text-xs text-gray-500 text-right">
      {formatTimeOnly((patient.vitals?.lastDataReceived || new Date()).toString())}
    </div>
  </div>
</div>
```

---

## Complete Structure

```tsx
<div className="p-2 border-b flex-shrink-0 h-[90px]">
  <div className="flex items-start justify-between h-full gap-3">
    {/* LEFT: Demographics (30%) */}
    {/* ... */}

    {/* CENTER: Alerts (40%) */}
    {/* ... */}

    {/* RIGHT: Monitoring (30%) */}
    {/* ... */}
  </div>
</div>
```

---

## Key Changes from Current Implementation

### Removed:
- Inline alerts next to patient name
- Watch status next to name
- Age/gender below name in old layout
- Department as separate line

### Added:
- MRN display (if available)
- Diagnosis in left column
- Centered alert display with sorting
- Alert counter for overflow
- Device battery level
- Data quality score
- Code status (DNR/Full Code)
- Active problems count
- Attending physician name

### Preserved:
- Bedside mode button functionality
- Watch details modal trigger
- Alert acknowledgment logic (skip certain alert types)
- Audit logging
- Status badge with color coding
- Last updated timestamp

---

## Fallback Handling

```typescript
// MRN
patient.mrn || 'N/A'

// Code Status
patient.codeStatus || undefined // Don't show if not set

// Attending Physician
patient.attendingPhysicianName || patient.attendingPhysician || 'Not assigned'

// Battery Level
patient.deviceBatteryLevel !== undefined ? `${patient.deviceBatteryLevel}%` : ''

// Data Quality
patient.vitals?.dataQualityScore !== undefined ?
  `${Math.round(patient.vitals.dataQualityScore * 100)}%` : ''

// Active Problems
patient.activeProblems?.length > 0 ? show count : hide
```

---

## Testing Checklist

- [ ] Layout renders correctly at 30-40-30 ratio
- [ ] All text truncates properly (no overflow)
- [ ] Alerts sort by criticality (critical > high > medium > low)
- [ ] Alert counter shows when > 3 alerts
- [ ] Acknowledge button works for top 3 alerts only
- [ ] Skips fall-risk, arrhythmia, seizure alerts
- [ ] Watch status clickable → opens watch details modal
- [ ] Bedside mode button → enters bedside mode
- [ ] All undefined fields handled gracefully
- [ ] All camelCase compliance maintained
- [ ] Audit logging works for all interactions

---

## Ready to Implement?

This plan maintains:
✅ Medical-grade information density
✅ All critical patient data visible
✅ Clear visual hierarchy
✅ Interactive elements preserved
✅ Safety features (alert filtering, code status)
✅ Device monitoring (battery, quality, connection)
✅ Staff accountability (attending physician)
✅ Audit compliance

**Proceed with implementation?**
