# GPIO Mode Pin Response Analysis

## Your Question
> "but other stuff kept changing no? except this one code? because i'd not want to reboot watch each time i put a new cable"

## What Actually Responds to GPIO Pin Changes (WITHOUT Rebooting)

### ✅ Things That Work Real-Time (Check GPIO Every Time):

1. **Vitals Messages (Line 1880):**
   ```cpp
   void sendVitals() {
     bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
     doc["mode"] = isECGMode ? "ecg" : "eeg";
   }
   ```
   - **Reads GPIO pin every time vitals are sent**
   - Mode field in vitals messages updates instantly
   - NO reboot needed

2. **Waveform Messages (Line 1995):**
   ```cpp
   void sendWaveformStream() {
     bool isECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
     doc["mode"] = isECGMode ? "ecg" : "eeg";
   }
   ```
   - **Reads GPIO pin every time waveforms are sent**
   - Mode field in waveform messages updates instantly
   - NO reboot needed

### ❌ Thing That Was BROKEN (Only Read Once at Boot):

3. **Simulator Mode (Line 1071 - OLD CODE):**
   ```cpp
   void setup() {
     bool initialECGMode = digitalRead(MODE_SELECT_PIN) == HIGH;
     simulator.setMode(initialECGMode ? MODE_ECG : MODE_EEG);
     // ❌ NEVER CHECKED AGAIN - stuck in this mode forever
   }
   ```
   - **Read GPIO pin ONCE at boot**
   - Simulator stuck generating same waveform type forever
   - REQUIRED reboot to change

### ✅ Now Fixed (Line 1124 - NEW CODE):

4. **Simulator Mode (Line 1124 - NEW CODE):**
   ```cpp
   void loop() {
     bool currentMode = digitalRead(MODE_SELECT_PIN) == HIGH;
     simulator.setMode(currentMode ? MODE_ECG : MODE_EEG);
     // ✅ NOW CHECKED EVERY LOOP - updates in real-time
   }
   ```
   - **Reads GPIO pin every loop iteration**
   - Simulator updates mode before generating new samples
   - NO reboot needed

## The Mismatch Explained

### Before the Fix:

| Component | GPIO Check Frequency | Result |
|-----------|---------------------|---------|
| Vitals messages | ✅ Every send | Mode field updates instantly |
| Waveform messages | ✅ Every send | Mode field updates instantly |
| Simulator | ❌ Once at boot | Stuck generating wrong waveforms |

**Result:** Messages said "mode: ecg" but simulator generated EEG waveforms (or vice versa)

### After the Fix:

| Component | GPIO Check Frequency | Result |
|-----------|---------------------|---------|
| Vitals messages | ✅ Every send | Mode field updates instantly |
| Waveform messages | ✅ Every send | Mode field updates instantly |
| Simulator | ✅ Every loop | Generates correct waveforms instantly |

**Result:** Everything in sync - no reboot needed to change modes!

## Why You Saw Changes Without Rebooting

You were seeing the **message mode field** changing (from lines 1880 and 1995) because those always read the GPIO pin in real-time.

But the **actual waveform data** wasn't changing (from line 1071) because the simulator mode was stuck at boot-time value.

So you'd see:
- Frontend shows "EEG" label (from message "mode": "eeg")
- But displays ECG waveform shapes (from simulator stuck in ECG mode)

## Summary

**Before Fix:** Only the mode LABEL changed without reboot (because messages check GPIO). The actual WAVEFORMS didn't change (because simulator was stuck at boot mode).

**After Fix:** Both mode LABEL and WAVEFORMS change without reboot (everything checks GPIO in real-time).

**You don't need to reboot to change modes anymore!** Just change GPIO pin and everything updates instantly.
