"""
Centralized application configuration.

All configuration is loaded from environment variables (see .env.example).
Nothing sensitive is ever hard-coded here — this module only defines names,
types, and safe defaults for local development.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "JobPilot AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api"

    # Security
    SECRET_KEY: str = "change-me-dev-secret-key"
    JWT_SECRET: str = "change-me-dev-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
        # Database
    DATABASE_URL: str = "postgresql+asyncpg://jobpilot:jobpilot@localhost:5432/jobpilot"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://jobpilot:jobpilot@localhost:5432/jobpilot"

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def _ensure_asyncpg_driver(cls, v: str) -> str:
        # Managed Postgres providers (Render, Railway, Heroku, ...) hand you
        # a bare postgres:// or postgresql:// connection string with no
        # driver -- SQLAlchemy needs +asyncpg/+psycopg2 or it errors.
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    @field_validator("DATABASE_URL_SYNC", mode="after")
    @classmethod
    def _ensure_psycopg2_driver(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return "postgresql+psycopg2://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            return "postgresql+psycopg2://" + v[len("postgresql://"):]
        return v

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery — eager mode runs tasks synchronously in-process (used by the
    # test suite and any environment without a separate worker process).
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # AI abstraction layer
    AI_PROVIDER: str = "mock"
    AI_API_KEY: str = ""
    AI_MODEL: str = "gpt-4o-mini"

    # Email
    EMAIL_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@jobpilot.ai"

    # Storage
    STORAGE_URL: str = "./storage"
    STORAGE_BACKEND: str = "local"

    # Phase 8: base URL browser automation uses to reach this same
    # backend's mock application-form server (app/api/mock_forms.py).
    # Never anything but this backend's own address — automation in this
    # build only ever targets forms it serves itself (spec section 6/51).
    MOCK_FORM_BASE_URL: str = "http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings are cached so env parsing happens once per process."""
    return Settings()


settings = get_settings()
