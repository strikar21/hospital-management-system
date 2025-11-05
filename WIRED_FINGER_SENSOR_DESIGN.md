# Wired Finger PPG Sensor Design - Pulse Oximeter Style
**Date**: 2025-10-30
**Concept**: Single magnetic cable from watch to fingertip sensor (like hospital pulse oximeter)

---

## Design Concept: Wired vs. Wireless

### Your Suggestion: Wired Finger Clip ✅ MUCH BETTER!

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   ESP32 Watch (Wrist)                  Finger Clip     │
│   ┌──────────────┐                     ┌──────────┐    │
│   │              │                     │          │    │
│   │  ESP32-S3    │═══════════════════>│ MAX30102 │    │
│   │              │   Magnetic Cable    │ (PPG #2) │    │
│   │  MAX86178    │   (4-wire I2C)     │          │    │
│   │  (PPG #1)    │                     │ Spring   │    │
│   │              │                     │ Clip     │    │
│   └──────────────┘                     └──────────┘    │
│        ↑                                     ↑          │
│        │                                     │          │
│      Wrist                               Fingertip     │
│                                                         │
└─────────────────────────────────────────────────────────┘

Cable: 4-wire (VCC, GND, SDA, SCL)
Length: 15-20 cm (flexible silicone)
Connector: 4-pin magnetic pogo pins
```

---

## Why Wired is MUCH Better than Wireless Ring

### ✅ Advantages of Wired Design:

#### 1. **No Battery in Sensor** 🔋
- Powered directly from watch
- Infinite runtime (no charging needed)
- Lighter fingertip sensor
- **Cost savings**: -$5/unit (no battery, no BLE chip)

#### 2. **No Bluetooth Issues** 📡
- No pairing needed
- No connection drops
- No interference from other devices
- Lower latency (I2C vs BLE)

#### 3. **Synchronized Timing** ⏱️
- Both PPG sensors on same clock
- No timestamp sync issues
- Perfect PTT accuracy (no BLE latency)

#### 4. **Medical Device Standard** 🏥
- Hospital pulse oximeters use wired design
- Proven form factor
- Familiar to nursing staff
- Easy to clean/sanitize

#### 5. **Lower Cost** 💰
```
Wireless Ring:
- MAX30105:        $3.50
- nRF52810 BLE:    $2.80
- LiPo battery:    $1.20
- Charging circuit: $0.30
- BLE antenna:     $0.50
─────────────────────────
Total:             $8.30

Wired Clip:
- MAX30102:        $3.00
- Spring clip:     $0.80
- Cable assembly:  $1.50
─────────────────────────
Total:             $5.30  (36% cheaper!)
```

#### 6. **Easier Compliance** 👍
- Clips on finger (like pulse ox)
- Removes easily when needed
- No sizing issues (spring clip fits all fingers)
- No "lost ring" problem

---

## Hardware Design: Wired Finger Clip

### Component Selection:

#### Finger Sensor (Distal End):

**MAX30102** - PPG + Heart Rate Sensor
- I2C address: 0x57 (same as MAX86178 - **PROBLEM!**)
- **SOLUTION**: Use address pins or I2C multiplexer

**Alternative: MAX30105**
- I2C address: 0x56 or 0x57 (configurable)
- Set to 0x56 → No conflict with watch's MAX86178 (0x57)

**Sensor Configuration**:
```
MAX30105 Fingertip Sensor (0x56)
- Red LED: 660 nm @ 50 mA
- IR LED: 880 nm @ 50 mA
- Sample rate: 100 Hz
- ADC resolution: 18-bit
- Power: 3.3V from watch (via cable)
```

#### Spring Clip Mechanism:

**Design**: Similar to hospital pulse oximeter
```
    ┌─────────────────┐
    │   MAX30105      │  ← PCB (15mm × 10mm)
    │   LED side      │
    ├─────────────────┤
    │                 │
    │  Spring hinge   │  ← Stainless steel spring
    │                 │
    ├─────────────────┤
    │  Photodiode     │
    │  side           │
    └─────────────────┘
```

**Materials**:
- Spring: Stainless steel (medical grade)
- Housing: ABS plastic (autoclavable)
- LED side: Transparent polycarbonate window
- Photodiode side: Black ABS (block ambient light)

**Specifications**:
- Finger opening: 8-20mm (accommodates index/middle/ring fingers)
- Spring force: 80-120 grams (comfortable, secure contact)
- Weight: ~8 grams
- Size: 25mm × 15mm × 12mm

---

### Cable Design: Magnetic Connector

#### Cable Specifications:

**Type**: 4-wire silicone ribbon cable
- Wire gauge: 30 AWG (0.25mm²)
- Jacket: Medical-grade silicone (flex-resistant)
- Length: 18 cm (wrist to fingertip)
- Color: Black or medical blue
- Flexibility: >10,000 bend cycles

**Wire Assignment**:
```
Pin 1 (Red):    VCC (+3.3V, max 100mA)
Pin 2 (Black):  GND
Pin 3 (Yellow): I2C SDA (data)
Pin 4 (Green):  I2C SCL (clock)
```

#### Magnetic Connector (Watch Side):

**Pogo Pin Design**:
```
┌────────────────────┐
│   ESP32 Watch      │
│                    │
│  ┌──────────────┐  │
│  │ ● ● ● ●      │  │ ← 4 spring-loaded pogo pins
│  │ 1 2 3 4      │  │   (VCC GND SDA SCL)
│  └──────────────┘  │
│                    │
└────────────────────┘
      ↑
      │ Magnetic attraction (4× neodymium magnets)
      ↓
┌────────────────────┐
│ Cable Connector    │
│  ┌──────────────┐  │
│  │ ● ● ● ●      │  │ ← 4 contact pads (gold plated)
│  │ 1 2 3 4      │  │
│  └──────────────┘  │
└────────────────────┘
```

**Magnet Specifications**:
- Type: Neodymium N52
- Size: 3mm diameter × 1mm thick (4 magnets)
- Pull force: 200g per magnet = 800g total (strong hold)
- Polarity: Alternating (prevents reverse connection)

**Pogo Pin Specifications**:
- Type: Spring-loaded contact pins
- Current rating: 1A per pin
- Travel: 1.5mm
- Contact resistance: <50 mΩ
- Gold plating: 30 μ-inch (corrosion resistant)

**Example Part**: Molex Pogo Pin Connector (51146-0400)

---

### Watch Modification: Add Magnetic Port

**Location**: Side of watch case (opposite charging port)

```
Top View of Watch:
┌─────────────────────────────┐
│                             │
│   [USB Charge Port]         │
│                             │
│   ┌───────────────────┐     │
│   │                   │     │
│   │    ESP32 Watch    │     │
│   │                   │     │
│   └───────────────────┘     │
│                             │
│   [Magnetic Sensor Port] ←  │  4-pin connector
│                             │
└─────────────────────────────┘
```

**PCB Changes**:
```diff
ESP32 Watch Schematic:

+ Add 4-pin magnetic connector footprint
+ Connect to I2C bus (shared with MAX86178)
+ Add pull-up resistors (4.7kΩ on SDA/SCL if not already present)
+ Add ESD protection diodes (optional but recommended)

No firmware changes needed - MAX30105 appears as second I2C device
```

---

## I2C Address Conflict Resolution

### Problem:
- MAX86178 (watch wrist PPG): I2C address 0x57
- MAX30102 (finger PPG): I2C address 0x57
- **CONFLICT!** Both sensors can't share same address on one bus

### Solution Options:

#### Option 1: Use MAX30105 (Different Address) ✅ EASIEST
```
MAX86178 (wrist):  0x57 (fixed)
MAX30105 (finger): 0x56 (configurable via AD0 pin)

No conflict! Both work on same I2C bus.
```

**Implementation**:
- Use MAX30105 instead of MAX30102
- Tie AD0 pin LOW → Address 0x56
- ESP32 can communicate with both sensors:
  ```cpp
  Wire.beginTransmission(0x57);  // Wrist PPG
  Wire.beginTransmission(0x56);  // Finger PPG
  ```

#### Option 2: I2C Multiplexer ⚠️ MORE COMPLEX
```
ESP32 ─── TCA9548A (I2C Mux) ─┬─ Channel 0 ─ MAX86178 (0x57)
                              └─ Channel 1 ─ MAX30102 (0x57)
```

**Pros**: Can use identical sensors
**Cons**: Extra chip ($1), more complex, more power

#### Option 3: GPIO Switch ⚠️ HACKY
```
ESP32 GPIO ─── MOSFET ─┬─ Enable wrist sensor
                       └─ Enable finger sensor
                       (only one active at a time)
```

**Pros**: Cheap
**Cons**: Can't sample both simultaneously (breaks PWV measurement!)

---

### **RECOMMENDATION**: Use MAX30105 (address 0x56) ✅

---

## Firmware Implementation

### ESP32 Code Changes:

```cpp
// Add second PPG sensor (finger)
#include "MAX30105.h"  // Sparkfun MAX30105 library

MAX30105 wristPPG;   // MAX86178 at 0x57 (existing)
MAX30105 fingerPPG;  // MAX30105 at 0x56 (new)

void setup() {
    Wire.begin();

    // Initialize wrist PPG
    if (!wristPPG.begin(Wire, 0x57)) {
        Serial.println("❌ Wrist PPG not found");
    }

    // Initialize finger PPG
    if (!fingerPPG.begin(Wire, 0x56)) {
        Serial.println("⚠️  Finger sensor not connected (optional)");
        fingerPPGAvailable = false;
    } else {
        fingerPPGAvailable = true;
        Serial.println("✅ Finger sensor connected");
    }

    // Configure both sensors identically
    wristPPG.setup();
    fingerPPG.setup();
}

// Dual-PPG BP measurement
void measureBloodPressure() {
    if (!fingerPPGAvailable) {
        Serial.println("⚠️ Finger sensor required for BP measurement");
        return;
    }

    // Read both sensors simultaneously
    uint32_t wristRed = wristPPG.getRed();
    uint32_t fingerRed = fingerPPG.getRed();

    // Detect peaks
    bool wristPeak = detectPeak(wristRed, wristHistory);
    bool fingerPeak = detectPeak(fingerRed, fingerHistory);

    // Calculate PTT when both peaks detected
    if (wristPeak) {
        wristPeakTime = micros();
    }

    if (fingerPeak && wristPeakTime > 0) {
        fingerPeakTime = micros();

        // PTT = time difference
        float PTT_ms = (fingerPeakTime - wristPeakTime) / 1000.0;

        // PWV = distance / time
        float distance_m = patientArmLength;  // Calibrated per patient
        float PWV = distance_m / (PTT_ms / 1000.0);

        // Estimate BP (calibrated coefficients per patient)
        float systolic = calibration_a * PWV * PWV + calibration_b;
        float diastolic = calibration_c * PWV * PWV + calibration_d;

        publishBPEstimate(systolic, diastolic);
    }
}
```

### Calibration Procedure:

**One-time setup per patient**:
1. Measure arm length (wrist to fingertip with finger extended)
2. Take 3 cuff BP readings
3. Simultaneously record PWV
4. Calculate patient-specific coefficients
5. Store in database

```python
# Backend calibration API
@app.post("/api/v1/patients/{id}/calibrate-bp")
async def calibrate_bp(patient_id: str, cuff_readings: List[float], pwv_readings: List[float]):
    # Linear regression: BP = a*PWV^2 + b
    coeffs = np.polyfit(np.array(pwv_readings)**2, cuff_readings, 1)

    # Store calibration
    await db.update_patient_calibration(patient_id, {
        'armLength': request.arm_length,
        'calibrationCoeffs': coeffs.tolist(),
        'calibratedAt': datetime.now(),
        'calibrationValidUntil': datetime.now() + timedelta(days=14)
    })
```

---

## Physical Design: Finger Clip

### Option A: Clothespin Style (Like Pulse Ox) ✅ RECOMMENDED

```
Side View:
                Cable →
                   │
    ┌──────────────┼──────────────┐
    │              ↓              │
    │  ┌────────────────────┐     │
    │  │   MAX30105 PCB     │     │
    │  │   (LED window)     │     │
    │  └────────────────────┘     │
    │           Spring            │ ← Stainless steel spring
    │  ┌────────────────────┐     │
    │  │   Photodiode PCB   │     │
    │  │   (detector)       │     │
    │  └────────────────────┘     │
    └─────────────────────────────┘
            Fingertip here
```

**Dimensions**:
- Length: 25-30mm
- Width: 15-18mm
- Thickness (open): 20mm
- Thickness (closed): 12mm
- Weight: 8-10 grams

**Materials**:
- Housing: ABS plastic (white or medical blue)
- Spring: Stainless steel 302
- Window: Polycarbonate (transparent)
- Cable: Medical-grade silicone

---

### Option B: Ring-Style with Detachable Cable ⚠️ MORE COMPLEX

```
Top View:
    ┌─────────────────┐
    │                 │
    │   MAX30105      │
    │                 │
    │  ┌───────────┐  │
    │  │  Finger   │  │ ← Ring opening
    │  │           │  │
    │  └───────────┘  │
    │                 │
    │   Photodiode    │
    │                 │
    └────────┬────────┘
             │
          Cable connector (magnetic)
```

**Pros**: Can wear as ring, attach cable when needed
**Cons**: More complex, requires ring sizing, higher cost

---

## Bill of Materials (BOM)

### Wired Finger Sensor Assembly:

| Component | Part Number | Qty | Unit Cost | Total |
|-----------|-------------|-----|-----------|-------|
| MAX30105 PPG Sensor | MAX30105EFD+ | 1 | $3.00 | $3.00 |
| Spring clip mechanism | Custom | 1 | $0.80 | $0.80 |
| PCB (2-layer, 15×10mm) | Custom | 1 | $0.30 | $0.30 |
| Silicone cable (18cm, 4-wire) | Custom | 1 | $1.00 | $1.00 |
| Magnetic connector (cable side) | Custom | 1 | $0.50 | $0.50 |
| ABS housing (injection molded) | Custom | 1 | $0.60 | $0.60 |
| Assembly & testing | - | - | $0.80 | $0.80 |
| **Total per sensor** | | | | **$7.00** |

### Watch Modification (Add Magnetic Port):

| Component | Part Number | Qty | Unit Cost | Total |
|-----------|-------------|-----|-----------|-------|
| Pogo pins (4-pin) | Molex 51146-0400 | 1 | $2.50 | $2.50 |
| Neodymium magnets (3×1mm) | N52 grade | 4 | $0.10 | $0.40 |
| PCB modification | - | - | $1.00 | $1.00 |
| **Total per watch** | | | | **$3.90** |

### **Grand Total**: $10.90 per patient (sensor + watch mod)

---

## Advantages Summary: Wired vs Ring

| Feature | Wired Clip | Wireless Ring |
|---------|-----------|---------------|
| **Cost** | $7 | $15 |
| **Battery** | No (powered by watch) | Yes (needs charging) |
| **Charging** | Never | Every 2-3 days |
| **Connection** | Plug and play | BLE pairing |
| **Reliability** | Very high | Medium (BLE drops) |
| **Timing accuracy** | Perfect (shared clock) | ±5ms (BLE latency) |
| **Patient compliance** | High (like pulse ox) | Medium (ring discomfort) |
| **Sizing** | One size fits all | Need S/M/L sizes |
| **Medical familiarity** | High (standard design) | Low (new form factor) |
| **Lost/damaged risk** | Low (attached to watch) | High (separate device) |
| **Sanitation** | Easy (autoclavable) | Medium (battery inside) |

**Winner**: Wired Clip ✅

---

## Recommended Next Steps

### Phase 1: Prototype (2 weeks)
1. **Order components**:
   - MAX30105 breakout board (Sparkfun)
   - Hospital pulse oximeter clip (dissect for spring mechanism)
   - 4-wire silicone cable (18cm)
   - Magnetic pogo pin connector kit

2. **Build proof-of-concept**:
   - Solder MAX30105 to cable
   - Hot-glue into pulse ox clip housing
   - Add magnetic connector
   - Test I2C communication with ESP32

3. **Test PWV accuracy**:
   - Measure on 5 volunteers
   - Compare PTT values with reference device
   - Validate BP estimation formula

### Phase 2: Custom PCB Design (2 weeks)
1. Design compact PCB (15×10mm)
2. Integrate MAX30105 + cable connector
3. Order 10 prototype PCBs

### Phase 3: Mechanical Design (2 weeks)
1. 3D model spring clip housing
2. Design cable strain relief
3. Design magnetic connector housing
4. 3D print prototypes, test fit

### Phase 4: Firmware Integration (1 week)
1. Implement dual-PPG sampling
2. Peak detection algorithm
3. PTT calculation
4. BP estimation with calibration
5. MQTT publishing to backend

### Phase 5: Clinical Validation (2 weeks)
1. Test on 10 patients
2. Compare with cuff BP (gold standard)
3. Calculate accuracy (mean error, std dev)
4. Refine calibration algorithm

**Total Timeline**: ~9 weeks from start to clinical validation

---

## Final Recommendation

### ✅ **GO WITH WIRED FINGER CLIP**

**Why**:
1. **36% cheaper** than wireless ring ($7 vs $11)
2. **No battery** = infinite runtime, no charging
3. **More reliable** = no BLE connection issues
4. **Better timing** = perfect synchronization for PTT
5. **Medical standard** = familiar to hospital staff
6. **Easier compliance** = clips on like pulse ox

**What to do**:
1. Order MAX30105 breakout board + pulse ox clip (~$15 for prototype)
2. Build proof-of-concept in 2 days
3. Test on yourself first
4. If PTT measurements look good → proceed to custom PCB

**Want me to**:
- Design the custom PCB schematic?
- Write the complete firmware (dual-PPG PTT measurement)?
- Create 3D models for the clip housing?

Let me know and I'll proceed!
