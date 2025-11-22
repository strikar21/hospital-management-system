# ESP32-S3 Hospital Watch - Upload Instructions

## ✅ FIXED: Custom partitions.csv Conflict Resolved

**What was the problem?**
- Arduino IDE tried to use BOTH the built-in "ESP SR 16M" partition scheme AND your custom `partitions.csv`
- This caused: `CSV Error at line 5: Partitions overlap`

**What was fixed?**
- Custom `partitions.csv` has been **renamed to `partitions.csv.backup`**
- Now Arduino IDE will use its built-in "ESP SR 16M" scheme without conflicts

---

## ⚠️ CRITICAL: Arduino IDE Configuration

### **Step 1: Board Selection**
In Arduino IDE, go to **Tools** menu and configure:

1. **Board**: "ESP32S3 Dev Module"
2. **USB CDC On Boot**: "Enabled"
3. **Flash Size**: "16MB (128Mb)"
4. **Partition Scheme**: "**ESP SR 16M (3MB APP/7MB SPIFFS/2.9MB MODEL)**" ← Use this!
5. **PSRAM**: "OPI PSRAM" (if your board has PSRAM)

### **Step 2: Upload Firmware**

Simply click **Upload** button in Arduino IDE:
1. Click **Upload** (Ctrl+U)
2. Wait for compilation and upload
3. Open Serial Monitor (115200 baud)

---

## 🔧 Partition Table Explained

**ESP SR 16M** partition scheme allocates 16MB flash as:

| Partition | Type | Size | Purpose |
|-----------|------|------|---------|
| nvs | data | 24KB | Non-volatile storage |
| otadata | data | 8KB | OTA metadata (not used) |
| app0 | app | 3MB | Main firmware ✅ |
| spiffs | data | 7MB | File system (CA certs, offline data) ✅ |
| model | data | 2.9MB | Speech recognition models (unused) ❌ |

**Note**: The `model` partition is for ESP-SR (speech recognition) - your project doesn't use it, so it sits empty. That's fine!

---

## 🐛 Troubleshooting

### **Error: "Partitions overlap"**
```
CSV Error at line 5: Partitions overlap
```
**Cause**: Custom `partitions.csv` file conflicts with Arduino IDE's built-in partition scheme.

**Solution**: ✅ **Already fixed!** The custom `partitions.csv` has been renamed to `partitions.csv.backup`.

---

### **Error: "SPIFFS mount failed"**
```
E (41261) SPIFFS: spiffs partition could not be found
❌ SPIFFS mount failed
```
**Cause**: Wrong partition scheme selected in Arduino IDE.

**Solution**: Select "**ESP SR 16M (3MB APP/7MB SPIFFS/2.9MB MODEL)**" in Tools → Partition Scheme.

---

## 📝 Current Code Version

**Firmware**: v5.4.8
- Modular UI components (StatusBar, PatientBar, VitalsCards, ECGChart, AlertPopup)
- Fall detection threshold: 3.5g (reduced false positives)
- Text colors: White on dark backgrounds, black on light backgrounds
- Alert persistence fixed (alerts now save to list)

---

## 🚨 Known Issues

1. **Fall detection triggers on screen taps**
   - Current threshold: 3.5g
   - Screen taps can generate 2.5-7.95g acceleration
   - **Workaround**: Increase threshold to 5.0g or add post-fall validation

2. **SPIFFS not mounting**
   - **Cause**: Partition table not uploaded
   - **Fix**: Use esptool command above

3. **NFC module not found**
   - This is optional - system works without it
   - Connect PN532 to I2C Bus 1 (SDA=GPIO16, SCL=GPIO17) if needed

---

## ✅ Verification Checklist

After upload, check Serial Monitor for:
- ✅ "StatusBar: Initialized (35px height)"
- ✅ "PatientBar: Initialized (35px height at Y=35)"
- ✅ "VitalsCards: Initialized (2×2 grid, 146px height at Y=70)"
- ✅ "ECGChart: Initialized (240px height at Y=216, medical grid)"
- ✅ "AlertPopup: Initialized (260×80px, hidden by default)"
- ✅ "Fall threshold: 3.5g" (NOT 2.5g)
- ✅ SPIFFS mounts successfully (no errors)

If you see "Fall threshold: 2.5g", the old code is still running - re-upload firmware.
