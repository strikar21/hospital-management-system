"""
Configuration settings for the Hospital Management System - SECURE VERSION
NO HARDCODED SECRETS - All sensitive values must come from environment variables
"""

import os
import sys
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings - All sensitive values REQUIRED from environment"""

    # ============================================
    # DATABASE CONFIGURATION - REQUIRED
    # ============================================

    # Primary database URL (PostgreSQL)
    databaseUrl: str

    # Alternative: Individual database components (if not using full URL)
    databaseHost: str = "localhost"
    databasePort: int = 5432
    databaseName: str = "hospitaldb"
    databaseUser: str = "hospital_user"
    databasePassword: str  # REQUIRED - no default

    # ============================================
    # TIMESCALEDB CONFIGURATION - REQUIRED
    # ============================================

    # TimescaleDB for vitals time-series data
    timescaledbUrl: str

    # Alternative: Individual components
    timescaledbHost: str = "localhost"
    timescaledbPort: int = 5433
    timescaledbName: str = "hospitaltimescale"
    timescaledbUser: str = "hospital_user"
    timescaledbPassword: str  # REQUIRED - no default

    # ============================================
    # SECURITY CONFIGURATION - REQUIRED
    # ============================================

    # JWT Secret Key - MUST be at least 32 characters
    secretKey: str  # REQUIRED - no default
    algorithm: str = "HS256"
    accessTokenExpireMinutes: int = 30

    # ============================================
    # API SETTINGS - Optional Defaults
    # ============================================

    apiV1Str: str = "/api/v1"
    projectName: str = "Hospital Management System"

    # ============================================
    # CORS CONFIGURATION
    # ============================================

    backendCorsOrigins: List[str] = ["http://localhost:3000"]

    # ============================================
    # LOGGING CONFIGURATION
    # ============================================

    logLevel: str = "INFO"

    # ============================================
    # ENVIRONMENT FLAGS
    # ============================================

    debug: bool = False
    testing: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Validate that all required fields are provided
        validate_assignment = True


def get_settings() -> Settings:
    """
    Get settings with validation
    Fails fast if required environment variables are missing
    """
    try:
        settings = Settings()

        # Additional validation for secret key length
        if len(settings.secretKey) < 32:
            print("ERROR: SECRET_KEY must be at least 32 characters long")
            sys.exit(1)

        return settings

    except Exception as e:
        print("=" * 80)
        print("CONFIGURATION ERROR")
        print("=" * 80)
        print("\nFailed to load configuration. Missing required environment variables.")
        print("\nPlease ensure you have:")
        print("  1. Created a .env file in the hospital-backend directory")
        print("  2. Copied values from .env.example")
        print("  3. Updated all placeholder values with real secrets")
        print("\nRequired environment variables:")
        print("  - DATABASE_URL or DATABASE_PASSWORD")
        print("  - TIMESCALEDB_URL or TIMESCALEDB_PASSWORD")
        print("  - SECRET_KEY (minimum 32 characters)")
        print("\nError details:", str(e))
        print("=" * 80)
        sys.exit(1)


# Global settings instance
try:
    settings = get_settings()
except SystemExit:
    # Re-raise to ensure application stops
    raise
except Exception as e:
    print(f"CRITICAL: Failed to initialize settings: {e}")
    sys.exit(1)
