from functools import lru_cache

from pydantic_settings import BaseSettings

PROVIDER_DEFAULTS: dict[str, dict[str, str | None]] = {
    "openai": {"base_url": None, "model": "gpt-4o-mini"},
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-chat"},
    "kimi": {"base_url": "https://api.moonshot.cn/v1", "model": "kimi-latest"},
    "anthropic": {"base_url": None, "model": "claude-opus-4-8"},
}


class Settings(BaseSettings):
    app_name: str = "AI Interview Coach API"
    database_url: str = "sqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"

    # Single-user local mode: no registration/login required; all requests act
    # as a default local account. For personal/offline use only.
    local_mode: bool = False

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # LLM provider: openai | deepseek | kimi | anthropic
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = ""      # empty = provider default
    llm_base_url: str = ""   # empty = provider default endpoint

    # Legacy aliases (still honored when llm_provider=openai)
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
    def resolved_api_key(self) -> str:
        if self.llm_api_key:
            return self.llm_api_key
        if self.llm_provider == "openai":
            return self.openai_api_key  # legacy alias
        return ""

    @property
    def resolved_model(self) -> str:
        if self.llm_model:
            return self.llm_model
        if self.llm_provider == "openai" and self.openai_model:
            return self.openai_model  # legacy alias
        return PROVIDER_DEFAULTS[self.llm_provider]["model"]

    @property
    def resolved_base_url(self) -> str | None:
        return self.llm_base_url or PROVIDER_DEFAULTS[self.llm_provider]["base_url"]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.resolved_api_key) and not self.mock_ai


@lru_cache
def get_settings() -> Settings:
    return Settings()
