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

# Database connection pools
_connection_pool = None
_timescaledb_pool = None

async def get_connection_pool():
    """Get or create PostgreSQL database connection pool"""
    global _connection_pool
    
    if _connection_pool is None:
        try:
            _connection_pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("✅ PostgreSQL connection pool created")
        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL pool: {e}")
            raise
    
    return _connection_pool

async def get_timescaledb_pool():
    """Get or create TimescaleDB connection pool for vitals data"""
    global _timescaledb_pool
    
    if _timescaledb_pool is None:
        try:
            _timescaledb_pool = await asyncpg.create_pool(
                settings.timescaledb_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("✅ TimescaleDB connection pool created for vitals")
        except Exception as e:
            logger.error(f"❌ Failed to create TimescaleDB pool: {e}")
            raise
    
    return _timescaledb_pool

@asynccontextmanager
async def get_db_connection():
    """Get PostgreSQL database connection context manager"""
    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        yield conn

@asynccontextmanager
async def get_timescale_connection():
    """Get TimescaleDB connection context manager for vitals data"""
    pool = await get_timescaledb_pool()
    async with pool.acquire() as conn:
        yield conn

async def create_tables():
    """Create PostgreSQL database tables"""
    
    tables_sql = """
        -- Staff table
        CREATE TABLE IF NOT EXISTS staff (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT UNIQUE,
            phoneNumber TEXT,
            department TEXT,
            pin TEXT,
            password TEXT,
            isActive BOOLEAN DEFAULT true,
            lastSeen TIMESTAMPTZ,
            nfcCardId TEXT UNIQUE,
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Patients table
        CREATE TABLE IF NOT EXISTS patients (
            id TEXT PRIMARY KEY,
            firstname TEXT NOT NULL,
            lastname TEXT NOT NULL,
            dateofbirth DATE,
            gender TEXT,
            phonenumber TEXT,
            emergencycontactname TEXT,
            emergencycontactphone TEXT,
            bloodtype TEXT,
            allergies TEXT,
            medicalhistory TEXT,
            currentmedications TEXT,
            admissiondate TIMESTAMPTZ,
            dischargedate TIMESTAMPTZ,
            roomnumber TEXT,
            bednumber TEXT,
            assigneddeviceid TEXT,
            attendingphysician TEXT,
            nurseincharge TEXT,
            status TEXT DEFAULT 'active',
            dischargerstatus TEXT DEFAULT 'active',
            createdat TIMESTAMPTZ DEFAULT NOW(),
            updatedat TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Devices table
        CREATE TABLE IF NOT EXISTS devices (
            id TEXT PRIMARY KEY,
            deviceType TEXT NOT NULL,
            serialNumber TEXT UNIQUE NOT NULL,
            macAddress TEXT UNIQUE,
            firmwareVersion TEXT,
            batteryLevel INTEGER,
            status TEXT DEFAULT 'available',
            lastSeen TIMESTAMPTZ,
            assignedPatientId TEXT,
            location TEXT,
            calibrationDate TIMESTAMPTZ,
            nextMaintenanceDate TIMESTAMPTZ,
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Device Assignments table
        CREATE TABLE IF NOT EXISTS deviceAssignments (
            id SERIAL PRIMARY KEY,
            patientId TEXT NOT NULL,
            deviceId TEXT NOT NULL,
            assignedBy TEXT NOT NULL,
            assignedAt TIMESTAMPTZ DEFAULT NOW(),
            unassignedAt TIMESTAMPTZ,
            status TEXT DEFAULT 'active',
            notes TEXT
        );
        
        -- Audit Log table
        CREATE TABLE IF NOT EXISTS auditLog (
            id SERIAL PRIMARY KEY,
            userId TEXT NOT NULL,
            action TEXT NOT NULL,
            resourceType TEXT NOT NULL,
            resourceId TEXT,
            details TEXT,
            ipAddress TEXT,
            userAgent TEXT,
            timestamp TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Medications table
        CREATE TABLE IF NOT EXISTS medications (
            id SERIAL PRIMARY KEY,
            patientId TEXT NOT NULL,
            name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            frequency TEXT NOT NULL,
            route TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            startDate TIMESTAMPTZ,
            endDate TIMESTAMPTZ,
            duration TEXT,
            prescribedBy TEXT NOT NULL,
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Medication Administrations table
        CREATE TABLE IF NOT EXISTS medicationAdministrations (
            id TEXT PRIMARY KEY,
            medicationId TEXT NOT NULL,
            patientId TEXT NOT NULL,
            scheduledTime TIMESTAMPTZ NOT NULL,
            administeredAt TIMESTAMPTZ,
            administeredBy TEXT,
            dosageGiven TEXT,
            route TEXT,
            status TEXT DEFAULT 'scheduled',
            notes TEXT,
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Investigations table  
        CREATE TABLE IF NOT EXISTS investigations (
            id SERIAL PRIMARY KEY,
            patientId TEXT NOT NULL,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            scheduledAt TIMESTAMPTZ,
            completedAt TIMESTAMPTZ,
            priority TEXT DEFAULT 'routine',
            status TEXT DEFAULT 'ordered',
            performedBy TEXT,
            results TEXT,
            notes TEXT,
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Therapy table
        CREATE TABLE IF NOT EXISTS therapy (
            id SERIAL PRIMARY KEY,
            patientId TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            startDate TIMESTAMPTZ,
            endDate TIMESTAMPTZ,
            frequency TEXT,
            duration TEXT,
            status TEXT DEFAULT 'active',
            performedBy TEXT,
            notes TEXT,
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Therapy Sessions table
        CREATE TABLE IF NOT EXISTS therapySessions (
            id TEXT PRIMARY KEY,
            therapyId TEXT NOT NULL,
            patientId TEXT NOT NULL,
            sessionNumber INTEGER NOT NULL,
            scheduledDate TIMESTAMPTZ,
            completedAt TIMESTAMPTZ,
            performedBy TEXT,
            sessionNotes TEXT,
            status TEXT DEFAULT 'scheduled',
            duration TEXT,
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Patient Notes table
        CREATE TABLE IF NOT EXISTS patientNotes (
            id SERIAL PRIMARY KEY,
            patientId TEXT NOT NULL,
            content TEXT NOT NULL,
            authorId TEXT NOT NULL,
            authorName TEXT NOT NULL,
            authorRole TEXT NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            editedAt TIMESTAMPTZ,
            isEdited BOOLEAN DEFAULT FALSE
        );
        
        -- Case Sheet Entries table
        CREATE TABLE IF NOT EXISTS caseSheetEntries (
            id SERIAL PRIMARY KEY,
            patientId TEXT NOT NULL,
            entryType TEXT NOT NULL,
            description TEXT NOT NULL,
            performedBy TEXT NOT NULL,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Admission Recommendations table
        CREATE TABLE IF NOT EXISTS admissionRecommendations (
            id SERIAL PRIMARY KEY,
            patientName TEXT NOT NULL,
            age INTEGER,
            dateOfBirth DATE,
            gender TEXT NOT NULL,
            diagnosis TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'routine',
            department TEXT NOT NULL,
            recommendedWard TEXT NOT NULL,
            assignedDoctor TEXT NOT NULL,
            recommendedBy TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            weight NUMERIC,
            admissionDate DATE,
            insuranceType TEXT,
            emergencyContact TEXT,
            allergies TEXT,
            admissionNotes TEXT,
            processedBy TEXT,
            processedAt TIMESTAMPTZ,
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT check_age_or_dob CHECK (age IS NOT NULL OR dateOfBirth IS NOT NULL)
        );
        
        -- Beds table
        CREATE TABLE IF NOT EXISTS beds (
            id TEXT PRIMARY KEY,
            bedNumber TEXT NOT NULL,
            roomNumber TEXT NOT NULL,
            wardType TEXT NOT NULL,
            department TEXT NOT NULL,
            status TEXT DEFAULT 'available',
            occupiedBy TEXT,
            lastCleaned TIMESTAMPTZ,
            createdAt TIMESTAMPTZ DEFAULT NOW(),
            updatedAt TIMESTAMPTZ DEFAULT NOW()
        );
        """
    
    try:
        async with get_db_connection() as conn:
            # Execute tables creation
            await conn.execute(tables_sql)
            logger.info("✅ Tables created successfully")
            
            # Add migrations for existing tables
            try:
                # Add dateOfBirth column to admissionRecommendations if it doesn't exist
                await conn.execute("""
                    ALTER TABLE admissionRecommendations 
                    ADD COLUMN IF NOT EXISTS dateOfBirth DATE;
                """)
                
                # Modify age column to allow NULL (ignore error if already nullable)
                try:
                    await conn.execute("""
                        ALTER TABLE admissionRecommendations 
                        ALTER COLUMN age DROP NOT NULL;
                    """)
                except:
                    pass  # Column might already be nullable
                
                logger.info("✅ Database migrations completed successfully")
            except Exception as migration_error:
                logger.warning(f"⚠️ Migration warning (may be expected): {migration_error}")
        
        logger.info("✅ Database tables created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise

async def create_timescale_tables():
    """Create TimescaleDB hypertables for vitals data"""
    
    timescale_sql = """
    -- Enable TimescaleDB extension
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
    
    -- Create vitals_timeseries table (using existing schema for compatibility)
    CREATE TABLE IF NOT EXISTS vitals_timeseries (
        time TIMESTAMPTZ NOT NULL,
        patientid TEXT NOT NULL,
        deviceid TEXT NOT NULL,
        vitaltype TEXT NOT NULL,
        value DOUBLE PRECISION,
        unit TEXT,
        quality TEXT DEFAULT 'good',
        rawdata JSONB,
        metadata JSONB
    );
    
    -- Convert to hypertable (only if not already a hypertable)
    SELECT create_hypertable('vitals_timeseries', 'time', if_not_exists => TRUE);
    
    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_vitals_patient_time ON vitals_timeseries (patientid, time);
    CREATE INDEX IF NOT EXISTS idx_vitals_device_time ON vitals_timeseries (deviceid, time);
    CREATE INDEX IF NOT EXISTS idx_vitals_metric ON vitals_timeseries (patientid, vitaltype, time);
    """
    
    try:
        async with get_timescale_connection() as conn:
            await conn.execute(timescale_sql)
            logger.info("✅ TimescaleDB hypertables created successfully")
            
    except Exception as e:
        logger.error(f"❌ Failed to create TimescaleDB tables: {e}")
        logger.warning("⚠️ Continuing without TimescaleDB - vitals storage may be limited")