"""DocuIntel AI — Application settings.

Uses pydantic-settings to read configuration from environment
variables or a .env file in the project root.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the DocuIntel AI backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",          # ignore env vars we don't define
    )

    # ── Application ───────────────────────────────
    PROJECT_NAME: str = "DocuIntel AI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # ── CORS ──────────────────────────────────────
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ── Database (used in later phases) ───────────
    DATABASE_URL: str = (
        "postgresql+psycopg://docuintel:changeme@localhost:5432/docuintel_db"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        """Accept a JSON string or a Python list."""
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v


# Single shared instance — import this everywhere.
settings = Settings()
