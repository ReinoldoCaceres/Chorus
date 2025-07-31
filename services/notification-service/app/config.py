from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Application settings
    app_name: str = "Notification Service API"
    debug: bool = Field(default=False, env="DEBUG")
    api_v1_str: str = "/api/v1"
    
    # Database settings
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/chorus_notifications",
        env="DATABASE_URL"
    )
    
    # Redis settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    
    # Celery settings
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_RESULT_BACKEND"
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
    
    # Email settings (SendGrid)
    sendgrid_api_key: str = Field(
        default="",
        env="SENDGRID_API_KEY"
    )
    sendgrid_from_email: str = Field(
        default="noreply@chorus.example.com",
        env="SENDGRID_FROM_EMAIL"
    )
    
    # SMS settings (Twilio)
    twilio_account_sid: str = Field(
        default="",
        env="TWILIO_ACCOUNT_SID"
    )
    twilio_auth_token: str = Field(
        default="",
        env="TWILIO_AUTH_TOKEN"
    )
    twilio_from_number: str = Field(
        default="",
        env="TWILIO_FROM_NUMBER"
    )
    
    # Notification settings
    max_retry_attempts: int = Field(
        default=3,
        env="MAX_RETRY_ATTEMPTS"
    )
    retry_delay_seconds: int = Field(
        default=60,
        env="RETRY_DELAY_SECONDS"
    )
    notification_batch_size: int = Field(
        default=100,
        env="NOTIFICATION_BATCH_SIZE"
    )
    
    # Template settings
    template_cache_ttl: int = Field(
        default=3600,  # 1 hour
        env="TEMPLATE_CACHE_TTL"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()