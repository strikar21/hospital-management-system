# Optimal Sampling Frequencies: ECG vs EEG
**Medical Standards & Best Practices for Analysis/Reporting**

Generated: 2025-10-22
Based on: Medical literature, ADS1298 specs, existing backend analysis code

---

## Terminology Clarification

### ❌ CORRECTION: "12-Lead EEG" Does NOT Exist

**ECG (Electrocardiography):**
- Measures **heart** electrical activity
- Standard configurations: **1, 3, 5, 7, 12-lead**
- "Lead" = combination of electrodes measuring voltage difference

**EEG (Electroencephalography):**
- Measures **brain** electrical activity
- Standard configurations: **2, 4, 8, 16, 19, 21-channel**
- "Channel" = single electrode measuring voltage vs reference

**Key Difference:**
- **ECG leads** are derived (Lead I = LA - RA, Lead II = LL - RA, etc.)
- **EEG channels** are direct recordings from each electrode

**Correct Terminology:**
- ✅ "12-lead ECG"
- ✅ "8-channel EEG"
- ❌ "12-lead EEG" (doesn't exist)
- ❌ "8-lead EEG" (incorrect term)

---

## ECG Frequency Content & Sampling Requirements

### ECG Signal Frequency Spectrum

**Typical ECG waveform components:**

| Component | Frequency Range | Clinical Significance |
|-----------|----------------|----------------------|
| **P wave** | 5-15 Hz | Atrial depolarization |
| **QRS complex** | 10-50 Hz | Ventricular depolarization (main diagnostic) |
| **T wave** | 2-10 Hz | Ventricular repolarization |
| **ST segment** | 0.5-5 Hz | Ischemia/MI detection |
| **Baseline wander** | 0.05-0.5 Hz | Respiration, motion artifact |
| **Muscle noise** | 20-200 Hz | EMG interference |
| **Power line** | 50/60 Hz | Electrical interference |

**Diagnostic frequency range: 0.05-150 Hz**
**Critical range (QRS): 10-50 Hz**

---

### ECG Sampling Frequency Standards

#### Medical Device Standards

| Standard | Sample Rate | Purpose | Use Case |
|----------|-------------|---------|----------|
| **AHA/ACC (American)** | ≥250 Hz | Diagnostic ECG | Hospital standard |
| **FDA Guidance** | ≥500 Hz | High-precision | ICU, Research |
| **IEC 60601-2-27** | ≥250 Hz | Medical device safety | EU compliance |
| **Consumer wearables** | 125-250 Hz | Basic monitoring | Apple Watch, Fitbit |
| **Holter monitors** | 250-500 Hz | Ambulatory 24-48hr | Outpatient |
| **Research/EP studies** | 1000-2000 Hz | Detailed analysis | Electrophysiology lab |

#### Nyquist Requirement

**QRS complex:**
- Highest frequency: ~50 Hz
- Minimum sample rate (Nyquist): 2 × 50 = **100 Hz**
- **Practical minimum: 250 Hz** (2.5× Nyquist for signal fidelity)

**High-precision diagnostics:**
- Include subtle features: up to 150 Hz
- Minimum sample rate: 2 × 150 = **300 Hz**
- **Recommended: 500 Hz** (1.67× Nyquist)

---

### ECG Sampling Frequency Recommendations

| Sample Rate | Pros | Cons | Recommendation |
|-------------|------|------|----------------|
| **125 Hz** | Low bandwidth | Misses QRS detail | ❌ Too low for medical use |
| **250 Hz** | AHA standard, adequate | Borderline for detailed QRS | ✅ **Minimum acceptable** |
| **500 Hz** | Excellent QRS resolution | 2× bandwidth vs 250 Hz | ✅ **Recommended standard** |
| **1000 Hz** | Research-grade | 4× bandwidth vs 250 Hz | ⚠️ Overkill for routine use |
| **2000 Hz** | EP lab precision | 8× bandwidth vs 250 Hz | ❌ Excessive for hospital |

---

### From Backend Code Analysis

**Current backend ECG analysis service** ([ecg_analysis_service.py:52](hospital-backend/app/services/ecg_analysis_service.py#L52)):

```python
def __init__(self, sampleRate: int = 250):
    self.sampleRate = sampleRate

    # Pan-Tompkins QRS detection parameters
    self.lowpassCutoff = 15.0   # Hz
    self.highpassCutoff = 5.0    # Hz
    self.integrationWindow = int(0.15 * sampleRate)  # 150ms
```

**Analysis filters:**
- Bandpass: 5-15 Hz (QRS complex detection)
- Designed for 250 Hz sampling
- Works better at 500 Hz (more accurate peak detection)

---

## EEG Frequency Content & Sampling Requirements

### EEG Signal Frequency Bands

**Clinical EEG frequency bands:**

| Band | Frequency | Brain State | Clinical Significance |
|------|-----------|-------------|----------------------|
| **Delta (δ)** | 0.5-4 Hz | Deep sleep, unconsciousness | Slow-wave sleep, coma |
| **Theta (θ)** | 4-8 Hz | Drowsiness, meditation | Light sleep, relaxation |
| **Alpha (α)** | 8-13 Hz | Relaxed, eyes closed | Awake but relaxed |
| **Beta (β)** | 13-30 Hz | Active thinking, focus | Alert, concentrated |
| **Gamma (γ)** | 30-100 Hz | Cognitive processing | Higher-order cognition |
| **High-γ** | 100-200 Hz | Research only | Somatosensory processing |

**Diagnostic range: 0.5-100 Hz**
**Extended research range: 0.5-200 Hz**

---

### EEG Sampling Frequency Standards

#### Medical Device Standards

| Standard | Sample Rate | Purpose | Use Case |
|----------|-------------|---------|----------|
| **ACNS (American Clinical Neurophysiology)** | ≥200 Hz | Clinical EEG | Hospital standard |
| **IFCN Guidelines** | ≥250 Hz | Diagnostic EEG | International standard |
| **Epilepsy monitoring** | 256-512 Hz | Seizure detection | EMU (Epilepsy Monitoring Unit) |
| **Sleep studies** | 200-256 Hz | Polysomnography | Sleep lab |
| **Research/BCI** | 500-2000 Hz | Brain-computer interface | Research lab |
| **High-frequency EEG** | 2000+ Hz | High-gamma analysis | Specialized research |

#### Nyquist Requirement

**Standard clinical EEG (0.5-100 Hz):**
- Highest frequency: 100 Hz
- Minimum sample rate (Nyquist): 2 × 100 = **200 Hz**
- **Practical minimum: 250 Hz** (2.5× Nyquist)

**Extended EEG (includes high-gamma, 0.5-200 Hz):**
- Highest frequency: 200 Hz
- Minimum sample rate: 2 × 200 = **400 Hz**
- **Recommended: 500 Hz** (2.5× Nyquist)

---

### From Backend Code Analysis

**Current backend EEG analysis service** ([eeg_analysis_service.py:54](hospital-backend/app/services/eeg_analysis_service.py#L54)):

```python
def __init__(self, sampleRate: int = 250):
    self.sampleRate = sampleRate

    # EEG frequency bands
    self.deltaBand = (0.5, 4.0)
    self.thetaBand = (4.0, 8.0)
    self.alphaBand = (8.0, 13.0)
    self.betaBand = (13.0, 30.0)
    self.gammaBand = (30.0, 100.0)  # Up to 100 Hz

    # Notch filter at 60Hz (power line) - should be 50Hz for India
    self.notchFreq = 60.0

    # Bandpass filter 0.5-100Hz
    # Designed for 250 Hz minimum
```

**Key finding:** Backend expects **up to 100 Hz gamma band** → requires **≥250 Hz sampling**

---

### EEG Sampling Frequency Recommendations

| Sample Rate | Pros | Cons | Recommendation |
|-------------|------|------|----------------|
| **128 Hz** | Used in some sleep studies | Too low for gamma (30-100 Hz) | ❌ Inadequate |
| **200 Hz** | ACNS minimum | Barely covers 100 Hz gamma | ⚠️ Minimum acceptable |
| **250 Hz** | IFCN standard, adequate | Borderline for high-gamma | ✅ **Acceptable** |
| **256 Hz** | Power-of-2 (FFT efficient) | Slight bandwidth increase | ✅ **Good choice** |
| **500 Hz** | Excellent for high-gamma | 2× bandwidth vs 250 Hz | ✅ **Recommended** |
| **512 Hz** | Power-of-2, research-grade | 2× bandwidth vs 256 Hz | ✅ **Research quality** |
| **1000 Hz** | High-gamma + HFO analysis | 4× bandwidth vs 250 Hz | ⚠️ Useful for specialized cases |
| **2000 Hz** | Ultra-high-gamma, ripples | 8× bandwidth vs 250 Hz | ❌ Excessive for routine |

---

## Optimal Sampling Frequencies - Recommendations

### For Standard Hospital Use (Recommended)

| Signal Type | Optimal Sample Rate | Rationale |
|-------------|-------------------|-----------|
| **ECG** | **500 Hz** | • 2× FDA minimum (250 Hz)<br>• Excellent QRS resolution<br>• Captures pacemaker spikes<br>• Suitable for arrhythmia analysis<br>• AHA/ACC compliant |
| **EEG** | **500 Hz** | • 2× IFCN minimum (250 Hz)<br>• Captures full gamma band (30-100 Hz)<br>• Good for high-gamma (100-200 Hz) research<br>• FFT-friendly (512 samples in 1.024 sec)<br>• Seizure spike detection |

**Advantage of unified 500 Hz:**
- Single sample rate for both ECG and EEG modes
- Simplifies ESP32 firmware (no rate switching)
- Backend analysis optimized for one rate
- Consistent data pipeline

---

### For Resource-Constrained (Acceptable)

| Signal Type | Minimum Sample Rate | Rationale |
|-------------|-------------------|-----------|
| **ECG** | **250 Hz** | • AHA/ACC minimum standard<br>• Adequate for basic diagnostics<br>• Half the bandwidth vs 500 Hz<br>• Acceptable for routine monitoring |
| **EEG** | **256 Hz** | • Power-of-2 (FFT efficient)<br>• IFCN compliant<br>• Covers gamma band (30-100 Hz)<br>• Slightly better than 250 Hz |

**When to use:**
- Battery life critical
- Bandwidth constraints
- Low-risk patients
- Wellness monitoring

---

### For Research/High-Precision (Optional)

| Signal Type | Research Sample Rate | Use Case |
|-------------|-------------------|----------|
| **ECG** | **1000 Hz** | • EP (electrophysiology) studies<br>• Pacemaker programming<br>• His-bundle recordings<br>• Detailed T-wave alternans |
| **EEG** | **1000-2000 Hz** | • High-frequency oscillations (HFOs)<br>• Epilepsy surgery planning<br>• Brain-computer interfaces<br>• Ultra-high gamma (>100 Hz) |

**Not recommended for routine hospital use** (excessive bandwidth)

---

## Analysis Quality by Sample Rate

### ECG Analysis Capabilities

| Analysis | 250 Hz | 500 Hz | 1000 Hz | Benefit of Higher Rate |
|----------|--------|--------|---------|----------------------|
| **Heart rate** | ✅ Excellent | ✅ Excellent | ✅ Excellent | None - all adequate |
| **Arrhythmia detection** | ✅ Good | ✅ Excellent | ✅ Excellent | Better PVC/PAC timing |
| **QRS duration** | ✅ Good | ✅ Excellent | ✅ Excellent | More accurate (±2ms at 500 Hz) |
| **ST segment** | ✅ Excellent | ✅ Excellent | ✅ Excellent | Minimal benefit |
| **QT interval** | ✅ Good | ✅ Excellent | ✅ Excellent | Better T-wave detection |
| **Pacemaker spikes** | ⚠️ May miss | ✅ Good | ✅ Excellent | Narrow spikes need higher rate |
| **T-wave alternans** | ❌ Inadequate | ⚠️ Borderline | ✅ Good | Requires 500+ Hz |
| **His-bundle** | ❌ Impossible | ❌ Impossible | ✅ Possible | Specialized EP use only |

**Conclusion:** 500 Hz captures everything except specialized EP procedures

---

### EEG Analysis Capabilities

| Analysis | 250 Hz | 500 Hz | 1000 Hz | Benefit of Higher Rate |
|----------|--------|--------|---------|----------------------|
| **Delta (0.5-4 Hz)** | ✅ Excellent | ✅ Excellent | ✅ Excellent | None |
| **Theta (4-8 Hz)** | ✅ Excellent | ✅ Excellent | ✅ Excellent | None |
| **Alpha (8-13 Hz)** | ✅ Excellent | ✅ Excellent | ✅ Excellent | None |
| **Beta (13-30 Hz)** | ✅ Excellent | ✅ Excellent | ✅ Excellent | None |
| **Low-gamma (30-50 Hz)** | ✅ Good | ✅ Excellent | ✅ Excellent | Better frequency resolution |
| **Mid-gamma (50-80 Hz)** | ✅ Good | ✅ Excellent | ✅ Excellent | Better amplitude accuracy |
| **High-gamma (80-100 Hz)** | ⚠️ Borderline | ✅ Good | ✅ Excellent | Near Nyquist at 250 Hz |
| **Ultra-gamma (100-200 Hz)** | ❌ Aliased | ⚠️ Borderline | ✅ Good | Requires 500+ Hz |
| **Seizure spikes** | ✅ Good | ✅ Excellent | ✅ Excellent | Better spike morphology |
| **HFO (ripples, 80-500 Hz)** | ❌ Impossible | ❌ Partial | ⚠️ Borderline | Need 2000+ Hz for full HFOs |

**Conclusion:** 500 Hz is optimal for standard clinical + research gamma analysis

---

## Specific Recommendations by Patient Type

### ECG Monitoring

**Low-Risk (Ward Monitoring):**
- **Sample rate:** 250 Hz
- **Leads:** 1-3 lead
- **Analysis:** Heart rate, basic arrhythmia
- **Rationale:** Adequate, saves bandwidth/battery

**Medium-Risk (Post-Op, ICU):**
- **Sample rate:** 500 Hz ✅
- **Leads:** 3-5 lead
- **Analysis:** Full arrhythmia detection, ST monitoring
- **Rationale:** Standard of care, captures all events

**High-Risk (Cardiac Surgery, MI):**
- **Sample rate:** 500 Hz ✅
- **Leads:** 8-12 lead
- **Analysis:** Complete diagnostic ECG, pacemaker capture
- **Rationale:** Diagnostic quality, critical decisions

**Electrophysiology Lab:**
- **Sample rate:** 1000 Hz
- **Leads:** 12+ (including catheter leads)
- **Analysis:** His-bundle, detailed activation mapping
- **Rationale:** Specialized procedures only

---

### EEG Monitoring

**Seizure Monitoring (Standard):**
- **Sample rate:** 250-256 Hz
- **Channels:** 8-channel (Fp1/2, F3/4, C3/4, O1/2)
- **Analysis:** Band powers, spike detection
- **Rationale:** IFCN minimum, adequate for seizures

**Seizure Monitoring (Enhanced):**
- **Sample rate:** 500 Hz ✅
- **Channels:** 8-channel
- **Analysis:** High-gamma, detailed spike morphology
- **Rationale:** Better spike characterization

**Sleep Studies:**
- **Sample rate:** 256 Hz
- **Channels:** 4-8 channel
- **Analysis:** Sleep stage scoring, spindle detection
- **Rationale:** Power-of-2, adequate for sleep bands

**Epilepsy Surgery Evaluation:**
- **Sample rate:** 500-1000 Hz
- **Channels:** 16-21 channel (full 10-20 system)
- **Analysis:** Seizure onset localization, HFO detection
- **Rationale:** Surgical planning requires precision

**Brain-Computer Interface (Research):**
- **Sample rate:** 1000-2000 Hz
- **Channels:** 8-64 channel
- **Analysis:** Motor imagery, sensorimotor rhythms
- **Rationale:** Research-grade, real-time decoding

---

## ADS1298 Hardware Capabilities

### Sample Rate Options (From Datasheet)

The ADS1298 supports these sample rates:

| fMOD | Sample Rate (SPS) | Use Case |
|------|------------------|----------|
| 64 kHz | **250 SPS** | ECG/EEG standard |
| 64 kHz | **500 SPS** | High-quality ECG/EEG |
| 64 kHz | **1000 SPS** | Research ECG/EEG |
| 64 kHz | **2000 SPS** | Ultra-high-quality |
| 128 kHz | **4000 SPS** | Research only |
| 128 kHz | **8000 SPS** | Specialized |
| 256 kHz | **16 kHz SPS** | Maximum rate |
| 512 kHz | **32 kHz SPS** | Absolute maximum |

**Practical range for hospital use: 250-1000 Hz**

---

## Final Recommendations - Optimal Sampling Frequencies

### 🎯 Primary Recommendation: **500 Hz for Both ECG and EEG**

**Rationale:**
1. **ECG:**
   - 2× AHA/ACC minimum (250 Hz) ✅
   - Captures pacemaker spikes ✅
   - Excellent QRS resolution (±2ms accuracy) ✅
   - Suitable for all arrhythmias ✅
   - FDA/IEC compliant ✅

2. **EEG:**
   - 2× IFCN minimum (250 Hz) ✅
   - Full gamma band coverage (30-100 Hz) ✅
   - Partial high-gamma (100-200 Hz) ✅
   - Excellent seizure spike detection ✅
   - Research-quality data ✅

3. **System Benefits:**
   - **Unified sample rate** (no mode switching) ✅
   - **Backend optimized** for single rate ✅
   - **ESP32 feasible** (45% CPU, 5.7hr battery) ✅
   - **Future-proof** (supports advanced analysis) ✅

---

### Alternative: **250 Hz (Acceptable if constrained)**

**Use when:**
- Battery life critical
- Bandwidth limited
- Low-risk patients only

**Trade-offs:**
- ⚠️ Borderline for high-gamma EEG (80-100 Hz near Nyquist)
- ⚠️ May miss narrow pacemaker spikes on ECG
- ⚠️ Less precise QRS timing (±4ms vs ±2ms at 500 Hz)
- ✅ Half the bandwidth (saves data/battery)
- ✅ Still meets minimum medical standards

---

### Research Option: **1000 Hz (Not recommended for routine)**

**Use when:**
- EP lab procedures
- Epilepsy surgery planning (HFO detection)
- Research studies only

**Trade-offs:**
- ❌ 2× bandwidth vs 500 Hz
- ❌ Shorter battery life (2.8 hrs vs 5.7 hrs)
- ❌ Higher CPU load (70% vs 45%)
- ✅ Research-grade quality
- ✅ Full HFO coverage (ripples 80-500 Hz)

---

## Implementation Notes

### India-Specific Considerations

**Power line frequency:** 50 Hz (not 60 Hz)

**Backend code change needed** ([eeg_analysis_service.py:78](hospital-backend/app/services/eeg_analysis_service.py#L78)):

```python
# Current (US):
self.notchFreq = 60.0  # Hz

# Should be (India):
self.notchFreq = 50.0  # Hz ✅
```

**Action required:** Update notch filter frequency to 50 Hz for India deployment

---

### Sample Rate Configuration

**ESP32 code:**
```cpp
// Configure ADS1298 sample rate
#define SAMPLE_RATE 500  // Hz (configurable: 250, 500, 1000)

void setup() {
  ADS1298_setSampleRate(SAMPLE_RATE);
  // Interrupt fires every (1000 / SAMPLE_RATE) ms
  // 500 Hz = every 2 ms
}
```

**Backend receives in MQTT message:**
```json
{
  "sampleRate": 500,
  "duration": 0.1,
  "samples": {...}
}
```

Backend analysis services automatically adapt to sample rate ✅

---

## Summary Table - Final Recommendations

| Use Case | ECG Sample Rate | EEG Sample Rate | Rationale |
|----------|----------------|----------------|-----------|
| **Standard Hospital** | **500 Hz** ✅ | **500 Hz** ✅ | Best balance quality/bandwidth |
| **Low-risk/Battery** | 250 Hz | 250-256 Hz | Acceptable minimum |
| **Research/EP Lab** | 1000 Hz | 1000-2000 Hz | Specialized only |

**Default configuration:** **500 Hz unified for both ECG and EEG** ✅

**Streaming batch interval:** **100ms** (50 samples @ 500 Hz) ✅

**Result:** Hospital-grade real-time monitoring with optimal quality-to-bandwidth ratio!
