# Database Cleanup and Structure Analysis

**Date**: 2025-11-06
**Purpose**: Identify empty/unused tables and recommend cleanup
**Status**: ✅ Complete inventory

---

## TimescaleDB (hospitaltimescale) - Port 5433

### Table 1: vitals_realtime ✅ KEEP - ACTIVE USE
```
Rows:        270,414 (active streaming)
Size:        32 kB
Hypertable:  YES
Status:      ✅ PRIMARY DATA SOURCE
```

**Data Flow**: ESP32 → MQTT → Backend → This table
**Usage**: Real-time vitals storage (1 record/second per patient)
**Latest Data**: 2025-11-06 00:33:34 (currently streaming)
**Columns**: 26 columns including heartRate, oxygenSaturation, skinTemperature, respiratoryRate, etc.
**Missing**: systolicPressure, diastolicPressure (BP columns not added yet)

**Action**: ✅ **KEEP** - This is the main vitals data table

---

### Table 2: waveform_snapshots ✅ KEEP - ACTIVE USE
```
Rows:        225,007 (active streaming)
Size:        40 kB
Hypertable:  YES
Status:      ✅ PRIMARY WAVEFORM DATA
```

**Data Flow**: ESP32 → MQTT → Backend → This table
**Usage**: ECG/EEG waveform storage (1 aggregated message/second)
**Latest Data**: 2025-11-06 00:33:35 (currently streaming)
**Columns**: ecgLimbLeads, ecgPrecordialLeads, ecgDerivedLeads, eegFrontalChannels, etc.

**Action**: ✅ **KEEP** - This is the main waveform data table

---

### Table 3: neural_events ⚠️ EMPTY BUT KEEP
```
Rows:        0
Size:        40 kB
Hypertable:  YES
Status:      ⚠️ EMPTY - Reserved for future alerts
```

**Purpose**: Store significant clinical events (arrhythmia, seizures, alerts)
**Usage**: Not yet implemented
**Columns**: eventType, severity, confidence, waveform snapshots during events

**Action**: ✅ **KEEP** - Infrastructure ready, will be used when alert system is activated

---

### Table 4: vitals_timeseries ❌ DROP - DUPLICATE SCHEMA
```
Rows:        0
Size:        40 kB
Hypertable:  YES
Status:      ❌ UNUSED - Wrong schema design
```

**Why It Exists**: Legacy "narrow schema" approach (one row per vital type)
**Why It's Empty**: System uses `vitals_realtime` instead (wide schema - all vitals in one row)
**Duplicates**: vitals_realtime functionality

**Schema Comparison**:
- **vitals_timeseries** (narrow): time, patientId, vitalType, value, unit ← ONE vital per row
- **vitals_realtime** (wide): time, patientId, heartRate, oxygenSat, temp, ... ← ALL vitals per row

**Action**: ❌ **DROP TABLE** - Unused, duplicates vitals_realtime

---

## PostgreSQL (hospitaldb) - Port 5432

### Table: vitals_timeseries ❌ DROP - OLD TEST DATA
```
Rows:        272 (old test data)
Size:        144 kB
Status:      ❌ LEGACY - No longer used
```

**Data Analysis**:
- All data from October 7-8, 2025 (old test data)
- All for patient: 6b851aa6-e564-40b6-963f-e1a5efdf024c (NOT current patient)
- Includes 1 BP record: bloodpressuresystolic: 118.00 mmHg
- Current patient (081a5294-da91-4c74-bb8a-e5062f5851dd) has ZERO rows here

**Why It Exists**: Early testing before TimescaleDB integration
**Why It's Not Used**: System moved to TimescaleDB vitals_realtime table

**Action**: ❌ **DROP TABLE** - Contains only old test data, no production data

---

## Summary

### Active Tables (KEEP)
1. ✅ **TimescaleDB vitals_realtime** - 270,414 rows, actively streaming
2. ✅ **TimescaleDB waveform_snapshots** - 225,007 rows, actively streaming
3. ✅ **TimescaleDB neural_events** - 0 rows, but infrastructure ready for alerts

### Empty/Unused Tables (DROP)
1. ❌ **TimescaleDB vitals_timeseries** - 0 rows, wrong schema design, unused
2. ❌ **PostgreSQL vitals_timeseries** - 272 rows, old test data from October 7-8

---

## Cleanup Commands

### Option 1: Drop Both vitals_timeseries Tables ⚠️ RECOMMENDED

**TimescaleDB** (drop empty duplicate):
```sql
-- Connect to hospitaltimescale
\c hospitaltimescale

-- Drop hypertable and all chunks
DROP TABLE IF EXISTS vitals_timeseries CASCADE;
```

**PostgreSQL** (drop old test data):
```sql
-- Connect to hospitaldb
\c hospitaldb

-- Drop table with old test data
DROP TABLE IF EXISTS vitals_timeseries CASCADE;
```

**Benefit**: Removes confusion, clears ~184 kB disk space, eliminates duplicate schemas

---

### Option 2: Keep for Historical Reference (NOT RECOMMENDED)

If you want to preserve the one BP test record from October 7:

**PostgreSQL**:
```sql
-- Export the BP record first
SELECT * FROM vitals_timeseries
WHERE vitaltype ILIKE '%pressure%';
-- Result: bloodpressuresystolic: 118.00 mmHg on 2025-10-07 13:46:06

-- Then drop table
DROP TABLE IF EXISTS vitals_timeseries CASCADE;
```

**Not recommended** because:
- It's just 1 test record
- Different patient (not current patient)
- BP was never actually working in production
- Takes up space and causes confusion

---

## Impact Analysis

### If We Drop vitals_timeseries (Both Databases):

**✅ Safe to Drop Because**:
1. **TimescaleDB vitals_timeseries** - Completely empty (0 rows)
2. **PostgreSQL vitals_timeseries** - Only old test data (October 7-8, different patient)
3. **No production data** - Current system uses vitals_realtime only
4. **No code uses it** - Backend queries are broken (SQL bug) and unused
5. **Frontend never sees it** - No API endpoints serve from this table

**❌ What Breaks**:
- database.py `getHistoricalVitals()` function (already broken with SQL bug anyway)
- Nothing else - no production functionality relies on it

**✅ What We Gain**:
- Removes confusion (two tables with same name)
- Clears duplicate schema design
- Forces proper fix (query vitals_realtime instead)
- Saves ~184 kB disk space

---

## Recommended Action Plan

### Step 1: Backup (Optional)
```bash
# Backup PostgreSQL vitals_timeseries (if you want to keep test data)
pg_dump -h localhost -p 5432 -U hospital_user -d hospitaldb -t vitals_timeseries -f vitals_timeseries_backup.sql
```

### Step 2: Drop TimescaleDB vitals_timeseries (Empty)
```bash
cd hospital-backend
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://hospital_user:hospital123@localhost:5433/hospitaltimescale')
cur = conn.cursor()
cur.execute('DROP TABLE IF EXISTS vitals_timeseries CASCADE')
conn.commit()
print('✅ Dropped TimescaleDB vitals_timeseries')
cur.close()
conn.close()
"
```

### Step 3: Drop PostgreSQL vitals_timeseries (Old Test Data)
```bash
cd hospital-backend
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://hospital_user:hospital123@localhost:5432/hospitaldb')
cur = conn.cursor()
cur.execute('DROP TABLE IF EXISTS vitals_timeseries CASCADE')
conn.commit()
print('✅ Dropped PostgreSQL vitals_timeseries')
cur.close()
conn.close()
"
```

### Step 4: Fix database.py getHistoricalVitals()
```python
# Change from:
SELECT time as timestamp, value
FROM vitals_timeseries  # ❌ Wrong table
WHERE "patientId" = $1
  AND "vitalType" = $2
  AND time > NOW() - INTERVAL '%s hours'  # ❌ SQL bug

# Change to:
SELECT time as timestamp,
       CASE
         WHEN $2 = 'heartRate' THEN "heartRate"
         WHEN $2 = 'oxygenSaturation' THEN "oxygenSaturation"
         WHEN $2 = 'skinTemperature' THEN "skinTemperature"
         WHEN $2 = 'respiratoryRate' THEN "respiratoryRate"
       END as value
FROM vitals_realtime  # ✅ Correct table
WHERE "patientId" = $1
  AND time > NOW() - INTERVAL '$3 hours'  # ✅ Fixed SQL
ORDER BY time ASC
```

---

## Final Database Structure (After Cleanup)

### TimescaleDB (hospitaltimescale)
```
✅ vitals_realtime       - 270,414 rows (ACTIVE - vitals data)
✅ waveform_snapshots    - 225,007 rows (ACTIVE - ECG/EEG data)
✅ neural_events         - 0 rows (READY - alert infrastructure)
```

### PostgreSQL (hospitaldb)
```
✅ patients              - Patient demographics
✅ staff                 - Staff records
✅ devices               - Device registry
✅ deviceassignments     - Device-patient assignments
✅ medications           - Medication orders
✅ investigations        - Lab orders
... (other application tables)
```

**No vitals_timeseries** - Removed duplicate/unused table

---

## Verification After Cleanup

```bash
# Verify TimescaleDB tables
cd hospital-backend && python -c "
import psycopg2
conn = psycopg2.connect('postgresql://hospital_user:hospital123@localhost:5433/hospitaltimescale')
cur = conn.cursor()
cur.execute(\"\"\"
SELECT table_name, pg_size_pretty(pg_total_relation_size(table_name::text))
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name
\"\"\")
print('TimescaleDB Tables:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')
cur.close()
conn.close()
"
```

---

## Recommendation

**DROP BOTH vitals_timeseries TABLES**

**Reason**:
1. TimescaleDB version is empty (0 rows)
2. PostgreSQL version has only old test data (October 7-8, different patient)
3. No production data loss
4. Removes schema confusion
5. Forces proper fix (use vitals_realtime with correct SQL)

**Risk**: ✅ **ZERO RISK** - No production data in either table
