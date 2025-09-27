"""
Configuration settings for the Hospital Management System
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Database configuration - Updated for hospital_user compatibility
    databaseUrl: str = os.environ.get("DATABASE_URL", "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb")
    databaseHost: str = os.environ.get("DATABASE_HOST", "localhost")
    databasePort: int = int(os.environ.get("DATABASE_PORT", "5432"))
    databaseName: str = os.environ.get("DATABASE_NAME", "hospitaldb")
    databaseUser: str = os.environ.get("DATABASE_USER", "hospital_user")
    databasePassword: str = os.environ.get("DATABASE_PASSWORD", "hospital123")

    # TimescaleDB configuration for vitals data
    timescaledbUrl: str = os.environ.get("TIMESCALEDB_URL", "postgresql://hospital_user:hospital123@localhost:5433/hospitaltimescale")
    timescaledbHost: str = os.environ.get("TIMESCALEDB_HOST", "localhost")
    timescaledbPort: int = int(os.environ.get("TIMESCALEDB_PORT", "5433"))
    timescaledbName: str = os.environ.get("TIMESCALEDB_NAME", "hospitaltimescale")
    timescaledbUser: str = os.environ.get("TIMESCALEDB_USER", "hospital_user")
    timescaledbPassword: str = os.environ.get("TIMESCALEDB_PASSWORD", "hospital123")

    # PostgreSQL only - no SQLite support
    
    # Security
    secretKey: str = os.environ.get("SECRET_KEY", "HSM-2024-SecureKey-ChangeInProd-V1.0")
    algorithm: str = "HS256"
    accessTokenExpireMinutes: int = 30
    
    # API Settings
    apiV1Str: str = "/api/v1"
    projectName: str = "Hospital Management System"
    
    # CORS
    backendCorsOrigins: list = ["http://localhost:3000"]
    
    # Logging
    logLevel: str = "INFO"
    
    class Config:
        envFile = ".env"
        caseSensitive = False

# Global settings instance
settings = Settings()