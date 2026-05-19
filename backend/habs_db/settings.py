"""
HABS — Application Settings
Reads from environment variables / .env file.
"""

from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── Postgres ──
    POSTGRES_USER:     str = "habs"
    POSTGRES_PASSWORD: str = "habs_secret"
    POSTGRES_HOST:     str = "localhost"
    POSTGRES_PORT:     int = 5432
    POSTGRES_DB:       str = "habs_db"

    # ── Pool ──
    DB_POOL_SIZE:     int  = 10
    DB_MAX_OVERFLOW:  int  = 20
    DB_POOL_RECYCLE:  int  = 3600    # seconds
    DB_ECHO:          bool = False

    # ── Misc ──
    TESTING: bool = False
    SECRET_KEY: str = "habs_local_secret_change_me"

    # ── ML Model ──
    ML_MODEL_PATH:    str   = "model/habs_noshow_model_v1.joblib"
    ML_MODEL_VERSION: str   = "habs_noshow_v1"
    ML_THRESHOLD:     float = 0.4

    # ── Frontend ──
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # ── Email & Security ──
    DOCTOR_INVITE_CODE: str = "HABS-DOCTOR-2026"  
    RESEND_API_KEY: str = ""
    EMAIL_HOST: str = "smtp-relay.brevo.com"
    EMAIL_PORT: int = 587
    EMAIL_USER: str = "ab8ef2001@smtp-brevo.com"
    EMAIL_PASSWORD: str = "4yKdkX2zahDI8bBn"
    EMAIL_FROM: str = ""

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Used by Alembic (sync driver)."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
