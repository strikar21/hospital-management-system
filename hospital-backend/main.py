#!/usr/bin/env python3
"""
Hospital Management System Backend
FastAPI application with PostgreSQL database
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import json
import asyncio
import os
from datetime import datetime
import logging

from app.core.config import settings
import pydantic
from pydantic import ConfigDict

# Configure Pydantic to disable auto-camelCase conversion in JSON schemas
import os
os.environ['PYDANTIC_V2_CONFIG_ALIAS_GENERATOR'] = 'none'

# HTTPS/SSL enforcement for production
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Middleware to transform lowercase field names to camelCase for Pydantic compatibility
class FieldNameTransformMiddleware(BaseHTTPMiddleware):
    """Middleware that transforms request field names from lowercase to camelCase"""

    def field_transform_map(self, data):
        """Transform lowercase fields to camelCase for Pydantic compatibility"""
        if not isinstance(data, dict):
            return data

        transformMap = {
            'staffid': 'staffId',
            'nfccardid': 'nfcCardId',
            'resourcetype': 'resourceType',
            'resourceid': 'resourceId',
            'ipaddress': 'ipAddress',
            'useragent': 'userAgent',
            'userid': 'userId'
        }

        transformed = {}
        for key, value in data.items():
            # Use the transform map if available, otherwise keep original
            newKey = transformMap.get(key, key)
            transformed[newKey] = value

        return transformed

    async def dispatch(self, request: Request, callNext):
        # Only transform auth endpoints
        if request.url.path.startswith("/api/v1/auth/login"):
            try:
                # Read and parse the request body
                body = await request.body()
                if body:
                    data = json.loads(body.decode('utf-8'))
                    transformedData = self.field_transform_map(data)

                    # Create a new request with transformed data
                    from starlette.requests import Request as StarletteRequest
                    newBody = json.dumps(transformedData).encode('utf-8')

                    # Replace the request body
                    request._body = newBody

            except (json.JSONDecodeError, Exception) as e:
                # If transformation fails, continue with original request
                pass

        response = await callNext(request)
        return response
from app.core.database import createTables, createTimescaleTables, getDbConnection, seedStaffCredentials
from app.api.v1.auth import router as authRouter
from app.api.v1.audit import router as auditRouter
from app.api.v1.staff import router as staffRouter
from app.api.v1.admission import router as admissionRouter
from app.api.v1.websocket import router as websocketRouter
from app.api.v1.esp32 import router as esp32Router
from app.api.v1.discharge_workflow import router as dischargeWorkflowRouter
from app.api.v1.system_admin import router as systemAdminRouter
from app.api.v1.nursing import router as nursingRouter
from app.api.v1.watch_management import router as watchManagementRouter
from app.api.v1.device_management import router as deviceManagementRouter

# Import v2 repository-based API endpoints
from app.api.v2.patients import router as patientsV2Router
from app.api.v2.medications import router as medicationsV2Router
from app.api.v2.atomic_medical import router as atomicMedicalRouter

# Configure logging with environment-based level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # Default INFO for production
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Hospital Management System API",
    description="Real-time hospital patient monitoring system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Temporarily disable middleware to test hanging issue
# app.add_middleware(FieldNameTransformMiddleware)

# Override the OpenAPI schema generation to prevent camelCase conversion
def customOpenapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi
    openapiSchema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Post-process the schema to convert camelCase back to lowercase
    def fixSchemaFieldNames(schemaDict):
        if isinstance(schemaDict, dict):
            if "properties" in schemaDict:
                properties = schemaDict["properties"]
                newProperties = {}
                for key, value in properties.items():
                    # Convert camelCase back to lowercase
                    if key == "staffId":
                        newKey = "staffid"
                    elif key == "nfcCardId":
                        newKey = "nfccardid"
                    elif key == "resourceType":
                        newKey = "resourcetype"
                    elif key == "resourceId":
                        newKey = "resourceid"
                    elif key == "ipAddress":
                        newKey = "ipaddress"
                    elif key == "userAgent":
                        newKey = "useragent"
                    elif key == "userId":
                        newKey = "userid"
                    else:
                        newKey = key.lower()

                    newProperties[newKey] = fixSchemaFieldNames(value)
                schemaDict["properties"] = newProperties

                # Also fix required fields
                if "required" in schemaDict:
                    newRequired = []
                    for reqField in schemaDict["required"]:
                        if reqField == "staffId":
                            newRequired.append("staffid")
                        elif reqField == "userId":
                            newRequired.append("userid")
                        elif reqField == "resourceType":
                            newRequired.append("resourcetype")
                        else:
                            newRequired.append(reqField.lower())
                    schemaDict["required"] = newRequired

            # Recursively process nested schemas
            for key, value in schemaDict.items():
                schemaDict[key] = fixSchemaFieldNames(value)
        elif isinstance(schemaDict, list):
            return [fixSchemaFieldNames(item) for item in schemaDict]

        return schemaDict

    # Fix the schema
    openapiSchema = fixSchemaFieldNames(openapiSchema)

    app.openapi_schema = openapiSchema
    return app.openapi_schema

app.openapi = customOpenapi

# CORS configuration for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Security Headers Middleware (Production)
if settings.environment == "production":
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

# =====================================================
# GLOBAL EXCEPTION HANDLERS (Day 7)
# =====================================================

from app.core.error_handlers import (
    base_app_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    generic_exception_handler,
    http_exception_handler
)
from app.core.exceptions import BaseAppException
from fastapi.exceptions import RequestValidationError, HTTPException
import asyncpg

# Register exception handlers in order (specific to general)
logger.info("🔄 Registering global exception handlers...")

# Custom app exceptions
app.add_exception_handler(BaseAppException, base_app_exception_handler)
logger.info("✅ BaseAppException handler registered")

# Pydantic validation errors
app.add_exception_handler(RequestValidationError, validation_exception_handler)
logger.info("✅ RequestValidationError handler registered")

# FastAPI HTTP exceptions
app.add_exception_handler(HTTPException, http_exception_handler)
logger.info("✅ HTTPException handler registered")

# Database exceptions
app.add_exception_handler(asyncpg.PostgresError, database_exception_handler)
logger.info("✅ PostgresError handler registered")

# Catch-all for unhandled exceptions
app.add_exception_handler(Exception, generic_exception_handler)
logger.info("✅ Generic exception handler registered (catch-all)")

logger.info("✅ All global exception handlers registered successfully")

# Include API routers - Use settings for consistent API versioning
app.include_router(authRouter, prefix=f"{settings.apiV1Str}/auth", tags=["Authentication"])
app.include_router(auditRouter, prefix=f"{settings.apiV1Str}/audit", tags=["Audit"])
app.include_router(staffRouter, prefix=f"{settings.apiV1Str}/staff", tags=["Staff"])
app.include_router(admissionRouter, prefix=f"{settings.apiV1Str}/admission", tags=["Admissions"])
app.include_router(websocketRouter, prefix=f"{settings.apiV1Str}/ws", tags=["WebSocket"])
app.include_router(esp32Router, prefix=f"{settings.apiV1Str}/esp32", tags=["ESP32 Devices"])
logger.info(f"🔄 Attempting to register discharge workflow router at {settings.apiV1Str}/discharge")
app.include_router(dischargeWorkflowRouter, prefix=f"{settings.apiV1Str}/discharge", tags=["Discharge Workflow"])
logger.info(f"✅ Discharge workflow router registered successfully at {settings.apiV1Str}/discharge")
app.include_router(systemAdminRouter, prefix=f"{settings.apiV1Str}/admin", tags=["System Administration"])
app.include_router(nursingRouter, prefix=f"{settings.apiV1Str}/nursing", tags=["Nursing Dashboard"])
logger.info(f"🔄 Attempting to register watch management router at {settings.apiV1Str}/watchmanagement")
app.include_router(watchManagementRouter, prefix=f"{settings.apiV1Str}/watchmanagement", tags=["Watch Management"])
logger.info(f"✅ Watch management router registered successfully at {settings.apiV1Str}/watchmanagement")
logger.info(f"🔄 Attempting to register device management router at {settings.apiV1Str}/devices")
app.include_router(deviceManagementRouter, prefix=f"{settings.apiV1Str}/devices", tags=["Device Management"])
logger.info(f"✅ Device management router registered successfully at {settings.apiV1Str}/devices")

# Register v2 repository-based API endpoints
logger.info("🔄 Registering v2 repository-based API endpoints...")
app.include_router(patientsV2Router, prefix="/api/v2/patients", tags=["Patients v2 (Repository)"])
app.include_router(medicationsV2Router, prefix="/api/v2/medications", tags=["Medications v2 (Repository)"])
app.include_router(atomicMedicalRouter, prefix="/api/v2", tags=["Atomic Medical Operations"])
logger.info("✅ Patient API registered successfully")
logger.info("✅ Medications API registered successfully")
logger.info("✅ Atomic medical operations API registered successfully (replacing individual APIs)")

@app.on_event("startup")
async def startup_event():
    """Initialize database tables and seed data on startup"""
    logger.info("🚀 Starting Hospital Management System Backend")
    logger.info(f"📊 Database: {settings.databaseUrl}")
    
    try:
        # Create PostgreSQL database tables
        await createTables()
        logger.info("✅ PostgreSQL database tables created successfully")

        # Create TimescaleDB hypertables
        await createTimescaleTables()
        logger.info("✅ TimescaleDB hypertables created successfully")

        # Seed staff credentials for authentication
        await seedStaffCredentials()
        logger.info("✅ Staff credentials seeded successfully")
        
        # Start WebSocket keepalive task
        from app.services.websocket_manager import startKeepaliveTask
        startKeepaliveTask()
        logger.info("✅ WebSocket services initialized")
        
        # Re-enable MQTT and watch monitoring services
        logger.info("🔄 Starting real-time services...")

        # Start MQTT service for ESP32 direct communication
        try:
            from app.services.mqtt_service import mqtt_service
            mqttStarted = await mqtt_service.start()
            if mqttStarted:
                logger.info("✅ MQTT service started - ESP32 watches can connect directly")
            else:
                logger.warning("⚠️ MQTT service failed to start - ESP32 watches will need display relay")
        except ImportError:
            logger.warning("⚠️ MQTT service not available - ESP32 watches will need display relay")
        except Exception as e:
            logger.error(f"❌ MQTT service startup error: {e}")

        # Start watch monitoring service for disconnect detection and alerts
        try:
            from app.services.watch_monitor import watch_monitor
            await watch_monitor.start()
            logger.info("✅ Watch monitoring service started - disconnect detection active")
        except ImportError:
            logger.warning("⚠️ Watch monitoring service not available")
        except Exception as e:
            logger.error(f"❌ Watch monitoring service startup error: {e}")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down Hospital Management System Backend")
    
    # Stop MQTT service
    try:
        from app.services.mqtt_service import mqtt_service
        await mqtt_service.stop()
        logger.info("✅ MQTT service stopped")
    except ImportError:
        pass  # Service not available
    except Exception as e:
        logger.error(f"Error stopping MQTT service: {e}")

    # Stop watch monitoring service
    try:
        from app.services.watch_monitor import watch_monitor
        await watch_monitor.stop()
        logger.info("✅ Watch monitoring service stopped")
    except ImportError:
        pass  # Service not available
    except Exception as e:
        logger.error(f"Error stopping watch monitor service: {e}")

@app.get("/health")
async def healthCheck():
    """Health check endpoint"""
    try:
        # Test database connection
        async with getDbConnection() as conn:
            result = await conn.fetchval("SELECT 1")
        
        return JSONResponse({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "version": "1.0.0"
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/working-patients")
async def getPatientsWorking():
    """Working patients list endpoint - bypasses problematic router"""
    try:
        async with getDbConnection() as conn:
            rows = await conn.fetch("SELECT * FROM patients ORDER BY \"createdAt\" DESC LIMIT 100")
            patients = []
            for row in rows:
                patientDict = dict(row)
                # Convert date/datetime objects to ISO strings for JSON serialization
                if patientDict.get('dateOfBirth'):
                    patientDict['dateOfBirth'] = patientDict['dateOfBirth'].isoformat()
                if patientDict.get('admissionDate'):
                    patientDict['admissionDate'] = patientDict['admissionDate'].isoformat()
                if patientDict.get('dischargeDate'):
                    patientDict['dischargeDate'] = patientDict['dischargeDate'].isoformat()
                if patientDict.get('createdAt'):
                    patientDict['createdAt'] = patientDict['createdAt'].isoformat()
                if patientDict.get('updatedAt'):
                    patientDict['updatedAt'] = patientDict['updatedAt'].isoformat()
                patients.append(patientDict)
            return JSONResponse(content={"patients": patients, "count": len(patients), "status": "success"})
    except Exception as e:
        return JSONResponse(content={"error": str(e), "status": "error"}, status_code=500)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Hospital Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    # Run the application
    # HTTPS/SSL Configuration
    ssl_config = {}
    if settings.enableSsl and settings.sslCertPath and settings.sslKeyPath:
        if os.path.exists(settings.sslCertPath) and os.path.exists(settings.sslKeyPath):
            ssl_config = {
                "ssl_certfile": settings.sslCertPath,
                "ssl_keyfile": settings.sslKeyPath
            }
            logger.info(f"🔒 HTTPS enabled with SSL certificate: {settings.sslCertPath}")
        else:
            logger.warning("⚠️ SSL paths configured but files not found - running HTTP")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info",
        **ssl_config
    )