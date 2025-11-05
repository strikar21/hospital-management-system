# Waveform Display Issues - Root Cause Analysis

## User Requirements (Clearly Stated)
1. **Canvas width not being used properly** - waveform appears horizontally compressed
2. **Pre-filled data on view change** - should start with BLANK canvas, not show old cached data

## Issue 1: Pre-Filled Data (Cache Loading)

### ROOT CAUSE CONFIRMED
[useECGViewer.ts:60-82](../hospital-display-app/src/hooks/useECGViewer.ts#L60-L82) - Loads cached waveform data when opening ECG viewer!

```typescript
// Load cached waveform data on mount or mode change
useEffect(() => {
  const loadCachedWaveform = async () => {
    const cached = await waveformCacheService.getWaveform(
      patient.id,
      isECGMode ? 'ecg' : 'eeg'
    );

    if (cached && cached.length > 0) {
      dataBufferRef.current = cached;  // ← PRE-FILLS with old data!
      setCacheLoaded(true);
      logger.log(`✅ Loaded ${cached.length} leads from waveform cache`);
    } else {
      // No cache - initialize empty buffers
      dataBufferRef.current = Array(leads.length).fill(null).map(() => []);
      setCacheLoaded(true);
    }
  };

  setCacheLoaded(false);
  loadCachedWaveform();
}, [patient.id, isECGMode, leads.length]);
```

### Why This Happens
The cache service stores waveform data in browser localStorage/sessionStorage. When you:
1. Open ECG viewer
2. Switch between ECG/EEG modes
3. Change layouts
4. Reload page

→ It **loads OLD cached data** instead of starting fresh!

### The Fix
**Option A:** Disable cache loading entirely (always start blank)
**Option B:** Clear cache on view open (start blank each time)
**Option C:** Keep cache but show loading indicator until first live data arrives

User wants: **BLANK CANVAS on view change**

## Issue 2: Horizontal Compression (Canvas Width Not Used)

### Actual Canvas Width Calculation
[ECGWaveformCanvas.tsx:85](../hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L85):
```typescript
const width = canvas.clientWidth;  // ← Dynamically gets browser window width
```

User's current window: **1313 pixels wide**

### Waveform Rendering Calculation
[ECGWaveformCanvas.tsx:106-108](../hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L106-L108):
```typescript
const pixelsPerSecond = mmToPixels(PAPER_SPEED_MM_PER_S); // 25mm/s at detected DPI
const pixelsPerSample = pixelsPerSecond / SAMPLE_RATE_HZ; // Fixed: 25mm/s ÷ 500Hz
const samplesVisible = Math.floor(width / pixelsPerSample);
```

### Console Log Evidence (from screenshot timestamp 11:19:53)
```
pixelsPerSecond=132.26 px/s
pixelsPerSample=0.2645 px/sample
samplesVisible=4963 samples
canvas width=1313px
```

**WAIT - THIS IS WRONG!**

Looking at browser console from previous session:
```
pixelsPerSample=0.1890
```

But the screenshot shows `pixelsPerSample=0.2645`!

### Actual DPI Detection
[medicalWaveformUtils.ts:45-79](../hospital-display-app/src/utils/medicalWaveformUtils.ts#L45-L79):
```typescript
export function getScreenDPI(): number {
  // ... creates 1-inch div, measures offsetWidth
  const dpi = div.offsetWidth;
  cachedDPI = dpi;
  console.log(`✅ DPI detected: ${dpi} (cached for future use)`);
  return dpi;
}
```

**DPI = 141** (from browser console: `1mm = 5.55 pixels, 5mm big square = 27.76 pixels`)

### Medical Standard Calculations
- **Paper Speed:** 25mm/s (medical standard)
- **DPI:** 141 pixels/inch
- **1mm = 141/25.4 = 5.55 pixels**
- **25mm/s = 25 × 5.55 = 138.75 pixels/second**
- **Sample Rate:** 500Hz (500 samples/second)
- **pixelsPerSample = 138.75 / 500 = 0.2775 pixels/sample**

### How Many Samples Fit on Screen?
- **Canvas Width:** 1313 pixels
- **pixelsPerSample:** 0.2775 px/sample
- **samplesVisible = 1313 / 0.2775 = 4730 samples**
- **At 500Hz, that's 4730 / 500 = 9.46 seconds of data**

### Why It Looks Compressed

**HYPOTHESIS:** The waveform is being rendered correctly at medical-grade 25mm/s speed, but the user expects SLOWER sweep speed (more stretched out horizontally).

**Medical Standard:** 25mm/s is the STANDARD ECG paper speed
**User Expectation:** Possibly wants SLOWER speed like 10mm/s or 5mm/s for more horizontal stretch

**OR:** The buffer contains MORE than 9.46 seconds of data, so older samples are being compressed/skipped

Let me check the actual buffer size:

### Current Buffer Management
[useECGViewer.ts:121](../hospital-display-app/src/hooks/useECGViewer.ts#L121):
```typescript
const maxBufferSize = (waveformData.sampleRate || 250) * 10; // 10 seconds
```

**Buffer holds:** 500 samples/sec × 10 sec = **5000 samples maximum**

### The Rendering Logic
[ECGWaveformCanvas.tsx:138-208](../hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L138-L208):

**Phase 1 (Growing):** When `data.length <= samplesVisible` (0 to 4730 samples)
- Renders from RIGHT edge, growing leftward
- Uses: `startX = width - (data.length * pixelsPerSample)`
- **THIS WORKS CORRECTLY**

**Phase 2 (Circular Buffer):** When `data.length > samplesVisible` (4730+ samples)
- Splits into two segments (older + newer)
- Uses wrap-around rendering
- **POTENTIAL ISSUE:** Might be compressing too many samples into limited canvas width

### Actual Problem Identified

Looking at the screenshot, the waveform is **VERY densely packed** - appears as a solid green band rather than distinct P-QRS-T waves.

**ROOT CAUSE OPTIONS:**

**A) Too Much Data in Buffer**
- Buffer holds 5000 samples (10 seconds)
- Canvas only shows 4730 samples (9.46 seconds) at medical-grade scale
- Excess 270 samples being compressed/skipped

**B) Medical Scale Too Small**
- 25mm/s is medically correct but visually compressed on a 1313px monitor
- User may want SLOWER sweep (e.g., 10mm/s or 5mm/s) for better visibility

**C) Rendering Bug in Phase 2**
- Circular buffer mode might be rendering ALL 5000 samples squeezed into 4730 sample slots
- Would cause 1.06× horizontal compression

## Recommended Fixes

### Fix 1: Blank Canvas on View Change (User Requirement #2)
**What to change:** [useECGViewer.ts:60-82](../hospital-display-app/src/hooks/useECGViewer.ts#L60-L82)

**Option A - Disable Cache Loading:**
```typescript
// Remove cache loading entirely - always start blank
useEffect(() => {
  dataBufferRef.current = Array(leads.length).fill(null).map(() => []);
  setCacheLoaded(true);
  logger.log(`📭 Initialized empty buffers for ${leads.length} leads`);
}, [patient.id, isECGMode, leads.length]);
```

**Option B - Clear Cache on Mount:**
```typescript
useEffect(() => {
  // Clear cache before opening
  waveformCacheService.clearWaveform(patient.id, isECGMode ? 'ecg' : 'eeg');
  dataBufferRef.current = Array(leads.length).fill(null).map(() => []);
  setCacheLoaded(true);
}, [patient.id, isECGMode, leads.length]);
```

### Fix 2: Canvas Width Usage (User Requirement #1)

**Need More Information from User:**

**Question 1:** Do you want medical-standard 25mm/s sweep speed, or SLOWER sweep (10mm/s, 5mm/s) for more horizontal stretch?

**Question 2:** When the waveform looks "compressed", is it:
- A) Too many samples squeezed horizontally (need slower sweep speed)?
- B) Rendering bug causing data compression?
- C) Amplitude too small vertically (separate issue)?

**Diagnostic Check:**
Let's verify if the rendering is actually using the full canvas width or if there's a bug.

### Additional Findings

**Calibration State (Vestigial Code):**
- [useECGViewer.ts:26](../hospital-display-app/src/hooks/useECGViewer.ts#L26): `showCalibration` state exists
- [useECGViewer.ts:324](../hospital-display-app/src/hooks/useECGViewer.ts#L324): Returns to components
- **BUT:** No canvas component actually uses this state!
- **Conclusion:** This is leftover code that should be removed (calibration comes from ESP32, not frontend)

## Summary

### Confirmed Issues
1. ✅ **Pre-filled data:** Cache loading at [useECGViewer.ts:68](../hospital-display-app/src/hooks/useECGViewer.ts#L68)
2. ⏳ **Horizontal compression:** Need user clarification on whether it's medical-scale expectation or rendering bug

### Questions for User
1. Do you want to DISABLE cache loading entirely (always start blank)?
2. What sweep speed do you expect? 25mm/s (medical standard) or slower (10mm/s, 5mm/s)?
3. Is the "compression" about horizontal density or vertical amplitude?

### Vestigial Code to Remove
- `showCalibration` state and related code (calibration comes from ESP32, not frontend)
