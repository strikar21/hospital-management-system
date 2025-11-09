"""
Database connection and configuration
"""

import asyncio
import asyncpg
from typing import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Database connection pools - Force reset for credential update
_connectionPool = None
_timescaledbPool = None

async def resetConnectionPools():
    """Reset connection pools to force re-connection with new credentials"""
    global _connectionPool, _timescaledbPool
    if _connectionPool:
        await _connectionPool.close()
        _connectionPool = None
    if _timescaledbPool:
        await _timescaledbPool.close()
        _timescaledbPool = None

async def getConnectionPool():
    """Get or create PostgreSQL database connection pool"""
    global _connectionPool

    if _connectionPool is None:
        try:
            logger.debug(f"Creating connection pool with URL: {settings.databaseUrl}")
            _connectionPool = await asyncpg.create_pool(
                settings.databaseUrl,
                min_size=2,  # Keep more connections ready
                max_size=20,  # Allow more concurrent connections
                command_timeout=30,  # Reduce timeout for faster failures
                server_settings={
                    'jit': 'off',  # Disable JIT for faster connection
                    'application_name': 'hospital_management'
                }
            )
            logger.info("✅ PostgreSQL connection pool created")
        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL pool: {e}")
            logger.error(f"Failed with URL: {settings.databaseUrl}")
            raise

    return _connectionPool

async def getTimescaleDbPool():
    """Get or create TimescaleDB connection pool for vitals data"""
    global _timescaledbPool

    if _timescaledbPool is None:
        try:
            _timescaledbPool = await asyncpg.create_pool(
                settings.timescaledbUrl,
                min_size=1,
                max_size=15,
                command_timeout=30,
                server_settings={
                    'jit': 'off',
                    'application_name': 'hospital_vitals'
                }
            )
            logger.info("✅ TimescaleDB connection pool created for vitals")
        except Exception as e:
            logger.error(f"❌ Failed to create TimescaleDB pool: {e}")
            raise
    
    return _timescaledbPool

@asynccontextmanager
async def getDbConnection():
    """Get PostgreSQL database connection context manager"""
    pool = await getConnectionPool()
    async with pool.acquire() as conn:
        yield conn

@asynccontextmanager
async def getTimescaleConnection():
    """Get TimescaleDB connection context manager for vitals data"""
    pool = await getTimescaleDbPool()
    async with pool.acquire() as conn:
        yield conn

async def migrateDeviceTable(conn):
    """Add missing columns to devices table for device management system"""
    try:
        # Add missing columns to devices table
        missingColumns = [
            ("name", "TEXT"),
            ("model", "TEXT"),
            ("manufacturer", "TEXT"),
            ("description", "TEXT")
        ]

        for columnName, columnType in missingColumns:
            try:
                await conn.execute(f"ALTER TABLE devices ADD COLUMN IF NOT EXISTS {columnName} {columnType}")
                logger.info(f"✅ Added column {columnName} to devices table")
            except Exception as e:
                logger.debug(f"Column {columnName} might already exist: {e}")

        # Update any existing devices that have null names
        await conn.execute("""
            UPDATE devices
            SET name = COALESCE(name, 'Device ' || id)
            WHERE name IS NULL
        """)

        logger.info("✅ Device table migration completed successfully")

    except Exception as e:
        logger.warning(f"⚠️ Device table migration error: {e}")


async def migrateInvestigationsTable(conn):
    """Add missing columns to investigations table for compliance tracking"""
    try:
        # Add missing columns to investigations table
        missingColumns = [
            ('"canEdit"', "BOOLEAN DEFAULT true"),
            ("urgency", "TEXT DEFAULT 'routine'"),
            ('"orderedAt"', "TIMESTAMPTZ")
        ]

        for columnName, columnType in missingColumns:
            try:
                await conn.execute(f"ALTER TABLE investigations ADD COLUMN IF NOT EXISTS {columnName} {columnType}")
                logger.info(f"✅ Added column {columnName} to investigations table")
            except Exception as e:
                logger.debug(f"Column {columnName} might already exist: {e}")

        logger.info("✅ Investigations table migration completed successfully")

    except Exception as e:
        logger.warning(f"⚠️ Investigations table migration error: {e}")


async def migrateMedicationsTable(conn):
    """Add missing columns to medications table for medication status tracking"""
    try:
        # Add missing columns to medications table
        missingColumns = [
            ('"modifiedBy"', "TEXT")
        ]

        for columnName, columnType in missingColumns:
            try:
                await conn.execute(f"ALTER TABLE medications ADD COLUMN IF NOT EXISTS {columnName} {columnType}")
                logger.info(f"✅ Added column {columnName} to medications table")
            except Exception as e:
                logger.debug(f"Column {columnName} might already exist: {e}")

        logger.info("✅ Medications table migration completed successfully")

    except Exception as e:
        logger.warning(f"⚠️ Medications table migration error: {e}")


async def migrateDeviceAssignmentsTable(conn):
    """Add missing audit trail columns to deviceassignments table"""
    try:
        # Add missing columns for device unassignment tracking
        missingColumns = [
            ('"unassignedBy"', "TEXT"),
            ('"unassignmentReason"', "TEXT")
        ]

        for columnName, columnType in missingColumns:
            try:
                await conn.execute(f"ALTER TABLE deviceassignments ADD COLUMN IF NOT EXISTS {columnName} {columnType}")
                logger.info(f"✅ Added column {columnName} to deviceassignments table")
            except Exception as e:
                logger.debug(f"Column {columnName} might already exist: {e}")

        logger.info("✅ Device assignments table migration completed successfully")

    except Exception as e:
        logger.warning(f"⚠️ Device assignments table migration error: {e}")


async def createTables():
    """Create PostgreSQL database tables"""

    # Force reset connection pools to ensure fresh connections
    await resetConnectionPools()

    tablesSql = """
        -- Staff table
        CREATE TABLE IF NOT EXISTS staff (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            email TEXT UNIQUE,
            "phoneNumber" TEXT,
            department TEXT,
            pin TEXT,
            password TEXT,
            "isActive" BOOLEAN DEFAULT true,
            "lastSeen" TIMESTAMPTZ,
            "nfcCardId" TEXT UNIQUE,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW(),
            "firstName" TEXT,
            "lastName" TEXT
        );
        
        -- Patients table
        CREATE TABLE IF NOT EXISTS patients (
            id TEXT PRIMARY KEY,
            "firstName" TEXT NOT NULL,
            "lastName" TEXT NOT NULL,
            "dateOfBirth" DATE,
            gender TEXT,
            "phoneNumber" TEXT,
            "emergencyContactName" TEXT,
            "emergencyContactPhone" TEXT,
            "bloodType" TEXT,
            allergies TEXT,
            "medicalHistory" TEXT,
            "currentMedications" TEXT,
            "admissionDate" TIMESTAMPTZ,
            "dischargeDate" TIMESTAMPTZ,
            "roomNumber" TEXT,
            "bedNumber" TEXT,
            -- Note: Device assignments tracked in deviceassignments table
            "attendingPhysician" TEXT,
            "nurseInCharge" TEXT,
            status TEXT DEFAULT 'active',
            "dischargeStatus" TEXT DEFAULT 'active',
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW(),
            "recommendedFrom" TEXT
        );
        
        -- Devices table
        CREATE TABLE IF NOT EXISTS devices (
            id TEXT PRIMARY KEY,
            "deviceType" TEXT NOT NULL,
            name TEXT NOT NULL,
            model TEXT,
            manufacturer TEXT,
            "serialNumber" TEXT UNIQUE NOT NULL,
            "macAddress" TEXT UNIQUE,
            "firmwareVersion" TEXT,
            "batteryLevel" INTEGER,
            status TEXT DEFAULT 'available',
            "lastSeen" TIMESTAMPTZ,
            -- Note: Device assignments tracked in deviceassignments table
            location TEXT,
            description TEXT,
            "calibrationDate" TIMESTAMPTZ,
            "nextMaintenanceDate" TIMESTAMPTZ,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Device Assignments table
        CREATE TABLE IF NOT EXISTS deviceassignments (
            id SERIAL PRIMARY KEY,
            "patientId" TEXT NOT NULL,
            "deviceId" TEXT NOT NULL,
            "assignedBy" TEXT NOT NULL,
            "assignedAt" TIMESTAMPTZ DEFAULT NOW(),
            "unassignedAt" TIMESTAMPTZ,
            "unassignedBy" TEXT,
            "unassignmentReason" TEXT,
            status TEXT DEFAULT 'active',
            notes TEXT
        );
        
        -- Audit Log table
        CREATE TABLE IF NOT EXISTS auditlog (
            id SERIAL PRIMARY KEY,
            "userId" TEXT NOT NULL,
            action TEXT NOT NULL,
            "resourceType" TEXT NOT NULL,
            "resourceId" TEXT,
            details TEXT,
            "ipAddress" TEXT,
            "userAgent" TEXT,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Medications table
        CREATE TABLE IF NOT EXISTS medications (
            id SERIAL PRIMARY KEY,
            "patientId" TEXT NOT NULL,
            name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            frequency TEXT NOT NULL,
            route TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            "startDate" TIMESTAMPTZ,
            "endDate" TIMESTAMPTZ,
            duration TEXT,
            "prescribedBy" TEXT NOT NULL,
            "createdBy" TEXT,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Medication Administrations table
        CREATE TABLE IF NOT EXISTS medicationadministrations (
            id TEXT PRIMARY KEY,
            "medicationId" INTEGER NOT NULL,
            "patientId" TEXT NOT NULL,
            "scheduledTime" TIMESTAMPTZ NOT NULL,
            "performedAt" TIMESTAMPTZ,
            "performedBy" TEXT,
            "dosageGiven" TEXT,
            route TEXT,
            status TEXT DEFAULT 'scheduled',
            notes TEXT,
            "createdBy" TEXT,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT fk_medicationadmin_medication FOREIGN KEY ("medicationId") REFERENCES medications(id) ON DELETE CASCADE
        );
        
        -- Investigations table
        CREATE TABLE IF NOT EXISTS investigations (
            id SERIAL PRIMARY KEY,
            "patientId" TEXT NOT NULL,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            "scheduledAt" TIMESTAMPTZ,
            "completedAt" TIMESTAMPTZ,
            priority TEXT DEFAULT 'routine',
            status TEXT DEFAULT 'ordered',
            "prescribedBy" TEXT,
            "performedBy" TEXT,
            results TEXT,
            notes TEXT,
            "canEdit" BOOLEAN DEFAULT true,
            urgency TEXT DEFAULT 'routine',
            "createdBy" TEXT,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Therapy table
        CREATE TABLE IF NOT EXISTS therapy (
            id SERIAL PRIMARY KEY,
            "patientId" TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            "startDate" TIMESTAMPTZ,
            "endDate" TIMESTAMPTZ,
            frequency TEXT,
            duration TEXT,
            status TEXT DEFAULT 'active',
            "prescribedBy" TEXT,
            notes TEXT,
            "createdBy" TEXT,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Therapy Sessions table
        CREATE TABLE IF NOT EXISTS therapysessions (
            id TEXT PRIMARY KEY,
            "therapyId" TEXT NOT NULL,
            "patientId" TEXT NOT NULL,
            "sessionNumber" INTEGER NOT NULL,
            "scheduledDate" TIMESTAMPTZ,
            "completedAt" TIMESTAMPTZ,
            "performedBy" TEXT,
            "sessionNotes" TEXT,
            status TEXT DEFAULT 'scheduled',
            duration TEXT,
            "createdBy" TEXT,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Patient Notes table
        CREATE TABLE IF NOT EXISTS patientnotes (
            id SERIAL PRIMARY KEY,
            "patientId" TEXT NOT NULL,
            content TEXT NOT NULL,
            "createdBy" TEXT NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            "editedBy" TEXT,
            "editedAt" TIMESTAMPTZ,
            "isEdited" BOOLEAN DEFAULT FALSE
        );

        -- Patient Alerts table
        CREATE TABLE IF NOT EXISTS patient_alerts (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            "patientId" TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'vital',
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            "vitalType" TEXT,
            "vitalValue" NUMERIC(10,2),
            "thresholdValue" NUMERIC(10,2),
            "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            "acknowledgedBy" TEXT,
            "acknowledgedAt" TIMESTAMPTZ,
            "resolvedBy" TEXT,
            "resolvedAt" TIMESTAMPTZ,
            "deletedAt" TIMESTAMPTZ,
            "createdBy" TEXT
        );

        -- Discharge Workflow table
        CREATE TABLE IF NOT EXISTS discharge_requests (
            id SERIAL PRIMARY KEY,
            "patientId" TEXT NOT NULL,
            status TEXT DEFAULT 'requested',
            reason TEXT,
            notes TEXT,
            "requestedBy" TEXT NOT NULL,
            "requestedAt" TIMESTAMPTZ DEFAULT NOW(),
            "approvedBy" TEXT,
            "approvedAt" TIMESTAMPTZ,
            "approvalNotes" TEXT,
            "performedBy" TEXT,
            "performedAt" TIMESTAMPTZ,
            "dischargeNotes" TEXT,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_discharge_requests_patient ON discharge_requests("patientId");
        CREATE INDEX IF NOT EXISTS idx_discharge_requests_status ON discharge_requests(status);

        -- Admission Recommendations table
        CREATE TABLE IF NOT EXISTS admissionrecommendations (
            id SERIAL PRIMARY KEY,
            "patientName" TEXT NOT NULL,
            age INTEGER,
            "dateOfBirth" DATE,
            gender TEXT NOT NULL,
            diagnosis TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'routine',
            department TEXT NOT NULL,
            "recommendedWard" TEXT NOT NULL,
            "assignedDoctor" TEXT NOT NULL,
            "recommendedBy" TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            weight NUMERIC,
            "admissionDate" DATE,
            "insuranceType" TEXT,
            "emergencyContact" TEXT,
            allergies TEXT,
            "admissionNotes" TEXT,
            "processedBy" TEXT,
            "processedAt" TIMESTAMPTZ,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT checkAgeOrDob CHECK (age IS NOT NULL OR "dateOfBirth" IS NOT NULL)
        );
        
        -- Beds table
        CREATE TABLE IF NOT EXISTS beds (
            id TEXT PRIMARY KEY,
            "bedNumber" TEXT NOT NULL,
            "roomNumber" TEXT NOT NULL,
            "wardType" TEXT NOT NULL,
            department TEXT NOT NULL,
            status TEXT DEFAULT 'available',
            "occupiedBy" TEXT,
            "lastCleaned" TIMESTAMPTZ,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW()
        );
        """
    
    try:
        async with getDbConnection() as conn:
            # Execute tables creation
            await conn.execute(tablesSql)
            logger.info("✅ Tables created successfully")
            
            # Add migrations for existing tables
            try:
                # Add dateOfBirth column to admissionrecommendations if it doesn't exist
                await conn.execute("""
                    ALTER TABLE admissionrecommendations
                    ADD COLUMN IF NOT EXISTS "dateOfBirth" DATE;
                """)

                # Modify age column to allow NULL (ignore error if already nullable)
                try:
                    await conn.execute("""
                        ALTER TABLE admissionrecommendations
                        ALTER COLUMN age DROP NOT NULL;
                    """)
                except:
                    pass  # Column might already be nullable
                
                logger.info("✅ Database migrations completed successfully")

                # Apply device table migrations for device management system
                await migrateDeviceTable(conn)

                # Apply investigations table migrations for compliance tracking
                await migrateInvestigationsTable(conn)

                # Apply medications table migrations for medication status tracking
                await migrateMedicationsTable(conn)

                # Apply device assignments table migrations for audit trail tracking
                await migrateDeviceAssignmentsTable(conn)

                # Create database indexes for performance optimization
                logger.info("🔄 Creating database indexes for performance optimization...")

                # Medication indexes (for patient medication history queries)
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_medications_patient ON medications("patientId")')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_medications_prescriber ON medications("prescribedBy")')

                # Investigation indexes (for patient investigation history queries)
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_investigations_patient ON investigations("patientId")')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_investigations_prescriber ON investigations("prescribedBy")')

                # Therapy indexes (for patient therapy history queries)
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_therapy_patient ON therapy("patientId")')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_therapy_prescribed ON therapy("prescribedBy")')

                # Patient notes indexes (for patient note history queries)
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_patientnotes_patient ON patientnotes("patientId")')

                # Patient alerts indexes (for alert dashboard queries)
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_patient_alerts_patient ON patient_alerts("patientId")')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_patient_alerts_status ON patient_alerts(status)')

                # Device assignment indexes (for watch management queries)
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_deviceassignments_patient ON deviceassignments("patientId")')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_deviceassignments_device ON deviceassignments("deviceId")')

                logger.info("✅ Database indexes created successfully (10 indexes)")

            except Exception as migrationError:
                logger.warning(f"⚠️ Migration warning (may be expected): {migrationError}")

        logger.info("✅ Database tables and indexes created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise

async def createTimescaleTables():
    """Create TimescaleDB hypertables for vitals data"""
    
    timescaleSql = """
    -- Enable TimescaleDB extension
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
    
    -- Create vitals_timeseries table (using camelCase schema)
    CREATE TABLE IF NOT EXISTS vitals_timeseries (
        time TIMESTAMPTZ NOT NULL,
        "patientId" TEXT NOT NULL,
        "deviceId" TEXT NOT NULL,
        "vitalType" TEXT NOT NULL,
        value DOUBLE PRECISION,
        unit TEXT,
        quality TEXT DEFAULT 'good',
        "rawData" JSONB,
        metadata JSONB
    );
    
    -- Convert to hypertable (only if not already a hypertable)
    SELECT create_hypertable('vitals_timeseries', 'time', if_not_exists => TRUE);
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_vitals_patient_time ON vitals_timeseries ("patientId", time);
    CREATE INDEX IF NOT EXISTS idx_vitals_device_time ON vitals_timeseries ("deviceId", time);
    CREATE INDEX IF NOT EXISTS idx_vitals_metric ON vitals_timeseries ("patientId", "vitalType", time);
    """
    
    try:
        async with getTimescaleConnection() as conn:
            await conn.execute(timescaleSql)
            logger.info("✅ TimescaleDB hypertables created successfully")
            
    except Exception as e:
        logger.error(f"❌ Failed to create TimescaleDB tables: {e}")

async def seedStaffCredentials():
    """
    Seed staff credentials for authentication testing
    """
    from .security import hash_pin, hash_password

    staffCredentials = [
        {
            "id": "DOC0001",
            "pin": hash_pin("1234"),
            "password": hash_password("doctor123")
        },
        {
            "id": "DOC0002",
            "pin": hash_pin("1235"),
            "password": hash_password("doctor124")
        },
        {
            "id": "NUR0001",
            "pin": hash_pin("5678"),
            "password": hash_password("nurse123")
        },
        {
            "id": "NUR0002",
            "pin": hash_pin("5679"),
            "password": hash_password("nurse124")
        },
        {
            "id": "ADM0001",
            "pin": hash_pin("9999"),
            "password": hash_password("admin123")
        },
        {
            "id": "PRV0001",
            "pin": hash_pin("1111"),
            "password": hash_password("prov123")
        },
        {
            "id": "TEC0001",
            "pin": hash_pin("2222"),
            "password": hash_password("tech123")
        }
    ]

    try:
        async with getDbConnection() as conn:
            for staff in staffCredentials:
                # Update existing staff with credentials
                result = await conn.execute(
                    "UPDATE staff SET pin = $1, password = $2 WHERE id = $3",
                    staff["pin"], staff["password"], staff["id"]
                )

                if result == "UPDATE 0":
                    logger.warning(f"⚠️ Staff member {staff['id']} not found in database")
                else:
                    logger.info(f"✅ Updated credentials for {staff['id']}")

            logger.info("✅ Staff credentials seeded successfully")

    except Exception as e:
        logger.error(f"❌ Failed to seed staff credentials: {e}")
        logger.warning("⚠️ Continuing without TimescaleDB - vitals storage may be limited")

# ========================================
# HISTORICAL VITALS QUERY METHODS
# For Component 1: Trend Analysis Alerts
# ========================================

async def getHistoricalVitals(
    patientId: str,
    vitalType: str,
    hoursBack: float = 24
) -> list:
    """
    Query TimescaleDB for historical vitals data

    Args:
        patientId: Patient identifier
        vitalType: Type of vital (heartRate, oxygenSaturation, temperature, respiratoryRate, etc.)
        hoursBack: Number of hours to look back (supports fractions, e.g., 0.5 for 30 minutes)

    Returns:
        List of dicts with 'timestamp' and 'value' keys
    """
    query = """
        SELECT time as timestamp, value
        FROM vitals_timeseries
        WHERE "patientId" = $1
          AND "vitalType" = $2
          AND time > NOW() - make_interval(hours => $3)
        ORDER BY time ASC
    """

    try:
        async with getTimescaleConnection() as conn:
            rows = await conn.fetch(query, patientId, vitalType, hoursBack)
            return [{'timestamp': row['timestamp'], 'value': row['value']} for row in rows]
    except Exception as e:
        logger.error(f"❌ Failed to get historical vitals for {patientId}/{vitalType}: {e}")
        return []

async def getVitalsTimeBuckets(
    patientId: str,
    vitalType: str,
    hoursBack: float = 24,
    bucketMinutes: int = 5
) -> list:
    """
    Get vitals aggregated into time buckets (for efficient trend analysis)

    Args:
        patientId: Patient identifier
        vitalType: Type of vital
        hoursBack: Number of hours to look back
        bucketMinutes: Size of time buckets in minutes

    Returns:
        List of dicts with 'bucket', 'avgValue', 'minValue', 'maxValue', 'count'
    """
    query = """
        SELECT time_bucket(($1 || ' minutes')::INTERVAL, time) AS bucket,
               AVG(value) as "avgValue",
               MIN(value) as "minValue",
               MAX(value) as "maxValue",
               COUNT(*) as count
        FROM vitals_timeseries
        WHERE "patientId" = $2
          AND "vitalType" = $3
          AND time > NOW() - make_interval(hours => $4)
        GROUP BY bucket
        ORDER BY bucket ASC
    """

    try:
        async with getTimescaleConnection() as conn:
            rows = await conn.fetch(query, bucketMinutes, patientId, vitalType, hoursBack)
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"❌ Failed to get vitals time buckets for {patientId}/{vitalType}: {e}")
        return []

# ========================================
# CROSS-PATIENT ANALYSIS METHODS
# For Component 2: System-Level Alerts
# ========================================

async def getDevicePoolStatus() -> dict:
    """
    Get current device pool availability status

    Returns:
        Dict with 'available', 'assigned', 'total', 'availabilityPercent'
    """
    query = """
        SELECT
            COUNT(*) FILTER (WHERE status = 'available') as available,
            COUNT(*) FILTER (WHERE status = 'assigned') as assigned,
            COUNT(*) as total
        FROM devices
        WHERE "deviceType" = 'ESP32_WATCH'
    """

    try:
        async with getDbConnection() as conn:
            result = await conn.fetchrow(query)
            total = result['total'] or 0
            available = result['available'] or 0
            assigned = result['assigned'] or 0

            return {
                'available': available,
                'assigned': assigned,
                'total': total,
                'availabilityPercent': (available / total * 100) if total > 0 else 0
            }
    except Exception as e:
        logger.error(f"❌ Failed to get device pool status: {e}")
        return {'available': 0, 'assigned': 0, 'total': 0, 'availabilityPercent': 0}

async def countPatientsWithCondition(
    wardId: str = None,
    condition: str = 'fever',
    timeWindowMinutes: int = 60
) -> int:
    """
    Count patients meeting a specific condition in time window

    Args:
        wardId: Optional ward filter (None = all wards)
        condition: 'fever' or 'spo2_declining'
        timeWindowMinutes: Time window to check

    Returns:
        Count of affected patients
    """

    if condition == 'fever':
        query = """
            SELECT COUNT(DISTINCT p.id)
            FROM patients p
            JOIN vitals_timeseries v ON p.id = v."patientId"
            WHERE ($1::TEXT IS NULL OR p."roomNumber" LIKE $1 || '%')
              AND v."vitalType" = 'temperature'
              AND v.value > 38.3
              AND v.time > NOW() - make_interval(mins => $2)
              AND p.status = 'active'
        """
    elif condition == 'spo2_declining':
        query = """
            WITH patient_spo2_trends AS (
                SELECT
                    p.id as "patientId",
                    FIRST_VALUE(v.value) OVER (PARTITION BY p.id ORDER BY v.time ASC) as "firstSpo2",
                    LAST_VALUE(v.value) OVER (PARTITION BY p.id ORDER BY v.time DESC ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as "lastSpo2"
                FROM patients p
                JOIN vitals_timeseries v ON p.id = v."patientId"
                WHERE ($1::TEXT IS NULL OR p."roomNumber" LIKE $1 || '%')
                  AND v."vitalType" = 'oxygenSaturation'
                  AND v.time > NOW() - make_interval(mins => $2)
                  AND p.status = 'active'
            )
            SELECT COUNT(DISTINCT "patientId")
            FROM patient_spo2_trends
            WHERE ("firstSpo2" - "lastSpo2") / "firstSpo2" > 0.05
        """
    else:
        return 0

    try:
        async with getTimescaleConnection() as conn:
            result = await conn.fetchval(query, wardId, timeWindowMinutes)
            return result or 0
    except Exception as e:
        logger.error(f"❌ Failed to count patients with condition {condition}: {e}")
        return 0

async def countRecentAdmissions(hoursBack: int = 24) -> int:
    """
    Count patients admitted in recent time period

    Args:
        hoursBack: Hours to look back

    Returns:
        Count of recent admissions
    """
    query = """
        SELECT COUNT(*)
        FROM patients
        WHERE "admissionDate" > NOW() - make_interval(hours => $1)
          AND status = 'active'
    """

    try:
        async with getDbConnection() as conn:
            result = await conn.fetchval(query, hoursBack)
            return result or 0
    except Exception as e:
        logger.error(f"❌ Failed to count recent admissions: {e}")
        return 0