"""
Application configuration using pydantic-settings.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://chaldeas:chaldeas_dev@127.0.0.1:5432/chaldeas"

    # Environment
    environment: str = "development"
    debug: bool = True

    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "CHALDEAS"

    # AI Keys (for SHEBA/LOGOS)
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # CORS - CHALDEAS fixed ports
    # NOTE: "*" + allow_credentials=True is rejected by browsers. List explicit origins only.
    backend_cors_origins: list[str] = [
        "http://localhost:5200",  # Chaldeas frontend (fixed)
        "http://localhost:5173",
        "http://localhost:3000",
        "https://chaldeas.site",  # Production domain
        "https://www.chaldeas.site",
        "https://chaldeas-frontend-951004107180.asia-northeast3.run.app",  # Cloud Run asia
        "https://chaldeas-frontend-951004107180.us-central1.run.app",  # Cloud Run us
        "https://chaldeas-backend-uh6woizycq-du.a.run.app",  # Backend self
    ]

    class Config:
        env_file = "../.env"  # Load from project root
        extra = "ignore"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
