from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    max_execution_seconds: int = 30
    memory_limit_mb: int = 512
    cpu_limit: float = 1.0
    max_retry_attempts: int = 3
    network_enabled: bool = False
    llm_model: str = "gpt-5"

    model_config = SettingsConfigDict(env_prefix="AGENT_")


settings = Settings()
