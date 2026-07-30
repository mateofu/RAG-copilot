from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RAG_COPILOT_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "RAG Copilot API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False

    database_url: str = Field(default="postgresql+psycopg://rag:rag@localhost:5432/rag_copilot")
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    readiness_timeout_seconds: float = Field(default=2.0, gt=0, le=10)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
