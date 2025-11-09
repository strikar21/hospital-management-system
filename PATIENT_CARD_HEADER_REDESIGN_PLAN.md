# Patient Card Header - 3-Column Redesign Plan

## Layout: 30% - 40% - 30% Split

---

## LEFT Column (30%) - Patient Demographics

### Top Row
- **Name**: `patient.name` (semibold, larger font)
- **Age**: `patient.age`y
- **Gender**: `patient.gender`

### Middle Row
- **MRN**: `patient.mrn` (Medical Record Number)
- **Department**: `patient.department`

### Bottom Row
- **Ward**: `patient.ward`
- **Bed**: `patient.bedNumber`
- **Diagnosis**: `patient.diagnosis` (truncated)

**Layout Strategy:**
- Compact, information-dense
- Small font sizes (text-xs, text-sm)
- Truncate long diagnosis text
- Vertical stack with minimal spacing

---

## CENTER Column (40%) - Alerts Display

### Alert Display Strategy
- Show **top 2-3 alerts** based on criticality
- Sort by severity: critical > high > medium > low
- Display format:
  - Alert severity badge (colored pill)
  - Alert message (truncated if needed)
  - Emoji indicator: 🚨 critical, ⚠️ high, ⚡ medium

### Alert Counter
- If more alerts exist: "2 of 5 alerts shown"
- Small text below alerts

### Acknowledge Button
- Green checkmark button
- Position: Bottom of center column or next to alerts
- Action: Acknowledge visible alerts only
- Skip permanent alerts (fall-risk, arrhythmia, seizure)

**Layout Strategy:**
- Vertical stack of alert badges
- Center alignment
- Scrollable if needed (but limit to top N)
- Visual prominence with colored backgrounds

---

## RIGHT Column (30%) - Watch & Status

### Suggested Content (Top to Bottom):

**Option A - Device & Actions Focus:**
1. **Watch Status** (Top)
   - Watch icon with connection status
   - Device battery level: `patient.deviceBatteryLevel`
   - Last seen: `patient.deviceLastSeen` (relative time)
   - Clickable for watch details modal

2. **Patient Status Badge** (Middle)
   - Large, prominent status pill
   - STABLE / CRITICAL / EMERGENCY
   - Color-coded background

3. **Action Buttons** (Bottom)
   - Bedside Mode button (Eye icon)
   - Maybe: Quick Actions dropdown

**Option B - Status & Metadata Focus:**
1. **Patient Status Badge** (Top)
   - Large status pill
   - Color-coded

2. **Watch Connection** (Middle)
   - Icon + connection status
   - Battery level indicator
   - Clickable for details

3. **Metadata** (Bottom)
   - Last updated: `vitals.lastDataReceived`
   - Admission date: `patient.admissionDate` (relative)
   - Attending: `patient.attendingPhysicianName`

**Option C - Comprehensive Monitoring:**
1. **Watch Vitals Status** (Top)
   - Watch icon with battery and connection
   - Data quality score: `vitals.dataQualityScore`
   - Last data received time

2. **Clinical Status** (Middle)
   - Patient status badge
   - Code status: `patient.codeStatus` (DNR/Full Code)
   - Active problems count: `patient.activeProblems?.length`

3. **Actions & Attending** (Bottom)
   - Bedside mode button
   - Attending physician name (truncated)

---

## Recommendation: **Option C** - Comprehensive Monitoring

### Reasoning:
✅ Medical-grade information density
✅ Device monitoring (watch battery, connection, data quality)
✅ Critical clinical info (code status, active problems)
✅ Staff accountability (attending physician)
✅ Quick actions (bedside mode)
✅ Balanced with left demographics and center alerts

---

## Implementation Details

### Height
- Keep 90px height (current)
- Or expand to 100px if needed for 3 rows in each column

### Spacing
- Use flexbox with `w-[30%]` `w-[40%]` `w-[30%]`
- Small gaps between columns (gap-2 or gap-3)
- Tight vertical spacing within columns (space-y-1)

### Typography
- LEFT: text-xs to text-sm, compact
- CENTER: text-xs for alerts, colored backgrounds
- RIGHT: text-xs for metadata, larger for status badge

### Interactivity
- LEFT: Static (no clicks)
- CENTER: Acknowledge button
- RIGHT: Watch status clickable, Bedside mode button clickable

### Responsive Behavior
- Truncate text where needed
- Maintain 30-40-30 ratio
- Ellipsis for overflow

---

## Data Availability Check

### Available in patient object:
✅ mrn (optional, may be undefined)
✅ diagnosis
✅ ward, bedNumber
✅ deviceBatteryLevel
✅ deviceLastSeen
✅ vitals.dataQualityScore
✅ codeStatus (optional)
✅ activeProblems (optional)
✅ attendingPhysicianName (optional)
✅ admissionDate

### Fallback Strategy:
- If `mrn` is undefined: show "MRN: N/A" or omit row
- If `codeStatus` is undefined: show "Full Code" (default assumption)
- If `attendingPhysicianName` is undefined: use `attendingPhysician` (ID)
- If `activeProblems` is undefined: don't show count

---

## Next Steps

**Which RIGHT column option do you prefer?**
- **Option A**: Device & Actions Focus
- **Option B**: Status & Metadata Focus
- **Option C**: Comprehensive Monitoring (Recommended)

Once confirmed, I'll implement the changes with:
1. Update PatientCardHeader.tsx
2. Ensure all camelCase compliance
3. Test with actual patient data
4. Handle undefined/optional fields gracefully
