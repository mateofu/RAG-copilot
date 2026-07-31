from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
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
    public_registration_enabled: bool = False
    jwt_secret: SecretStr | None = None
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "rag-copilot"
    jwt_audience: str = "rag-copilot-api"
    access_token_ttl_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_ttl_days: int = Field(default=30, ge=1, le=90)
    document_storage_path: Path = Path("data/documents")
    max_document_size_bytes: int = Field(
        default=25 * 1024 * 1024,
        ge=1024,
        le=100 * 1024 * 1024,
    )
    embedding_provider: Literal["hashing", "ollama"] = "ollama"
    embedding_model: str = Field(default="bge-m3", min_length=1, max_length=128)
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout_seconds: float = Field(default=120.0, gt=0, le=300)
    chat_model: str = Field(default="qwen2.5:1.5b", min_length=1, max_length=128)
    chat_timeout_seconds: float = Field(default=180.0, gt=0, le=600)
    chat_max_output_tokens: int = Field(default=512, ge=32, le=4096)
    chat_max_concurrency: int = Field(default=1, ge=1, le=8)
    retrieval_limit: int = Field(default=5, ge=1, le=20)
    max_context_characters: int = Field(default=12_000, ge=1000, le=100_000)
    conversation_max_turns: int = Field(default=20, ge=1, le=100)
    conversation_history_messages: int = Field(default=10, ge=2, le=50)
    max_history_characters: int = Field(default=8_000, ge=500, le=50_000)

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if not self.is_production:
            return self

        if self.jwt_secret is None:
            raise ValueError("RAG_COPILOT_JWT_SECRET is required in production")
        secret = self.jwt_secret.get_secret_value()
        if len(secret) < 32 or secret.startswith("replace-"):
            raise ValueError("RAG_COPILOT_JWT_SECRET must be a strong production secret")
        if self.debug:
            raise ValueError("DEBUG cannot be enabled in production")
        if self.public_registration_enabled:
            raise ValueError("public registration must be disabled in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
