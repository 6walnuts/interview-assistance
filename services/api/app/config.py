from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Interview Coach API"
    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # When true (or no API key is set), agents return deterministic mock output
    # so the full loop runs offline and in tests.
    mock_ai: bool = False

    # "docker" (safe, default) or "subprocess" (dev-only, no isolation)
    sandbox_mode: str = "docker"
    sandbox_image: str = "ai-coach-sandbox:latest"
    sandbox_timeout_seconds: int = 10
    sandbox_memory: str = "256m"
    sandbox_cpus: str = "0.5"

    cors_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key) and not self.mock_ai


@lru_cache
def get_settings() -> Settings:
    return Settings()
