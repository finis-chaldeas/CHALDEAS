"""
Application configuration using pydantic-settings.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


# Default CORS origins (used when CORS_ORIGINS env var is not set)
_DEFAULT_CORS_ORIGINS = [
    "http://localhost:5200",
    "http://localhost:5173",
    "http://localhost:3000",
    "https://chaldeas.site",
    "https://www.chaldeas.site",
    "https://chaldeas-frontend-951004107180.asia-northeast3.run.app",
    "https://chaldeas-frontend-951004107180.us-central1.run.app",
    "https://chaldeas-backend-uh6woizycq-du.a.run.app",
]


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

    # CORS — set CORS_ORIGINS env var as comma-separated list to override defaults.
    # Example: CORS_ORIGINS=https://chaldeas.site,https://www.chaldeas.site
    cors_origins: list[str] = _DEFAULT_CORS_ORIGINS

    class Config:
        env_file = "../.env"  # Load from project root
        extra = "ignore"
        case_sensitive = False

    @property
    def effective_cors_origins(self) -> list[str]:
        """Return CORS origins, stripping whitespace from each entry."""
        return [o.strip() for o in self.cors_origins if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
