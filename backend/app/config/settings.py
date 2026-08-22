"""
Central application settings.

All values are sourced from environment variables so the same codebase
works across local development, demo, and production without code changes
(see PRD Section 45 - Environment Configuration).

Never hard-code secrets here. Defaults are provided ONLY for local/demo
convenience and must be overridden in production via a real .env file
or platform environment variables.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Environment ---
    ENVIRONMENT: str = "development"  # development | staging | production

    # --- Database ---
    # Preferred: PostgreSQL in production. SQLite is acceptable for the
    # hackathon prototype/demo (PRD Section 6).
    DATABASE_URL: str = "sqlite:///./s41_dev.db"

    # --- Security ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_this_is_a_dev_only_default_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # --- CORS ---
    # Comma-separated list of allowed origins for the frontend.
    FRONTEND_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # --- Optional AI/LLM ---
    # Used ONLY for natural-language explanation phrasing (PRD Section 6/19).
    # The assistant and credit-readiness engine MUST work correctly without
    # this key set at all (PRD Section 34 - ML/AI Should Be Modular).
    AI_API_KEY: str | None = None
    AI_PROVIDER_MODEL: str = "claude-sonnet-4-6"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()
