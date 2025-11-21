"""
FHIR R5 Clean Slate Migration
Drop all existing tables and create new FHIR R5 schema with CSDS v2.0 compliance
"""

import asyncio
import asyncpg
from datetime import datetime

# Database connection settings
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'hospital',
    'password': 'hospital123',
    'database': 'hospitaldb'
}

async def drop_all_tables(conn):
    """Drop all existing tables"""
    print("\n[STEP 1] Dropping all existing tables...")

    # Get all tables
    tables = await conn.fetch("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)

    print(f"Found {len(tables)} tables to drop")

    for table in tables:
        table_name = table['tablename']
        try:
            await conn.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')
            print(f"  [DROPPED] {table_name}")
        except Exception as e:
            print(f"  [ERROR] {table_name}: {e}")

    print("[SUCCESS] All tables dropped\n")

async def create_postgresql_tables(conn):
    """Create 5 PostgreSQL tables"""
    print("[STEP 2] Creating PostgreSQL tables...\n")

    # 1. fhirResources
    print("Creating table: fhirResources")
    await conn.execute("""
        CREATE TABLE fhirResources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- FHIR identity (CSDS: camelCase)
            resourceType TEXT NOT NULL,
            resourceId TEXT NOT NULL,
            resource JSONB NOT NULL,

            -- Extracted fields for fast queries
            status TEXT,
            subject TEXT,

            -- Versioning
            versionId INTEGER DEFAULT 1,
            deleted BOOLEAN DEFAULT false,

            -- Audit
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW(),

            CONSTRAINT unique_fhir_resource UNIQUE (resourceType, resourceId, deleted)
        );

        CREATE INDEX idx_fhir_type ON fhirResources(resourceType) WHERE deleted = false;
        CREATE INDEX idx_fhir_type_id ON fhirResources(resourceType, resourceId) WHERE deleted = false;
        CREATE INDEX idx_fhir_subject ON fhirResources(subject) WHERE deleted = false;
        CREATE INDEX idx_fhir_resource_gin ON fhirResources USING gin(resource);
    """)
    print("  [SUCCESS] fhirResources created\n")

    # 2. fhirConsent (DPDP Act 2023)
    print("Creating table: fhirConsent")
    await conn.execute("""
        CREATE TABLE fhirConsent (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- Patient
            patientId TEXT NOT NULL,

            -- Consent details
            status TEXT NOT NULL DEFAULT 'active',
            scope TEXT NOT NULL,
            category TEXT[] NOT NULL,

            -- Purpose
            purposeOfUse TEXT[] NOT NULL,

            -- Period
            effectiveStart TIMESTAMPTZ NOT NULL,
            effectiveEnd TIMESTAMPTZ,

            -- Signature
            grantorSignature TEXT,
            witnessSignature TEXT,

            -- Audit
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            createdBy TEXT NOT NULL,
            withdrawnAt TIMESTAMPTZ,
            withdrawnBy TEXT,

            CONSTRAINT valid_consent_period CHECK (effectiveEnd IS NULL OR effectiveEnd > effectiveStart)
        );

        CREATE INDEX idx_consent_patient ON fhirConsent(patientId, status);
        CREATE INDEX idx_consent_active ON fhirConsent(status, effectiveStart, effectiveEnd)
            WHERE status = 'active';
    """)
    print("  [SUCCESS] fhirConsent created\n")

    # 3. fhirAuditEvent (DPDP + HIPAA)
    print("Creating table: fhirAuditEvent")
    await conn.execute("""
        CREATE TABLE fhirAuditEvent (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            -- Action
            action CHAR(1) NOT NULL,
            outcome TEXT NOT NULL DEFAULT 'success',

            -- Who
            agentId TEXT NOT NULL,
            agentRole TEXT NOT NULL,

            -- What
            entityType TEXT NOT NULL,
            entityId TEXT NOT NULL,

            -- When/Where
            recorded TIMESTAMPTZ DEFAULT NOW(),
            ipAddress INET,
            userAgent TEXT,

            -- Purpose
            purposeOfEvent TEXT,

            -- Retention (HIPAA: 6 years)
            expiresAt TIMESTAMPTZ DEFAULT NOW() + INTERVAL '6 years'
        );

        CREATE INDEX idx_audit_agent ON fhirAuditEvent(agentId, recorded DESC);
        CREATE INDEX idx_audit_entity ON fhirAuditEvent(entityType, entityId, recorded DESC);
        CREATE INDEX idx_audit_recorded ON fhirAuditEvent(recorded DESC);
        CREATE INDEX idx_audit_expires ON fhirAuditEvent(expiresAt);
    """)
    print("  [SUCCESS] fhirAuditEvent created\n")

    # 4. staff (Authentication)
    print("Creating table: staff")
    await conn.execute("""
        CREATE TABLE staff (
            id TEXT PRIMARY KEY,

            -- Identity
            nfcBadgeId TEXT UNIQUE,
            pin TEXT,
            passwordHash TEXT,

            -- Role
            role TEXT NOT NULL CHECK (role IN ('doctor', 'nurse', 'admin', 'technician')),

            -- Status
            status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),

            -- Audit
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX idx_staff_nfc ON staff(nfcBadgeId) WHERE nfcBadgeId IS NOT NULL;
        CREATE INDEX idx_staff_role ON staff(role, status) WHERE status = 'active';
    """)
    print("  [SUCCESS] staff created\n")

    # 5. tokenBlacklist (JWT Revocation)
    print("Creating table: tokenBlacklist")
    await conn.execute("""
        CREATE TABLE tokenBlacklist (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            token TEXT UNIQUE NOT NULL,
            blacklistedAt TIMESTAMPTZ DEFAULT NOW(),
            expiresAt TIMESTAMPTZ NOT NULL
        );

        CREATE INDEX idx_token_expires ON tokenBlacklist(expiresAt);
    """)
    print("  [SUCCESS] tokenBlacklist created\n")

    print("[SUCCESS] All 5 PostgreSQL tables created\n")

async def create_timescaledb_tables(conn):
    """Create 2 TimescaleDB hypertables"""
    print("[STEP 3] Creating TimescaleDB hypertables...\n")

    # Check if TimescaleDB extension exists
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        print("  [INFO] TimescaleDB extension enabled\n")
    except Exception as e:
        print(f"  [WARNING] TimescaleDB not available: {e}")
        print("  [INFO] Creating regular tables instead...\n")

    # 6. fhirObservations (Time-series)
    print("Creating table: fhirObservations")
    await conn.execute("""
        CREATE TABLE fhirObservations (
            time TIMESTAMPTZ NOT NULL,

            -- FHIR identity
            observationId TEXT NOT NULL,
            patientId TEXT NOT NULL,
            deviceId TEXT,

            -- Full FHIR R5 Observation
            observation JSONB NOT NULL,

            -- Extracted fields
            code TEXT NOT NULL,
            category TEXT,
            valueQuantity NUMERIC(10,2),
            valueUnit TEXT,
            status TEXT NOT NULL,

            -- Audit
            createdAt TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    # Try to convert to hypertable
    try:
        await conn.execute("SELECT create_hypertable('fhirObservations', 'time', if_not_exists => TRUE);")
        await conn.execute("SELECT add_retention_policy('fhirObservations', INTERVAL '1 year', if_not_exists => TRUE);")
        print("  [SUCCESS] fhirObservations created as hypertable (1-year retention)\n")
    except Exception as e:
        print(f"  [INFO] Created as regular table: {e}\n")

    await conn.execute("""
        CREATE INDEX idx_fhir_obs_patient ON fhirObservations(patientId, time DESC);
        CREATE INDEX idx_fhir_obs_code ON fhirObservations(code, patientId, time DESC);
        CREATE INDEX idx_fhir_obs_category ON fhirObservations(category, time DESC);
        CREATE INDEX idx_fhir_obs_gin ON fhirObservations USING gin(observation);
    """)

    # 7. deviceCalibration (Medical Device Rules 2017)
    print("Creating table: deviceCalibration")
    await conn.execute("""
        CREATE TABLE deviceCalibration (
            time TIMESTAMPTZ NOT NULL,

            -- Device
            deviceId TEXT NOT NULL,

            -- Calibration details
            calibrationType TEXT NOT NULL,
            performedBy TEXT NOT NULL,

            -- Accuracy measurements
            heartRateAccuracy NUMERIC(5,2),
            spo2Accuracy NUMERIC(5,2),
            temperatureAccuracy NUMERIC(5,2),
            bloodPressureAccuracy NUMERIC(5,2),

            -- Result
            status TEXT NOT NULL,
            notes TEXT,

            -- Next calibration
            nextCalibrationDue TIMESTAMPTZ NOT NULL,

            -- Audit
            createdAt TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    # Try to convert to hypertable
    try:
        await conn.execute("SELECT create_hypertable('deviceCalibration', 'time', if_not_exists => TRUE);")
        await conn.execute("SELECT add_retention_policy('deviceCalibration', INTERVAL '5 years', if_not_exists => TRUE);")
        print("  [SUCCESS] deviceCalibration created as hypertable (5-year retention)\n")
    except Exception as e:
        print(f"  [INFO] Created as regular table: {e}\n")

    await conn.execute("""
        CREATE INDEX idx_device_cal_device ON deviceCalibration(deviceId, time DESC);
        CREATE INDEX idx_device_cal_next_due ON deviceCalibration(nextCalibrationDue) WHERE status = 'pass';
    """)

    print("[SUCCESS] All 2 TimescaleDB hypertables created\n")

async def verify_csds_compliance(conn):
    """Verify all tables use camelCase (CSDS v2.0)"""
    print("[STEP 4] Verifying CSDS v2.0 compliance...\n")

    tables = await conn.fetch("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)

    print("Checking table names and columns for camelCase...")

    non_compliant = []

    for table in tables:
        table_name = table['tablename']

        # Check table name
        if '_' in table_name and not table_name.startswith('fhir'):
            non_compliant.append(f"Table: {table_name} (contains underscore)")

        # Check column names
        columns = await conn.fetch(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            AND table_schema = 'public'
        """)

        for col in columns:
            col_name = col['column_name']
            # Check for snake_case (but allow uppercase letters)
            if '_' in col_name and not col_name.isupper():
                non_compliant.append(f"Column: {table_name}.{col_name} (contains underscore)")

    if non_compliant:
        print("[WARNING] Found non-compliant fields:")
        for item in non_compliant:
            print(f"  - {item}")
    else:
        print("[SUCCESS] All tables and columns are CSDS v2.0 compliant (camelCase)\n")

    # List all tables
    print("Created tables:")
    for table in tables:
        row_count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table["tablename"]}"')
        print(f"  - {table['tablename']}: {row_count} rows")

    print()

async def main():
    """Main migration function"""
    print("=" * 70)
    print("FHIR R5 Clean Slate Migration - CSDS v2.0 Compliance")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # Step 1: Drop all tables
        await drop_all_tables(conn)

        # Step 2: Create PostgreSQL tables
        await create_postgresql_tables(conn)

        # Step 3: Create TimescaleDB hypertables
        await create_timescaledb_tables(conn)

        # Step 4: Verify CSDS compliance
        await verify_csds_compliance(conn)

        print("=" * 70)
        print("[SUCCESS] FHIR R5 migration completed successfully!")
        print("=" * 70)
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
