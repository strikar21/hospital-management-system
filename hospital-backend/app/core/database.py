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
            logger.info(f"🔍 DEBUG: Creating connection pool with URL: {settings.databaseUrl}")
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
            logger.error(f"🔍 DEBUG: Failed with URL: {settings.databaseUrl}")
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
            "assignedDeviceId" TEXT,
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
            "assignedPatientId" TEXT,
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
            "medicationId" TEXT NOT NULL,
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
            "updatedAt" TIMESTAMPTZ DEFAULT NOW()
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
        
        -- Case Sheet Entries table
        CREATE TABLE IF NOT EXISTS casesheetentries (
            id SERIAL PRIMARY KEY,
            "patientId" TEXT NOT NULL,
            "entryType" TEXT NOT NULL,
            description TEXT NOT NULL,
            "performedBy" TEXT NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            "createdBy" TEXT,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW()
        );

        -- Patient Alerts table
        CREATE TABLE IF NOT EXISTS patient_alerts (
            id TEXT PRIMARY KEY,
            "patientId" TEXT NOT NULL,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            status TEXT DEFAULT 'active',
            "performedBy" TEXT,
            "performedAt" TIMESTAMPTZ,
            "createdBy" TEXT,
            "createdAt" TIMESTAMPTZ DEFAULT NOW(),
            "updatedAt" TIMESTAMPTZ DEFAULT NOW()
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


            except Exception as migrationError:
                logger.warning(f"⚠️ Migration warning (may be expected): {migrationError}")
        
        logger.info("✅ Database tables created successfully")
        
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