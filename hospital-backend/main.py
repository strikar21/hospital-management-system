#!/usr/bin/env python3
"""
Hospital Management System Backend
FastAPI application with PostgreSQL database
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import os
from datetime import datetime
import logging

from app.core.config import settings
from app.core.database import create_tables, create_timescale_tables, get_db_connection
from app.api.v1.auth import router as auth_router
from app.api.v1.patients import router as patients_router
from app.api.v1.staff import router as staff_router
from app.api.v1.admission import router as admission_router
from app.api.v1.websocket import router as websocket_router
from app.api.v1.esp32 import router as esp32_router
from app.api.v1.discharge_workflow import router as discharge_workflow_router
from app.api.v1.audit import router as audit_router
from app.api.v1.nursing import router as nursing_router
from app.api.v1.medication_administration import router as medication_administration_router
from app.api.v1.therapy_sessions import router as therapy_sessions_router
from app.api.v1.watch_management import router as watch_management_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Hospital Management System API",
    description="Real-time hospital patient monitoring system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React frontend
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Include API routers - Use settings for consistent API versioning
app.include_router(auth_router, prefix=f"{settings.api_v1_str}/auth", tags=["Authentication"])
app.include_router(patients_router, prefix=f"{settings.api_v1_str}/patients", tags=["Patients"])
app.include_router(staff_router, prefix=f"{settings.api_v1_str}/staff", tags=["Staff"])
app.include_router(admission_router, prefix=f"{settings.api_v1_str}/admission", tags=["Admissions"])
app.include_router(websocket_router, prefix=f"{settings.api_v1_str}/ws", tags=["WebSocket"])
app.include_router(esp32_router, prefix=f"{settings.api_v1_str}/esp32", tags=["ESP32 Devices"])
logger.info(f"🔄 Attempting to register discharge workflow router at {settings.api_v1_str}/discharge-workflow")
app.include_router(discharge_workflow_router, prefix=f"{settings.api_v1_str}/discharge-workflow", tags=["Discharge Workflow"])
logger.info(f"✅ Discharge workflow router registered successfully at {settings.api_v1_str}/discharge-workflow")
app.include_router(audit_router, prefix=f"{settings.api_v1_str}/audit", tags=["Audit Logging"])
app.include_router(nursing_router, prefix=f"{settings.api_v1_str}/nursing", tags=["Nursing Dashboard"])
app.include_router(medication_administration_router, prefix=f"{settings.api_v1_str}/medication-administration", tags=["Medication Administration"])
app.include_router(therapy_sessions_router, prefix=f"{settings.api_v1_str}/therapy-sessions", tags=["Therapy Sessions"])
logger.info(f"🔄 Attempting to register watch management router at {settings.api_v1_str}/watch-management")
app.include_router(watch_management_router, prefix=f"{settings.api_v1_str}/watch-management", tags=["Watch Management"])
logger.info(f"✅ Watch management router registered successfully at {settings.api_v1_str}/watch-management")

@app.on_event("startup")
async def startup_event():
    """Initialize database tables and seed data on startup"""
    logger.info("🚀 Starting Hospital Management System Backend")
    logger.info(f"📊 Database: {settings.database_url}")
    
    try:
        # Create PostgreSQL database tables
        await create_tables()
        logger.info("✅ PostgreSQL database tables created successfully")
        
        # Create TimescaleDB hypertables
        await create_timescale_tables()
        logger.info("✅ TimescaleDB hypertables created successfully")
        
        # Initial data seeding removed
        
        # Start WebSocket keepalive task
        from app.services.websocket_manager import start_keepalive_task
        start_keepalive_task()
        logger.info("✅ WebSocket services initialized")
        
        # Temporarily disable MQTT and watch monitoring services for debugging
        logger.info("⚠️ MQTT and watch monitoring services disabled for debugging")

        # # Start MQTT service for ESP32 direct communication
        # from app.services.mqtt_service import mqtt_service
        # mqtt_started = await mqtt_service.start()
        # if mqtt_started:
        #     logger.info("✅ MQTT service started - ESP32 watches can connect directly")
        # else:
        #     logger.warning("⚠️ MQTT service failed to start - ESP32 watches will need display relay")

        # # Start watch monitoring service for disconnect detection and alerts
        # from app.services.watch_monitor import watch_monitor
        # await watch_monitor.start()
        # logger.info("✅ Watch monitoring service started - disconnect detection active")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down Hospital Management System Backend")
    
    # # Stop MQTT service
    # try:
    #     from app.services.mqtt_service import mqtt_service
    #     await mqtt_service.stop()
    # except Exception as e:
    #     logger.error(f"Error stopping MQTT service: {e}")

    # # Stop watch monitoring service
    # try:
    #     from app.services.watch_monitor import watch_monitor
    #     await watch_monitor.stop()
    # except Exception as e:
    #     logger.error(f"Error stopping watch monitor service: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        async with get_db_connection() as conn:
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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,  # Standard port as per CLAUDE.md specifications
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )