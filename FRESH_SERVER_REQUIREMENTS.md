# Fresh Server Requirements - Complete Analysis

## Answer: Will a new server have all your columns and tables?

**NO** - A fresh server will be missing:

### PostgreSQL (Main Database):
- ❌ **26 tables missing** (65% of your schema)
- ❌ **Multiple columns missing** from existing tables

### TimescaleDB (Time-Series Database):
- ❌ **3 critical hypertables missing** (`vitals_realtime`, `waveform_snapshots`, `neural_events`)
- ❌ Current init only creates `vitals_timeseries` (which you don't even use!)

---

## Current Production Status

### PostgreSQL - localhost:5432 (database: `hospitaldb`)
**Tables**: 40 tables
**Status**: Fully populated with patient/device/staff data

### TimescaleDB - Docker container on localhost:5433 (database: `hospitaltimescale`)
**Tables**: 4 hypertables
**Data Volume**:
- `vitals_realtime`: **450,770 rows** ✅ (actively used)
- `waveform_snapshots`: **576,526 rows** ✅ (actively used)
- `neural_events`: 0 rows (not used yet)
- `vitals_timeseries`: 0 rows (legacy, replaced by vitals_realtime)

---

## What's Missing from database.py Init Functions

### 1. PostgreSQL - `createTables()` Missing 26 Tables

#### Critical Business Logic:
1. **caseEntries** - Patient case sheet entries
2. **medical_operations** - Idempotency tracking
3. **atomic_transactions** - Transaction recovery

#### Device Management:
4. **deviceBaselines** - Performance baselines
5. **deviceCalibration** - Calibration history
6. **deviceMaintenanceHistory** - Maintenance logs
7. **device_certificates** - TLS certificates for ESP32
8. **device_mac_mapping** - MAC to device ID mapping
9. **provisioning_codes** - Device provisioning
10. **watchremovalevents** - Watch removal tracking
11. **impedancereadings** - Impedance measurements

#### Patient Monitoring:
12. **patientstates** - Alert state tracking

#### Security:
13. **token_blacklist** - JWT revocation

#### Other:
14-26. (13 more tables - see SCHEMA_COMPARISON_NEW_SERVER.md for full list)

### 2. PostgreSQL - Missing Columns in Existing Tables

#### **patients** table:
- ❌ `mrn` VARCHAR (Medical Record Number)
- ❌ `weight` NUMERIC
- ❌ `diagnosis` TEXT

#### **patient_alerts** table:
- ❌ `deviceId` TEXT
- ❌ `source` TEXT (e.g., 'ESP32', 'Backend')
- ❌ `alertTimestamp` TIMESTAMP
- ❌ `category` TEXT
- ❌ `confidence` DOUBLE PRECISION
- ❌ `context` JSONB

#### **devices** table:
- ❌ `lastCalibrationDate` TIMESTAMP
- ❌ `calibrationDueDate` TIMESTAMP
- ❌ `batteryHealthPercentage` INTEGER
- ❌ `totalDisconnects` INTEGER
- ❌ `lastCommandSentAt` TIMESTAMP
- ❌ `lastCommandAckAt` TIMESTAMP

### 3. TimescaleDB - `createTimescaleTables()` Missing 3 Tables

**Current init only creates**: `vitals_timeseries` (which you don't use!)

**Missing critical tables**:

#### **vitals_realtime** ❌ (450K rows in production!)
Your PRIMARY vitals table with:
- Standard vitals (HR, SpO2, temp, BP, RR)
- ECG metrics (RR interval, QRS, QT, axis, rhythm, ST segment)
- EEG metrics (alpha/beta/theta/delta/gamma power, dominant frequency, seizure detection)
- New sensor vitals (tremor, bioimpedance, IMU fall risk, perfusion index, step count, watch worn status)
- 275 time-based chunks
- Multiple performance indexes

#### **waveform_snapshots** ❌ (576K rows in production!)
Your waveform storage table with:
- ECG limb leads, precordial leads, derived leads
- EEG frontal/central/occipital channels
- Event detection data
- 103 time-based chunks
- Compression support

#### **neural_events** ❌ (0 rows but schema exists)
Event detection table for:
- Arrhythmias, seizures, other neural events
- Severity levels and confidence scores
- Acknowledgment and resolution tracking

---

## Impact: What Will Break on Fresh Server

### PostgreSQL Missing Tables:
❌ **Device provisioning** - No provisioning_codes table
❌ **TLS certificates** - No device_certificates table
❌ **Case sheet entries** - No caseEntries table
❌ **Alert state tracking** - No patientstates table
❌ **Device maintenance** - No maintenance tables
❌ **Idempotency** - No medical_operations table
❌ **Token revocation** - No token_blacklist table
❌ **Impedance tracking** - No impedancereadings table
❌ **Watch removal tracking** - No watchremovalevents table

### PostgreSQL Missing Columns:
⚠️ **Patient records** - No MRN, weight, diagnosis
⚠️ **Alerts** - No deviceId, source, category
⚠️ **Devices** - No maintenance tracking

### TimescaleDB Missing Tables:
❌ **Vitals storage** - No vitals_realtime (450K rows of data lost!)
❌ **Waveform storage** - No waveform_snapshots (576K rows lost!)
❌ **Event detection** - No neural_events table

**Result**: Fresh server would have NO vitals or waveform history! Data only exists in real-time WebSocket streams.

---

## Action Required

You need to update TWO functions in `database.py`:

### Task 1: Update `createTables()` (PostgreSQL)
Add 26 missing tables + missing columns to existing tables

**Estimated effort**: 3-4 hours

### Task 2: Update `createTimescaleTables()` (TimescaleDB)
Replace current `vitals_timeseries` with 3 active tables:
- `vitals_realtime` (with ALL 35 columns!)
- `waveform_snapshots`
- `neural_events`

**Estimated effort**: 1-2 hours

### Task 3: Test on Fresh Database
Create test database and verify schema matches production

**Estimated effort**: 30 minutes

---

## Next Steps - Your Choice

**Option A**: I can update both functions now (recommended)
- Complete schema for fresh server deployments
- ~5 hours of work automated

**Option B**: I can create SQL export files for you to review first
- Export current schema using pg_dump
- You review and approve
- Then I update the functions

**Option 3**: I can just update TimescaleDB first (quick win)
- Fix the missing vitals_realtime table
- Then tackle PostgreSQL tables

Which would you prefer?

---

## Files to Reference

- `SCHEMA_COMPARISON_NEW_SERVER.md` - PostgreSQL detailed analysis
- `SQL_MIGRATION_FILES_ANALYSIS.md` - Migration files analysis
- `SERVER_RESTART_SUMMARY.md` - Current server status

## Current Database State

**PostgreSQL**: 40 tables, fully functional
**TimescaleDB**: 4 hypertables, 1M+ rows of vitals/waveform data
**Backend**: Running on port 8001 ✅
**Frontend**: Running on port 3000 ✅
