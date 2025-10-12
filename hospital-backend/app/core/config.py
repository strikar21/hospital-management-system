"""
Configuration settings for the Hospital Management System
"""

import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings"""

    # Database configuration - Updated for hospital_user compatibility
    databaseUrl: str = Field(default="postgresql://hospital_user:hospital123@localhost:5432/hospitaldb", validation_alias="DATABASE_URL")
    databaseHost: str = Field(default="localhost", validation_alias="DATABASE_HOST")
    databasePort: int = Field(default=5432, validation_alias="DATABASE_PORT")
    databaseName: str = Field(default="hospitaldb", validation_alias="DATABASE_NAME")
    databaseUser: str = Field(default="hospital_user", validation_alias="DATABASE_USER")
    databasePassword: str = Field(default="hospital123", validation_alias="DATABASE_PASSWORD")

    # TimescaleDB configuration for vitals data
    timescaledbUrl: str = Field(default="postgresql://hospital_user:hospital123@localhost:5432/hospitaldb", validation_alias="TIMESCALEDB_URL")
    timescaledbHost: str = Field(default="localhost", validation_alias="TIMESCALEDB_HOST")
    timescaledbPort: int = Field(default=5432, validation_alias="TIMESCALEDB_PORT")
    timescaledbName: str = Field(default="hospitaldb", validation_alias="TIMESCALEDB_NAME")
    timescaledbUser: str = Field(default="hospital_user", validation_alias="TIMESCALEDB_USER")
    timescaledbPassword: str = Field(default="hospital123", validation_alias="TIMESCALEDB_PASSWORD")

    # PostgreSQL only - no SQLite support

    # Security
    secretKey: str = Field(default="HSM-2024-SecureKey-ChangeInProd-V1.0", validation_alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    accessTokenExpireMinutes: int = Field(default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # API Settings
    apiV1Str: str = Field(default="/api/v1", validation_alias="API_V1_STR")
    projectName: str = Field(default="Hospital Management System", validation_alias="PROJECT_NAME")

    # CORS
    backendCorsOrigins: List[str] = Field(default=["http://localhost:3000"], validation_alias="BACKEND_CORS_ORIGINS")

    # Logging
    logLevel: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # Environment
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    testing: bool = Field(default=False, validation_alias="TESTING")

    # HTTPS/SSL Configuration
    sslCertPath: Optional[str] = Field(default=None, validation_alias="SSL_CERT_PATH")
    sslKeyPath: Optional[str] = Field(default=None, validation_alias="SSL_KEY_PATH")
    forceHttps: bool = Field(default=False, validation_alias="FORCE_HTTPS")
    enableSsl: bool = Field(default=False, validation_alias="ENABLE_SSL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra fields from .env
    )

# Global settings instance
settings = Settings()