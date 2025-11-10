# Schema Comparison: Fresh Server vs Current Database

## Question: Will a new server have all the columns I have now?

**Short Answer**: **NO** - You would need to make many changes. The `createTables()` function in `database.py` is **MISSING 26 TABLES** that exist in your current database.

---

## Current Database Status

**Total Tables in Current Database**: 40 tables
**Tables in `createTables()` Function**: 14 tables
**Missing from Init Code**: **26 tables** (65% missing!)

---

## Tables Comparison

### ✅ Tables PRESENT in createTables():

1. **staff** - ✅ All columns match
2. **patients** - ⚠️ **MISSING**: `mrn`, `weight`, `diagnosis` columns
3. **devices** - ⚠️ **MISSING**: Many maintenance/calibration columns
4. **deviceassignments** - ✅ Mostly complete (migrations add missing fields)
5. **auditlog** - ✅ Complete
6. **medications** - ⚠️ **MISSING**: `modifiedBy`, `createdBy` (added by migration)
7. **medicationadministrations** - ⚠️ **MISSING**: `createdBy` column
8. **investigations** - ⚠️ **MISSING**: `performedBy`, `performedAt`, `createdBy` (migrations add some)
9. **therapy** - ⚠️ **MISSING**: `createdBy` column
10. **therapysessions** - ⚠️ **MISSING**: Integer type issue for `therapyId` (should be INTEGER, init creates TEXT)
11. **patientnotes** - ✅ Complete
12. **patient_alerts** - ⚠️ **MISSING**: Many columns (deviceId, source, alertTimestamp, category, confidence, context, resolvedAt, etc.)
13. **discharge_requests** - ✅ Complete
14. **admissionrecommendations** - ✅ Complete (with migration)
15. **beds** - ✅ Complete

### ❌ Tables MISSING from createTables():

16. **atomic_transactions** - ❌ NOT IN INIT
17. **caseEntries** - ❌ NOT IN INIT
18. **deviceBaselines** - ❌ NOT IN INIT
19. **deviceCalibration** - ❌ NOT IN INIT
20. **deviceMaintenanceHistory** - ❌ NOT IN INIT
21. **device_certificates** - ❌ NOT IN INIT
22. **device_mac_mapping** - ❌ NOT IN INIT
23. **devices_enriched** (VIEW) - ❌ NOT IN INIT
24. **impedancereadings** - ❌ NOT IN INIT
25. **medical_operations** - ❌ NOT IN INIT
26. **patientstates** - ❌ NOT IN INIT
27. **provisioning_codes** - ❌ NOT IN INIT
28. **therapies_legacy** - ❌ NOT IN INIT (legacy table)
29. **token_blacklist** - ❌ NOT IN INIT
30. **watchremovalevents** - ❌ NOT IN INIT

---

## Detailed Missing Schema

### 1. **atomic_transactions** (Atomic Operations)
```sql
CREATE TABLE IF NOT EXISTS atomic_transactions (
    id UUID PRIMARY KEY,
    "transactionId" UUID NOT NULL,
    "patientId" TEXT NOT NULL,
    "operationType" VARCHAR NOT NULL,
    "operationData" JSONB NOT NULL,
    status VARCHAR NOT NULL,
    "startedAt" TIMESTAMPTZ NOT NULL,
    "completedAt" TIMESTAMPTZ,
    "errorMessage" TEXT,
    "retryCount" INTEGER
);
```

### 2. **caseEntries** (Patient Case Notes)
```sql
CREATE TABLE IF NOT EXISTS "caseEntries" (
    id UUID PRIMARY KEY,
    "patientId" TEXT NOT NULL,
    "entryType" TEXT NOT NULL,
    description TEXT NOT NULL,
    findings TEXT,
    recommendations TEXT,
    "followUpDate" DATE,
    severity TEXT,
    category TEXT,
    "createdBy" TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    "createdAt" TIMESTAMPTZ NOT NULL,
    "updatedAt" TIMESTAMPTZ NOT NULL,
    "deletedAt" TIMESTAMPTZ,
    "performedBy" TEXT
);
```

### 3. **deviceBaselines** (Device Performance Baselines)
```sql
CREATE TABLE IF NOT EXISTS "deviceBaselines" (
    "baselineId" SERIAL PRIMARY KEY,
    "deviceId" TEXT NOT NULL,
    "batteryDrainRatePerHour" DOUBLE PRECISION,
    "batteryHealthPercentage" INTEGER,
    "heartRateMean" DOUBLE PRECISION,
    "heartRateStdDev" DOUBLE PRECISION,
    "spo2Mean" DOUBLE PRECISION,
    "spo2StdDev" DOUBLE PRECISION,
    "temperatureMean" DOUBLE PRECISION,
    "temperatureStdDev" DOUBLE PRECISION,
    "systolicBpMean" DOUBLE PRECISION,
    "systolicBpStdDev" DOUBLE PRECISION,
    "diastolicBpMean" DOUBLE PRECISION,
    "diastolicBpStdDev" DOUBLE PRECISION,
    "baselineCalculatedAt" TIMESTAMP,
    "baselineUpdatedAt" TIMESTAMP,
    "sampleCount" INTEGER,
    "calculationPeriodDays" INTEGER
);
```

### 4. **deviceCalibration** (Calibration Records)
```sql
CREATE TABLE IF NOT EXISTS "deviceCalibration" (
    "calibrationId" SERIAL PRIMARY KEY,
    "deviceId" TEXT NOT NULL,
    "calibratedAt" TIMESTAMP NOT NULL,
    "calibratedBy" TEXT,
    "calibrationType" TEXT,
    "sensorType" TEXT,
    notes TEXT,
    "expiresAt" TIMESTAMP,
    "createdAt" TIMESTAMP
);
```

### 5. **deviceMaintenanceHistory** (Maintenance Logs)
```sql
CREATE TABLE IF NOT EXISTS "deviceMaintenanceHistory" (
    "maintenanceId" SERIAL PRIMARY KEY,
    "deviceId" TEXT NOT NULL,
    "maintenanceType" TEXT NOT NULL,
    "performedAt" TIMESTAMP NOT NULL,
    "performedBy" TEXT,
    notes TEXT,
    "nextMaintenanceDue" TIMESTAMP,
    cost NUMERIC,
    "createdAt" TIMESTAMP
);
```

### 6. **device_certificates** (TLS Certificates for ESP32)
```sql
CREATE TABLE IF NOT EXISTS device_certificates (
    id SERIAL PRIMARY KEY,
    "deviceId" VARCHAR NOT NULL,
    "certificatePem" TEXT NOT NULL,
    "issuedAt" TIMESTAMPTZ DEFAULT NOW(),
    "expiresAt" TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    "revokedAt" TIMESTAMPTZ,
    "revokedBy" VARCHAR,
    "revocationReason" TEXT,
    "macAddress" VARCHAR NOT NULL,
    "serialNumber" VARCHAR
);
```

### 7. **device_mac_mapping** (MAC to Device ID Mapping)
```sql
CREATE TABLE IF NOT EXISTS device_mac_mapping (
    "macAddress" TEXT PRIMARY KEY,
    "deviceId" TEXT NOT NULL,
    "createdAt" TIMESTAMP,
    "updatedAt" TIMESTAMP
);
```

### 8. **devices_enriched** (View - Not a Table)
This is a **VIEW** that joins `devices`, `deviceassignments`, and `patients`.
Would need to be recreated with a `CREATE VIEW` statement.

### 9. **impedancereadings** (Impedance Tracking)
```sql
CREATE TABLE IF NOT EXISTS impedancereadings (
    readingid SERIAL PRIMARY KEY,
    patientid TEXT NOT NULL,
    deviceid TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    impedance DOUBLE PRECISION NOT NULL
);
```

### 10. **medical_operations** (Idempotency Tracking)
```sql
CREATE TABLE IF NOT EXISTS medical_operations (
    id UUID PRIMARY KEY,
    "idempotencyKey" VARCHAR NOT NULL UNIQUE,
    "operationType" VARCHAR NOT NULL,
    "patientId" TEXT NOT NULL,
    result JSONB,
    status VARCHAR NOT NULL,
    "createdAt" TIMESTAMPTZ NOT NULL,
    "completedAt" TIMESTAMPTZ
);
```

### 11. **patientstates** (Alert State Tracking)
```sql
CREATE TABLE IF NOT EXISTS patientstates (
    stateid SERIAL PRIMARY KEY,
    patientid TEXT NOT NULL UNIQUE,
    tachycardiastarttime TIMESTAMP,
    tachycardiaalertsent BOOLEAN,
    bradycardiastarttime TIMESTAMP,
    bradycardiaalertsent BOOLEAN,
    hypotensionstarttime TIMESTAMP,
    hypotensionalertsent BOOLEAN,
    hypoxiastarttime TIMESTAMP,
    hypoxiaalertsent BOOLEAN,
    feverstarttime TIMESTAMP,
    feveralertsent BOOLEAN,
    hypothermiastarttime TIMESTAMP,
    hypothermiaalertsent BOOLEAN,
    lastvitalstimestamp TIMESTAMP,
    novitalsalertsent BOOLEAN,
    connectiondrops JSONB,
    createdat TIMESTAMP,
    updatedat TIMESTAMP
);
```

### 12. **provisioning_codes** (Device Provisioning)
```sql
CREATE TABLE IF NOT EXISTS provisioning_codes (
    code VARCHAR PRIMARY KEY,
    "technicianId" VARCHAR NOT NULL,
    "createdAt" TIMESTAMPTZ DEFAULT NOW(),
    "expiresAt" TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    "usedAt" TIMESTAMPTZ,
    "deviceId" VARCHAR
);
```

### 13. **token_blacklist** (JWT Token Revocation)
```sql
CREATE TABLE IF NOT EXISTS token_blacklist (
    token TEXT PRIMARY KEY,
    blacklisted_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);
```

### 14. **watchremovalevents** (Watch Removal Tracking)
```sql
CREATE TABLE IF NOT EXISTS watchremovalevents (
    eventid SERIAL PRIMARY KEY,
    patientid TEXT NOT NULL,
    deviceid TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    duration INTEGER,
    reason TEXT
);
```

---

## Column Mismatches in Existing Tables

### **patients** table - Missing Columns:
- `mrn` VARCHAR (Medical Record Number)
- `weight` NUMERIC
- `diagnosis` TEXT

### **patient_alerts** table - Missing Many Columns:
Current init only has:
```sql
id, patientId, type, message, severity, status,
vitalType, vitalValue, thresholdValue, createdAt,
acknowledgedBy, acknowledgedAt, resolvedBy, resolvedAt,
deletedAt, createdBy
```

Missing from init:
- `deviceId` TEXT
- `source` TEXT NOT NULL (e.g., 'ESP32', 'Backend')
- `alertTimestamp` TIMESTAMP NOT NULL
- `category` TEXT
- `confidence` DOUBLE PRECISION
- `context` JSONB

### **devices** table - Missing Maintenance Columns:
- `lastCalibrationDate` TIMESTAMP
- `calibrationDueDate` TIMESTAMP
- `batteryHealthPercentage` INTEGER
- `totalDisconnects` INTEGER
- `lastCommandSentAt` TIMESTAMP
- `lastCommandAckAt` TIMESTAMP

### **therapysessions** table - Wrong Data Type:
- `therapyId` should be INTEGER (to match therapy table FK)
- Init creates it as TEXT

---

## Impact Analysis

### If You Create a New Server:

❌ **Critical Features That Won't Work:**
1. **Device Provisioning** - No provisioning_codes table
2. **TLS Certificates** - No device_certificates table
3. **Case Sheet Entries** - No caseEntries table
4. **Alert State Tracking** - No patientstates table
5. **Device Maintenance** - No maintenance tables
6. **Idempotency** - No medical_operations table
7. **Token Revocation** - No token_blacklist table
8. **Impedance Tracking** - No impedancereadings table
9. **Watch Removal Events** - No watchremovalevents table
10. **Device Enriched View** - No devices_enriched view

⚠️ **Partial Features:**
- Patients missing MRN, weight, diagnosis fields
- Alerts missing deviceId, source, category fields
- Devices missing maintenance tracking fields

---

## What You Need to Do

### Option 1: Update createTables() Function (RECOMMENDED)

Add all 26 missing tables to the `createTables()` function in [database.py](hospital-backend/app/core/database.py).

**Pros:**
- ✅ Complete schema on fresh install
- ✅ No manual migrations needed
- ✅ One source of truth

**Cons:**
- ❌ Large one-time effort (~2-3 hours)
- ❌ Need to extract schema from production DB

### Option 2: Create Comprehensive SQL Migration Files

Create new SQL migration files that would be run on a fresh server.

**Pros:**
- ✅ Keep history of schema changes
- ✅ Can be version controlled

**Cons:**
- ❌ Need to build migration runner
- ❌ Current system doesn't use SQL migrations
- ❌ Adds complexity

### Option 3: Export/Import Schema from Production

Use `pg_dump` to export schema and import on new server.

**Pros:**
- ✅ Fastest solution
- ✅ Guaranteed accuracy

**Cons:**
- ❌ Not reproducible
- ❌ Can't version control
- ❌ Manual process

---

## Recommended Action Plan

### Step 1: Export Current Schema
```bash
pg_dump -h localhost -U hospital_user -d hospitaldb --schema-only --no-owner --no-privileges > current_schema.sql
```

### Step 2: Extract Table Definitions
Review `current_schema.sql` and extract CREATE TABLE statements for all 26 missing tables.

### Step 3: Update database.py
Add all missing tables to `createTables()` function, ensuring camelCase column names.

### Step 4: Add Missing Columns
Update existing table definitions in `createTables()` to include all missing columns.

### Step 5: Test on Fresh Database
```bash
# Drop and recreate test database
dropdb test_hospitaldb
createdb test_hospitaldb
# Run backend to test schema creation
python main.py
```

### Step 6: Verify Schema Match
```bash
# Compare schemas
pg_dump -h localhost -U hospital_user -d hospitaldb --schema-only > prod_schema.sql
pg_dump -h localhost -U hospital_user -d test_hospitaldb --schema-only > test_schema.sql
diff prod_schema.sql test_schema.sql
```

---

## Summary

**Answer**: NO, a fresh server will NOT have all the columns and tables you have now.

**Missing**: 26 tables (65% of your schema)
**Action Required**: Update `createTables()` function with all missing tables and columns
**Estimated Effort**: 2-3 hours to update schema init code

**Critical**: Without these tables, major features like device provisioning, case sheets, alerts, and maintenance tracking will fail.

---

## Next Steps

Would you like me to:
1. Export your current schema using `pg_dump`
2. Create updated `createTables()` function with all missing tables
3. Generate migration code to add missing columns to existing tables
4. Create a validation script to compare schemas

Let me know how you'd like to proceed!
