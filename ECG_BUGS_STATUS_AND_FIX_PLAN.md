# ECG/EEG Bug Fixes - Status & Implementation Plan

**Date:** 2025-11-01
**Status Check:** Automated audit of current implementation
**Reference:** [ECG_BUGS_CORRECTED_FINAL.md](ECG_BUGS_CORRECTED_FINAL.md)

---

## ✅ COMPLETED WORK

### BUG #1: Error Boundaries - ✅ DONE
**Status:** FULLY IMPLEMENTED

**Evidence:**
- ✅ Created: `src/components/ErrorBoundary.tsx` with both `ErrorBoundary` and `WaveformErrorBoundary`
- ✅ Wrapped: `PatientCardWaveform.tsx` line 84 uses `<WaveformErrorBoundary>`
- ✅ Features:
  - Retry button for failed renders
  - Medical-safe fallback UI ("Vital signs monitoring continues")
  - Dev mode error details
  - Component name tracking

**Files Modified:**
1. `hospital-display-app/src/components/ErrorBoundary.tsx` - Created (139 lines)
2. `hospital-display-app/src/components/PatientCard/PatientCardWaveform.tsx` - Wrapped with ErrorBoundary

**Testing Status:** ⚠️ Needs manual injection test
- [ ] Test with malformed WebSocket data
- [ ] Verify error boundary catches exceptions
- [ ] Verify rest of dashboard remains functional

---

### BUG #3: Vestigial Lead Selector Dropdown - ❌ STILL EXISTS
**Status:** NOT FIXED

**Current Location:** `src/components/ECGViewer.tsx:120-149`

**Current Code:**
```typescript
<select
  className="text-sm border rounded px-2 py-1"
  defaultValue={isECGMode ? 'II' : 'C3-C4'}
>
  {isECGMode ? (
    <>
      <option value="I">Lead I</option>
      <option value="II">Lead II</option>
      // ... 12 options total
```

**Why It's Still Wrong:**
- Dropdown displays but is **non-functional**
- Code hardcodes: `const leadIndex = isECGMode ? 1 : 14;` (Lead II / F3)
- Confuses users who think they can change leads
- **Clinical workflow is CORRECT** - embedded viewer should show standard leads only
- Dropdown is just vestigial placeholder UI

**Fix Required:** Remove dropdown, add label showing current lead

---

## 🔧 REMAINING WORK

### Priority Order (Based on ECG_BUGS_CORRECTED_FINAL.md)

| Priority | Bug | Status | Effort | Files Affected |
|----------|-----|--------|--------|----------------|
| **P0** | Error Boundaries | ✅ DONE | 2 hours | Already completed |
| **P2** | Console Logging | ❌ TODO | 1 hour | 4 files, 17 replacements |
| **P3** | Vestigial Dropdown | ❌ TODO | 15 min | 1 file, 30 lines |
| **P4** | Wrong Default Value | MOOT | 1 min | Fixed by P3 |
| **P5** | Memory Profiling | INVESTIGATE | TBD | Only if issues reported |

---

## 📋 DETAILED FIX PLAN

### FIX #1: Replace Console Logging (P2)
**Severity:** MINOR - Professional quality issue
**Impact:** Console spam, performance hit, harder debugging
**Effort:** 1 hour

#### Current Console.log Usage:
```bash
# ECG Components
ECGWaveformCanvas.tsx: 6 instances (60 logs/second per canvas!)
ECGViewerContainer.tsx: 5 instances
ECGDisplayGrid.tsx: 1 instance
PatientCardWaveform.tsx: 5 instances

# Total: 17 console.log calls
# In 12-lead mode: 12 canvases × 60fps = 720 logs/second
```

#### Files to Modify:
1. **`src/components/ECGViewer/ECGWaveformCanvas.tsx`** (6 replacements)
   - Line 54: `console.log` → `logger.log`
   - Line 60: `console.log` → `logger.log`
   - Line 79: `console.log` → `logger.log` (runs at 60fps!)
   - Line 104: `console.log` → `logger.log`
   - Line 106: `console.log` → `logger.log`
   - Line 124: `console.log` → `logger.log`

2. **`src/components/ECGViewer/ECGViewerContainer.tsx`** (5 replacements)
   - Line 41: `console.log` → `logger.log`
   - Line 45: `console.log` → `logger.log`
   - Line 59: `console.log` → `logger.log`
   - Line 65: `console.log` → `logger.log`
   - Line 85: `console.log` → `logger.log`

3. **`src/components/ECGViewer/ECGDisplayGrid.tsx`** (1 replacement)
   - Line 77: `console.log` → `logger.log`

4. **`src/components/PatientCard/PatientCardWaveform.tsx`** (5 replacements)
   - Line 34: `console.log` → `logger.log`
   - Line 40: `console.log` → `logger.log`
   - Line 49: `console.log` → `logger.log`
   - Line 52: `console.log` → `logger.log`
   - Line 64: `console.log` → `logger.log`

#### Required Import:
```typescript
import { logger } from '../utils/logger'; // or correct relative path
```

#### Why logger.log?
- Already exists at `src/utils/logger.ts`
- HIPAA compliant - no PHI in production logs
- Only logs in development mode (process.env.NODE_ENV === 'development')
- Production builds have clean console
- Still available for debugging in dev mode

#### Testing Steps:
1. **Dev mode test:**
   ```bash
   npm start
   # Verify logs still appear in console
   # Check for proper [Component] prefixes
   ```

2. **Production build test:**
   ```bash
   npm run build
   npm run serve # or appropriate serve command
   # Verify console is clean
   # Verify no waveform logs appear
   ```

3. **Performance verification:**
   - Open Chrome DevTools Performance tab
   - Record 10 seconds of 12-lead ECG viewing
   - Verify no console-related jank
   - Compare before/after CPU usage

---

### FIX #2: Remove Vestigial Dropdown (P3)
**Severity:** MINOR - UX confusion
**Impact:** Users might think they can change leads
**Effort:** 15 minutes

#### File to Modify:
**`src/components/ECGViewer.tsx`**

#### Current Code (Lines 120-149):
```typescript
<select
  className="text-sm border rounded px-2 py-1"
  defaultValue={isECGMode ? 'II' : 'C3-C4'}
>
  {isECGMode ? (
    <>
      <option value="I">Lead I</option>
      <option value="II">Lead II</option>
      <option value="III">Lead III</option>
      <option value="aVR">aVR</option>
      <option value="aVL">aVL</option>
      <option value="aVF">aVF</option>
      <option value="V1">V1</option>
      <option value="V2">V2</option>
      <option value="V3">V3</option>
      <option value="V4">V4</option>
      <option value="V5">V5</option>
      <option value="V6">V6</option>
    </>
  ) : (
    <>
      <option value="F3-F4">F3-F4</option>
      <option value="C3-C4">C3-C4</option>
      <option value="P3-P4">P3-P4</option>
      <option value="O1-O2">O1-O2</option>
      <option value="T3-T4">T3-T4</option>
      <option value="T5-T6">T5-T6</option>
    </>
  )}
</select>
```

#### Replacement Code:
```typescript
{/* Standard lead label - embedded viewer shows Lead II (ECG) or F3 (EEG) */}
<span className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded border">
  {isECGMode ? 'Lead II' : 'F3'} <span className="text-gray-400">(Standard)</span>
</span>
```

#### Clinical Justification:
- **Embedded viewer purpose:** Quick review, NOT detailed analysis
- **Standard leads are correct:** Lead II for rhythm monitoring, F3 for frontal EEG
- **Fullscreen viewer:** Users who need lead selection should use "Full View" button
- **UX principle:** Don't show controls that don't work

#### Testing Steps:
1. View patient detail page
2. Verify ECG mode shows "Lead II (Standard)"
3. Verify EEG mode shows "F3 (Standard)"
4. Verify "Full View" button still navigates to fullscreen viewer
5. Verify waveform still displays correctly (hardcoded lead selection unchanged)

---

### FIX #3: Memory Profiling (P5)
**Severity:** UNKNOWN - Needs investigation
**Status:** DO NOT FIX PREEMPTIVELY

#### Current Code Pattern:
```typescript
// useECGViewer.ts:139 - Spread operator creates new array every update
dataBufferRef.current[0] = [
  ...dataBufferRef.current[0],  // Copy existing array
  ...limb.lead1                  // Add new samples
].slice(-maxBufferSize);          // Trim to size

// Runs for 21 channels at 2 updates/second = 42 array allocations/sec
```

#### Theoretical Concern:
- High GC pressure from constant array reallocation
- Could cause frame drops or jank

#### Counter-Evidence:
- Modern JS engines optimize array operations
- Total data size is small (~420KB)
- **No performance issues have been reported**

#### Action Plan:
1. **Do NOT implement changes now** - No reported issues
2. **Monitor in production** - Add performance metrics if deployed
3. **Profile only if issues arise:**
   - Use Chrome DevTools Memory Profiler
   - Record heap snapshots during 12-lead viewing
   - Check for excessive GC activity
4. **Alternative approach (if needed):**
   - Circular buffer implementation (zero allocations)
   - More complex but more performant
   - Only implement if profiling confirms issue

**Estimated Effort (if issues found):** 4-8 hours

---

## 🚀 IMPLEMENTATION SEQUENCE

### Step 1: Console Logging Cleanup (1 hour)
1. Add `logger` import to 4 files
2. Replace 17 `console.log` calls with `logger.log`
3. Test in dev mode (verify logs appear)
4. Test production build (verify logs suppressed)

### Step 2: Remove Vestigial Dropdown (15 min)
1. Delete lines 120-149 in ECGViewer.tsx
2. Add standard lead label
3. Test ECG/EEG mode switching
4. Verify "Full View" still works

### Step 3: Memory Monitoring (ongoing)
1. Do NOT implement changes
2. Monitor for performance issues in production
3. Profile only if jank/slowness reported

**Total Active Work:** 1 hour 15 minutes

---

## 📊 TESTING CHECKLIST

### After Console Logging Fix:
- [ ] Dev mode: Logs still appear
- [ ] Dev mode: Log prefixes correct ([ComponentName])
- [ ] Production build: Console is clean
- [ ] Production build: No waveform logs
- [ ] No performance regression in dev mode

### After Dropdown Removal:
- [ ] ECG mode shows "Lead II (Standard)"
- [ ] EEG mode shows "F3 (Standard)"
- [ ] ECG/EEG toggle buttons work
- [ ] Waveform displays correctly (Lead II for ECG, F3 for EEG)
- [ ] "Full View" button navigates to fullscreen viewer
- [ ] No console errors

### Error Boundary (Already Complete):
- [ ] Inject malformed WebSocket data
- [ ] Verify error boundary catches exception
- [ ] Verify fallback UI displays
- [ ] Verify retry button works
- [ ] Verify rest of dashboard functional
- [ ] Test in both PatientCardWaveform and fullscreen ECGViewer

---

## 📁 FILES REQUIRING CHANGES

### To Modify (6 files):
1. ✅ `src/components/ErrorBoundary.tsx` - ALREADY CREATED
2. ✅ `src/components/PatientCard/PatientCardWaveform.tsx` - ALREADY WRAPPED
3. ⏳ `src/components/ECGViewer.tsx` - Remove dropdown (lines 120-149)
4. ⏳ `src/components/ECGViewer/ECGWaveformCanvas.tsx` - Replace 6 console.log
5. ⏳ `src/components/ECGViewer/ECGViewerContainer.tsx` - Replace 5 console.log
6. ⏳ `src/components/ECGViewer/ECGDisplayGrid.tsx` - Replace 1 console.log

### Existing Resources (no changes needed):
- ✅ `src/utils/logger.ts` - Already exists and works correctly

---

## 🎯 SUMMARY

**Completed:**
- ✅ P0: Error Boundaries (2 hours) - DONE
- ✅ Medical-safe fallback UI implemented
- ✅ WaveformErrorBoundary for specialized handling

**Remaining:**
- ⏳ P2: Console Logging (1 hour) - 17 replacements across 4 files
- ⏳ P3: Vestigial Dropdown (15 min) - Remove 30 lines, add label
- 🔍 P5: Memory Profiling (TBD) - Monitor only, don't fix preemptively

**Total Remaining Effort:** 1 hour 15 minutes of focused work

**Risk Level:** LOW - All changes are straightforward refactoring

---

## ✅ READY TO PROCEED?

**Question for user:**
Should I proceed with:
1. **P2: Console Logging Cleanup** (1 hour)?
2. **P3: Dropdown Removal** (15 min)?
3. Both in sequence?

All changes are low-risk and follow established patterns in the codebase.

---

**End of Status & Plan**
