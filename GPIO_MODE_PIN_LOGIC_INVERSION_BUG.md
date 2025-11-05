# GPIO Mode Pin Logic Inversion Issue

**Date:** 2025-11-04
**Issue Type:** Logic inversion bug
**Severity:** Low (confusing but functional)
**Status:** Awaiting decision on fix

---

## Issue Description

The ESP32 mode selection GPIO logic is **inverted** from what would be expected with `INPUT_PULLUP` configuration.

---

## Current Behavior (INVERTED)

**GPIO Configuration:**
```cpp
pinMode(MODE_SELECT_PIN, INPUT_PULLUP);  // Line 983
```

**Mode Detection Logic:**
```cpp
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;  // Lines 1853, 1968
```

**Current Mapping:**
```
Pin State → Mode Selected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HIGH (floating, pulled up) → ECG Mode ❌
LOW (grounded)              → EEG Mode ❌
```

**Console Output:** (Line 986)
```
"HIGH=ECG, LOW=EEG"
```

---

## Expected Behavior (CORRECT)

With `INPUT_PULLUP`, the **intuitive logic** would be:

```
Pin State → Mode Selected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HIGH (floating, pulled up) → EEG Mode ✅ (default, no jumper needed)
LOW (grounded)              → ECG Mode ✅ (jumper to ground for cardiac monitoring)
```

**Rationale:**
1. **Default to EEG** - More advanced/specialized monitoring mode
2. **Ground for ECG** - More common use case, easy to jumper
3. **Standard embedded practice** - Active state (grounded) selects primary function

---

## Why This Is Confusing

### Problem 1: Counter-Intuitive Default
- With nothing connected, you get **ECG mode** (cardiac monitoring)
- User might expect **EEG mode** as default (since it's pulled HIGH)
- Requires jumper wire to ground for the "default" state

### Problem 2: Conflicts with Pull-Up Purpose
- `INPUT_PULLUP` typically means "default HIGH = inactive/default state"
- Current logic treats HIGH as "active ECG mode"
- This inverts the typical embedded systems convention

### Problem 3: Documentation Says Opposite
The `GPIO_AND_EEG_SIMULATOR_ANALYSIS.md` document stated:
```
GPIO State → Mode Selected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HIGH (1)  →  EEG Mode (brain monitoring)
LOW (0)   →  ECG Mode (heart monitoring)
```

But the code actually does the opposite!

---

## Current Code Locations

### Setup (Line 983-986)
```cpp
pinMode(MODE_SELECT_PIN, INPUT_PULLUP);
bool initialMode = digitalRead(MODE_SELECT_PIN) == HIGH;
Serial.println("🔌 GPIO " + String(MODE_SELECT_PIN) + " configured for mode selection");
Serial.println("   Current mode: " + String(initialMode ? "ECG" : "EEG") + " (HIGH=ECG, LOW=EEG)");
```

### Vitals Streaming (Line 1853-1854)
```cpp
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
doc["mode"] = isECGMode ? "ecg" : "eeg";
```

### Waveform Streaming (Line 1968-1974)
```cpp
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
doc["mode"] = isECGMode ? "ecg" : "eeg";

if (isECGMode) {
  // Generate ECG waveforms
} else {
  // Generate EEG waveforms
}
```

---

## Two Possible Fixes

### Option 1: Fix the Logic (Recommended)

**Change the comparison from HIGH to LOW:**

```cpp
// Current (WRONG):
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;

// Fixed (CORRECT):
bool isECGMode = digitalRead(MODE_SELECT_PIN) == LOW;
```

**Result:**
- Floating pin (HIGH) → EEG mode (default)
- Grounded pin (LOW) → ECG mode (jumper to ground)

**Files to change:**
1. Line 984: `bool initialMode = digitalRead(MODE_SELECT_PIN) == LOW;`
2. Line 986: `"(LOW=ECG, HIGH=EEG)"`
3. Line 1853: `bool isECGMode = digitalRead(MODE_SELECT_PIN) == LOW;`
4. Line 1968: `bool isECGMode = digitalRead(MODE_SELECT_PIN) == LOW;`

**Pros:**
- Intuitive behavior (default = EEG)
- Matches standard embedded conventions
- Pull-up serves its intended purpose

**Cons:**
- Existing hardware setups would need to swap jumper logic
- If users expect ECG as default, this breaks that

---

### Option 2: Fix the Documentation Only

**Keep the code as-is, but update documentation to match reality:**

```
GPIO State → Mode Selected (ACTUAL CURRENT BEHAVIOR)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HIGH (floating, pulled up) → ECG Mode (default)
LOW (grounded)              → EEG Mode (jumper to ground)
```

**Pros:**
- No code changes needed
- Existing hardware setups continue to work
- If ECG is more common use case, this might be intentional

**Cons:**
- Counter-intuitive (why use INPUT_PULLUP if HIGH means "active ECG"?)
- Inverted from typical embedded systems conventions

---

### Option 3: Change to INPUT_PULLDOWN (Alternative)

**Change pull direction to match current logic:**

```cpp
// Current:
pinMode(MODE_SELECT_PIN, INPUT_PULLUP);
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;

// Alternative:
pinMode(MODE_SELECT_PIN, INPUT_PULLDOWN);
bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
```

**Result:**
- Floating pin (LOW) → EEG mode (default)
- Pulled-high pin (HIGH) → ECG mode (3.3V jumper)

**Pros:**
- Logic stays the same
- Default behavior changes to EEG (floating = LOW = EEG)

**Cons:**
- ESP32 pull-down resistors are weaker than pull-ups (~40kΩ vs ~45kΩ)
- More susceptible to noise
- Requires VCC jumper instead of GND jumper (less common)

---

## Questions to Answer Before Fixing

1. **What should the default mode be?**
   - ECG (cardiac monitoring - more common?)
   - EEG (brain monitoring - more advanced?)

2. **What hardware setup do you prefer?**
   - Jumper to GND for ECG (common practice)
   - Jumper to GND for EEG (current behavior)

3. **Do you have existing hardware?**
   - If yes, changing logic would break existing setups
   - If no, we can fix it properly now

---

## My Recommendation

**Fix Option 1** - Change the logic to match `INPUT_PULLUP` convention:

```cpp
bool isECGMode = digitalRead(MODE_SELECT_PIN) == LOW;
```

**Reasoning:**
1. **Standard practice:** Pull-up resistors default to inactive/high-level mode
2. **EEG as default:** More sophisticated feature (brain monitoring)
3. **Easy ECG activation:** Jump to ground for common cardiac monitoring
4. **Future-proof:** Matches what most embedded engineers would expect

---

## Testing After Fix

If we apply Option 1, verify:

1. **No jumper (floating):** Should display EEG waveforms (Fp1, Fp2, F3, F4, C3, C4, O1, O2)
2. **GPIO 15 to GND:** Should display ECG waveforms (Lead I, II, III, aVR, aVL, aVF, V1-V6)

Check Serial output:
```
🔌 GPIO 15 configured for mode selection
   Current mode: EEG (LOW=ECG, HIGH=EEG)
```

And MQTT messages:
```json
{
  "mode": "eeg"  // When floating (no jumper)
}
```

---

## Decision Needed

**What would you like to do?**

1. ✅ **Fix the logic** (HIGH=EEG, LOW=ECG) - Recommended
2. ❌ **Keep current behavior** (HIGH=ECG, LOW=EEG) - Update docs only
3. 🤔 **Change to INPUT_PULLDOWN** (alternative approach)

Please confirm your preference and I'll implement the fix immediately.
