from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Application settings
    app_name: str = "Process Monitor API"
    debug: bool = Field(default=False, env="DEBUG")
    api_v1_str: str = "/api/v1"
    
    # Database settings
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/chorus_monitoring",
        env="DATABASE_URL"
    )
    
    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # Security settings
    secret_key: str = Field(
        default="your-secret-key-here",
        env="SECRET_KEY"
    )
    
    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    
    # Monitoring settings
    metrics_collection_interval: int = Field(
        default=30,
        env="METRICS_COLLECTION_INTERVAL"
    )
    
    health_check_interval: int = Field(
        default=60,
        env="HEALTH_CHECK_INTERVAL"
    )
    
    # Service endpoints for health checks
    service_endpoints: dict[str, str] = Field(
        default={
            "websocket-gateway": "http://localhost:8081/health",
            "chat-service": "http://localhost:8000/api/v1/health",
            "presence-service": "http://localhost:8083/health",
            "summary-engine": "http://localhost:8084/api/v1/health",
            "notification-worker": "http://localhost:8085/health",
            "admin-ui": "http://localhost:3000"
        },
        env="SERVICE_ENDPOINTS"
    )
    
    # Alert thresholds
    cpu_alert_threshold: float = Field(default=80.0, env="CPU_ALERT_THRESHOLD")
    memory_alert_threshold: float = Field(default=85.0, env="MEMORY_ALERT_THRESHOLD")
    disk_alert_threshold: float = Field(default=90.0, env="DISK_ALERT_THRESHOLD")
    response_time_alert_threshold: int = Field(default=5000, env="RESPONSE_TIME_ALERT_THRESHOLD")  # ms
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()