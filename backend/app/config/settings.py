"""
Central application settings.

All values are sourced from environment variables so the same codebase
works across local development, demo, and production without code changes
(see PRD Section 45 - Environment Configuration).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Environment ---
    ENVIRONMENT: str = "development"

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./s41_dev.db"

    # --- Security ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_this_is_a_dev_only_default_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # --- CORS ---
    # Comma-separated list of allowed origins or "*" for universal frontend access.
    FRONTEND_ORIGINS: str = (
        "*,http://localhost:5173,http://localhost:3000,"
        "http://localhost:5500,http://127.0.0.1:5500"
    )

    # --- AI & LLM Engine Configuration ---
    # Supports Google Gemini, OpenAI, Groq, Anthropic, Ollama, and Local Deterministic Reasoner
    AI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    OLLAMA_BASE_URL: str | None = None  # e.g., "http://localhost:11434"

    AI_PROVIDER: str = "auto"  # "auto", "gemini", "openai", "groq", "ollama", "reasoner"
    AI_MODEL: str | None = None  # default resolved dynamically based on provider
    AI_PROVIDER_MODEL: str = "gemini-1.5-flash"
    AI_TEMPERATURE: float = 0.2
    AI_TIMEOUT_SECONDS: float = 12.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]
        if "*" in origins:
            return ["*"]
        return origins

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def active_gemini_key(self) -> str | None:
        return self.GEMINI_API_KEY or self.AI_API_KEY


settings = Settings()
