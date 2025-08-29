#!/usr/bin/env python3
"""
Hospital Streaming Backend Startup Script
"""

import uvicorn
import sys
import os
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from app.core.config import settings

if __name__ == "__main__":
    print(f"""
Hospital Streaming Backend
===============================
Starting server on {settings.API_HOST}:{settings.API_PORT}
SSL Enabled: {settings.USE_SSL}
Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}
MQTT Broker: {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}
Redis: {settings.REDIS_URL}
===============================
    """)
    
    ssl_config = {}
    if settings.USE_SSL:
        ssl_config = {
            "ssl_keyfile": settings.SSL_KEY_FILE,
            "ssl_certfile": settings.SSL_CERT_FILE
        }
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info",
        access_log=True,
        **ssl_config
    )