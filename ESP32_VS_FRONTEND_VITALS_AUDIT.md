# ESP32 vs Frontend Vitals - Gap Analysis

## Frontend Requirements (PatientTypes.ts:45-71)

The frontend expects **12 vital sign fields**:

### Cardiovascular (3 fields):
1. ✅ `heartRate` - BPM (integer)
2. ❌ `systolicPressure` - mmHg (integer)
3. ❌ `diastolicPressure` - mmHg (integer)

### Respiratory (2 fields):
4. ❌ `respiratoryRate` - breaths/min (integer)
5. ❌ `oxygenSaturation` - percentage (integer)

### Temperature (1 field):
6. ✅ `skinTemperature` - Fahrenheit (decimal)

### Neurological/Cardiac Monitoring (3 fields):
7. ❌ `ecgReading` - mV * 100 (integer)
8. ❌ `eegReading` - μV (integer)
9. ❌ `isEcgMode` - boolean (ECG vs EEG mode)

### Advanced Monitoring (3 fields):
10. ❌ `bioelectricalImpedance` - Ohms
11. ❌ `tremorIntensity` - 0-10 scale
12. ❌ `fallRisk` - 'low' | 'medium' | 'high'

### Metadata (2 fields):
13. ✅ `lastDataReceived` - ISO timestamp
14. ❌ `dataQualityScore` - 0-1 scale

---

## ESP32 Current Implementation (esp32_hospital_watch_complete.ino:833-859)

### What ESP32 IS Sending (lines 843-851):

```cpp
JsonDocument doc;
doc["deviceId"] = deviceId;
doc["patientId"] = assignedPatientId;
doc["timestamp"] = millis();          // ❌ Wrong - should be ISO timestamp
doc["heartRate"] = heartRate;         // ✅ Matches frontend
doc["temperature"] = temperature;     // ⚠️ Close - frontend expects "skinTemperature"
doc["oxygenSat"] = oxygenSat;         // ⚠️ Close - frontend expects "oxygenSaturation"
doc["batteryLevel"] = batteryLevel;   // ✅ For device status (not vitals)
doc["quality"] = 95;                  // ⚠️ Close - frontend expects "dataQualityScore" (0-1 scale)
```

### Mock Sensor Data (lines 96-99):
```cpp
float heartRate = 75;
float temperature = 98.6;
int oxygenSat = 98;
int batteryLevel = 85;
```

### What's Missing:
- ❌ `systolicPressure` / `diastolicPressure`
- ❌ `respiratoryRate`
- ❌ `ecgReading` / `eegReading` / `isEcgMode`
- ❌ `bioelectricalImpedance`
- ❌ `tremorIntensity`
- ❌ `fallRisk`

---

## Field Name Mismatches

| ESP32 Field | Frontend Field | Status |
|-------------|----------------|--------|
| `heartRate` | `heartRate` | ✅ Match |
| `temperature` | `skinTemperature` | ⚠️ Name mismatch |
| `oxygenSat` | `oxygenSaturation` | ⚠️ Name mismatch |
| `quality` (0-100) | `dataQualityScore` (0-1) | ⚠️ Name + scale mismatch |
| `timestamp` (millis) | `lastDataReceived` (ISO) | ⚠️ Format mismatch |

---

## Backend MQTT Handler

Need to check:
1. Does backend MQTT service receive ESP32 vitals?
2. Does it transform field names (temperature → skinTemperature)?
3. Does it store in TimescaleDB?
4. Does it update patient vitals in real-time?

**Files to check**:
- `hospital-backend/app/services/mqtt_service.py`
- `hospital-backend/app/api/v1/esp32.py`

---

## Current Status Summary

### ✅ Working:
- ESP32 sends vitals via MQTT every 5 seconds (when assigned to patient)
- Sends: `heartRate`, `temperature`, `oxygenSat`, `batteryLevel`

### ❌ Issues:
1. **Field name mismatches**: `temperature` vs `skinTemperature`, `oxygenSat` vs `oxygenSaturation`
2. **Missing 9 vital signs**: Blood pressure, respiratory rate, ECG/EEG, impedance, tremor, fall risk
3. **Timestamp format**: Sending `millis()` instead of ISO timestamp
4. **Quality score scale**: Sending 0-100 instead of 0-1

### ⚠️ Unknown:
- Does backend transform field names?
- Does backend calculate missing vitals?
- Does backend store in TimescaleDB and serve to frontend?

---

## Next Steps - RESEARCH REQUIRED

1. **Check backend MQTT service** - Does it handle ESP32 vitals and transform field names?
2. **Check TimescaleDB schema** - What columns exist for vitals?
3. **Check if vitals are displaying** - Are the 3 fields ESP32 sends (HR, temp, SpO2) showing on frontend dashboard?
4. **Determine gaps** - Which of the 9 missing vitals are actually needed vs nice-to-have?

**DO NOT modify ESP32 firmware until we understand backend data flow!**
