"""
Configuration settings for the Hospital Management System
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Database configuration
    database_url: str = "postgresql://hospital_user:hospital_pass@localhost:5432/hospital_db"
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "hospital_db" 
    database_user: str = "hospital_user"
    database_password: str = "hospital_pass"
    
    # TimescaleDB configuration for vitals data
    timescaledb_url: str = "postgresql://hospital_user:hospital_pass@localhost:5433/hospital_timescale"
    timescaledb_host: str = "localhost"
    timescaledb_port: int = 5433
    timescaledb_name: str = "hospital_timescale"
    timescaledb_user: str = "hospital_user"
    timescaledb_password: str = "hospital_pass"
    
    # PostgreSQL only - no SQLite support
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API Settings
    api_v1_str: str = "/api/v1"
    project_name: str = "Hospital Management System"
    
    # CORS
    backend_cors_origins: list = ["http://localhost:3000"]
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()