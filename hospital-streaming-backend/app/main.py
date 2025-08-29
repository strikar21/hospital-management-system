from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn
from contextlib import asynccontextmanager

from app.api.v1 import devices, streaming, ingestion, health, patients, auth, vitals, staff, provisioning, hospital_admin, device_assignment, admission_workflow, audit, system, mobile, vitals_analytics, discharge, discharge_workflow, discharge_summary_fixed as discharge_summary
from app.core.config import settings
from app.services.mqtt_service import MQTTService
from app.services.websocket_manager import WebSocketManager
from app.db.database import init_db, close_db
from app.middleware.security import SecurityMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global services
mqtt_service = MQTTService()
websocket_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting Hospital Streaming Backend...")
    
    # Initialize database (optional for development)
    try:
        await init_db()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.warning(f"Database connection failed: {e}. Continuing without database for development.")
    
    # Start MQTT service (non-blocking)
    try:
        await mqtt_service.start()
    except Exception as e:
        logger.warning(f"MQTT service failed to start: {e}. Continuing without MQTT.")
    
    # Start vitals simulation for existing patient-device assignments
    try:
        from app.services.vitals_simulator import vitals_simulator
        await vitals_simulator.start_all_simulations()
        logger.info("Vitals simulation service started")
    except Exception as e:
        logger.warning(f"Vitals simulation failed to start: {e}. Continuing without simulation.")
    
    # Make services available to the app
    app.state.mqtt_service = mqtt_service
    app.state.websocket_manager = websocket_manager
    
    logger.info("Backend services initialized successfully")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down Hospital Streaming Backend...")
    
    # Stop vitals simulation
    try:
        from app.services.vitals_simulator import vitals_simulator
        await vitals_simulator.stop_all_simulations()
        logger.info("Vitals simulation stopped")
    except Exception as e:
        logger.warning(f"Failed to stop vitals simulation: {e}")
    
    await mqtt_service.stop()
    try:
        await close_db()
    except Exception as e:
        logger.warning(f"Database cleanup failed: {e}")

app = FastAPI(
    title="Hospital Streaming Backend",
    description="Backend for managing hospital devices and streaming real-time data",
    version="1.0.0",
    lifespan=lifespan
)

# Add comprehensive security middleware
app.add_middleware(SecurityMiddleware, rate_limit_requests=200, rate_limit_window=60)

# Enable CORS for development frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(devices.router, prefix="/api/v1", tags=["devices"])
app.include_router(streaming.router, prefix="/api/v1", tags=["streaming"])
app.include_router(ingestion.router, prefix="/api/v1", tags=["ingestion"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(patients.router, prefix="/api/v1", tags=["patients"])
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
app.include_router(vitals.router, prefix="/api/v1", tags=["vitals"])
app.include_router(staff.router, prefix="/api/v1", tags=["staff"])
app.include_router(provisioning.router, prefix="/api/v1", tags=["provisioning"])
app.include_router(hospital_admin.router, prefix="/api/v1", tags=["hospital-administration"])
app.include_router(device_assignment.router, prefix="/api/v1", tags=["device-assignment"])
app.include_router(admission_workflow.router, prefix="/api/v1/admission", tags=["admission-workflow"])
app.include_router(audit.router, prefix="/api/v1", tags=["audit"])
app.include_router(system.router, prefix="/api/v1", tags=["system"])
app.include_router(mobile.router, prefix="/api/v1", tags=["mobile-tablet"])
app.include_router(vitals_analytics.router, prefix="/api/v1", tags=["vitals-analytics"])
app.include_router(discharge.router, prefix="/api/v1", tags=["discharge"])
app.include_router(discharge_workflow.router, prefix="/api/v1", tags=["discharge-workflow"])
app.include_router(discharge_summary.router, prefix="/api/v1", tags=["discharge-summary"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Hospital Streaming Backend",
        "version": "1.0.1",
        "status": "running"
    }

@app.get("/health")
async def root_health():
    """Root health endpoint for Docker health checks"""
    try:
        from app.db.database import database
        await database.fetch_val("SELECT 1")
        return {"status": "healthy", "service": "hospital-backend"}
    except:
        return {"status": "unhealthy", "service": "hospital-backend"}

@app.websocket("/ws/vitals/{client_id}")
async def websocket_vitals_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time vitals streaming"""
    await websocket_manager.connect(websocket, client_id, "vitals")
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            logger.debug(f"Received from {client_id}: {data}")
    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)

@app.websocket("/ws/alerts/{client_id}")
async def websocket_alerts_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time alerts streaming"""
    await websocket_manager.connect(websocket, client_id, "alerts")
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received from {client_id}: {data}")
    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    ssl_config = {}
    if settings.USE_SSL:
        import os
        ssl_keyfile = os.path.join(os.path.dirname(os.path.dirname(__file__)), settings.SSL_KEY_FILE)
        ssl_certfile = os.path.join(os.path.dirname(os.path.dirname(__file__)), settings.SSL_CERT_FILE)
        ssl_config = {
            "ssl_keyfile": ssl_keyfile,
            "ssl_certfile": ssl_certfile
        }
        logger.info(f"🔒 HTTPS enabled with cert: {ssl_certfile}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info",
        **ssl_config
    )