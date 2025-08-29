import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    
    # SSL/HTTPS Settings
    USE_SSL: bool = True
    SSL_CERT_FILE: str = "ssl/cert.pem"
    SSL_KEY_FILE: str = "ssl/key.pem"
    
    # Database Settings
    DB_USER: str = "hospital_user"
    DB_PASSWORD: str = "secure_password_123"
    DB_HOST: str = "localhost"
    DB_NAME: str = "hospital_streaming"
    DB_PORT: int = 5432
    
    # TimescaleDB Settings
    TIMESCALE_USER: str = "hospital_user"
    TIMESCALE_PASSWORD: str = "secure_timescale_123"
    TIMESCALE_HOST: str = "localhost"
    TIMESCALE_NAME: str = "hospital_vitals"
    TIMESCALE_PORT: int = 5434
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    
    # MQTT
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    
    # JWT
    JWT_SECRET_KEY: str = "6K+VqQxH8J2M9nP3rT7uW0zZ4dF6hK2mN5sV8yB1eI4gL7pR9tX2cF5hK8mQ1sU4"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Device Settings
    DEVICE_HEARTBEAT_INTERVAL: int = 30  # seconds
    DEVICE_OFFLINE_THRESHOLD: int = 90   # seconds
    
    # Streaming Settings
    MAX_WEBSOCKET_CONNECTIONS: int = 1000
    DATA_RETENTION_DAYS: int = 30
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def TIMESCALE_URL(self) -> str:
        """Construct TimescaleDB URL from components"""
        return f"postgresql://{self.TIMESCALE_USER}:{self.TIMESCALE_PASSWORD}@{self.TIMESCALE_HOST}:{self.TIMESCALE_PORT}/{self.TIMESCALE_NAME}"
    
    @property
    def REDIS_URL(self) -> str:
        """Construct Redis URL from components"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()