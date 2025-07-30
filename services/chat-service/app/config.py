from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Application settings
    app_name: str = "Chat Service API"
    debug: bool = Field(default=False, env="DEBUG")
    api_v1_str: str = "/api/v1"
    
    # Database settings
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/chorus_chat",
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()