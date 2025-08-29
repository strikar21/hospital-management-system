from fastapi import APIRouter
from datetime import datetime

from app.db.database import database

router = APIRouter(prefix="/system")

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    
    try:
        # Test database connection
        await database.fetch_val("SELECT 1")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "timestamp": datetime.now().isoformat(),
            "database": "disconnected",
            "error": str(e)
        }

@router.get("/status")
async def system_status():
    """Get system status"""
    
    return {
        "online": True,
        "lastSync": datetime.now().isoformat(),
        "serverHealth": "healthy",
        "connectedDevices": 12,
        "activeUsers": 3
    }