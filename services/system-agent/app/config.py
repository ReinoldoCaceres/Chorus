from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # Application settings
    app_name: str = "System Agent"
    debug: bool = Field(default=False, env="DEBUG")
    api_v1_str: str = "/api/v1"
    
    # Database settings
    database_url: str = Field(
        default="postgresql+asyncpg://chorus:chorus_password@localhost:5432/chorus",
        env="DATABASE_URL"
    )
    
    # Redis/Celery settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        env="CELERY_RESULT_BACKEND"
    )
    
    # OpenAI settings
    openai_api_key: str = Field(
        default="your-openai-api-key-here",
        env="OPENAI_API_KEY"
    )
    openai_model: str = Field(
        default="gpt-3.5-turbo",
        env="OPENAI_MODEL"
    )
    
    # ChromaDB settings
    chromadb_host: str = Field(
        default="localhost",
        env="CHROMADB_HOST"
    )
    chromadb_port: int = Field(
        default=8000,
        env="CHROMADB_PORT"
    )
    chromadb_persist_directory: str = Field(
        default="./chroma_db",
        env="CHROMADB_PERSIST_DIRECTORY"
    )
    
    # Agent settings
    max_tokens: int = Field(
        default=2000,
        env="MAX_TOKENS"
    )
    agent_temperature: float = Field(
        default=0.7,
        env="AGENT_TEMPERATURE"
    )
    max_context_length: int = Field(
        default=8000,
        env="MAX_CONTEXT_LENGTH"
    )
    
    # Task settings
    max_retries: int = Field(
        default=3,
        env="MAX_RETRIES"
    )
    task_timeout: int = Field(
        default=300,  # 5 minutes
        env="TASK_TIMEOUT"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()