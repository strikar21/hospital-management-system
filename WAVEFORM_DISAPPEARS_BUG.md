# CRITICAL BUG: Waveform Disappears After Few Seconds

## User Report

**Observed:** Waveform displays initially with calibration pulse, then after a few seconds the waveform completely disappears, leaving only blank grid.

**Expected:** Waveform should continuously scroll across screen like a real ECG machine.

---

## Root Cause #1: Infinite Scroll Translation ❌

### The Bug: [ECGWaveformCanvas.tsx:98-102](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L98-L102)

```typescript
const samplesToRender = data.slice(-800); // Last 800 samples
scrollOffset.current += mmToPixels(speed) * deltaTime; // ❌ KEEPS INCREASING FOREVER!

ctx.save();
ctx.translate(-scrollOffset.current, 0); // ❌ TRANSLATES WAVEFORM OFF-SCREEN!
renderWaveformCanvas(samplesToRender, ctx, width, height, isECGMode, true, leadColor);
ctx.restore();
```

**What happens:**
1. Initial render: `scrollOffset = 0`, waveform visible ✅
2. After 1 second: `scrollOffset = mmToPixels(25)` = ~100 pixels, waveform shifted left 100px
3. After 5 seconds: `scrollOffset = 500 pixels`, waveform shifted left 500px
4. After 10 seconds: `scrollOffset = 1000 pixels`, **waveform completely off-screen** ❌
5. After 30 seconds: `scrollOffset = 3000 pixels`, waveform is **3 screen widths off to the left** ❌

**The waveform never wraps around or resets!** It just scrolls infinitely left until it disappears.

---

## Root Cause #2: No Data from ESP32 Watch ❌

### Possible Issue: No Real Waveform Data Arriving

**From:** [useECGViewer.ts:104-247](hospital-display-app/src/hooks/useECGViewer.ts#L104-L247)

The hook subscribes to WebSocket for waveform data, but if:
- ❌ Watch is not connected
- ❌ Watch is not sending data
- ❌ Backend is not forwarding data
- ❌ WebSocket subscription fails

Then the calibration pulse (200 samples) is the **only data** in the buffer.

**After a few seconds:**
1. User opens ECG viewer
2. Calibration pulse added: 200 samples (100 spacer + 100 pulse)
3. No new data arrives from watch
4. Scroll offset keeps increasing
5. After ~5 seconds, the 200-sample calibration pulse has scrolled off-screen
6. Buffer still has 200 samples, but they're all translated off-screen
7. **Result:** Blank screen with only grid visible

---

## Root Cause #3: Calibration Pulse Wrong Duration ❌

### The Bug: [ECGViewerContainer.tsx:51-57](hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx#L51-L57)

```typescript
const samplesPerSecond = 500;
const pulseDuration = 0.2; // 200ms pulse
const totalPulseSamples = Math.floor(samplesPerSecond * pulseDuration); // 100 samples
const pulseADC = 8388608 + (1 * 100000); // 1mV in ADC units
const calibrationPulse = new Array(totalPulseSamples).fill(pulseADC);
const spacerSamples = new Array(100).fill(8388608); // 0.2s baseline
```

**Total calibration data:** 200 samples = 0.4 seconds at 500 Hz

**Scroll speed:** 25mm/s = ~100 pixels/second (at 96 DPI)

**Time until calibration disappears:** 200 samples / 500 Hz = 0.4 seconds of data

**At scroll speed of 100 px/s:**
- Canvas width: ~1600 pixels (fullscreen)
- Time to scroll 1600 pixels: 1600 / 100 = **16 seconds**
- But calibration is only 0.4 seconds wide!
- After ~1 second of scrolling, calibration pulse is already off-screen ❌

---

## Multiple Compounding Bugs

### Bug Summary:

1. **Infinite scroll translation** - `scrollOffset` never resets, waveform scrolls off forever
2. **No new data** - If watch isn't sending data, only calibration pulse exists (200 samples)
3. **Calibration too short** - 0.4 seconds of data scrolls off-screen in ~5 seconds
4. **Wrong scaling** - Horizontal stretch makes it worse (discussed in CALIBRATION_PULSE_SCALING_BUG.md)

**Result:** User sees calibration pulse for a few seconds, then it scrolls off-screen and never comes back.

---

## How Real ECG Machines Handle This

### Traditional Paper ECG:
- Paper continuously feeds at 25mm/s
- Pen draws waveform on paper
- Paper keeps moving forever
- **No scrolling** - paper is infinite

### Digital ICU Monitors:
- **Fixed time window:** Show last 6-10 seconds
- **No scrolling:** Waveform updates in place (sweep mode)
- **OR circular buffer:** Old waveform erased, new data drawn at same position
- **Never translates off-screen**

### Correct Approach (Sweep Mode):

**Philips IntelliVue, GE Solar style:**
1. Show fixed 8-second window on screen
2. Red sweep line moves left-to-right at 25mm/s
3. As sweep line passes, **erase old data** behind it
4. Draw new data where sweep line was
5. When sweep reaches right edge, **wrap to left** and continue
6. **Result:** Continuous scrolling appearance without actually translating

---

## The Correct Implementation

### Option 1: Sweep Mode (Recommended) ✅

**How it works:**
- Canvas shows fixed time window (e.g., 8 seconds = 4000 samples at 500 Hz)
- Red sweep line moves at 25mm/s (paper speed)
- Waveform is drawn at sweep line position
- Old waveform behind sweep is erased
- When sweep reaches right edge, reset to left edge

**Implementation:**

```typescript
// Calculate sweep position (0 to canvas width, then wrap)
const pixelsPerSecond = mmToPixels(25); // 25mm/s paper speed
const sweepX = (scrollOffset.current % width); // Wrap at canvas width
scrollOffset.current += pixelsPerSecond * deltaTime;

// Draw waveform at sweep position (not translated off-screen!)
const samplesVisible = (width / pixelsPerSecond) * 500; // Samples that fit on screen
const samplesToRender = data.slice(-samplesVisible);

// NO TRANSLATION! Draw waveform from 0 to width
renderWaveformCanvas(samplesToRender, ctx, width, height, isECGMode, true, leadColor);

// Draw sweep line at current position
ctx.strokeStyle = '#FF0000';
ctx.lineWidth = 2;
ctx.beginPath();
ctx.moveTo(sweepX, 0);
ctx.lineTo(sweepX, height);
ctx.stroke();

// Erase old waveform just ahead of sweep line (creates erasing effect)
const eraseWidth = pixelsPerSecond * deltaTime * 2; // Erase slightly ahead
ctx.fillStyle = '#000000';
ctx.fillRect(sweepX, 0, eraseWidth, height);
```

**Pros:**
- ✅ Waveform never disappears
- ✅ Looks exactly like real ICU monitor
- ✅ No infinite translation bug
- ✅ Works with any amount of data

**Cons:**
- ⚠️ Slightly more complex logic

### Option 2: Scrolling Mode (Current, but fix translation) ⚠️

**Fix the infinite translation:**

```typescript
// Calculate how wide the waveform actually is in pixels
const pixelsPerSample = mmToPixels(25) / 500; // 25mm/s ÷ 500 Hz
const waveformWidth = data.length * pixelsPerSample;

// Wrap scroll offset when it exceeds waveform width
scrollOffset.current += mmToPixels(speed) * deltaTime;
if (scrollOffset.current > waveformWidth) {
  scrollOffset.current = scrollOffset.current % waveformWidth; // Wrap around
}

// Translate waveform (but it will wrap now)
ctx.save();
ctx.translate(-scrollOffset.current, 0);
renderWaveformCanvas(data, ctx, width + waveformWidth, height, isECGMode, true, leadColor);
ctx.restore();
```

**Pros:**
- ✅ Fixes infinite translation
- ✅ Waveform wraps around

**Cons:**
- ❌ Requires enough data in buffer
- ❌ If only calibration pulse (200 samples), will loop every 0.4 seconds (jarring)
- ❌ Doesn't match real ECG behavior

---

## Root Cause of "No Real Data"

### Why might watch data not arrive?

**Possible causes:**

1. **Watch not assigned:** `patient.assignedDeviceId` is null
   - Code: [useECGViewer.ts:94-99](hospital-display-app/src/hooks/useECGViewer.ts#L94-L99)
   - If no device assigned, WebSocket never subscribes

2. **Watch not connected:** Device is assigned but not actively streaming
   - ESP32 may be offline, battery dead, or not provisioned

3. **WebSocket not broadcasting:** Backend receiving data but not forwarding via WebSocket
   - Check backend logs for waveform messages

4. **Wrong patient ID:** WebSocket filtering by wrong patient ID
   - Code: [useECGViewer.ts:106](hospital-display-app/src/hooks/useECGViewer.ts#L106)
   - `if (message.patientId !== patient.id) return;`

5. **Data format mismatch:** Backend sending data in wrong format
   - Expected: `message.waveform.ecgWaveform.limb.lead1` (array)
   - If format is wrong, data won't be processed

### Diagnostic Steps:

1. Check if device is assigned:
```typescript
console.log('Device assigned:', patient.assignedDeviceId);
```

2. Check WebSocket messages arriving:
```typescript
// In useECGViewer.ts subscription
console.log('WebSocket message:', message);
```

3. Check buffer contents:
```typescript
// In ECGWaveformCanvas
console.log('Buffer length:', data.length);
console.log('Buffer samples:', data.slice(0, 10));
```

4. Check ESP32 logs:
- Is watch sending data over MQTT?
- Are waveform messages being published?

5. Check backend logs:
- Is backend receiving MQTT waveform messages?
- Is backend broadcasting via WebSocket?

---

## Impact

### Medical Consequences:

- ❌ **No continuous monitoring:** Waveform disappears after seconds
- ❌ **Unusable for clinical monitoring:** Can't track patient status
- ❌ **Arrhythmia detection impossible:** No waveform to analyze
- ❌ **Defeats entire purpose:** ECG viewer that doesn't show ECG

**System is currently non-functional for waveform monitoring.**

---

## Recommended Fix Priority

### CRITICAL - Must fix immediately:

1. **✅ Fix infinite scroll translation** (Option 1: Sweep mode) - HIGHEST PRIORITY
   - Estimated time: 3-4 hours
   - Implement proper sweep line with circular buffer

2. **✅ Diagnose why no real data** - HIGHEST PRIORITY
   - Check device assignment
   - Check WebSocket subscription
   - Check ESP32 streaming
   - Estimated time: 1-2 hours investigation

3. **✅ Fix scaling bugs** (see CALIBRATION_PULSE_SCALING_BUG.md) - HIGH PRIORITY
   - Ensures waveform renders at correct medical scale
   - Estimated time: 2-3 hours

### Total estimated fix time: 6-9 hours

---

## Testing Verification

### After fixing, verify:

1. ✅ Waveform visible continuously (never disappears)
2. ✅ Sweep line moves smoothly at 25mm/s
3. ✅ Works with only calibration pulse (no real data)
4. ✅ Works with real streaming data from watch
5. ✅ Waveform wraps around at screen edge
6. ✅ No jarring jumps or flicker
7. ✅ Grid stays visible behind waveform
8. ✅ Pause button freezes waveform (stops sweep)

---

## Conclusion

**Current state:**
- ❌ Waveform disappears after ~5 seconds due to infinite scroll translation
- ❌ Calibration pulse scrolls off-screen and never returns
- ❌ No real data from watch (possible separate issue)
- ❌ **System is non-functional for ECG monitoring**

**Required fixes:**
1. ✅ Implement proper sweep mode (like real ICU monitors)
2. ✅ Diagnose and fix data flow from ESP32 → Backend → Frontend
3. ✅ Fix waveform scaling to match grid (separate bug)

**This bug makes the ECG viewer completely unusable - it must be fixed before any clinical use.**

---

**Reference Files:**
- Scroll translation bug: [ECGWaveformCanvas.tsx:98-102](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L98-L102)
- Data subscription: [useECGViewer.ts:92-247](hospital-display-app/src/hooks/useECGViewer.ts#L92-L247)
- Calibration pulse: [ECGViewerContainer.tsx:38-72](hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx#L38-L72)
